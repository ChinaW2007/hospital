# ============================================================
# Hospital Backend Configuration Template
# ============================================================
# Copy this file to config.py and fill in your actual values

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

    # ============================================================
    # Camera Configuration
    # ============================================================
    camera_host: str = "YOUR_CAMERA_IP"  # e.g., 192.168.1.100
    camera_port: int = 554
    camera_user: str = "admin"
    camera_password: str = "YOUR_CAMERA_PASSWORD"
    camera_stream_path: str = "/Streaming/Channels/101"

    # Audio Announcement (ISAPI)
    camera_audio_port: int = 80
    audio_id_start: int = 15  # car_can_go
    audio_check_interval: int = 30
    audio_connect_timeout: int = 5

    # ============================================================
    # HIS MySQL Configuration
    # ============================================================
    his_mysql_host: str = "YOUR_MYSQL_HOST"  # e.g., 192.168.1.50
    his_mysql_port: int = 3306
    his_mysql_user: str = "YOUR_MYSQL_USER"
    his_mysql_pass: str = "YOUR_MYSQL_PASSWORD"
    his_mysql_db: str = "YOUR_DATABASE_NAME"

    # ============================================================
    # ROS WebSocket Configuration
    # ============================================================
    ros_ws_host: str = "YOUR_ROS_IP"  # e.g., 192.168.1.10
    ros_ws_port: int = 9090
    ros_topic: str = "/car01_pub"
    ros_check_interval: int = 30
    ros_connect_timeout: int = 5


settings = Settings()


def get_camera_rtsp_url() -> str:
    return (
        f"rtsp://{settings.camera_user}:{settings.camera_password}@"
        f"{settings.camera_host}:{settings.camera_port}{settings.camera_stream_path}"
    )


def get_ros_ws_url() -> str:
    return f"ws://{settings.ros_ws_host}:{settings.ros_ws_port}"


def get_camera_audio_base_url() -> str:
    return f"http://{settings.camera_host}:{settings.camera_audio_port}"


def get_audio_trigger_url(audio_id: int) -> str:
    return (
        f"http://{settings.camera_host}:{settings.camera_audio_port}"
        f"/ISAPI/Event/triggers/notifications/AudioAlarm/{audio_id}/test?format=json"
    )