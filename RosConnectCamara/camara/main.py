"""摄像头语音播报系统主程序。

在代码中定义 audio_id，直接触发对应的语音播放。

使用方式:
    python main.py
"""

from rule_engine import RuleEngine

# =========================
# 在此定义要播放的 audio_id
# =========================
# 15 = 车辆可以通行 (start)
# 14 = 车辆已到达 (end)
AUDIO_ID = 15


def main():
    """主函数，直接播放预定义的 audio_id 对应的语音。"""
    engine = RuleEngine()
    engine.handle_signal(AUDIO_ID)


if __name__ == "__main__":
    main()
