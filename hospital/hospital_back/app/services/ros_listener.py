"""
ROS WebSocket 监听服务
周期性检测端口可达性，自动重连，处理所有机器人状态消息
"""
import asyncio
import json
import socket
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

try:
    import websockets
except ImportError:
    websockets = None

from app.core.config import settings, get_ros_ws_url

logger = logging.getLogger(__name__)


class ROSListenerState(Enum):
    """监听服务状态"""
    STOPPED = "stopped"
    CHECKING = "checking"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


# 全局状态存储（供 API 查询）
_ros_state: Dict[str, Any] = {
    "listener_state": ROSListenerState.STOPPED.value,
    "ws_reachable": False,
    "last_check_time": None,
    "last_message_time": None,
    "current_robot_status": None,
    "current_prescription_code": None,  # 当前处理的处方编码
    "current_step": 1,
    "steps": [
        {"id": 1, "name": "开具处方", "status": "pending", "desc": "等待处方开具"},
        {"id": 2, "name": "任务确认", "status": "pending", "desc": "等待任务启动"},
        {"id": 3, "name": "扫码复合", "status": "pending", "desc": "等待扫码复核"},
        {"id": 4, "name": "站台交互", "status": "pending", "desc": "等待站台交互"},
    ]
}


def get_ros_state() -> Dict[str, Any]:
    """获取当前 ROS 监听状态（供 API 使用）"""
    return _ros_state.copy()


def check_port_reachable(host: str, port: int, timeout: int = 5) -> bool:
    """检测目标端口是否可达"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"端口检测失败: {e}")
        return False


def parse_ros_message(data: str) -> Dict[str, Any]:
    """
    解析 ROS 消息，多版本适配
    
    支持格式：
    1. JSON 格式: {"status": "running_started", "prescription_code": "RX..."}
    2. 分隔符格式（竖线）: "running_started|RX..."
    3. 新格式（下划线）: "{prescription_code}_running-started"
    4. 纯字符串格式（旧版本兼容）: "running_started"
    
    返回：
    - status: ROS 状态字符串
    - prescription_code: 药单编码（可选）
    """
    # 尝试解析 JSON 格式
    if data.startswith("{") and data.endswith("}"):
        try:
            msg = json.loads(data)
            return {
                "status": msg.get("status", ""),
                "prescription_code": msg.get("prescription_code")
            }
        except json.JSONDecodeError:
            pass
    
    # 尝试解析分隔符格式（竖线）
    if "|" in data:
        parts = data.split("|")
        return {
            "status": parts[0],
            "prescription_code": parts[1] if len(parts) > 1 else None
        }
    
    # 尝试解析新格式: {prescription_code}_running-started
    # 检查是否包含 "_running-started" 或 "_running_started"
    if "_running-started" in data:
        parts = data.split("_running-started")
        if len(parts) >= 1:
            return {
                "status": "running-started",
                "prescription_code": parts[0] if parts[0] else None
            }
    
    if "_running_started" in data:
        parts = data.split("_running_started")
        if len(parts) >= 1:
            return {
                "status": "running_started",
                "prescription_code": parts[0] if parts[0] else None
            }
    
    # 纯字符串格式（旧版本兼容）
    return {
        "status": data,
        "prescription_code": None
    }


def update_prescription_workflow_db(prescription_code: str, status: str) -> bool:
    """
    更新处方流程状态到数据库
    
    Args:
        prescription_code: 药单编码
        status: ROS 状态
    
    Returns:
        bool: 是否更新成功
    """
    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings
        
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # 根据 ROS 状态确定节点更新
            node_updates = get_node_updates_from_status(status)
            
            # 使用 UPSERT 语法：INSERT OR REPLACE（SQLite 特有）
            # 如果 prescription_code 已存在，则替换；否则插入新记录
            upsert_sql = text("""
                INSERT OR REPLACE INTO prescription_workflow_state 
                (prescription_code, current_node, node2_status, node2_desc, 
                 node3_status, node3_desc, node4_status, node4_desc, ros_status, updated_at)
                VALUES (:code, :current_node, :node2_status, :node2_desc,
                        :node3_status, :node3_desc, :node4_status, :node4_desc, 
                        :ros_status, datetime('now', 'localtime'))
            """)
            conn.execute(upsert_sql, {
                "code": prescription_code,
                "current_node": node_updates["current_node"],
                "node2_status": node_updates["node2_status"],
                "node2_desc": node_updates["node2_desc"],
                "node3_status": node_updates["node3_status"],
                "node3_desc": node_updates["node3_desc"],
                "node4_status": node_updates["node4_status"],
                "node4_desc": node_updates["node4_desc"],
                "ros_status": status,
            })
            conn.commit()
            print(f"[成功] 更新处方流程状态: {prescription_code} -> {status}")
            logger.info(f"已更新处方流程状态: {prescription_code} -> {status}")
            return True
    
    except Exception as e:
        print(f"[失败] 更新处方流程状态失败: {e}")
        logger.error(f"更新处方流程状态失败: {e}")
        return False


def get_node_updates_from_status(status: str) -> Dict[str, Any]:
    """
    根据 ROS 状态获取节点更新数据
    
    支持新旧两种格式：
    - 新格式（横线）: running-started, running-step1-navigate-to-pharmacy, error-step1-cannot-reach-pharmacy 等
    - 旧格式（下划线）: running_started, running_step1_navigate_to_pharmacy, error_step1_cannot_reach_pharmacy 等
    
    Returns:
        Dict: 包含各节点状态和描述的字典
    """
    defaults = {
        "current_node": 1,
        "node2_status": "pending",
        "node2_desc": "等待任务启动",
        "node3_status": "pending",
        "node3_desc": "等待扫码复核",
        "node4_status": "pending",
        "node4_desc": "等待站台交互",
    }
    
    # ===== 任务启动 =====
    # 新格式（节点2直接完成）
    if status == "running-started":
        defaults["current_node"] = 2
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
    
    # 旧格式（节点2为进行中）
    elif status == "running_started":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "任务已确认"
    
    # ===== Step 1: 前往药房 =====
    # 新格式（横线）
    elif status == "running-step1-navigate-to-pharmacy":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在前往药房"
    
    elif status == "error-step1-cannot-reach-pharmacy":
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "到达药房失败"
    
    # 旧格式（下划线）
    elif status == "running_step1_navigate_to_pharmacy":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在前往药房"
    
    elif status == "error_step1_cannot_reach_pharmacy":
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "到达药房失败"
    
    # ===== Step 2: 抓药 =====
    # 新格式
    elif status == "running-step2-pick":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在抓药"
    
    # 旧格式
    elif status == "running_step2_pick":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在抓药"
    
    # ===== Step 3: 前往病房 =====
    # 新格式（注意拼写：doctor）
    elif status == "running-step3-navigate-doctor":
        defaults["current_node"] = 3
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "前往病房"
    
    elif status == "error-step3-cannot-reach-patient-room":
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "无法到达病房"
    
    # 旧格式（注意拼写：docter）
    elif status == "running_step3_navigate_docter":
        defaults["current_node"] = 3
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "前往病房"
    
    elif status == "error_step3_cannot_reach_patient_room":
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "无法到达病房"
    
    # ===== Step 4: 送药 =====
    # 新格式
    elif status == "running-step4-deliver-medicine":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在送药"
    
    # 旧格式
    elif status == "running_step4_deliver_medicine":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在送药"
    
    # ===== Step 5: 返回 =====
    # 新格式
    elif status == "running-step5-return":
        defaults["current_node"] = 4
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在返回起点"
    
    elif status == "error-step5-cannot-return-to-home":
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "无法返回起点"
    
    # 旧格式
    elif status == "running_step5_return":
        defaults["current_node"] = 4
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在返回起点"
    
    elif status == "error_step5_cannot_return_to_home":
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "无法返回起点"
    
    # ===== 任务完成 =====
    elif status == "end":
        defaults["current_node"] = 5
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "completed"
        defaults["node4_desc"] = "站台交互完成"
    
    return defaults


def handle_robot_status(data: str) -> None:
    """
    处理机器人状态消息，更新全局状态
    支持多版本解析：JSON格式 / 分隔符格式 / 新格式 / 纯字符串格式
    
    ROS 状态映射：
    - running-started: 任务启动（新格式）→ 节点2 任务确认 completed
    - running_started: 任务启动（旧格式）→ 节点2 任务确认 active
    - running_step1_navigate_to_pharmacy: 前往药房
    - running_step2_pick: 正在抓药
    - running_step3_navigate_docter: 前往医生/患者 → 节点3 扫码复合 active
    - running_step4_deliver_medicine: 正在送药 → 节点4 站台交互 active
    - running_step5_return: 正在返回
    - end: 任务完成 → 全部节点 completed
    """
    # 多版本解析
    parsed_msg = parse_ros_message(data)
    status = parsed_msg["status"]
    prescription_code = parsed_msg["prescription_code"]
    
    logger.info(f"收到 ROS 状态: {status}, 药单编码: {prescription_code}")
    
    _ros_state["last_message_time"] = datetime.now().isoformat()
    _ros_state["current_robot_status"] = status
    _ros_state["current_prescription_code"] = prescription_code
    
    steps = _ros_state["steps"]
    
    # 重置所有节点状态
    for step in steps:
        if step["status"] != "completed":
            step["status"] = "pending"
    
    # ===== 任务启动（新格式：running-started，节点2直接完成）=====
    if status == "running-started":
        _ros_state["current_step"] = 2
        steps[0]["status"] = "completed"
        steps[0]["desc"] = "处方已开具"
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "任务确认完成"
        logger.info("🟢 任务启动 - 任务确认完成")
    
    # ===== 任务启动（旧格式：running_started，节点2为进行中）=====
    elif status == "running_started":
        _ros_state["current_step"] = 2
        steps[0]["status"] = "completed"
        steps[0]["desc"] = "处方已开具"
        steps[1]["status"] = "active"
        steps[1]["desc"] = "任务已启动"
        logger.info("🟢 任务启动")
    
    # ===== 步骤1: 前往药房 =====
    elif status == "running_step1_navigate_to_pharmacy":
        _ros_state["current_step"] = 2
        steps[0]["status"] = "completed"
        steps[1]["status"] = "active"
        steps[1]["desc"] = "正在前往药房"
        logger.info("🚗 正在前往药房")
    
    elif status == "error_step1_cannot_reach_pharmacy":
        steps[1]["status"] = "active"
        steps[1]["desc"] = "到达药房失败"
        logger.warning("❌ 到达药房失败")
    
    # ===== 步骤2: 抓药 =====
    elif status == "running_step2_pick":
        _ros_state["current_step"] = 2
        steps[0]["status"] = "completed"
        steps[1]["status"] = "active"
        steps[1]["desc"] = "正在抓药"
        logger.info("🤖 正在抓药")
    
    # ===== 步骤3: 前往医生/患者 =====
    elif status == "running_step3_navigate_docter":
        _ros_state["current_step"] = 3
        steps[0]["status"] = "completed"
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "抓药完成"
        steps[2]["status"] = "active"
        steps[2]["desc"] = "前往医生/患者"
        logger.info("🚗 前往医生/患者")
    
    elif status == "error_step3_cannot_reach_patient_room":
        steps[2]["status"] = "active"
        steps[2]["desc"] = "无法到达患者房间"
        logger.warning("❌ 无法到达患者房间")
    
    # ===== 步骤4: 送药 =====
    elif status == "running_step4_deliver_medicine":
        _ros_state["current_step"] = 4
        steps[0]["status"] = "completed"
        steps[1]["status"] = "completed"
        steps[2]["status"] = "completed"
        steps[2]["desc"] = "扫码复核完成"
        steps[3]["status"] = "active"
        steps[3]["desc"] = "正在送药"
        logger.info("📦 正在送药")
    
    # ===== 步骤5: 返回 =====
    elif status == "running_step5_return":
        _ros_state["current_step"] = 4
        steps[3]["status"] = "active"
        steps[3]["desc"] = "正在返回起点"
        logger.info("🔄 正在返回起点")
    
    elif status == "error_step5_cannot_return_to_home":
        steps[3]["status"] = "active"
        steps[3]["desc"] = "无法返回起点"
        logger.warning("❌ 无法返回起点")
    
    # ===== 任务完成 =====
    elif status == "end":
        _ros_state["current_step"] = 5
        for step in steps:
            step["status"] = "completed"
        steps[0]["desc"] = "处方已开具"
        steps[1]["desc"] = "任务确认完成"
        steps[2]["desc"] = "扫码复核完成"
        steps[3]["desc"] = "站台交互完成"
        logger.info("🏁 任务完成")
    
    else:
        logger.warning(f"⚠️ 未知状态: {status}")
    
    # 如果有药单编码，更新数据库
    if prescription_code:
        update_prescription_workflow_db(prescription_code, status)


async def ros_websocket_listener() -> None:
    """
    ROS WebSocket 监听主循环
    周期性检测端口可达性，自动重连
    """
    if websockets is None:
        print("[错误] websockets 库未安装，无法启动 ROS 监听")
        logger.error("websockets 库未安装，无法启动 ROS 监听")
        return
    
    ws_url = get_ros_ws_url()
    print(f"[ROS] WebSocket 目标地址: {ws_url}")
    logger.info(f"ROS WebSocket 监听服务启动，目标地址: {ws_url}")
    
    while True:
        try:
            # 检测端口是否可达
            _ros_state["listener_state"] = ROSListenerState.CHECKING.value
            reachable = check_port_reachable(
                settings.ros_ws_host,
                settings.ros_ws_port,
                settings.ros_connect_timeout
            )
            _ros_state["ws_reachable"] = reachable
            _ros_state["last_check_time"] = datetime.now().isoformat()
            
            if not reachable:
                _ros_state["listener_state"] = ROSListenerState.DISCONNECTED.value
                logger.warning(f"ROS WebSocket 端口不可达: {ws_url}")
                # 等待下次检测
                await asyncio.sleep(settings.ros_check_interval)
                continue
            
            # 端口可达，尝试连接
            _ros_state["listener_state"] = ROSListenerState.CONNECTING.value
            logger.info(f"正在连接 ROS WebSocket: {ws_url}")
            
            try:
                async with websockets.connect(ws_url) as ws:
                    _ros_state["listener_state"] = ROSListenerState.CONNECTED.value
                    logger.info(f"✅ 已连接 ROS WebSocket: {ws_url}")
                    
                    # 订阅 Topic
                    subscribe_msg = json.dumps({
                        "op": "subscribe",
                        "topic": settings.ros_topic
                    })
                    await ws.send(subscribe_msg)
                    logger.info(f"📡 已订阅 ROS Topic: {settings.ros_topic}")
                    
                    # 持续接收消息
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(),
                                timeout=settings.ros_check_interval
                            )
                            msg_data = json.loads(message)
                            
                            # 解析 rosbridge 消息格式
                            if "msg" in msg_data and "data" in msg_data["msg"]:
                                data = msg_data["msg"]["data"]
                                print(f"[收到] ROS 消息: {data}")
                                handle_robot_status(data)
                                
                                # 任务确认时触发语音播报（使用解析后的 status）
                                parsed_msg = parse_ros_message(data)
                                status = parsed_msg["status"]
                                # 支持新旧两种格式：running-started 和 running_started
                                if status == "running-started" or status == "running_started":
                                    logger.info("🎵 任务确认 - 触发语音播报")
                                    # 异步调用语音播报服务
                                    try:
                                        from app.services.audio_service import trigger_audio_on_task_confirm
                                        await trigger_audio_on_task_confirm()
                                    except Exception as audio_err:
                                        logger.error(f"语音播报失败: {audio_err}")
                            
                        except asyncio.TimeoutError:
                            # 超时，发送 ping 保持连接
                            try:
                                await ws.ping()
                            except Exception:
                                logger.warning("WebSocket ping 失败，连接可能已断开")
                                break
                        
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("WebSocket 连接已关闭")
                            break
                        
            except Exception as conn_err:
                _ros_state["listener_state"] = ROSListenerState.RECONNECTING.value
                logger.error(f"WebSocket 连接失败: {conn_err}")
            
            # 等待下次重连
            logger.info(f"等待 {settings.ros_check_interval} 秒后重连...")
            await asyncio.sleep(settings.ros_check_interval)
            
        except asyncio.CancelledError:
            logger.info("ROS WebSocket 监听任务被取消")
            _ros_state["listener_state"] = ROSListenerState.STOPPED.value
            break
        
        except Exception as e:
            logger.error(f"ROS 监听异常: {e}")
            _ros_state["listener_state"] = ROSListenerState.RECONNECTING.value
            await asyncio.sleep(settings.ros_check_interval)


async def start_ros_listener() -> None:
    """启动 ROS 监听服务（供 lifespan 调用）"""
    print("=" * 60)
    print("ROS WebSocket 监听服务启动中...")
    print("=" * 60)
    logger.info("启动 ROS WebSocket 监听服务...")
    await ros_websocket_listener()