"""ROS-摄像头桥接系统主程序。

监听 ROS topic，根据消息内容触发摄像头播放对应语音。

使用方式:
    python main.py
"""

import signal
import sys
from ros_listener import ROSListener
from audio_trigger import AudioTrigger


def main():
    """主函数，启动 ROS 监听并连接音频触发器。"""
    print("=" * 50)
    print("ROS-摄像头桥接系统启动")
    print("=" * 50)

    # 创建音频触发器
    audio_trigger = AudioTrigger()

    # 打印当前规则
    audio_trigger.list_rules()

    # 创建 ROS 监听器，将音频触发回调传入
    ros_listener = ROSListener(callback=audio_trigger.handle_message)

    # 注册 Ctrl+C 信号处理
    def signal_handler(sig, frame):
        print("\n[系统] 接收到退出信号，正在停止...")
        ros_listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("[系统] 按 Ctrl+C 退出\n")

    # 启动监听（阻塞）
    ros_listener.start()


if __name__ == "__main__":
    main()