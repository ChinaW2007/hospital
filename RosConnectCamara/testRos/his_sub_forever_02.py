import websocket
import json
import time

ws = websocket.create_connection(
    "ws://192.168.51.43:9090"
)

# 只注册一次 Topic
ws.send(json.dumps({
    "op": "advertise",
    "topic": "/his_sub_02",
    "type": "std_msgs/String"
}))

time.sleep(1)

# 循环不间断发送 data="start"
while True:
    ws.send(json.dumps({
        "op": "publish",
        "topic": "/his_sub_02",
        "msg": {
            "data": "start"
        }
    }))
    print("已发送: start")
    time.sleep(1)