"""音频触发逻辑模块。

根据 ROS 消息内容触发摄像头播放对应的语音。
"""

import time
import requests
from requests.auth import HTTPDigestAuth
from typing import Optional, Tuple
from config import (
    CAMERA_IP,
    CAMERA_USERNAME,
    CAMERA_PASSWORD,
    AUDIO_TRIGGER_RULES,
    PLAY_INTERVAL
)


class AudioTrigger:
    """音频触发器。

    根据预定义的规则，将 ROS 消息映射到摄像头音频播放。

    Attributes:
        base_url: 摄像头 API 基础地址。
        auth: HTTP 摘要认证对象。
        headers: 请求头字典。
    """

    def __init__(self):
        """初始化音频触发器。"""
        self.base_url = f"http://{CAMERA_IP}"
        self.auth = HTTPDigestAuth(CAMERA_USERNAME, CAMERA_PASSWORD)
        self.headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        }

    def _play_audio(self, audio_id: int, repeat: int = 1) -> bool:
        """播放指定 ID 的语音。

        通过海康威视 ISAPI 接口触发摄像头播放语音。

        Args:
            audio_id: 语音文件 ID。
            repeat: 重复播放次数。

        Returns:
            bool: 是否播放成功。
        """
        url = f"{self.base_url}/ISAPI/Event/triggers/notifications/AudioAlarm/{audio_id}/test?format=json"

        for i in range(repeat):
            print(f"[音频] 第 {i + 1}/{repeat} 次播放 (音频ID={audio_id})")

            try:
                r = requests.put(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    timeout=5
                )

                if r.status_code == 200:
                    print(f"[音频] 播放成功")
                else:
                    print(f"[音频] 播放失败: HTTP {r.status_code}, {r.text}")
                    return False

                # 多次播放时添加间隔
                if i < repeat - 1:
                    time.sleep(PLAY_INTERVAL)

            except requests.exceptions.Timeout:
                print(f"[音频] 连接超时")
                return False
            except requests.exceptions.RequestException as e:
                print(f"[音频] 请求错误: {e}")
                return False

        return True

    def handle_message(self, message: str) -> bool:
        """处理 ROS 消息并触发对应音频。

        根据配置的规则映射，将消息转换为音频播放。

        Args:
            message: ROS 消息内容。

        Returns:
            bool: 是否成功触发音频播放。
        """
        # 查找匹配的规则
        rule = AUDIO_TRIGGER_RULES.get(message)

        if rule:
            audio_id, repeat = rule
            print(f"[触发] 消息 '{message}' -> 音频 ID={audio_id}, 播放{repeat}次")
            return self._play_audio(audio_id, repeat)
        else:
            print(f"[触发] 消息 '{message}' 无匹配规则，跳过")
            return False

    def list_rules(self):
        """打印当前所有音频触发规则。"""
        print("\n=== 当前音频触发规则 ===")
        for message, (audio_id, repeat) in AUDIO_TRIGGER_RULES.items():
            print(f"  '{message}' -> 音频ID={audio_id}, 播放{repeat}次")
        print("========================\n")