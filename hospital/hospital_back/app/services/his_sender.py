"""
HIS 处方自动发送服务
定时轮询 HIS 数据库，检测新处方并发送到 ROS WebSocket
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


async def send_prescription_to_ros(prescription_code: str):
    """
    发送处方编码到 ROS WebSocket
    
    消息格式：
    {
        "op": "publish",
        "topic": "/his_sub",
        "msg": {
            "data": "start",
            "prescription_code": "处方编码"
        }
    }
    """
    global _ws_connection
    
    try:
        # 检查连接是否有效（websockets 11.x+ 使用 open 属性）
        need_new_connection = False
        if _ws_connection is None:
            need_new_connection = True
        else:
            # 兼容不同版本的 websockets 库
            try:
                # websockets 11.x+ 使用 open 属性
                if hasattr(_ws_connection, 'open') and not _ws_connection.open:
                    need_new_connection = True
                # websockets 10.x 使用 closed 属性
                elif hasattr(_ws_connection, 'closed') and _ws_connection.closed:
                    need_new_connection = True
            except:
                # 无法判断状态，创建新连接
                need_new_connection = True
        
        # 如果需要新连接，创建连接
        if need_new_connection:
            # 先关闭旧连接
            if _ws_connection is not None:
                try:
                    await _ws_connection.close()
                except:
                    pass
            
            _ws_connection = await asyncio.wait_for(
                websockets.connect(ROS_WS_URL),
                timeout=settings.ros_connect_timeout
            )
            
            # 先清除旧的Topic注册（防止ROS缓存旧类型）
            await _ws_connection.send(json.dumps({
                "op": "unadvertise",
                "topic": ROS_TOPIC
            }))
            await asyncio.sleep(0.1)
            
            # 重新注册 Topic（注意类型必须完全一致：his_sub/HisSub）
            await _ws_connection.send(json.dumps({
                "op": "advertise",
                "topic": ROS_TOPIC,
                "type": "his_sub/HisSub"
            }))
            await asyncio.sleep(0.3)
            print("[HIS Sender] Topic 注册成功: /his_sub (his_sub/HisSub)")
        
        # 发送处方编码
        message = json.dumps({
            "op": "publish",
            "topic": ROS_TOPIC,
            "msg": {
                "data": "start",
                "prescription_code": prescription_code
            }
        })
        await _ws_connection.send(message)
        print(f"[HIS Sender] 发送成功: start + {prescription_code}")
        return True
    
    except Exception as e:
        print(f"[HIS Sender] 发送失败: {e}")
        # 关闭失败连接，下次重连
        if _ws_connection:
            try:
                await _ws_connection.close()
            except:
                pass
            _ws_connection = None
        return False


async def his_sender_loop():
    """
    HIS 处方发送主循环
    
    逻辑：
    1. 定时轮询 HIS 数据库，获取最新 pending 处方
    2. 检测 ROS WebSocket 是否可达
    3. 持续发送当前处方编码（每2秒一次）
    4. 当处方编码更新时，切换到新处方继续发送
    """
    global _current_prescription_code, _sender_running
    
    print("=" * 50)
    print("[HIS Sender] 服务启动")
    print(f"[HIS Sender] HIS MySQL: {settings.his_mysql_host}:{settings.his_mysql_port}")
    print(f"[HIS Sender] ROS WebSocket: {ROS_WS_URL}")
    print(f"[HIS Sender] Topic: {ROS_TOPIC}")
    print("=" * 50)
    
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
            
            # 3. 检测处方编码是否更新
            if new_code != _current_prescription_code:
                if new_code:
                    print(f"\n[HIS Sender] {'='*20}")
                    print(f"[HIS Sender] 处方编码更新: {_current_prescription_code} -> {new_code}")
                    print(f"[HIS Sender] {'='*20}")
                else:
                    print("[HIS Sender] 无待处理处方，等待新处方...")
                _current_prescription_code = new_code
            
            # 4. 如果有处方编码，持续发送
            if _current_prescription_code:
                success = await send_prescription_to_ros(_current_prescription_code)
                if success:
                    _last_sent_code = _current_prescription_code
            
            # 5. 等待发送间隔
            await asyncio.sleep(SEND_INTERVAL)
            
        except asyncio.CancelledError:
            print("[HIS Sender] 服务停止")
            break
        except Exception as e:
            print(f"[HIS Sender] 主循环异常: {e}")
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
        "ros_ws_url": ROS_WS_URL,
        "ros_topic": ROS_TOPIC,
    }