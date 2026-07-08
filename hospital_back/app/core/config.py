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

    # HIS 系统数据库配置（与 HIS 系统共用数据库）
    his_mysql_host: str = "192.168.51.133"
    his_mysql_port: int = 3306
    his_mysql_user: str = "ros"
    his_mysql_pass: str = "123456"
    his_mysql_db: str = "test"


settings = Settings()


def get_camera_rtsp_url() -> str:
    return (
        f"rtsp://{settings.camera_user}:{settings.camera_password}@"
        f"{settings.camera_host}:{settings.camera_port}{settings.camera_stream_path}"
    )
