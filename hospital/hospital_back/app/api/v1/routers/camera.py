import subprocess
import threading
import time
import requests

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import get_camera_rtsp_url
from app.schemas.camera import CameraTestResponse, CameraUrlResponse

ROBOT_CAMERA_BASE = "http://192.168.51.12:8080"
ROBOT_CAMERA_TOPIC = "/camera/color/image_raw"
ROBOT_CAMERA_STREAM_URL = f"{ROBOT_CAMERA_BASE}/stream?topic={ROBOT_CAMERA_TOPIC}"
ROBOT_CAMERA_SNAPSHOT_URL = f"{ROBOT_CAMERA_BASE}/snapshot?topic={ROBOT_CAMERA_TOPIC}"

router = APIRouter()


def _build_ffmpeg_command(rtsp_url: str):
    return [
        "ffmpeg",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        "5000000",
        "-i",
        rtsp_url,
        "-t",
        "1",
        "-f",
        "null",
        "-",
    ]


def _ensure_ffmpeg_installed() -> bool:
    return subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0


def _opencv_connect(rtsp_url: str):
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    time.sleep(0.5)
    ret, frame = cap.read()
    if not ret or frame is None:
        cap.release()
        return False
    cap.release()
    return True


@router.get("/url", response_model=CameraUrlResponse)
def camera_url():
    return {"rtsp_url": get_camera_rtsp_url()}


@router.get("/test", response_model=CameraTestResponse)
def camera_test():
    if not _ensure_ffmpeg_installed():
        raise HTTPException(status_code=500, detail="ffmpeg 未安装，无法测试 RTSP 连接。")

    rtsp_url = get_camera_rtsp_url()
    command = _build_ffmpeg_command(rtsp_url)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        raise HTTPException(status_code=500, detail="ffmpeg 测试超时，摄像头可能无法连接。")

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="ignore")
        raise HTTPException(status_code=500, detail=f"ffmpeg 测试失败: {detail}")

    return {"ok": True, "message": "摄像头 RTSP 连接正常"}


@router.get("/proxy")
def camera_proxy():
    if not _ensure_ffmpeg_installed():
        raise HTTPException(status_code=500, detail="ffmpeg 未安装，无法启动 RTSP 代理。")

    rtsp_url = get_camera_rtsp_url()
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-timeout",
            "5000000",
            "-i",
            rtsp_url,
            "-f",
            "mpjpeg",
            "-q:v",
            "5",
            "-r",
            "15",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    time.sleep(1.0)
    if process.poll() is not None:
        _, stderr = process.communicate()
        raise HTTPException(status_code=500, detail=f"ffmpeg 启动失败: {stderr.decode('utf-8', errors='ignore')}" )

    def stream_generator():
        try:
            assert process.stdout is not None
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                process.kill()
            except Exception:
                pass

    return StreamingResponse(stream_generator(), media_type="multipart/x-mixed-replace; boundary=ffmpeg")


@router.get("/opencv/test", response_model=CameraTestResponse)
def opencv_test():
    rtsp_url = get_camera_rtsp_url()
    if not _opencv_connect(rtsp_url):
        raise HTTPException(status_code=500, detail="OpenCV 无法连接摄像头。")
    return {"ok": True, "message": "OpenCV 摄像头连接正常"}


@router.get("/opencv")
def opencv_stream():
    rtsp_url = get_camera_rtsp_url()

    # 预先生成占位图
    connecting_img = _create_placeholder_image("Connecting...")
    offline_img = _create_placeholder_image("Camera Offline")

    def frame_generator():
        cap = None
        try:
            # 1. 立即发送"正在连接"占位图，让浏览器立刻显示内容
            yield _mjpeg_frame(connecting_img)

            # 2. 后台尝试打开RTSP
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                cap = None
                raise Exception("无法打开RTSP流")

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 3. 发送"连接中"图，同时等待RTSP稳定
            yield _mjpeg_frame(connecting_img)
            time.sleep(2.0)

            # 4. 尝试读取真实帧
            consecutive_failures = 0
            max_failures = 30

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures > max_failures:
                        # 连续失败，发送离线占位图（不断开流）
                        yield _mjpeg_frame(offline_img)
                        time.sleep(0.5)
                    else:
                        time.sleep(0.2)
                    continue

                # 读帧成功
                consecutive_failures = 0
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
                ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                if ret:
                    yield _mjpeg_frame(buffer.tobytes())

        except Exception as e:
            # 任何异常都发送离线占位图，保持流不中断
            while True:
                yield _mjpeg_frame(offline_img)
                time.sleep(0.5)

        finally:
            if cap is not None:
                cap.release()

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=mjpeg")


def _mjpeg_frame(jpeg_data: bytes) -> bytes:
    """封装单帧 JPEG 为 MJPEG multipart 格式"""
    return (b'--mjpeg\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-length: ' + str(len(jpeg_data)).encode() + b'\r\n\r\n'
            + jpeg_data + b'\r\n')


def _create_placeholder_image(text: str) -> bytes:
    """生成占位图片（JPEG 格式）"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # 深色背景
    img[:] = [15, 23, 42]
    # 绘制边框
    cv2.rectangle(img, (20, 20), (620, 460), (51, 65, 85), 2)
    # 绘制文字
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 1.0, 2)[0]
    text_x = (640 - text_size[0]) // 2
    text_y = (480 + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 1.0, (148, 163, 184), 2)
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()


@router.get("/robot/test", response_model=CameraTestResponse)
def robot_camera_test():
    try:
        response = requests.get(ROBOT_CAMERA_SNAPSHOT_URL, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '')
        if 'image' in content_type:
            return {"ok": True, "message": "机器人摄像头连接正常"}
        else:
            raise HTTPException(status_code=500, detail=f"机器人摄像头返回非预期内容类型: {content_type}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"机器人摄像头连接失败: {str(e)}")


@router.get("/robot")
def robot_camera_stream():
    try:
        resp = requests.get(ROBOT_CAMERA_STREAM_URL, stream=True, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get('content-type', 'multipart/x-mixed-replace; boundary=frame')

        def stream_generator():
            try:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            finally:
                resp.close()

        return StreamingResponse(stream_generator(), media_type=content_type)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"机器人摄像头流获取失败: {str(e)}")


ROBOT2_CAMERA_STREAM_URL = "http://192.168.51.43:5000/video_feed"

@router.get("/robot2")
def robot2_camera_stream():
    try:
        resp = requests.get(ROBOT2_CAMERA_STREAM_URL, stream=True, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get('content-type', 'multipart/x-mixed-replace; boundary=frame')

        def stream_generator():
            try:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            finally:
                resp.close()

        return StreamingResponse(stream_generator(), media_type=content_type)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"机器人2摄像头流获取失败: {str(e)}")
