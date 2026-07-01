"""ROS WebSocket 监听模块。

通过 rosbridge 协议连接 ROS，订阅指定 topic 并接收消息。
"""

import json
import websocket
from typing import Callable, Optional
from config import ROS_BRIDGE_URL, ROS_TOPIC, ROS_MESSAGE_TYPE


class ROSListener:
    """ROS WebSocket 监听器。

    连接到 rosbridge 服务器，订阅指定 topic 并接收消息。

    Attributes:
        url: rosbridge WebSocket 地址。
        topic: 要订阅的 ROS topic。
        message_type: ROS 消息类型。
        callback: 收到消息时的回调函数。
        ws: WebSocket 应用实例。
    """

    def __init__(self, callback: Callable[[str], None]):
        """初始化 ROS 监听器。

        Args:
            callback: 收到消息时的回调函数，接收消息内容字符串。
        """
        self.url = ROS_BRIDGE_URL
        self.topic = ROS_TOPIC
        self.message_type = ROS_MESSAGE_TYPE
        self.callback = callback
        self.ws: Optional[websocket.WebSocketApp] = None

    def _on_message(self, ws, message):
        """WebSocket 消息回调。

        解析 rosbridge 消息格式，提取 data 字段并调用用户回调。

        Args:
            ws: WebSocket 实例。
            message: 收到的原始消息。
        """
        try:
            msg = json.loads(message)

            # rosbridge 标准格式: {"op": "publish", "topic": "...", "msg": {"data": "..."}}
            if "msg" in msg and "data" in msg["msg"]:
                data = msg["msg"]["data"]
                print(f"[ROS] 收到消息: {data}")
                self.callback(data)
            else:
                print(f"[ROS] 非标准消息格式: {msg}")

        except json.JSONDecodeError as e:
            print(f"[ROS] JSON 解析错误: {e}")
        except Exception as e:
            print(f"[ROS] 消息处理错误: {e}")

    def _on_open(self, ws):
        """WebSocket 连接成功回调。

        连接成功后自动订阅指定 topic。

        Args:
            ws: WebSocket 实例。
        """
        print(f"[ROS] 已连接到 {self.url}")

        # 订阅 topic
        subscribe_msg = {
            "op": "subscribe",
            "topic": self.topic,
            "type": self.message_type
        }
        ws.send(json.dumps(subscribe_msg))
        print(f"[ROS] 已订阅 topic: {self.topic}")

    def _on_error(self, ws, error):
        """WebSocket 错误回调。

        Args:
            ws: WebSocket 实例。
            error: 错误信息。
        """
        print(f"[ROS] 连接错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 关闭回调。

        Args:
            ws: WebSocket 实例。
            close_status_code: 关闭状态码。
            close_msg: 关闭消息。
        """
        print(f"[ROS] 连接关闭 (状态码: {close_status_code}, 消息: {close_msg})")

    def start(self):
        """启动 ROS 监听器。

        创建 WebSocket 连接并开始监听消息，阻塞运行。
        """
        print(f"[ROS] 启动监听器，目标: {self.url}, topic: {self.topic}")

        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # 阻塞运行
        self.ws.run_forever()

    def stop(self):
        """停止 ROS 监听器。

        关闭 WebSocket 连接。
        """
        if self.ws:
            self.ws.close()
            print("[ROS] 监听器已停止")