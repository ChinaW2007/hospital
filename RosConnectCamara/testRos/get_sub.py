import websocket
import json

def on_message(ws, message):
    print("收到：", message)

def on_open(ws):

    print("连接成功")

    # 订阅Topic
    ws.send(json.dumps({
        "op":"subscribe",
        "topic":"/car01_pub",
        "type":"std_msgs/String"
    }))

ws = websocket.WebSocketApp(
    "ws://192.168.51.12:9090",
    on_open=on_open,
    on_message=on_message
)

ws.run_forever()