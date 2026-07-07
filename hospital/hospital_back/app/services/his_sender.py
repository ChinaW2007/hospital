"""
HIS 处方自动发送服务
定时轮询 HIS 数据库，检测新处方并发送到 ROS WebSocket
支持逐个药品发送，包含药品坐标信息
"""
import asyncio
import json
import time
import pymysql
import websockets
from app.core.config import settings

# HIS 数据库连接配置
HIS_DB_CONFIG = {
    "host": settings.his_mysql_host,
    "port": settings.his_mysql_port,
    "user": settings.his_mysql_user,
    "password": settings.his_mysql_pass,
    "database": settings.his_mysql_db,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# ROS WebSocket 配置
ROS_WS_URL = f"ws://{settings.ros_ws_host}:{settings.ros_ws_port}"
ROS_TOPIC = "/his_sub"
SEND_INTERVAL = 2  # 发送间隔（秒）
POLL_INTERVAL = 2  # 轮询间隔（秒）

# 全局状态
_current_prescription_code = None
_last_sent_code = None
_sender_running = False
_ws_connection = None

# 药品发送相关状态
_medicine_list = []              # 当前处方的药品列表
_current_medicine_index = 0      # 当前发送的药品索引（从0开始）
_medicine_total = 0              # 药品总数
_medicine_send_count = {}        # 每个药品的发送计数器 {medicine_id: count}
_medicine_started = {}           # 药品是否已收到 running-started {medicine_id: True/False}
_all_medicines_completed = False # 所有药品是否完成抓取（收到 all_completed）
_task_completed = False          # 整个任务是否完成（收到 end）

# ===== 新增：发送 end 消息相关状态 =====
_medicine_need_send_end = False  # 是否需要发送 end 消息（在切换药品前）
_medicine_end_data = {}          # 需要发送 end 的药品数据

# ===== 修复：防竞态状态标志（必须在模块级定义，否则global声明后读取会NameError）=====
# 此前缺失这4个变量定义，导致 notify_prescription_step5_return() 第一次被调用时
# 抛出 'name _medicine_end_in_progress is not defined'，end流程无法启动，
# 主循环继续发送药品1的running消息，药品2永远拿不到。
_medicine_end_in_progress = False          # end消息正在发送中（防止两次end之间ROS返回的药品级end触发提前切换）
_medicine_end_pending_switch = False        # 两次end都发送完后，等待ROS返回药品级end以触发切换
_medicine_end_medicine_id = None            # 正在等待end确认的药品ID（独立保存，防止_current被清空）
_medicine_end_prescription_code = None      # 正在等待end确认的处方编码（独立保存）


def get_latest_pending_prescription():
    """
    从 HIS 数据库获取最新待处理的处方编码
    
    查询条件：
    - 状态为 pending（医生已开具处方）
    - 按创建时间倒序排列
    - 返回最新的处方编码
    """
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT prescription_code, id, created_at
                FROM prescriptions
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                prescription_code = result["prescription_code"]
                print(f"[HIS Sender] 获取到最新处方: {prescription_code}")
                return prescription_code
            else:
                return None
    except Exception as e:
        print(f"[HIS Sender] 查询 HIS 数据库失败: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_prescription_medicine_locations(prescription_code: str) -> list:
    """
    根据处方编码查询该处方开具的所有药品的坐标
    
    查询路径：
    prescriptions -> prescription_items -> medicine_locations
    
    返回：
    [
        {"medicine_id": 1, "x": 10.5, "y": 20.3, "z": 5.0},
        {"medicine_id": 2, "x": 15.2, "y": 18.7, "z": 3.5},
        ...
    ]
    """
    print("=" * 60)
    print(f"[HIS Sender] 开始查询药品坐标")
    print(f"[HIS Sender] 处方编码: {prescription_code}")
    
    try:
        print(f"[HIS Sender] 正在连接 HIS MySQL...")
        print(f"[HIS Sender] MySQL地址: {settings.his_mysql_host}:{settings.his_mysql_port}")
        print(f"[HIS Sender] MySQL数据库: {settings.his_mysql_db}")
        
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        print(f"[HIS Sender] MySQL连接成功")
        
        with conn.cursor() as cursor:
            # ===== 修复：pymysql 使用 %s 格式，不是 ? =====
            # ===== 修复：使用 GROUP BY 去重，防止 medicine_locations 表中有重复记录 =====
            # 问题：medicine_locations 表中同一个 medicine_id 可能有多条记录
            # 解决：按 pi.medicine_id 分组，每个药品只取第一条坐标记录
            # 注意：数据库字段名是 yaw，不是 yam
            sql_query = """
                SELECT 
                    pi.medicine_id,
                    MIN(ml.x) as x,
                    MIN(ml.y) as y,
                    MIN(ml.z) as z,
                    MIN(ml.yaw) as yaw
                FROM prescriptions p
                JOIN prescription_items pi ON p.id = pi.prescription_id
                JOIN medicine_locations ml ON pi.medicine_id = ml.medicine_id
                WHERE p.prescription_code = %s
                GROUP BY pi.medicine_id
                ORDER BY pi.medicine_id ASC
            """
            print(f"[HIS Sender] 执行SQL查询: {sql_query.strip()}")
            print(f"[HIS Sender] 查询参数: prescription_code={prescription_code}")
            
            cursor.execute(sql_query, (prescription_code,))
            results = cursor.fetchall()
            
            print(f"[HIS Sender] 查询结果数量: {len(results)}")
            
            if results:
                medicine_list = []
                for i, row in enumerate(results):
                    print(f"[HIS Sender] 查询结果{i+1}: medicine_id={row['medicine_id']}, x={row['x']}, y={row['y']}, z={row['z']}, yaw={row['yaw']}")
                    
                    # ===== 修复：检查 medicine_id 是否为 NULL 或 0 =====
                    medicine_id_value = row["medicine_id"]
                    if medicine_id_value is None or medicine_id_value == 0:
                        print(f"[HIS Sender] WARNING: 药品{i+1} 的 medicine_id 为 NULL 或 0，跳过该药品")
                        continue  # 跳过无效药品
                    
                    medicine_list.append({
                        "medicine_id": int(medicine_id_value),  # 确保是整数
                        "x": float(row["x"]) if row["x"] is not None else 0.0,
                        "y": float(row["y"]) if row["y"] is not None else 0.0,
                        "z": float(row["z"]) if row["z"] is not None else 0.0,
                        "yaw": float(row["yaw"]) if row["yaw"] is not None else 0.0
                    })
                print(f"[HIS Sender] 处方 {prescription_code} 包含 {len(medicine_list)} 个药品")
                for i, med in enumerate(medicine_list):
                    print(f"[HIS Sender]   药品{i+1}: ID={med['medicine_id']}, xyz=({med['x']}, {med['y']}, {med['z']}), yaw={med['yaw']}")
                print("=" * 60)
                return medicine_list
            else:
                print(f"[HIS Sender] 处方 {prescription_code} 未找到药品坐标信息")
                print(f"[HIS Sender] 可能原因：")
                print(f"[HIS Sender]   1. prescription_items 表中没有该处方的药品")
                print(f"[HIS Sender]   2. medicine_locations 表中没有对应的坐标")
                print("=" * 60)
                return []
    except pymysql.Error as e:
        print(f"[HIS Sender] MySQL错误: {e}")
        print(f"[HIS Sender] 错误代码: {e.args[0]}")
        print(f"[HIS Sender] 错误信息: {e.args[1]}")
        print("=" * 60)
        return []
    except Exception as e:
        print(f"[HIS Sender] 查询药品坐标失败: {e}")
        print(f"[HIS Sender] 错误类型: {type(e).__name__}")
        print("=" * 60)
        return []
    finally:
        if 'conn' in locals():
            conn.close()
            print(f"[HIS Sender] MySQL连接已关闭")


async def send_medicine_end_to_ros(prescription_code: str, medicine_data: dict, medicine_index: int, medicine_total: int):
    """
    发送药品完成信号（end）到 ROS WebSocket
    
    消息格式：
    {
        "op": "publish",
        "topic": "/his_sub",
        "msg": {
            "data": "end",
            "prescription_code": "处方编码",
            "medicine_id": 药品ID,
            "x": X坐标,
            "y": Y坐标,
            "z": Z坐标,
            "yaw": yaw值,
            "medicine_total": 药品总数,
            "medicine_index": 当前药品序号（从1开始）
        }
    }
    
    发送逻辑：
    - 发送两次 end 消息
    - 每次间隔 2 秒
    - 表示当前药品已完成
    """
    global _ws_connection
    
    try:
        medicine_id = medicine_data["medicine_id"]
        
        # 检查连接是否有效
        need_new_connection = False
        if _ws_connection is None:
            need_new_connection = True
        else:
            try:
                if hasattr(_ws_connection, 'open') and not _ws_connection.open:
                    need_new_connection = True
                elif hasattr(_ws_connection, 'closed') and _ws_connection.closed:
                    need_new_connection = True
            except:
                need_new_connection = True
        
        # 如果需要新连接，创建连接
        if need_new_connection:
            if _ws_connection is not None:
                try:
                    await _ws_connection.close()
                except:
                    pass
            
            _ws_connection = await asyncio.wait_for(
                websockets.connect(ROS_WS_URL),
                timeout=settings.ros_connect_timeout
            )
            
            # 先清除旧的Topic注册
            await _ws_connection.send(json.dumps({
                "op": "unadvertise",
                "topic": ROS_TOPIC
            }))
            await asyncio.sleep(0.1)
            
            # 重新注册 Topic
            await _ws_connection.send(json.dumps({
                "op": "advertise",
                "topic": ROS_TOPIC,
                "type": "his_sub/HisSub"
            }))
            await asyncio.sleep(0.3)
            print("[HIS Sender] Topic 注册成功: /his_sub (his_sub/HisSub)")
        
        # ===== 发送两次 end 消息 =====
        for send_count in range(2):
            message_dict = {
                "op": "publish",
                "topic": ROS_TOPIC,
                "msg": {
                    "data": "end",
                    "prescription_code": prescription_code,
                    "medicine_id": medicine_id,
                    "x": medicine_data["x"],
                    "y": medicine_data["y"],
                    "z": medicine_data["z"],
                    "yaw": medicine_data["yaw"],
                    "medicine_total": medicine_total,
                    "medicine_index": medicine_index  # 从1开始
                }
            }
            message = json.dumps(message_dict)
            
            # ===== 详细日志打印 =====
            print("=" * 60)
            print(f"[HIS Sender] 发送药品完成信号（end）:")
            print(f"[HIS Sender]   发送次数: 第{send_count+1}次（共2次）")
            print(f"[HIS Sender]   data: end")
            print(f"[HIS Sender]   prescription_code: {prescription_code}")
            print(f"[HIS Sender]   medicine_id: {medicine_id}")
            print(f"[HIS Sender]   x: {medicine_data['x']}")
            print(f"[HIS Sender]   y: {medicine_data['y']}")
            print(f"[HIS Sender]   z: {medicine_data['z']}")
            print(f"[HIS Sender]   yaw: {medicine_data['yaw']}")
            print(f"[HIS Sender]   medicine_total: {medicine_total}")
            print(f"[HIS Sender]   medicine_index: {medicine_index}")
            print("=" * 60)
            
            await _ws_connection.send(message)
            
            print(f"[HIS Sender] end 消息发送成功（第{send_count+1}次）")
            
            # ===== 两次发送间隔2秒 =====
            if send_count == 0:  # 第一次发送后，等待2秒
                print(f"[HIS Sender] 等待2秒后发送第二次...")
                await asyncio.sleep(SEND_INTERVAL)
        
        return True
    
    except Exception as e:
        print(f"[HIS Sender] 发送 end 消息失败: {e}")
        import traceback
        traceback.print_exc()
        if _ws_connection:
            try:
                await _ws_connection.close()
            except:
                pass
            _ws_connection = None
        return False


async def check_ros_ws_available():
    """检测 ROS WebSocket 是否可达"""
    try:
        ws = await asyncio.wait_for(
            websockets.connect(ROS_WS_URL),
            timeout=settings.ros_connect_timeout
        )
        await ws.close()
        return True
    except Exception as e:
        print(f"[HIS Sender] ROS WebSocket 不可达: {ROS_WS_URL} - {e}")
        return False


async def send_medicine_to_ros(prescription_code: str, medicine_data: dict, medicine_index: int, medicine_total: int):
    """
    发送单个药品坐标到 ROS WebSocket
    
    消息格式：
    {
        "op": "publish",
        "topic": "/his_sub",
        "msg": {
            "data": "start" 或 "running",
            "prescription_code": "处方编码",
            "medicine_id": 药品ID,
            "x": X坐标,
            "y": Y坐标,
            "z": Z坐标,
            "medicine_total": 药品总数,
            "medicine_index": 当前药品序号（从1开始）
        }
    }
    
    发送逻辑：
    - 如果药品已收到 running-started，发送 running
    - 否则发送 start
    """
    global _ws_connection, _medicine_send_count, _medicine_started
    
    try:
        medicine_id = medicine_data["medicine_id"]
        
        # ===== 修改：使用 _medicine_started 状态判断发送 start 还是 running =====
        # 逻辑：
        # - 如果药品已收到 running-started，发送 running
        # - 否则发送 start
        
        # ===== 新增：打印完整的 _medicine_started 状态 =====
        print(f"[HIS Sender] 判断发送状态:")
        print(f"[HIS Sender]   当前药品ID: {medicine_id}")
        print(f"[HIS Sender]   _medicine_started 完整状态: {_medicine_started}")
        print(f"[HIS Sender]   _medicine_started.get({medicine_id}, False): {_medicine_started.get(medicine_id, False)}")
        
        is_started = _medicine_started.get(medicine_id, False)
        
        print(f"[HIS Sender]   is_started 结果: {is_started}")
        
        if is_started:
            data = "running"  # 药品已收到 running-started
            print(f"[HIS Sender]   决定发送: running")
        else:
            data = "start"    # 药品未收到 running-started，继续发送 start
            print(f"[HIS Sender]   决定发送: start")
        
        # 检查连接是否有效
        need_new_connection = False
        if _ws_connection is None:
            need_new_connection = True
        else:
            try:
                if hasattr(_ws_connection, 'open') and not _ws_connection.open:
                    need_new_connection = True
                elif hasattr(_ws_connection, 'closed') and _ws_connection.closed:
                    need_new_connection = True
            except:
                need_new_connection = True
        
        # 如果需要新连接，创建连接
        if need_new_connection:
            if _ws_connection is not None:
                try:
                    await _ws_connection.close()
                except:
                    pass
            
            _ws_connection = await asyncio.wait_for(
                websockets.connect(ROS_WS_URL),
                timeout=settings.ros_connect_timeout
            )
            
            # 先清除旧的Topic注册
            await _ws_connection.send(json.dumps({
                "op": "unadvertise",
                "topic": ROS_TOPIC
            }))
            await asyncio.sleep(0.1)
            
            # 重新注册 Topic
            await _ws_connection.send(json.dumps({
                "op": "advertise",
                "topic": ROS_TOPIC,
                "type": "his_sub/HisSub"
            }))
            await asyncio.sleep(0.3)
            print("[HIS Sender] Topic 注册成功: /his_sub (his_sub/HisSub)")
        
        # 发送药品坐标
        message_dict = {
            "op": "publish",
            "topic": ROS_TOPIC,
            "msg": {
                "data": data,
                "prescription_code": prescription_code,
                "medicine_id": medicine_id,
                "x": medicine_data["x"],
                "y": medicine_data["y"],
                "z": medicine_data["z"],
                "yaw": medicine_data["yaw"],
                "medicine_total": medicine_total,
                "medicine_index": medicine_index  # 从1开始
            }
        }
        message = json.dumps(message_dict)
        
        # ===== 详细日志打印 =====
        print("=" * 60)
        print(f"[HIS Sender] 发送药品坐标消息:")
        print(f"[HIS Sender]   data: {data}")
        print(f"[HIS Sender]   prescription_code: {prescription_code}")
        print(f"[HIS Sender]   medicine_id: {medicine_id}")
        print(f"[HIS Sender]   x: {medicine_data['x']}")
        print(f"[HIS Sender]   y: {medicine_data['y']}")
        print(f"[HIS Sender]   z: {medicine_data['z']}")
        print(f"[HIS Sender]   yaw: {medicine_data['yaw']}")
        print(f"[HIS Sender]   medicine_total: {medicine_total}")
        print(f"[HIS Sender]   medicine_index: {medicine_index}")
        print(f"[HIS Sender]   药品状态: {'已收到running-started' if is_started else '未收到running-started，发送start'}")
        print("=" * 60)
        
        await _ws_connection.send(message)
        
        return True
    
    except Exception as e:
        print(f"[HIS Sender] 发送失败: {e}")
        if _ws_connection:
            try:
                await _ws_connection.close()
            except:
                pass
            _ws_connection = None
        return False


def reset_medicine_state(prescription_code: str):
    """
    重置药品发送状态（新处方时调用）
    
    重置内容：
    - 获取新处方的药品列表
    - 重置当前药品索引为0
    - 计算药品总数
    - 初始化每个药品的发送计数器为0
    - 重置完成标志为False
    
    如果药品列表为空，设置 _medicine_total=0，停止发送
    """
    global _medicine_list, _current_medicine_index, _medicine_total, _medicine_send_count, _medicine_started, _all_medicines_completed, _task_completed
    
    print("=" * 60)
    print(f"[HIS Sender] 重置药品发送状态")
    print(f"[HIS Sender] 处方编码: {prescription_code}")
    
    # 获取药品列表
    _medicine_list = get_prescription_medicine_locations(prescription_code)
    
    # 计算药品总数
    _medicine_total = len(_medicine_list)
    
    # ===== 新增：如果药品列表为空，停止发送 =====
    if _medicine_total == 0:
        print(f"[HIS Sender] WARNING: 处方 {prescription_code} 的药品列表为空")
        print(f"[HIS Sender] 可能原因：")
        print(f"[HIS Sender]   1. 处方数据已被删除")
        print(f"[HIS Sender]   2. prescription_items 表中没有该处方的药品")
        print(f"[HIS Sender]   3. medicine_locations 表中没有对应的坐标")
        print(f"[HIS Sender] 停止发送药品坐标")
        print("=" * 60)
        return
    
    # 重置当前药品索引
    _current_medicine_index = 0
    
    # 初始化每个药品的发送计数器（保留，用于统计）
    _medicine_send_count = {}
    for medicine in _medicine_list:
        _medicine_send_count[medicine["medicine_id"]] = 0
    
    # ===== 新增：初始化药品 started 状态（全部为 False） =====
    _medicine_started = {}
    for medicine in _medicine_list:
        _medicine_started[medicine["medicine_id"]] = False
    
    # 重置完成标志
    _all_medicines_completed = False
    _task_completed = False
    
    print(f"[HIS Sender] 药品状态已重置:")
    print(f"[HIS Sender]   药品总数: {_medicine_total}")
    print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
    print(f"[HIS Sender]   药品started状态: {_medicine_started}")
    print(f"[HIS Sender]   药品列表: {_medicine_list}")
    print("=" * 60)


def switch_to_next_medicine():
    """
    切换到下一个药品（收到药品完成信号时调用）
    
    逻辑：
    - 当前药品索引 +1
    - 初始化下一个药品的发送计数器为0
    - 初始化下一个药品的 started 状态为 False
    """
    global _current_medicine_index, _medicine_send_count, _medicine_started
    
    if _current_medicine_index < _medicine_total - 1:
        _current_medicine_index += 1
        next_medicine = _medicine_list[_current_medicine_index]
        next_medicine_id = next_medicine["medicine_id"]
        
        # 初始化下一个药品的发送计数器
        _medicine_send_count[next_medicine_id] = 0
        
        # ===== 新增：初始化下一个药品的 started 状态为 False =====
        _medicine_started[next_medicine_id] = False
        
        print(f"[HIS Sender] 切换到下一个药品:")
        print(f"[HIS Sender]   序号: {_current_medicine_index + 1}/{_medicine_total}")
        print(f"[HIS Sender]   药品ID: {next_medicine_id}")
        print(f"[HIS Sender]   started状态已初始化: {_medicine_started[next_medicine_id]}")
        print(f"[HIS Sender]   当前所有started状态: {_medicine_started}")
        return True
    else:
        print(f"[HIS Sender] 已到最后一个药品，等待 all_completed 信号")
        return False


async def his_sender_loop():
    """
    HIS 处方发送主循环
    
    逻辑：
    1. 定时轮询 HIS 数据库，获取最新 pending 处方
    2. 检测 ROS WebSocket 是否可达
    3. 逐个药品发送坐标信息（每2秒一次）
    4. 当处方编码更新时，重置药品状态，继续发送
    5. 收到药品完成信号（step5-return）时，先发送 end（两次），然后切换到下一个药品
    6. 收到 all_completed 信号后，停止发送药品坐标
    7. 收到 end 信号后，完全停止
    """
    # ===== 修复：声明所有使用的全局变量 =====
    global _current_prescription_code, _sender_running, _all_medicines_completed, _task_completed
    global _medicine_list, _medicine_total, _current_medicine_index, _last_sent_code
    global _medicine_need_send_end, _medicine_end_data  # 新增：end 发送相关状态
    global _medicine_end_in_progress, _medicine_end_pending_switch, _medicine_end_medicine_id, _medicine_end_prescription_code
    
    print("=" * 60)
    print("[HIS Sender] 服务启动（逐个药品发送模式）")
    print(f"[HIS Sender] HIS MySQL: {settings.his_mysql_host}:{settings.his_mysql_port}")
    print(f"[HIS Sender] ROS WebSocket: {ROS_WS_URL}")
    print(f"[HIS Sender] Topic: {ROS_TOPIC}")
    print("=" * 60)
    
    _sender_running = True
    
    while _sender_running:
        try:
            # 1. 检测 ROS WebSocket 是否可达
            ros_available = await check_ros_ws_available()
            
            if not ros_available:
                print("[HIS Sender] ROS WebSocket 不可达，等待重试...")
                await asyncio.sleep(settings.ros_check_interval)
                continue
            
            # 2. 获取最新处方编码
            # 修复：如果当前还有未发送完的药品，跳过处方查询，避免处方状态被提前更新为 dispensed 导致的循环
            if _medicine_list and _current_medicine_index < _medicine_total and _current_prescription_code:
                # 当前还有药品未发送完，直接使用当前处方编码，不查询数据库
                new_code = _current_prescription_code
            else:
                new_code = get_latest_pending_prescription()
            
            print(f"[HIS Sender] 主循环状态检查:")
            print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
            print(f"[HIS Sender]   查询处方编码: {new_code}")
            print(f"[HIS Sender]   是否相同: {new_code == _current_prescription_code}")
            print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
            print(f"[HIS Sender]   药品总数: {_medicine_total}")
            if _medicine_list and _current_medicine_index < len(_medicine_list):
                current_medicine_id = _medicine_list[_current_medicine_index]["medicine_id"]
                print(f"[HIS Sender]   当前药品ID: {current_medicine_id}")
                print(f"[HIS Sender]   当前药品started状态: {_medicine_started.get(current_medicine_id, '未初始化')}")
            print(f"[HIS Sender]   所有started状态: {_medicine_started}")
            
            # 3. 检测处方编码是否更新
            if new_code != _current_prescription_code:
                if new_code:
                    print(f"\n[HIS Sender] {'='*40}")
                    print(f"[HIS Sender] 处方编码更新: {_current_prescription_code} -> {new_code}")
                    _current_prescription_code = new_code
                    # 重置药品状态
                    reset_medicine_state(new_code)
                    print(f"[HIS Sender] {'='*40}")
                    continue
                else:
                    # 修复：如果当前还有未发送完的药品，不要清空状态，也不要 continue
                    # 处方状态可能在 end 发送过程中被HIS系统或其他途径更新为 dispensed，
                    # 但药品还没发完，此时清空状态会导致药品2永远发不出去
                    if _medicine_list and _current_medicine_index < _medicine_total:
                        remaining = _medicine_total - _current_medicine_index
                        print(f"[HIS Sender] 查询不到pending处方，但当前还有 {remaining} 个药品未发送，继续处理当前处方")
                        # 不 continue，让代码继续执行后续的发送药品坐标逻辑
                    else:
                        print("[HIS Sender] 无待处理处方，等待新处方...")
                        _current_prescription_code = None
                        _medicine_list = []
                        _medicine_total = 0
                        _current_medicine_index = 0
                        continue
            
            # ===== 检查是否需要发送 end 消息 =====
            # 新逻辑：当收到药单级running-step5-return时，发送end（两次），不切换药品
            # 等待ROS端返回药品级end消息，然后触发切换药品
            if _medicine_need_send_end and _medicine_end_data:
                print(f"\n[HIS Sender] {'='*60}")
                print(f"[HIS Sender] 检测到需要发送 end 消息")
                print(f"[HIS Sender]   处方编码: {_medicine_end_data.get('prescription_code')}")
                print(f"[HIS Sender]   药品ID: {_medicine_end_data.get('medicine_id')}")
                print(f"[HIS Sender] {'='*60}")

                # ===== 修复：设置 in_progress 标志，防止两次end之间ROS返回的药品级end触发提前切换 =====
                _medicine_end_in_progress = True
                _medicine_end_medicine_id = _medicine_end_data.get('medicine_id')
                _medicine_end_prescription_code = _medicine_end_data.get('prescription_code')
                print(f"[HIS Sender] 已设置 _medicine_end_in_progress=True（期间禁止切换药品）")

                # 发送 end 消息（两次，间隔2秒）
                success = await send_medicine_end_to_ros(
                    _medicine_end_data.get('prescription_code'),
                    _medicine_end_data.get('medicine_data'),
                    _medicine_end_data.get('medicine_index'),
                    _medicine_end_data.get('medicine_total')
                )

                # ===== 修复：两次end都发完后，直接切换药品（不再等待回执，避免时序死锁）=====
                # 此前的设计是等ROS返回药品级end才切换，但ROS端end_ack_sent去重导致第二次end不回执，
                # 而第一次end的回执被in_progress=True跳过 → 死锁，药品永远不切换
                _medicine_end_in_progress = False

                if success:
                    print(f"[HIS Sender] end 消息发送成功（两次）")
                    _medicine_need_send_end = False

                    # 清除防竞态标志
                    _medicine_end_medicine_id = None
                    _medicine_end_prescription_code = None

                    # 等待ROS端处理end消息
                    print(f"[HIS Sender] 等待3秒，让ROS端处理end消息...")
                    await asyncio.sleep(3)

                    # 直接切换药品，不再等待药品级end回执
                    print(f"[HIS Sender] 3秒等待完成，直接切换药品")
                    if switch_to_next_medicine():
                        print(f"[HIS Sender] [OK] 切换成功，下次主循环将发送下一个药品的 start")
                    else:
                        print(f"[HIS Sender] 已到最后一个药品，等待任务完成")
                    print(f"[HIS Sender] {'='*60}")
                else:
                    print(f"[HIS Sender] [ERROR] end 消息发送失败")
                    # 不重置标志，下次循环继续尝试发送
                    _medicine_end_in_progress = False

                # 跳过本次循环的发送药品坐标步骤
                continue
            
            # 4. 如果任务已完成，停止发送
            if _task_completed:
                print("[HIS Sender] 任务已完成，停止发送")
                await asyncio.sleep(SEND_INTERVAL)
                continue
            
            # 5. 如果所有药品已完成抓取，停止发送药品坐标
            if _all_medicines_completed:
                print("[HIS Sender] 所有药品已完成抓取，等待 end 信号...")
                await asyncio.sleep(SEND_INTERVAL)
                continue
            
            # 6. 如果有处方编码和药品，发送当前药品坐标
            if _current_prescription_code and _medicine_list and _medicine_total > 0:
                # 获取当前药品数据
                if _current_medicine_index < _medicine_total:
                    current_medicine = _medicine_list[_current_medicine_index]
                    
                    # ===== 新增：双重检查 medicine_id 是否为 0 =====
                    medicine_id_check = current_medicine.get("medicine_id", 0)
                    if medicine_id_check == 0 or medicine_id_check is None:
                        print(f"[HIS Sender] ERROR: 当前药品的 medicine_id 为 0 或 NULL，不发送")
                        print(f"[HIS Sender]   药品索引: {_current_medicine_index}")
                        print(f"[HIS Sender]   药品数据: {current_medicine}")
                        print(f"[HIS Sender] 跳过该药品，切换到下一个")
                        # 切换到下一个药品
                        _current_medicine_index += 1
                        if _current_medicine_index >= _medicine_total:
                            print(f"[HIS Sender] 所有药品已跳过，停止发送")
                            _all_medicines_completed = True
                        continue
                    
                    medicine_index_display = _current_medicine_index + 1  # 显示时从1开始
                    
                    # 发送药品坐标
                    success = await send_medicine_to_ros(
                        _current_prescription_code,
                        current_medicine,
                        medicine_index_display,
                        _medicine_total
                    )
                    
                    if success:
                        _last_sent_code = _current_prescription_code
            else:
                # ===== 新增：处方不存在或药品列表为空时，不发送 =====
                if _current_prescription_code and not _medicine_list:
                    print(f"[HIS Sender] 处方 {_current_prescription_code} 的药品列表为空，停止发送")
                    print(f"[HIS Sender] 可能原因：处方数据已被删除或药品坐标不存在")
                    # 清空状态，避免下次继续发送旧数据
                    _current_prescription_code = None
                    _medicine_list = []
                    _medicine_total = 0
                    _current_medicine_index = 0
                    _all_medicines_completed = False
                    _task_completed = False
            
            # 7. 等待发送间隔
            await asyncio.sleep(SEND_INTERVAL)
            
        except asyncio.CancelledError:
            print("[HIS Sender] 服务停止")
            break
        except Exception as e:
            print(f"[HIS Sender] 主循环异常: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)


async def start_his_sender():
    """启动 HIS 处方发送服务"""
    await his_sender_loop()


async def stop_his_sender():
    """停止 HIS 处方发送服务"""
    global _sender_running, _ws_connection
    _sender_running = False
    if _ws_connection:
        try:
            await _ws_connection.close()
        except:
            pass
        _ws_connection = None
    print("[HIS Sender] 服务已停止")


def get_sender_status():
    """获取发送服务状态"""
    return {
        "running": _sender_running,
        "current_prescription_code": _current_prescription_code,
        "last_sent_code": _last_sent_code,
        "medicine_list": _medicine_list,
        "medicine_total": _medicine_total,
        "current_medicine_index": _current_medicine_index + 1 if _medicine_total > 0 else 0,  # 从1开始显示
        "medicine_send_count": _medicine_send_count,
        "all_medicines_completed": _all_medicines_completed,
        "task_completed": _task_completed,
        "ros_ws_url": ROS_WS_URL,
        "ros_topic": ROS_TOPIC,
    }


# ===== 外部调用接口（供 ROS Listener 调用） =====

def notify_medicine_started(medicine_id: int, prescription_code: str):
    """
    通知 HIS Sender 当前药品已收到 running-started（供 ROS Listener 调用）
    
    当收到 {medicine_id}_{prescription_code}_running-started 时调用
    
    逻辑（严格判断药品ID）：
    - 检查处方编码是否匹配
    - 检查药品ID是否是当前发送的药品
    - 只有都匹配才设置 started 状态为 True
    """
    global _medicine_started, _current_prescription_code, _current_medicine_index, _medicine_list
    
    print("=" * 60)
    print(f"[HIS Sender] 收到药品 started 通知:")
    print(f"[HIS Sender]   收到的消息: {medicine_id}_{prescription_code}_running-started")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
    print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
    print(f"[HIS Sender]   药品总数: {_medicine_total}")
    
    # ===== 严格判断1：处方编码是否匹配 =====
    if prescription_code != _current_prescription_code:
        print(f"[HIS Sender] [ERROR] 处方编码不匹配！不更新 started状态")
        print(f"[HIS Sender]   收到: {prescription_code}")
        print(f"[HIS Sender]   当前: {_current_prescription_code}")
        print("=" * 60)
        return
    
    # ===== 严格判断2：检查是否是当前发送的药品 =====
    if _current_medicine_index < len(_medicine_list):
        current_medicine = _medicine_list[_current_medicine_index]
        current_medicine_id = current_medicine["medicine_id"]
        
        print(f"[HIS Sender] 当前发送药品ID: {current_medicine_id}")
        
        # ===== 严格判断：药品ID必须匹配 =====
        if current_medicine_id == medicine_id:
            print(f"[HIS Sender] [OK] 药品ID匹配！started状态更新为 True")
            _medicine_started[medicine_id] = True
            print(f"[HIS Sender] 当前 started状态: {_medicine_started}")
        else:
            print(f"[HIS Sender] [ERROR] 药品ID不匹配！不更新 started状态")
            print(f"[HIS Sender]   收到: medicine_id={medicine_id}")
            print(f"[HIS Sender]   当前发送: medicine_id={current_medicine_id}")
    else:
        print(f"[HIS Sender] [ERROR] 药品索引超出范围")
        print(f"[HIS Sender]   当前索引: {_current_medicine_index}")
        print(f"[HIS Sender]   药品列表长度: {len(_medicine_list)}")
    
    print("=" * 60)


def notify_prescription_step5_return(prescription_code: str):
    """
    通知 HIS Sender 药单完成（Step5返回），触发发送end消息（供 ROS Listener 调用）

    当收到 {prescription_code}_running-step5-return 时调用（药单级消息）

    新逻辑：
    - 检查处方编码是否匹配
    - 检查是否已在发送end或等待切换（防止重复触发）
    - 设置 end 发送标志
    - 主循环会检测标志，发送当前药品的 end（两次）
    - 不切换药品，等待ROS端返回药品级end消息
    """
    global _current_prescription_code, _current_medicine_index, _medicine_list
    global _medicine_need_send_end, _medicine_end_data, _medicine_total
    global _medicine_end_in_progress, _medicine_end_pending_switch

    print("=" * 60)
    print(f"[HIS Sender] 收到药单完成通知（Step5返回）:")
    print(f"[HIS Sender]   收到的消息: {prescription_code}_running-step5-return")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
    print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
    print(f"[HIS Sender]   药品总数: {_medicine_total}")
    print(f"[HIS Sender]   end_in_progress: {_medicine_end_in_progress}")
    print(f"[HIS Sender]   end_pending_switch: {_medicine_end_pending_switch}")
    print(f"[HIS Sender]   need_send_end: {_medicine_need_send_end}")

    # ===== 防重复：如果正在发送end或等待切换，不重复触发 =====
    if _medicine_end_in_progress or _medicine_end_pending_switch or _medicine_need_send_end:
        print(f"[HIS Sender] [跳过] end流程已在进行中（in_progress/pending_switch/need_send_end），不重复触发")
        print("=" * 60)
        return

    # ===== 严格判断：处方编码是否匹配 =====
    if prescription_code != _current_prescription_code:
        print(f"[HIS Sender] [ERROR] 处方编码不匹配！不设置 end 发送标志")
        print(f"[HIS Sender]   收到: {prescription_code}")
        print(f"[HIS Sender]   当前: {_current_prescription_code}")
        print("=" * 60)
        return
    
    # ===== 检查是否有当前药品 =====
    if _current_medicine_index < len(_medicine_list):
        current_medicine = _medicine_list[_current_medicine_index]
        current_medicine_id = current_medicine["medicine_id"]
        
        print(f"[HIS Sender] 当前发送药品ID: {current_medicine_id}")
        print(f"[HIS Sender] [OK] 处方编码匹配！设置 end 发送标志")
        
        # ===== 设置 end 发送标志和数据 =====
        _medicine_need_send_end = True
        _medicine_end_data = {
            "prescription_code": prescription_code,
            "medicine_id": current_medicine_id,
            "medicine_data": current_medicine,  # 当前药品的完整数据
            "medicine_index": _current_medicine_index + 1,  # 从1开始
            "medicine_total": _medicine_total
        }
        
        print(f"[HIS Sender] 已设置 end 发送标志:")
        print(f"[HIS Sender]   处方编码: {prescription_code}")
        print(f"[HIS Sender]   药品ID: {current_medicine_id}")
        print(f"[HIS Sender]   药品索引: {_current_medicine_index + 1}/{_medicine_total}")
        print(f"[HIS Sender]   下次主循环将发送 end 消息（两次，间隔2秒）")
        print(f"[HIS Sender]   发送end后，等待ROS端返回 {current_medicine_id}_{prescription_code}_end")
    else:
        print(f"[HIS Sender] [ERROR] 药品索引超出范围")
        print(f"[HIS Sender]   当前索引: {_current_medicine_index}")
        print(f"[HIS Sender]   药品列表长度: {len(_medicine_list)}")
    
    print("=" * 60)


def notify_medicine_completed(medicine_id: int, prescription_code: str):
    """
    通知 HIS Sender 当前药品已完成（供 ROS Listener 调用）

    当收到 {medicine_id}_{prescription_code}_end 时调用（药品级消息）

    修复逻辑（三重检查防止竞态条件）：
    - 检查1: _medicine_end_in_progress → end正在发送中，暂不切换
    - 检查2: _medicine_end_pending_switch → 未在等待切换，忽略（防止重复切换）
    - 检查3: medicine_id 匹配 → 用独立保存的 _medicine_end_medicine_id 比对
    - 检查4: prescription_code 匹配 → 用独立保存的 _medicine_end_prescription_code 比对
    - 全部通过才切换到下一个药品
    """
    global _current_prescription_code, _current_medicine_index, _medicine_list, _medicine_started
    global _medicine_total
    global _medicine_end_in_progress, _medicine_end_pending_switch
    global _medicine_end_medicine_id, _medicine_end_prescription_code

    print("=" * 60)
    print(f"[HIS Sender] 收到药品完成通知（end消息）:")
    print(f"[HIS Sender]   收到的消息: {medicine_id}_{prescription_code}_end")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
    print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
    print(f"[HIS Sender]   药品总数: {_medicine_total}")
    print(f"[HIS Sender]   end_in_progress: {_medicine_end_in_progress}")
    print(f"[HIS Sender]   end_pending_switch: {_medicine_end_pending_switch}")
    print(f"[HIS Sender]   end_medicine_id: {_medicine_end_medicine_id}")
    print(f"[HIS Sender]   end_prescription_code: {_medicine_end_prescription_code}")

    # ===== 检查1: end消息正在发送中（两次end之间），暂不切换 =====
    if _medicine_end_in_progress:
        print(f"[HIS Sender] [跳过] end消息正在发送中，暂不切换药品（防止竞态）")
        print(f"[HIS Sender]   此消息可能是第1次end的回执，等两次end都发完后再切换")
        print("=" * 60)
        return

    # ===== 检查2: 未在等待切换，忽略（防止重复切换或意外消息） =====
    if not _medicine_end_pending_switch:
        print(f"[HIS Sender] [跳过] 未在等待药品级end切换（可能是重复消息），忽略")
        print("=" * 60)
        return

    # ===== 检查3: 药品ID必须匹配（用独立保存的值，不用_current可能已被清空） =====
    if medicine_id != _medicine_end_medicine_id:
        print(f"[HIS Sender] [ERROR] 药品ID不匹配！不切换药品")
        print(f"[HIS Sender]   收到: medicine_id={medicine_id}")
        print(f"[HIS Sender]   期望: medicine_id={_medicine_end_medicine_id}")
        print("=" * 60)
        return

    # ===== 检查4: 处方编码必须匹配（用独立保存的值） =====
    if prescription_code != _medicine_end_prescription_code:
        print(f"[HIS Sender] [ERROR] 处方编码不匹配！不切换药品")
        print(f"[HIS Sender]   收到: {prescription_code}")
        print(f"[HIS Sender]   期望: {_medicine_end_prescription_code}")
        print("=" * 60)
        return

    # ===== 所有检查通过，清除 pending_switch 标志（防止重复切换） =====
    _medicine_end_pending_switch = False
    _medicine_end_medicine_id = None
    _medicine_end_prescription_code = None

    print(f"[HIS Sender] [OK] 三重检查通过！切换到下一个药品")

    # ===== 切换到下一个药品 =====
    if _current_medicine_index < len(_medicine_list):
        current_medicine = _medicine_list[_current_medicine_index]
        current_medicine_id = current_medicine["medicine_id"]
        print(f"[HIS Sender] 当前发送药品ID: {current_medicine_id}")

        if switch_to_next_medicine():
            print(f"[HIS Sender] 切换成功，下次主循环将发送下一个药品的 start")
        else:
            print(f"[HIS Sender] 已到最后一个药品，等待任务完成")
    else:
        print(f"[HIS Sender] [ERROR] 药品索引超出范围")
        print(f"[HIS Sender]   当前索引: {_current_medicine_index}")
        print(f"[HIS Sender]   药品列表长度: {len(_medicine_list)}")

    print("=" * 60)


def notify_all_medicines_completed(prescription_code: str):
    """
    通知 HIS Sender 所有药品已完成抓取（供 ROS Listener 调用）
    
    当收到 {prescription_code}_all_completed 时调用
    
    逻辑：
    - 设置 _all_medicines_completed = True
    - 停止发送药品坐标
    """
    global _current_prescription_code, _all_medicines_completed
    
    # 检查处方编码是否匹配
    if prescription_code == _current_prescription_code:
        print(f"[HIS Sender] 收到所有药品完成信号: {prescription_code}")
        _all_medicines_completed = True
    else:
        print(f"[HIS Sender] all_completed 处方编码不匹配: {prescription_code} != {_current_prescription_code}")


def notify_task_completed(prescription_code: str):
    """
    通知 HIS Sender 任务完成（供 ROS Listener 调用）
    
    当收到 {prescription_code}_end 时调用
    
    逻辑：
    - 设置 _task_completed = True
    - 完全停止发送
    """
    global _current_prescription_code, _task_completed
    
    # 检查处方编码是否匹配
    if prescription_code == _current_prescription_code:
        print(f"[HIS Sender] 收到任务完成信号: {prescription_code}")
        _task_completed = True
    else:
        print(f"[HIS Sender] end 处方编码不匹配: {prescription_code} != {_current_prescription_code}")