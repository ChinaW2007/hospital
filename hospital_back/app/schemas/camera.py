from pydantic import BaseModel


class CameraUrlResponse(BaseModel):
    rtsp_url: str


class CameraTestResponse(BaseModel):
    ok: bool
    message: str
