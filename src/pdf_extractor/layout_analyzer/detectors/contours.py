"""Contour detection helpers."""

from __future__ import annotations

import cv2
import numpy as np

from ..config import LayoutConfig


def detect_contours(
    binary_image: np.ndarray, config: LayoutConfig
) -> list[tuple[int, int, int, int]]:
    """Detect significant contour boxes from the binary image."""
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < config.min_region_area:
            continue
        boxes.append((x, y, x + w, y + h))
    boxes.sort(key=lambda item: (item[1], item[0]))
    return boxes

