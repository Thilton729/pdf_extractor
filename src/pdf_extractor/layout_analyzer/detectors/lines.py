"""Line detection helpers."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ..config import LayoutConfig


def detect_lines(binary_image: np.ndarray, config: LayoutConfig) -> dict[str, Any]:
    """Detect coarse horizontal/vertical structure from a binary image."""
    height, width = binary_image.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(8, width // config.line_kernel_scale), 1),
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(8, height // config.line_kernel_scale)),
    )

    horizontal_mask = cv2.morphologyEx(
        binary_image, cv2.MORPH_OPEN, horizontal_kernel
    )
    vertical_mask = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, vertical_kernel)

    horizontal_lines = _mask_to_boxes(horizontal_mask)
    vertical_lines = _mask_to_boxes(vertical_mask)

    combined = cv2.bitwise_or(horizontal_mask, vertical_mask)
    non_zero = int(np.count_nonzero(combined))
    line_density = non_zero / float(width * height) if width and height else 0.0

    return {
        "horizontal_lines": horizontal_lines,
        "vertical_lines": vertical_lines,
        "line_density": line_density,
        "horizontal_mask": horizontal_mask,
        "vertical_mask": vertical_mask,
        "combined_mask": combined,
    }


def _mask_to_boxes(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        boxes.append((x, y, x + w, y + h))
    boxes.sort(key=lambda item: (item[1], item[0]))
    return boxes

