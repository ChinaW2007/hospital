"""
HIS 处方自动发送服务（顺序结构版）

核心改变：
- 从"选择结构（if/elif分支+全局变量通信）"改为"顺序结构（for循环+Event等待）"
- 每个药品的发送流程严格顺序执行：start → 等待started → running → 等待step5-return → end → 下一个
- 消除了两个协程通过全局变量通信的竞态条件

功能保持不变：
- HIS数据库轮询、药品坐标查询、WebSocket连接管理
- 所有外部接口（notify_*、get_sender_status等）
- 详细的日志打印和错误处理
"""
import asyncio
import json
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

# ===== 事件（替代全局标志变量，消除竞态）=====
# 这些Event用于 ros_listener 通知 his_sender 收到了特定的ROS消息
# 在 his_sender_loop() 启动时初始化
_started_event = None        # 收到 running-started
_step5_return_event = None   # 收到 running-step5-return（药单级）
_all_completed_event = None  # 收到 all_completed
_task_end_event = None       # 收到 end（药单级，任务完成）

# ===== 状态（供API查询）=====
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

# ===== 当前预期上下文（用于验证收到的消息是否匹配当前药品）=====
_expected_medicine_id = None         # 当前正在处理的药品ID
_expected_prescription_code = None   # 当前正在处理的处方编码


def _init_events():
    """初始化Event（在事件循环中调用）"""
    global _started_event, _step5_return_event, _all_completed_event, _task_end_event
    _started_event = asyncio.Event()
    _step5_return_event = asyncio.Event()
    _all_completed_event = asyncio.Event()
    _task_end_event = asyncio.Event()


# ===== 数据库查询函数 =====

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

    查询路径：prescriptions -> prescription_items -> medicine_locations

    返回：
    [
        {"medicine_id": 1, "x": 10.5, "y": 20.3, "z": 5.0, "yaw": 0.0},
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
            # 修复：pymysql 使用 %s 格式，不是 ?
            # 修复：使用 GROUP BY 去重，防止 medicine_locations 表中有重复记录
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

                    # 修复：检查 medicine_id 是否为 NULL 或 0
                    medicine_id_value = row["medicine_id"]
                    if medicine_id_value is None or medicine_id_value == 0:
                        print(f"[HIS Sender] WARNING: 药品{i+1} 的 medicine_id 为 NULL 或 0，跳过该药品")
                        continue  # 跳过无效药品

                    medicine_list.append({
                        "medicine_id": int(medicine_id_value),
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


# ===== WebSocket 连接管理 =====

async def _ensure_ws_connection():
    """确保WebSocket连接有效（提取公共逻辑，减少重复代码）"""
    global _ws_connection

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


async def check_ros_ws_available():
    """检测 Ros WebSocket 是否可达"""
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


# ===== 消息发送函数 =====

async def send_medicine_to_ros(prescription_code: str, medicine_data: dict, medicine_index: int, medicine_total: int, data: str = None):
    """
    发送单个药品坐标到 ROS WebSocket

    参数：
    - data: 指定发送 "start" 或 "running"（顺序结构下由调用方决定）
    - 如果不传data，则根据 _medicine_started 判断（兼容旧逻辑）

    消息格式：
    {
        "op": "publish",
        "topic": "/his_sub",
        "msg": {
            "data": "start" 或 "running",
            "prescription_code": "处方编码",
            "medicine_id": 药品ID,
            "x": X坐标, "y": Y坐标, "z": Z坐标, "yaw": yaw值,
            "medicine_total": 药品总数,
            "medicine_index": 当前药品序号（从1开始）
        }
    }
    """
    global _ws_connection, _medicine_send_count

    try:
        medicine_id = medicine_data["medicine_id"]

        # 判断发送 start 还是 running
        if data is None:
            # 兼容旧逻辑：根据 _medicine_started 判断
            is_started = _medicine_started.get(medicine_id, False)
            data = "running" if is_started else "start"
            print(f"[HIS Sender] 判断发送状态:")
            print(f"[HIS Sender]   当前药品ID: {medicine_id}")
            print(f"[HIS Sender]   _medicine_started 完整状态: {_medicine_started}")
            print(f"[HIS Sender]   is_started 结果: {is_started}")
            print(f"[HIS Sender]   决定发送: {data}")

        # 更新发送计数
        _medicine_send_count[medicine_id] = _medicine_send_count.get(medicine_id, 0) + 1

        await _ensure_ws_connection()

        # 构造消息
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

        # 详细日志打印
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
        print(f"[HIS Sender]   发送计数: {_medicine_send_count[medicine_id]}")
        print("=" * 60)

        await _ws_connection.send(message)
        return True

    except Exception as e:
        print(f"[HIS Sender] 发送失败: {e}")
        import traceback
        traceback.print_exc()
        if _ws_connection:
            try:
                await _ws_connection.close()
            except:
                pass
            _ws_connection = None
        return False


async def send_medicine_end_to_ros(prescription_code: str, medicine_data: dict, medicine_index: int, medicine_total: int):
    """
    发送药品完成信号（end）到 ROS WebSocket

    发送逻辑：
    - 发送两次 end 消息
    - 每次间隔 2 秒
    - 表示当前药品已完成
    """
    global _ws_connection

    try:
        medicine_id = medicine_data["medicine_id"]

        await _ensure_ws_connection()

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

            # 详细日志打印
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

            # 两次发送间隔2秒
            if send_count == 0:
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


# ===== 状态管理 =====

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

    # 如果药品列表为空，停止发送
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

    # 初始化每个药品的发送计数器
    _medicine_send_count = {}
    for medicine in _medicine_list:
        _medicine_send_count[medicine["medicine_id"]] = 0

    # 初始化药品 started 状态（全部为 False）
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


# ===== 核心：顺序处理单个药品 =====

async def process_single_medicine(medicine_data: dict, prescription_code: str, medicine_index: int, medicine_total: int):
    """
    处理单个药品的完整发送流程（顺序执行）

    流程：
    1. 发送 start，循环每2秒一次，直到收到 running-started
    2. 发送 running，循环每2秒一次，直到收到 running-step5-return
    3. 发送 end，两次，间隔2秒
    4. 等待3秒，让ROS端处理

    这是顺序结构的核心：每个步骤严格等待完成后才进入下一步，
    不存在两个协程通过全局变量通信的竞态条件。
    """
    global _expected_medicine_id, _medicine_started

    medicine_id = medicine_data["medicine_id"]
    _expected_medicine_id = medicine_id

    print(f"\n[HIS Sender] {'='*60}")
    print(f"[HIS Sender] 开始处理药品 {medicine_index}/{medicine_total} (ID={medicine_id})")
    print(f"[HIS Sender] {'='*60}")

    # 清除事件
    _started_event.clear()
    _step5_return_event.clear()

    # ===== 阶段1：发送 start，等待 running-started =====
    print(f"[HIS Sender] 阶段1：发送 start，等待 running-started")
    send_count = 0
    while not _started_event.is_set() and _sender_running:
        send_count += 1
        print(f"[HIS Sender] 发送 start（第{send_count}次）")
        await send_medicine_to_ros(
            prescription_code, medicine_data, medicine_index, medicine_total, "start"
        )
        # 等待2秒或直到收到started
        try:
            await asyncio.wait_for(_started_event.wait(), timeout=SEND_INTERVAL)
        except asyncio.TimeoutError:
            pass  # 超时，继续发送start

    if not _sender_running:
        return False

    print(f"[HIS Sender] [OK] 收到 running-started（共发送{send_count}次start）")
    _medicine_started[medicine_id] = True

    # ===== 阶段2：发送 running，等待 running-step5-return =====
    print(f"[HIS Sender] 阶段2：发送 running，等待 running-step5-return")
    # 方案A修复：不再无条件清除 _step5_return_event
    # 如果 step5-return 在阶段1就已经到达（由于 started 延迟导致），保留事件状态
    # 这样可以直接跳过 running 发送阶段，避免卡死
    if _step5_return_event.is_set():
        print(f"[HIS Sender] [OK] step5-return 在阶段1已到达，跳过 running 发送")
    send_count = 0
    while not _step5_return_event.is_set() and _sender_running:
        send_count += 1
        print(f"[HIS Sender] 发送 running（第{send_count}次）")
        await send_medicine_to_ros(
            prescription_code, medicine_data, medicine_index, medicine_total, "running"
        )
        # 等待2秒或直到收到step5-return
        try:
            await asyncio.wait_for(_step5_return_event.wait(), timeout=SEND_INTERVAL)
        except asyncio.TimeoutError:
            pass  # 超时，继续发送running

    if not _sender_running:
        return False

    print(f"[HIS Sender] [OK] 收到 running-step5-return（共发送{send_count}次running）")

    # ===== 阶段3：发送 end（两次，间隔2秒）=====
    print(f"[HIS Sender] 阶段3：发送 end（两次，间隔2秒）")
    success = await send_medicine_end_to_ros(
        prescription_code, medicine_data, medicine_index, medicine_total
    )

    if not success:
        print(f"[HIS Sender] [ERROR] end 消息发送失败")
        return False

    # ===== 阶段4：等待3秒，让ROS端处理end消息 =====
    print(f"[HIS Sender] 阶段4：等待3秒，让ROS端处理end消息...")
    await asyncio.sleep(3)

    print(f"[HIS Sender] [OK] 药品 {medicine_index}/{medicine_total} (ID={medicine_id}) 处理完成")
    return True


# ===== 主循环（顺序结构）=====

async def his_sender_loop():
    """
    HIS 处方发送主循环（顺序结构版）

    逻辑：
    1. 定时轮询 HIS 数据库，获取最新 pending 处方
    2. 检测 ROS WebSocket 是否可达
    3. 逐个药品顺序发送（for循环）：
       a. 发送 start，等待 running-started
       b. 发送 running，等待 running-step5-return
       c. 发送 end（两次），等待3秒
       d. 自动切换到下一个药品
    4. 所有药品完成后，回到步骤1检测新处方
    """
    global _current_prescription_code, _sender_running
    global _medicine_list, _medicine_total, _current_medicine_index, _last_sent_code
    global _all_medicines_completed, _task_completed
    global _expected_prescription_code

    # 初始化Event
    _init_events()

    print("=" * 60)
    print("[HIS Sender] 服务启动（顺序结构模式）")
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
            new_code = get_latest_pending_prescription()

            print(f"[HIS Sender] 主循环状态检查:")
            print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
            print(f"[HIS Sender]   查询处方编码: {new_code}")
            print(f"[HIS Sender]   是否相同: {new_code == _current_prescription_code}")

            # 3. 检测处方编码是否更新
            if new_code != _current_prescription_code:
                if new_code:
                    print(f"\n[HIS Sender] {'='*40}")
                    print(f"[HIS Sender] 处方编码更新: {_current_prescription_code} -> {new_code}")
                    _current_prescription_code = new_code
                    _expected_prescription_code = new_code
                    reset_medicine_state(new_code)
                    print(f"[HIS Sender] {'='*40}")

                    if not _medicine_list:
                        print(f"[HIS Sender] 药品列表为空，等待新处方...")
                        await asyncio.sleep(POLL_INTERVAL)
                        continue
                else:
                    print("[HIS Sender] 无待处理处方，等待新处方...")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

            # 4. 检查任务是否完成
            if _task_completed:
                print("[HIS Sender] 任务已完成，停止发送")
                await asyncio.sleep(SEND_INTERVAL)
                continue

            # 5. 逐个药品顺序发送（for循环，顺序结构的核心）
            if _medicine_list and _medicine_total > 0:
                for idx in range(_current_medicine_index, _medicine_total):
                    if not _sender_running:
                        break

                    _current_medicine_index = idx
                    current_medicine = _medicine_list[idx]

                    # 双重检查 medicine_id 是否为 0 或 NULL
                    medicine_id_check = current_medicine.get("medicine_id", 0)
                    if medicine_id_check == 0 or medicine_id_check is None:
                        print(f"[HIS Sender] ERROR: 当前药品的 medicine_id 为 0 或 NULL，跳过")
                        print(f"[HIS Sender]   药品索引: {_current_medicine_index}")
                        print(f"[HIS Sender]   药品数据: {current_medicine}")
                        continue

                    medicine_index_display = _current_medicine_index + 1  # 显示时从1开始

                    # 顺序处理单个药品
                    success = await process_single_medicine(
                        current_medicine,
                        _current_prescription_code,
                        medicine_index_display,
                        _medicine_total
                    )

                    if success:
                        _last_sent_code = _current_prescription_code
                    else:
                        print(f"[HIS Sender] 药品发送失败，退出当前处方处理")
                        break

                # for循环结束，所有药品发送完成
                if _current_medicine_index >= _medicine_total - 1:
                    print(f"[HIS Sender] 所有药品发送完成")
                    _all_medicines_completed = True
                    # 等待一段时间，让HIS系统更新处方状态
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                # 处方不存在或药品列表为空
                if _current_prescription_code and not _medicine_list:
                    print(f"[HIS Sender] 处方 {_current_prescription_code} 的药品列表为空，停止发送")
                    _current_prescription_code = None
                    _expected_prescription_code = None
                    _medicine_list = []
                    _medicine_total = 0
                    _current_medicine_index = 0
                    _all_medicines_completed = False
                    _task_completed = False
                await asyncio.sleep(POLL_INTERVAL)

        except asyncio.CancelledError:
            print("[HIS Sender] 服务停止")
            break
        except Exception as e:
            print(f"[HIS Sender] 主循环异常: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)


# ===== 生命周期管理 =====

async def start_his_sender():
    """启动 HIS 处方发送服务"""
    await his_sender_loop()


async def stop_his_sender():
    """停止 HIS 处方发送服务"""
    global _sender_running, _ws_connection
    _sender_running = False
    # 设置所有Event，防止等待中的协程死锁
    if _started_event:
        _started_event.set()
    if _step5_return_event:
        _step5_return_event.set()
    if _all_completed_event:
        _all_completed_event.set()
    if _task_end_event:
        _task_end_event.set()
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


# ===== 外部通知接口（供 ROS Listener 调用）=====
# 顺序结构下，这些接口改为设置 asyncio.Event，不再操作全局标志变量

def notify_medicine_started(medicine_id: int, prescription_code: str):
    """
    通知 HIS Sender 当前药品已收到 running-started（供 ROS Listener 调用）

    当收到 {medicine_id}_{prescription_code}_running-started 时调用

    顺序结构逻辑：
    - 检查药品ID和处方编码是否匹配当前正在处理的药品
    - 匹配则设置 _started_event，让 process_single_medicine 从 start 阶段进入 running 阶段
    """
    global _expected_medicine_id

    print("=" * 60)
    print(f"[HIS Sender] 收到药品 started 通知:")
    print(f"[HIS Sender]   收到的消息: {medicine_id}_{prescription_code}_running-started")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
    print(f"[HIS Sender]   预期药品ID: {_expected_medicine_id}")

    # 严格判断1：处方编码是否匹配
    if prescription_code != _current_prescription_code:
        print(f"[HIS Sender] [ERROR] 处方编码不匹配！不设置 started 事件")
        print(f"[HIS Sender]   收到: {prescription_code}")
        print(f"[HIS Sender]   当前: {_current_prescription_code}")
        print("=" * 60)
        return

    # 严格判断2：药品ID是否匹配当前正在处理的药品
    if medicine_id == _expected_medicine_id:
        print(f"[HIS Sender] [OK] 药品ID匹配！设置 started 事件")
        _medicine_started[medicine_id] = True
        print(f"[HIS Sender]   当前 started状态: {_medicine_started}")
        if _started_event:
            _started_event.set()
    else:
        print(f"[HIS Sender] [ERROR] 药品ID不匹配！不设置 started 事件")
        print(f"[HIS Sender]   收到: medicine_id={medicine_id}")
        print(f"[HIS Sender]   预期: medicine_id={_expected_medicine_id}")

    print("=" * 60)


def notify_prescription_step5_return(prescription_code: str):
    """
    通知 HIS Sender 药单完成（Step5返回）（供 ROS Listener 调用）

    当收到 {prescription_code}_running-step5-return 时调用（药单级消息）

    顺序结构逻辑：
    - 检查处方编码是否匹配
    - 匹配则设置 _step5_return_event，让 process_single_medicine 从 running 阶段进入 end 阶段
    """
    print("=" * 60)
    print(f"[HIS Sender] 收到药单完成通知（Step5返回）:")
    print(f"[HIS Sender]   收到的消息: {prescription_code}_running-step5-return")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")

    # 严格判断：处方编码是否匹配
    if prescription_code != _current_prescription_code:
        print(f"[HIS Sender] [ERROR] 处方编码不匹配！不设置 step5-return 事件")
        print(f"[HIS Sender]   收到: {prescription_code}")
        print(f"[HIS Sender]   当前: {_current_prescription_code}")
        print("=" * 60)
        return

    print(f"[HIS Sender] [OK] 处方编码匹配！设置 step5-return 事件")
    print(f"[HIS Sender]   process_single_medicine 将从 running 阶段进入 end 阶段")
    if _step5_return_event:
        _step5_return_event.set()

    print("=" * 60)


def notify_medicine_completed(medicine_id: int, prescription_code: str):
    """
    通知 HIS Sender 当前药品已完成（供 ROS Listener 调用）

    当收到 {medicine_id}_{prescription_code}_end 时调用（药品级消息）

    顺序结构逻辑：
    - 顺序结构下，药品切换由 for 循环自动处理，此函数不需要做切换操作
    - 仅打印日志，记录药品完成事件
    - ROS Listener 中的语音播报和HIS状态更新逻辑不受影响
    """
    print("=" * 60)
    print(f"[HIS Sender] 收到药品完成通知（end消息）:")
    print(f"[HIS Sender]   收到的消息: {medicine_id}_{prescription_code}_end")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")
    print(f"[HIS Sender]   当前药品索引: {_current_medicine_index}")
    print(f"[HIS Sender]   药品总数: {_medicine_total}")
    print(f"[HIS Sender]   （顺序结构下由for循环自动切换，无需手动切换）")
    print("=" * 60)


def notify_all_medicines_completed(prescription_code: str):
    """
    通知 HIS Sender 所有药品已完成抓取（供 ROS Listener 调用）

    当收到 {prescription_code}_all_completed 时调用
    """
    global _all_medicines_completed

    print(f"[HIS Sender] 收到所有药品完成信号: {prescription_code}")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")

    # 检查处方编码是否匹配
    if prescription_code == _current_prescription_code:
        print(f"[HIS Sender] [OK] 处方编码匹配")
        _all_medicines_completed = True
        if _all_completed_event:
            _all_completed_event.set()
    else:
        print(f"[HIS Sender] [ERROR] all_completed 处方编码不匹配: {prescription_code} != {_current_prescription_code}")


def notify_task_completed(prescription_code: str):
    """
    通知 HIS Sender 任务完成（供 ROS Listener 调用）

    当收到 {prescription_code}_end 时调用（药单级，任务完成）
    """
    global _task_completed

    print(f"[HIS Sender] 收到任务完成信号: {prescription_code}")
    print(f"[HIS Sender]   当前处方编码: {_current_prescription_code}")

    # 检查处方编码是否匹配
    if prescription_code == _current_prescription_code:
        print(f"[HIS Sender] [OK] 处方编码匹配")
        _task_completed = True
        if _task_end_event:
            _task_end_event.set()
    else:
        print(f"[HIS Sender] [ERROR] end 处方编码不匹配: {prescription_code} != {_current_prescription_code}")
