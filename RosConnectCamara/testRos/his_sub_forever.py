import websocket
import json
import time

ws = websocket.create_connection("ws://192.168.51.12:9090")

# 1️⃣ 注册 topic（注意类型必须完全一致）
ws.send(json.dumps({
    "op": "advertise",
    "topic": "/his_sub",
    "type": "his_sub/HisSub"
}))

time.sleep(1)

print("已注册 topic")

# 2️⃣ 循环发送
while True:

    msg = {
        "data": "start",
        "prescription_code": "200218699269"
    }

    ws.send(json.dumps({
        "op": "publish",
        "topic": "/his_sub",
        "msg": msg
    }))

    print("发送成功:", msg)

    time.sleep(1)