"""语音播报规则引擎模块。

负责根据接收到的 audio_id，通过 if 条件判断触发对应的语音播放。
保留先报警逻辑，确保 start 语音先于 end 语音触发。
"""

from camera import HikvisionCamera
from config import AUDIO_ID_START, AUDIO_ID_END, START_REPEAT, END_REPEAT


class RuleEngine:
    """语音播报规则引擎。

    根据接收到的 audio_id，通过 if 条件判断触发对应的语音播放。
    保留先报警逻辑，确保 start 语音先于 end 语音触发。

    Attributes:
        camera: 海康威视摄像头控制器实例。
    """

    def __init__(self):
        """初始化规则引擎，创建摄像头实例。"""
        self.camera = HikvisionCamera()

    def handle_signal(self, audio_id: int) -> bool:
        """处理接收到的 audio_id 并触发对应的语音播放。

        通过 if 条件判断 audio_id，触发对应的语音播放。
        保留先报警逻辑：start 语音先触发。

        Args:
            audio_id: 音频ID（如 AUDIO_ID_START=15, AUDIO_ID_END=14）。

        Returns:
            bool: audio_id 是否被成功识别并处理。
        """
        # 通过 if 条件判断触发哪个报警
        if audio_id == AUDIO_ID_START:
            print(f"\n触发 start 报警 → 车辆可以通行")
            print(f"播放配置: 语音ID={AUDIO_ID_START}，重复{START_REPEAT}次")
            self.camera.play(audio_id=AUDIO_ID_START, repeat=START_REPEAT)
            return True

        elif audio_id == AUDIO_ID_END:
            print(f"\n触发 end 报警 → 车辆已到达")
            print(f"播放配置: 语音ID={AUDIO_ID_END}，重复{END_REPEAT}次")
            self.camera.play(audio_id=AUDIO_ID_END, repeat=END_REPEAT)
            return True

        else:
            print(f"⚠️ 未知音频ID: '{audio_id}'，无对应规则")
            return False

    def list_rules(self):
        """打印当前所有可用的语音规则，方便调试与查看。"""
        print("\n=== 当前语音规则列表 ===")
        print(f"  start (ID={AUDIO_ID_START}) → 播放{START_REPEAT}次，车辆可以通行")
        print(f"  end   (ID={AUDIO_ID_END}) → 播放{END_REPEAT}次，车辆已到达")
        print("========================\n")
