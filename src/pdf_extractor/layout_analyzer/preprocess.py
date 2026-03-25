"""Image preprocessing helpers for layout analysis."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .config import LayoutConfig


def to_grayscale(image: Any) -> np.ndarray:
    """Convert a page image to grayscale."""
    array = _to_numpy(image)
    if len(array.shape) == 2:
        return array
    if len(array.shape) == 3 and array.shape[2] == 3:
        return cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
    raise ValueError(f"Unsupported image shape: {array.shape}")


def denoise(image: np.ndarray) -> np.ndarray:
    """Apply light denoising before thresholding."""
    return cv2.GaussianBlur(image, (3, 3), 0)


def binarize(image: np.ndarray, method: str = "adaptive") -> np.ndarray:
    """Convert grayscale image to a binary mask."""
    if method == "adaptive":
        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            11,
        )
    if method == "otsu":
        _, binary = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
        )
        return binary
    raise ValueError(f"Unsupported threshold method: {method}")


def prepare_analysis_layers(
    image: Any, config: LayoutConfig | None = None
) -> dict[str, np.ndarray]:
    """Prepare the minimal layer set required by V1 detectors."""
    resolved = config or LayoutConfig()
    gray = to_grayscale(image)
    cleaned = denoise(gray)
    binary = binarize(cleaned, method=resolved.threshold_method)
    return {
        "original": _to_numpy(image),
        "gray": gray,
        "binary": binary,
    }


def _to_numpy(image: Any) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image.copy()

    if hasattr(image, "convert"):
        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    raise ValueError("Unsupported image type for preprocessing.")

