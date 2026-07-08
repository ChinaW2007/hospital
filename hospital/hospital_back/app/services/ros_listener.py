"""
ROS WebSocket 监听服务（顺序结构版）

核心改变：
- 消息处理逻辑从巨大的内联代码块提取为独立的 handle_ros_message() 函数
- 语音播报逻辑提取为 handle_audio_broadcast() 函数
- 主循环职责单一：接收消息 → 调用处理函数

功能保持不变：
- 周期性端口检测、自动重连
- 所有消息解析和处理（新旧格式兼容）
- 语音播报（car_can_go, car_already_arrive）
- HIS处方状态更新、workflow数据库更新
- 所有外部接口和详细日志
"""
import asyncio
import json
import socket
import logging
import pymysql
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
    "current_prescription_code": None,
    "current_medicine_id": None,
    "current_step": 1,
    "steps": [
        {"id": 1, "name": "开具处方", "status": "pending", "desc": "等待处方开具"},
        {"id": 2, "name": "任务确认", "status": "pending", "desc": "等待任务启动"},
        {"id": 3, "name": "扫码复合", "status": "pending", "desc": "等待扫码复核"},
        {"id": 4, "name": "站台交互", "status": "pending", "desc": "等待站台交互"},
    ]
}

# ===== 语音播报状态（按单子触发） =====
_audio_state: Dict[str, Any] = {
    "car_can_go_triggered": False,
    "car_already_arrive_triggered": False,
    "current_prescription_code": None,
}


def get_ros_state() -> Dict[str, Any]:
    """获取当前 Ros 监听状态（供 API 使用）"""
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


# ===== 消息解析 =====

def parse_ros_message(data: str) -> Dict[str, Any]:
    """
    解析 Ros 消息，多版本适配

    支持格式：
    1. JSON 格式: {"status": "running_started", "prescription_code": "RX..."}
    2. 分隔符格式（竖线）: "running_started|RX..."
    3. 新格式（药品坐标发送）: "{medicine_id}_{prescription_code}_{status}"
       例如："1_012026070300122_running-started"
    4. 处方完成格式: "{prescription_code}_all_completed"
    5. 任务结束格式: "{prescription_code}_end"
    6. 旧格式: "{prescription_code}_running-started"
    """
    # 尝试解析 JSON 格式
    if data.startswith("{") and data.endswith("}"):
        try:
            msg = json.loads(data)
            return {
                "status": msg.get("status", ""),
                "prescription_code": msg.get("prescription_code"),
                "medicine_id": msg.get("medicine_id")
            }
        except json.JSONDecodeError:
            pass

    # 尝试解析分隔符格式（竖线）
    if "|" in data:
        parts = data.split("|")
        return {
            "status": parts[0],
            "prescription_code": parts[1] if len(parts) > 1 else None,
            "medicine_id": None
        }

    # 解析药品坐标发送格式 {medicine_id}_{prescription_code}_{status}
    parts = data.split("_")
    if len(parts) >= 3:
        try:
            medicine_id = int(parts[0])
            prescription_code = parts[1]
            status = "_".join(parts[2:])
            return {
                "status": status,
                "prescription_code": prescription_code,
                "medicine_id": medicine_id
            }
        except ValueError:
            pass

    # 解析旧格式 {prescription_code}_{status}
    if len(parts) == 2:
        return {
            "status": parts[1],
            "prescription_code": parts[0],
            "medicine_id": None
        }

    # 纯字符串格式（旧版本兼容）
    return {
        "status": data,
        "prescription_code": None,
        "medicine_id": None
    }


# ===== 数据库更新 =====

def update_prescription_workflow_db(prescription_code: str, status: str, medicine_id: Optional[int] = None) -> bool:
    """
    更新处方流程状态到数据库

    Args:
        prescription_code: 药单编码
        status: ROS 状态
        medicine_id: 药品ID（可选，新格式）

    Returns:
        bool: 是否更新成功
    """
    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            node_updates = get_node_updates_from_status(status)

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

            medicine_info = f", 药品ID={medicine_id}" if medicine_id else ""
            print(f"[成功] 更新处方流程状态: {prescription_code}{medicine_info} -> {status}")
            logger.info(f"已更新处方流程状态: {prescription_code}{medicine_info} -> {status}")

            # 修复：HIS处方状态更新移到 end 处理中（仅最后一个药品完成时调用）
            return True

    except Exception as e:
        print(f"[失败] 更新处方流程状态失败: {e}")
        logger.error(f"更新处方流程状态失败: {e}")
        return False


def update_his_prescription_status(prescription_code: str) -> bool:
    """
    更新 HIS MySQL prescriptions 表状态为 dispensed

    修复：只在最后一个药品完成时调用（不是每个药品的end都更新）
    """
    try:
        his_conn = pymysql.connect(
            host=settings.his_mysql_host,
            port=settings.his_mysql_port,
            user=settings.his_mysql_user,
            password=settings.his_mysql_pass,
            database=settings.his_mysql_db,
            charset="utf8mb4",
            connect_timeout=5
        )
        with his_conn.cursor() as his_cursor:
            his_cursor.execute("""
                UPDATE prescriptions
                SET status = 'dispensed'
                WHERE prescription_code = %s AND status = 'pending'
            """, (prescription_code,))
            his_conn.commit()

            affected_rows = his_cursor.rowcount
            if affected_rows > 0:
                print(f"[成功] HIS处方状态更新: {prescription_code} -> dispensed（最后一个药品完成）")
                logger.info(f"HIS处方状态更新: {prescription_code} -> dispensed")
            else:
                print(f"[警告] HIS处方未找到或状态已更新: {prescription_code}")
                logger.warning(f"HIS处方未找到或状态已更新: {prescription_code}")

        his_conn.close()
        return True

    except pymysql.Error as e:
        print(f"[失败] HIS MySQL同步失败: {e}")
        logger.error(f"HIS MySQL同步失败: {e}")
        return False
    except Exception as e:
        print(f"[失败] HIS MySQL同步异常: {e}")
        logger.error(f"HIS MySQL同步异常: {e}")
        return False


def get_node_updates_from_status(status: str) -> Dict[str, Any]:
    """
    根据 ROS 状态获取节点更新数据

    支持新旧两种格式：
    - 新格式（横线）: running-started, running-step1-navigate-to-pharmacy, all_completed 等
    - 旧格式（下划线）: running_started, running_step1_navigate_to_pharmacy 等
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
    if status == "running-started":
        defaults["current_node"] = 2
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
    elif status == "running_started":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "任务已确认"

    # ===== 所有药品完成抓取 =====
    elif status == "all_completed":
        defaults["current_node"] = 3
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成（所有药品已抓取）"
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "正在扫码复核"
        defaults["node4_status"] = "pending"
        defaults["node4_desc"] = "等待站台交互"

    # ===== Step 1: 前往药房 =====
    elif status == "running-step1-navigate-to-pharmacy":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在前往药房"
    elif status == "error-step1-cannot-reach-pharmacy":
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "到达药房失败"
    elif status == "running_step1_navigate_to_pharmacy":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在前往药房"
    elif status == "error_step1_cannot_reach_pharmacy":
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "到达药房失败"

    # ===== Step 2: 抓药 =====
    elif status == "running-step2-pick":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在抓药"
    elif status == "running_step2_pick":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在抓药"

    # ===== Step 3: 前往病房 =====
    elif status == "running-step3-navigate-doctor":
        defaults["current_node"] = 3
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "前往病房"
    elif status == "error-step3-cannot-reach-patient-room":
        defaults["node3_status"] = "active"
        defaults["node3_desc"] = "无法到达病房"
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
    elif status == "running-step4-deliver-medicine":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在送药"
    elif status == "running_step4_deliver_medicine":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在送药"

    # ===== Step 5: 返回 =====
    elif status == "running-step5-return":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "正在返回起点"
    elif status == "error-step5-cannot-return-to-home":
        defaults["node4_status"] = "active"
        defaults["node4_desc"] = "无法返回起点"
    elif status == "running_step5_return":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node2_desc"] = "任务确认完成"
        defaults["node3_status"] = "completed"
        defaults["node3_desc"] = "扫码复合完成"
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


# ===== 机器人状态处理（更新全局状态和数据库）=====

def handle_robot_status(data: str) -> None:
    """
    处理机器人状态消息，更新全局状态

    支持多版本解析：JSON格式 / 分隔符格式 / 新格式 / 纯字符串格式

    ROS 状态映射：
    - running-started: 任务启动 → 节点2 任务确认 completed
    - all_completed: 所有药品完成 → 节点2 completed, 节点3 active
    - running-step5-return: 送药返回 → 节点3 completed, 节点4 active
    - end: 任务完成 → 全部节点 completed
    """
    parsed_msg = parse_ros_message(data)
    status = parsed_msg["status"]
    prescription_code = parsed_msg["prescription_code"]
    medicine_id = parsed_msg.get("medicine_id")

    medicine_info = f", 药品ID={medicine_id}" if medicine_id else ""
    logger.info(f"收到 ROS 状态: {status}, 药单编码: {prescription_code}{medicine_info}")

    _ros_state["last_message_time"] = datetime.now().isoformat()
    _ros_state["current_robot_status"] = status
    _ros_state["current_prescription_code"] = prescription_code
    _ros_state["current_medicine_id"] = medicine_id

    steps = _ros_state["steps"]

    # 重置所有节点状态
    for step in steps:
        if step["status"] != "completed":
            step["status"] = "pending"

    # ===== 任务启动 =====
    if status == "running-started":
        _ros_state["current_step"] = 2
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "任务确认完成"

    # ===== 所有药品完成抓取 =====
    elif status == "all_completed":
        _ros_state["current_step"] = 3
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "任务确认完成（所有药品已抓取）"
        steps[2]["status"] = "active"
        steps[2]["desc"] = "正在扫码复核"

    # ===== 送药返回 =====
    elif status == "running-step5-return" or status == "running_step5_return":
        _ros_state["current_step"] = 4
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "任务确认完成"
        steps[2]["status"] = "completed"
        steps[2]["desc"] = "扫码复合完成"
        steps[3]["status"] = "active"
        steps[3]["desc"] = "正在返回起点"

    # ===== 任务完成 =====
    elif status == "end":
        _ros_state["current_step"] = 5
        steps[1]["status"] = "completed"
        steps[1]["desc"] = "任务确认完成"
        steps[2]["status"] = "completed"
        steps[2]["desc"] = "扫码复合完成"
        steps[3]["status"] = "completed"
        steps[3]["desc"] = "站台交互完成"

    # 更新数据库
    if prescription_code:
        update_prescription_workflow_db(prescription_code, status, medicine_id)


# ===== 语音播报处理 =====

async def handle_audio_broadcast(status: str, prescription_code: str, medicine_id: Optional[int]) -> None:
    """
    处理语音播报（从主消息处理流程中提取）

    规则：
    - car_can_go (audio_id=15): 第一个药品收到 running-started 时触发一次
    - car_already_arrive (audio_id=14): 最后一个药品收到 end 时触发两次（间隔2秒）
    """
    from app.services.audio_service import play_audio_async

    # ===== 药品任务启动：car_can_go 语音播报 =====
    if status == "running-started" or status == "running_started":
        if medicine_id is not None and prescription_code:
            # 检查处方编码是否更新（新单子）
            if _audio_state["current_prescription_code"] != prescription_code:
                _audio_state["current_prescription_code"] = prescription_code
                _audio_state["car_can_go_triggered"] = False
                _audio_state["car_already_arrive_triggered"] = False
                print(f"[ROS Listener] 新单子开始，重置语音播报状态")

            # 触发 car_can_go（单子开始）
            if not _audio_state["car_can_go_triggered"]:
                print(f"[ROS Listener] 触发语音播报：单子开始（car_can_go）")
                try:
                    await play_audio_async(15)
                    _audio_state["car_can_go_triggered"] = True
                    print(f"[ROS Listener] 语音播报成功：car_can_go")
                except Exception as audio_err:
                    logger.error(f"语音播报失败: {audio_err}")
                    print(f"[ROS Listener] 语音播报失败: {audio_err}")
            else:
                print(f"[ROS Listener] car_can_go 已触发过，不重复播放")
        else:
            # 旧格式（没有药品ID），说明是任务确认（节点2）
            logger.info("任务确认 - 触发语音播报")
            try:
                from app.services.audio_service import trigger_audio_on_task_confirm
                await trigger_audio_on_task_confirm()
            except Exception as audio_err:
                logger.error(f"语音播报失败: {audio_err}")

    # ===== 药品完成：car_already_arrive 语音播报 + HIS状态更新 =====
    elif status == "end":
        if medicine_id is not None and prescription_code:
            # 判断是否是最后一个药品
            try:
                from app.services.his_sender import get_sender_status
                sender_status = get_sender_status()
                current_medicine_index = sender_status.get("current_medicine_index", 0)  # 从1开始
                medicine_total = sender_status.get("medicine_total", 0)
                is_last_medicine = (current_medicine_index == medicine_total)

                print(f"[ROS Listener] 药品状态:")
                print(f"[ROS Listener]   当前药品序号: {current_medicine_index}")
                print(f"[ROS Listener]   药品总数: {medicine_total}")
                print(f"[ROS Listener]   是否是最后一个药品: {is_last_medicine}")

                # 仅在最后一个药品收到end时触发语音播报和HIS状态更新
                if is_last_medicine and not _audio_state["car_already_arrive_triggered"]:
                    print(f"[ROS Listener] 触发语音播报：单子完成（最后一个药品收到 end）")
                    try:
                        print(f"[ROS Listener] 播放 audio_id=14 (car_already_arrive) - 第1次")
                        await play_audio_async(14)
                        print(f"[ROS Listener] 等待2秒...")
                        await asyncio.sleep(2)
                        print(f"[ROS Listener] 播放 audio_id=14 (car_already_arrive) - 第2次")
                        await play_audio_async(14)
                        _audio_state["car_already_arrive_triggered"] = True
                        print(f"[ROS Listener] 语音播报成功：car_already_arrive")
                    except Exception as audio_err:
                        logger.error(f"语音播报失败: {audio_err}")
                        print(f"[ROS Listener] 语音播报失败: {audio_err}")

                    # 修复：仅在最后一个药品完成时更新HIS处方状态为dispensed
                    print(f"[ROS Listener] 最后一个药品完成，更新HIS处方状态为dispensed")
                    update_his_prescription_status(prescription_code)

                elif not is_last_medicine:
                    print(f"[ROS Listener] 不是最后一个药品，暂不触发 car_already_arrive，不更新HIS状态")
                else:
                    print(f"[ROS Listener] car_already_arrive 已触发过，不重复播放")
            except Exception as status_err:
                logger.error(f"获取药品状态失败: {status_err}")
                print(f"[ROS Listener] 获取药品状态失败: {status_err}")


# ===== ROS 消息处理（核心分发函数）=====

async def handle_ros_message(data: str) -> None:
    """
    处理收到的 ROS 消息（从主循环中提取的核心函数）

    逻辑：
    1. 解析消息，执行去0检查（medicine_id=0 的消息直接忽略）
    2. 更新全局状态和数据库（handle_robot_status）
    3. 根据消息类型通知 HIS Sender（通过 notify_* 接口）
    4. 触发语音播报（handle_audio_broadcast）
    """
    # 先解析消息，用于去0检查
    parsed_msg = parse_ros_message(data)
    status = parsed_msg["status"]
    prescription_code = parsed_msg["prescription_code"]
    medicine_id = parsed_msg.get("medicine_id")

    # 去0机制：medicine_id=0 的消息是无效的（ROS端初始化默认值），直接忽略
    # 避免 medicine_id=0 的 started/step 消息干扰 HIS Sender 的状态机
    if medicine_id == 0:
        print(f"\n[ROS Listener] [去0机制] 忽略 medicine_id=0 的消息: {data}")
        return

    # 更新全局状态和数据库
    handle_robot_status(data)

    # 详细日志打印
    print(f"\n[ROS Listener] 收到消息解析结果:")
    print(f"[ROS Listener]   原始消息: {data}")
    print(f"[ROS Listener]   解析后:")
    print(f"[ROS Listener]     status: {status}")
    print(f"[ROS Listener]     prescription_code: {prescription_code}")
    print(f"[ROS Listener]     medicine_id: {medicine_id}")
    print(f"[ROS Listener]     medicine_id类型: {type(medicine_id)}")

    # ===== 药品任务启动：通知 HIS Sender 切换为 running =====
    if status == "running-started" or status == "running_started":
        if medicine_id is not None and prescription_code:
            logger.info(f"药品任务启动: ID={medicine_id}, 处方={prescription_code}")
            print(f"[ROS Listener] 药品任务启动: ID={medicine_id}, 处方={prescription_code}")
            try:
                from app.services.his_sender import notify_medicine_started
                notify_medicine_started(medicine_id, prescription_code)
            except Exception as sender_err:
                logger.error(f"通知 HIS Sender 失败: {sender_err}")
                print(f"[ROS Listener] ERROR: 通知 HIS Sender 失败: {sender_err}")

    # ===== 所有药品完成：通知 HIS Sender 停止发送 =====
    elif status == "all_completed":
        logger.info(f"所有药品完成抓取: {prescription_code}")
        print(f"[ROS Listener] 所有药品完成抓取: {prescription_code}")
        try:
            from app.services.his_sender import notify_all_medicines_completed
            notify_all_medicines_completed(prescription_code)
        except Exception as sender_err:
            logger.error(f"通知 HIS Sender 失败: {sender_err}")

    # ===== 药单完成（Step5返回）：通知 HIS Sender 发送end =====
    elif status == "running-step5-return" or status == "running_step5_return":
        print(f"[ROS Listener] 判断是否有药品ID:")
        print(f"[ROS Listener]   medicine_id值: {medicine_id}")
        print(f"[ROS Listener]   medicine_id is None: {medicine_id is None}")
        print(f"[ROS Listener]   prescription_code值: {prescription_code}")

        # 区分药单级和药品级消息
        if medicine_id is None and prescription_code:
            # 药单级消息：{prescription_code}_running-step5-return
            print(f"[ROS Listener] 进入【药单级消息分支】- 药单完成，触发发送end")
            logger.info(f"药单完成: 处方={prescription_code}")
            print(f"[ROS Listener] 药单完成: 处方={prescription_code}")

            try:
                from app.services.his_sender import notify_prescription_step5_return
                notify_prescription_step5_return(prescription_code)
                print(f"[ROS Listener] 已调用 notify_prescription_step5_return()")
            except Exception as sender_err:
                logger.error(f"通知 HIS Sender 失败: {sender_err}")
                print(f"[ROS Listener] ERROR: 通知 HIS Sender 失败: {sender_err}")

        elif medicine_id is not None and prescription_code:
            # 药品级消息（旧格式，不处理）
            print(f"[ROS Listener] 收到药品级running-step5-return（旧格式），不处理")
            logger.info(f"收到药品级running-step5-return: ID={medicine_id}, 处方={prescription_code}")
        else:
            print(f"[ROS Listener] running-step5-return消息格式异常，缺少关键字段")

    # ===== 药品完成：通知 HIS Sender 切换药品 =====
    elif status == "end":
        print(f"[ROS Listener] 判断是否有药品ID:")
        print(f"[ROS Listener]   medicine_id值: {medicine_id}")
        print(f"[ROS Listener]   medicine_id is None: {medicine_id is None}")
        print(f"[ROS Listener]   prescription_code值: {prescription_code}")

        if medicine_id is not None and prescription_code:
            # 药品级消息：{medicine_id}_{prescription_code}_end
            print(f"[ROS Listener] 进入【药品级end消息分支】- 药品完成，触发切换")
            logger.info(f"药品完成: ID={medicine_id}, 处方={prescription_code}")
            print(f"[ROS Listener] 药品完成: ID={medicine_id}, 处方={prescription_code}")

            # 通知 HIS Sender（顺序结构下仅记录日志，切换由for循环处理）
            try:
                from app.services.his_sender import notify_medicine_completed
                notify_medicine_completed(medicine_id, prescription_code)
                print(f"[ROS Listener] 已调用 notify_medicine_completed()")
            except Exception as sender_err:
                logger.error(f"通知 HIS Sender 失败: {sender_err}")
                print(f"[ROS Listener] ERROR: 通知 HIS Sender 失败: {sender_err}")

        elif medicine_id is None and prescription_code:
            # 药单级end消息（任务完成）
            print(f"[ROS Listener] 收到药单级end消息，任务完成")
            logger.info(f"收到药单级end消息: 处方={prescription_code}")
            try:
                from app.services.his_sender import notify_task_completed
                notify_task_completed(prescription_code)
            except Exception as sender_err:
                logger.error(f"通知 HIS Sender 失败: {sender_err}")
        else:
            print(f"[ROS Listener] end消息格式异常，缺少关键字段")

    # ===== 语音播报处理 =====
    await handle_audio_broadcast(status, prescription_code, medicine_id)


# ===== ROS WebSocket 监听主循环 =====

async def ros_websocket_listener() -> None:
    """
    ROS WebSocket 监听主循环（顺序结构版）

    职责单一：
    1. 周期性检测端口可达性
    2. 自动连接和重连
    3. 接收消息 → 调用 handle_ros_message() 处理

    消息处理逻辑全部在 handle_ros_message() 中，主循环不做任何业务逻辑判断
    """
    ws_url = get_ros_ws_url()

    logger.info(f"启动 ROS WebSocket 监听服务，目标: {ws_url}")

    while True:
        try:
            # 1. 检测端口可达性
            ws_reachable = check_port_reachable(
                settings.ros_ws_host,
                settings.ros_ws_port,
                timeout=5
            )

            _ros_state["ws_reachable"] = ws_reachable
            _ros_state["last_check_time"] = datetime.now().isoformat()

            if not ws_reachable:
                _ros_state["listener_state"] = ROSListenerState.DISCONNECTED.value
                logger.warning(f"ROS WebSocket 端口不可达: {ws_url}")
                await asyncio.sleep(settings.ros_check_interval)
                continue

            # 2. 端口可达，尝试连接
            _ros_state["listener_state"] = ROSListenerState.CONNECTING.value
            logger.info(f"正在连接 ROS WebSocket: {ws_url}")

            try:
                async with websockets.connect(ws_url) as ws:
                    _ros_state["listener_state"] = ROSListenerState.CONNECTED.value
                    logger.info(f"已连接 Ros WebSocket: {ws_url}")
                    print(f"[成功] 已连接 Ros WebSocket: {ws_url}")

                    # 3. 订阅 Topic（添加 type 字段）
                    subscribe_msg = json.dumps({
                        "op": "subscribe",
                        "topic": settings.ros_topic,
                        "type": "std_msgs/String"
                    })
                    await ws.send(subscribe_msg)
                    print(f"[订阅] 已发送订阅请求: topic={settings.ros_topic}, type=std_msgs/String")

                    # 主动读取 subscribe 确认消息
                    try:
                        confirm = await asyncio.wait_for(ws.recv(), timeout=3)
                        print(f"[订阅] rosbridge 确认: {confirm}")
                    except asyncio.TimeoutError:
                        print(f"[订阅] 等待确认超时（3秒），继续监听消息...")
                    except Exception as e:
                        print(f"[订阅] 读取确认异常: {e}，继续监听消息...")

                    # 4. 持续接收消息
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(),
                                timeout=settings.ros_check_interval
                            )
                            msg_data = json.loads(message)

                            # 打印原始消息（便于诊断）
                            print(f"[ROS Listener] 收到原始消息: {message[:200]}")

                            # 解析 rosbridge 消息格式
                            if "msg" in msg_data and "data" in msg_data["msg"]:
                                data = msg_data["msg"]["data"]
                                print(f"[收到] ROS 消息: {data}")

                                # 调用消息处理函数（所有业务逻辑在此函数中）
                                await handle_ros_message(data)
                            else:
                                print(f"[ROS Listener] [警告] 消息格式不符合预期，已跳过:")
                                print(f"[ROS Listener]   期望: {{'msg': {{'data': '...'}}}}")
                                print(f"[ROS Listener]   实际: {msg_data}")

                        except asyncio.TimeoutError:
                            # 超时，发送 ping 保持连接
                            try:
                                await ws.ping()
                            except Exception as ping_err:
                                print(f"[ROS Listener] [警告] WebSocket ping 失败，连接可能已断开: {ping_err}")
                                logger.warning(f"WebSocket ping 失败: {ping_err}")
                                break

                        except websockets.exceptions.ConnectionClosed as close_err:
                            print(f"[ROS Listener] [警告] WebSocket 连接已关闭: {close_err}")
                            logger.warning(f"WebSocket 连接已关闭: {close_err}")
                            break

            except Exception as conn_err:
                _ros_state["listener_state"] = ROSListenerState.RECONNECTING.value
                print(f"[ROS Listener] [错误] WebSocket 连接失败: {conn_err}")
                logger.error(f"WebSocket 连接失败: {conn_err}")

            # 等待下次重连
            print(f"[ROS Listener] 等待 {settings.ros_check_interval} 秒后重连...")
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
    print("支持消息格式：{medicine_id}_{prescription_code}_{status}")
    print("=" * 60)
    logger.info("启动 ROS WebSocket 监听服务...")
    await ros_websocket_listener()
