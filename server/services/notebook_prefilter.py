"""Pre-filter for notebook photos. Layer 2 of the 4-layer guard.

Rejects blank/scenery/skewed photos BEFORE any LLM call so we never spend
tokens on hallucination-prone input. Returns a structured rejection reason
the route layer maps to a localized retry message.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class PrefilterResult:
    ok: bool
    reason: Optional[str]            # "skew_too_high" | "blank_or_scene" | "scene_detected" | None
    deskewed_bytes: Optional[bytes]  # JPEG bytes after deskew + binarize, None if rejected
    detected_skew_deg: float = 0.0
    pen_density_ratio: float = 0.0
    face_ratio: float = 0.0


def validate(
    image_bytes: bytes,
    *,
    max_skew_deg: float = 15.0,
    min_pen_density: float = 0.005,
    max_face_ratio: float = 0.20,
) -> PrefilterResult:
    """Run all pre-filter checks. Returns PrefilterResult.

    Checks performed in order:
    1. Decode image bytes — reject as "invalid_file" on failure.
    2. OTSU binarize and measure pen-stroke density.
    3. Compute skew angle via minAreaRect on ink pixels — reject if > max_skew_deg.
    4. Density gate — reject as "blank_or_scene" when density < min_pen_density.
    5. Face detection via Haar cascade — reject as "scene_detected" when largest
       face covers > max_face_ratio of the total pixel area.
    6. Deskew and re-encode to JPEG.
    """
    # ── 1. Decode ─────────────────────────────────────────────────────────────
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return PrefilterResult(ok=False, reason="invalid_file", deskewed_bytes=None)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── 2. OTSU binarize ──────────────────────────────────────────────────────
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # ── 3. Skew detection via minAreaRect ─────────────────────────────────────
    coords = np.column_stack(np.where(binary > 0))
    angle = 0.0
    if coords.size > 0:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > max_skew_deg:
            return PrefilterResult(
                ok=False,
                reason="skew_too_high",
                deskewed_bytes=None,
                detected_skew_deg=abs(angle),
            )

    # ── 4. Pen-stroke density gate ────────────────────────────────────────────
    dark_pixels = int(np.sum(binary > 0))
    total_pixels = binary.size
    density = float(dark_pixels) / total_pixels
    if density < min_pen_density:
        return PrefilterResult(
            ok=False,
            reason="blank_or_scene",
            deskewed_bytes=None,
            pen_density_ratio=density,
        )

    # ── 5. Face detection (Haar cascade) ──────────────────────────────────────
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    face_ratio = 0.0
    if len(faces) > 0:
        biggest = max(faces, key=lambda f: f[2] * f[3])
        face_area = int(biggest[2]) * int(biggest[3])
        face_ratio = float(face_area) / total_pixels
        if face_ratio > max_face_ratio:
            return PrefilterResult(
                ok=False,
                reason="scene_detected",
                deskewed_bytes=None,
                face_ratio=face_ratio,
            )

    # ── 6. Deskew (rotate by detected angle, fill white) ─────────────────────
    if abs(angle) > 0.5:
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))

    # ── 7. Re-encode to JPEG ──────────────────────────────────────────────────
    success, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        return PrefilterResult(ok=False, reason="invalid_file", deskewed_bytes=None)

    return PrefilterResult(
        ok=True,
        reason=None,
        deskewed_bytes=encoded.tobytes(),
        detected_skew_deg=abs(angle),
        pen_density_ratio=density,
        face_ratio=face_ratio,
    )
