import websocket
import json
import time

ws = websocket.create_connection(
    "ws://192.168.51.12:9090"
)


# 先注册Topic
ws.send(json.dumps({
    "op": "advertise",
    "topic": "/his_sub",
    "type": "std_msgs/String"
}))


time.sleep(1)

# 再发布
ws.send(json.dumps({
    "op": "publish",
    "topic": "/his_sub",
    "msg": {
        "data": "start"
    }
}))


time.sleep(2)

ws.close()