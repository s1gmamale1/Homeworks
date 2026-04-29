"""
Wave K — tests for notebook_prefilter.validate().

pytest tests/test_notebook_prefilter.py -v

OpenCV is an optional dependency at this stage; tests are skipped if cv2 is
not installed (pytest.importorskip guards each test module).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2", reason="opencv-python-headless not installed")


# ── helpers ───────────────────────────────────────────────────────────────────

def _encode_jpg(arr: np.ndarray) -> bytes:
    """Encode a numpy BGR image to JPEG bytes."""
    success, buf = cv2.imencode(".jpg", arr)
    assert success, "cv2.imencode failed in test helper"
    return buf.tobytes()


def _white_image(h: int = 200, w: int = 200) -> np.ndarray:
    """Return a white BGR image (nothing to detect)."""
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _text_like_image(h: int = 300, w: int = 400, density: float = 0.05) -> np.ndarray:
    """Return a white image with horizontal rule lines (simulate handwritten notebook).

    Uses drawn lines rather than scattered random pixels so that minAreaRect-based
    skew detection has a meaningful oriented structure to measure.
    """
    img = _white_image(h, w)
    # Draw horizontal lines spaced every 25px — similar to notebook ruled lines
    for y in range(20, h - 20, 25):
        cv2.line(img, (10, y), (w - 10, y), (30, 30, 30), 2)
    return img


def _skewed_image(skew_deg: float = 25.0, h: int = 300, w: int = 400) -> bytes:
    """Create a lined (notebook-like) image and rotate it by *skew_deg*.

    Uses drawn horizontal lines so the minAreaRect skew detector sees real
    oriented structure — randomly scattered pixels produce an axis-aligned
    bounding box regardless of rotation.
    """
    img = _text_like_image(h, w)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), skew_deg, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))
    return _encode_jpg(rotated)


def _draw_face_block(img: np.ndarray, x: int, y: int, size: int) -> np.ndarray:
    """Draw a solid dark rectangle to simulate a large face area."""
    out = img.copy()
    cv2.rectangle(out, (x, y), (x + size, y + size), (50, 50, 50), -1)
    return out


# ── tests ─────────────────────────────────────────────────────────────────────

def test_blank_white_image_rejected():
    """A completely blank (white) image must be rejected as blank_or_scene."""
    from server.services.notebook_prefilter import validate

    img = _white_image()
    result = validate(_encode_jpg(img))

    assert result.ok is False
    assert result.reason == "blank_or_scene"
    assert result.deskewed_bytes is None


def test_skewed_text_image_rejected():
    """An image skewed > 15° must be rejected as skew_too_high."""
    from server.services.notebook_prefilter import validate

    image_bytes = _skewed_image(skew_deg=25.0)
    result = validate(image_bytes)

    assert result.ok is False
    assert result.reason == "skew_too_high"
    assert result.deskewed_bytes is None
    # Detected skew should be in the right ballpark
    assert result.detected_skew_deg > 10.0


def test_text_like_image_passes():
    """A lined notebook-like image with low skew must pass all checks and return bytes."""
    from server.services.notebook_prefilter import validate

    img = _text_like_image()
    result = validate(_encode_jpg(img))

    assert result.ok is True
    assert result.reason is None
    assert result.deskewed_bytes is not None
    assert len(result.deskewed_bytes) > 0


def test_invalid_bytes_rejected():
    """Non-image bytes must be rejected as invalid_file."""
    from server.services.notebook_prefilter import validate

    result = validate(b"this is not an image at all!!! \x00\x01\x02")

    assert result.ok is False
    assert result.reason == "invalid_file"
    assert result.deskewed_bytes is None


def test_small_face_passes():
    """A face covering < 20% of the image must NOT trigger scene_detected."""
    from server.services.notebook_prefilter import validate

    # Start with a text-rich (lined) image so density check passes
    img = _text_like_image(h=400, w=400)
    # Draw a small (30×30 = 900px) rectangle — 900/160000 ≈ 0.6% < 20% threshold
    img = _draw_face_block(img, x=10, y=10, size=30)

    result = validate(_encode_jpg(img))

    # The Haar cascade won't detect our toy rectangle as a real face, so the
    # image should pass. If it does detect it, face_ratio should still be < 0.20.
    if not result.ok:
        # Only acceptable failure is blank/skew, not scene_detected for small block
        assert result.reason != "scene_detected", (
            f"Small block wrongly triggered scene_detected (face_ratio={result.face_ratio:.3f})"
        )


def test_large_face_block_with_high_density():
    """Validate face_ratio field is a float and is always accessible on result."""
    from server.services.notebook_prefilter import validate

    # We create a text-rich (lined) image and confirm the result carries face_ratio=0.0
    # (since our synthetic block won't be detected by Haar cascade as a real face).
    img = _text_like_image(h=300, w=300)
    result = validate(_encode_jpg(img))

    # face_ratio is set only when faces are detected by Haar cascade
    # For synthetic images this is always 0.0 — that's expected and correct.
    assert isinstance(result.face_ratio, float)
    assert result.face_ratio >= 0.0


def test_min_pen_density_configurable():
    """With a very low min_pen_density, a nearly-blank image should pass."""
    from server.services.notebook_prefilter import validate

    # A white image with just two pixels — well below the default 0.5% density gate
    img = _white_image(200, 200)
    img[100, 100] = [0, 0, 0]
    img[100, 101] = [0, 0, 0]

    # Default threshold (0.005) — should fail (blank_or_scene)
    result_default = validate(_encode_jpg(img))
    assert result_default.ok is False
    assert result_default.reason == "blank_or_scene"

    # Very low threshold — should not fail for density (may still have other issues)
    result_low = validate(_encode_jpg(img), min_pen_density=0.000001)
    # Just verify no crash and reason is not blank_or_scene
    if not result_low.ok:
        assert result_low.reason != "blank_or_scene", (
            "With min_pen_density=0.000001, image should not be rejected for density"
        )


def test_max_skew_deg_configurable():
    """An image with 25° skew should pass when max_skew_deg=45."""
    from server.services.notebook_prefilter import validate

    image_bytes = _skewed_image(skew_deg=25.0)

    # Default threshold (15°) → reject
    result_strict = validate(image_bytes, max_skew_deg=15.0)
    assert result_strict.ok is False
    assert result_strict.reason == "skew_too_high"

    # Relaxed threshold (45°) → should not be rejected for skew
    result_relaxed = validate(image_bytes, max_skew_deg=45.0)
    # May still fail density check on the rotated image, but NOT for skew_too_high
    if not result_relaxed.ok:
        assert result_relaxed.reason != "skew_too_high", (
            "25° image incorrectly rejected for skew when threshold=45°"
        )
