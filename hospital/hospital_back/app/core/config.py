import importlib

_spec_settings = importlib.util.find_spec("pydantic_settings")
_spec_pydantic = importlib.util.find_spec("pydantic")

if _spec_settings is not None:
    from pydantic_settings import BaseSettings, SettingsConfigDict
elif _spec_pydantic is not None:
    import pydantic as _pydantic
    _ver = getattr(_pydantic, "__version__", "")
    if _ver and _ver.split(".")[0] == "1":
        from pydantic import BaseSettings
    else:
        raise ImportError(
            "pydantic v2 is installed; please install 'pydantic-settings' (pip install pydantic-settings)."
        )
else:
    raise ImportError(
        "Neither 'pydantic' nor 'pydantic-settings' is installed. Install one of them."
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Medicine API Server"
    database_url: str = "sqlite:///./app.db"

    camera_host: str = "192.168.51.251"
    camera_port: int = 554
    camera_user: str = "admin"
    camera_password: str = "Gsydj666"
    camera_stream_path: str = "/Streaming/Channels/101"

    # 摄像头语音播报配置（ISAPI 接口）
    camera_audio_port: int = 80  # 摄像头 HTTP API 端口
    audio_id_start: int = 15  # car_can_go - 车辆可以通行（任务确认时播放）
    audio_check_interval: int = 30  # 语音播报端口检测间隔（秒）
    audio_connect_timeout: int = 5  # 语音播报连接超时（秒）

    # HIS 系统数据库配置（与 HIS 系统共用数据库）
    his_mysql_host: str = "192.168.51.133"
    his_mysql_port: int = 3306
    his_mysql_user: str = "ros"
    his_mysql_pass: str = "123456"
    his_mysql_db: str = "test"

    # ROS WebSocket 配置（用于监听机器人状态）
    ros_ws_host: str = "192.168.51.12"
    ros_ws_port: int = 9090
    ros_topic: str = "/car01_pub"
    ros_check_interval: int = 30  # 周期检测间隔（秒）
    ros_connect_timeout: int = 5  # 连接超时（秒）


settings = Settings()


def get_camera_rtsp_url() -> str:
    return (
        f"rtsp://{settings.camera_user}:{settings.camera_password}@"
        f"{settings.camera_host}:{settings.camera_port}{settings.camera_stream_path}"
    )


def get_ros_ws_url() -> str:
    """获取 ROS WebSocket 连接地址"""
    return f"ws://{settings.ros_ws_host}:{settings.ros_ws_port}"


def get_camera_audio_base_url() -> str:
    """获取摄像头语音播报 API 基础地址"""
    return f"http://{settings.camera_host}:{settings.camera_audio_port}"


def get_audio_trigger_url(audio_id: int) -> str:
    """获取摄像头语音触发 API 地址"""
    return (
        f"http://{settings.camera_host}:{settings.camera_audio_port}"
        f"/ISAPI/Event/triggers/notifications/AudioAlarm/{audio_id}/test?format=json"
    )
