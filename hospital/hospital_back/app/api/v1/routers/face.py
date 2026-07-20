import base64
from typing import Tuple

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
MATCH_THRESHOLD = 0.62


class FaceImageRequest(BaseModel):
    face_image: str


class FaceCompareRequest(BaseModel):
    reference_image: str
    candidate_image: str


def _decode_image(data_url: str) -> np.ndarray:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("图片格式无效")
    try:
        encoded = data_url.split(",", 1)[1]
        raw = base64.b64decode(encoded, validate=True)
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception as exc:
        raise ValueError("图片无法解析") from exc
    if image is None:
        raise ValueError("图片无法解析")
    return image


def _extract_face(data_url: str) -> np.ndarray:
    image = _decode_image(data_url)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = _detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    if len(faces) == 0:
        raise ValueError("未检测到人脸，请正对镜头并确保光线充足")

    x, y, width, height = max(faces, key=lambda rect: rect[2] * rect[3])
    margin_x = int(width * 0.12)
    margin_y = int(height * 0.12)
    x1, y1 = max(0, x - margin_x), max(0, y - margin_y)
    x2, y2 = min(gray.shape[1], x + width + margin_x), min(gray.shape[0], y + height + margin_y)
    face = gray[y1:y2, x1:x2]
    face = cv2.resize(face, (160, 160), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(face)


def _similarity(reference: np.ndarray, candidate: np.ndarray) -> Tuple[float, dict]:
    template = float(cv2.matchTemplate(reference, candidate, cv2.TM_CCOEFF_NORMED)[0][0])
    template_score = max(0.0, min(1.0, (template + 1.0) / 2.0))

    hist_ref = cv2.calcHist([reference], [0], None, [64], [0, 256])
    hist_candidate = cv2.calcHist([candidate], [0], None, [64], [0, 256])
    cv2.normalize(hist_ref, hist_ref)
    cv2.normalize(hist_candidate, hist_candidate)
    histogram = float(cv2.compareHist(hist_ref, hist_candidate, cv2.HISTCMP_CORREL))
    histogram_score = max(0.0, min(1.0, (histogram + 1.0) / 2.0))

    mse = float(np.mean((reference.astype(np.float32) - candidate.astype(np.float32)) ** 2))
    pixel_score = max(0.0, 1.0 - min(mse / 6500.0, 1.0))
    score = 0.55 * template_score + 0.25 * histogram_score + 0.20 * pixel_score
    return score, {
        "template_score": round(template_score, 4),
        "histogram_score": round(histogram_score, 4),
        "pixel_score": round(pixel_score, 4),
    }


@router.post("/validate")
def validate_face(payload: FaceImageRequest):
    try:
        _extract_face(payload.face_image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"face_detected": True, "message": "已检测到清晰人脸"}


@router.post("/compare")
def compare_face(payload: FaceCompareRequest):
    try:
        reference = _extract_face(payload.reference_image)
        candidate = _extract_face(payload.candidate_image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    score, metrics = _similarity(reference, candidate)
    matched = score >= MATCH_THRESHOLD
    return {
        "matched": matched,
        "score": round(score, 4),
        "threshold": MATCH_THRESHOLD,
        "metrics": metrics,
        "message": "人脸比对成功" if matched else "人脸比对未通过，请正对镜头后重试",
    }
