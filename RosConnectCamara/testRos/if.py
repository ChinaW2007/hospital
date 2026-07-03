import websocket
import json

# =========================
# 任务状态解析函数
# =========================
def handle_robot_state(data):

    print("收到ROS状态:", data)

    # ===== 任务开始 =====
    if "running-started" in data:
        print("🟢 任务启动")

    # ===== Step 1 =====
    elif data == "running_step1_navigate_to_pharmacy":
        print("🚗 正在前往药房")

    elif data == "error_step1_cannot_reach_pharmacy":
        print("❌ 到达药房失败")

    # ===== Step 2 =====
    elif data == "running_step2_pick":
        print("🤖 正在抓药")

    # ===== Step 3 =====
    elif data == "running_step3_navigate_docter":
        print("🚗 前往医生/患者")

    elif data == "error_step3_cannot_reach_patient_room":
        print("❌ 无法到达患者房间")

    # ===== Step 4 =====
    elif data == "running_step4_deliver_medicine":
        print("📦 正在送药")

    # ===== Step 5 =====
    elif data == "running_step5_return":
        print("🔄 正在返回起点")

    elif data == "error_step5_cannot_return_to_home":
        print("❌ 无法返回起点")

    # ===== 结束 =====
    elif data == "end":
        print("🏁 任务完成")

    else:
        print("⚠ 未知状态:", data)


# =========================
# WebSocket 回调
# =========================
def on_message(ws, message):

    try:
        msg = json.loads(message)

        # rosbridge标准格式
        if "msg" in msg and "data" in msg["msg"]:

            data = msg["msg"]["data"]

            handle_robot_state(data)

    except Exception as e:
        print("解析错误:", e)


def on_open(ws):

    print("✅ 已连接ROS rosbridge")

    # 订阅你的状态Topic
    ws.send(json.dumps({
        "op": "subscribe",
        "topic": "/car01_pub"
    }))

    print("📡 已订阅 /car01_pub")


def on_error(ws, error):
    print("❌ 错误:", error)


def on_close(ws, close_status_code, close_msg):
    print("🔌 连接关闭")


# =========================
# 主程序
# =========================
if __name__ == "__main__":

    ws = websocket.WebSocketApp(
        "ws://192.168.51.12:9090",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()