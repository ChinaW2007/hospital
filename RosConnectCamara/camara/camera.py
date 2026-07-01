"""海康威视摄像头语音播报控制模块。

封装海康威视ISAPI接口，通过 audioID 直接播放对应的语音文件。
"""

import time
import requests
from requests.auth import HTTPDigestAuth
from config import CAMERA_IP, USERNAME, PASSWORD, PLAY_INTERVAL


class HikvisionCamera:
    """海康威视摄像头控制器。

    通过 ISAPI 的 /AudioAlarm/{audio_id}/test 接口直接播放指定语音，
    无需预先切换配置，播放即时生效。

    Attributes:
        base_url: 摄像头API基础地址。
        auth: HTTP摘要认证对象。
        headers: 请求头字典。
    """

    def __init__(self):
        """初始化摄像头控制器，建立连接配置。"""
        self.base_url = f"http://{CAMERA_IP}"
        self.auth = HTTPDigestAuth(USERNAME, PASSWORD)

        self.headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        }

    # =========================
    # 播放指定语音（支持重复播放）
    # =========================
    def play(self, audio_id: int, repeat: int = 1):
        """播放指定ID的语音，支持重复播放。

        通过 /AudioAlarm/{audio_id}/test 接口直接触发播放，
        不同 audio_id 对应不同的语音文件，无需预先切换配置。

        Args:
            audio_id: 语音文件ID（可通过 capabilities 接口查询可用列表）。
            repeat: 重复播放次数，默认为1次。
        """
        url = f"{self.base_url}/ISAPI/Event/triggers/notifications/AudioAlarm/{audio_id}/test?format=json"

        for i in range(repeat):
            print(f"\n--- 第 {i + 1}/{repeat} 次播放 (音频ID={audio_id}) ---")

            r = requests.put(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=5
            )

            print("HTTP:", r.status_code)

            if r.status_code == 200:
                print("播放成功")
            else:
                print("播放失败:", r.text)

            # 多次播放时，添加间隔防止摄像头卡顿
            if i < repeat - 1:
                time.sleep(PLAY_INTERVAL)
