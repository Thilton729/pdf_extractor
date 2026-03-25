"""Configuration for layout analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


LAYOUT_ANALYSIS_MODES = ("off", "auto", "debug")
LAYOUT_CLASSIFIER_MODES = ("heuristic",)
LAYOUT_THRESHOLD_METHODS = ("adaptive", "otsu")


@dataclass(slots=True)
class LayoutConfig:
    """Configuration for the V1 layout analyzer."""

    enabled: bool = True
    mode: str = "auto"
    render_scale: float = 2.0
    detect_tables: bool = True
    min_region_area: int = 500
    merge_iou_threshold: float = 0.5
    classifier_mode: str = "heuristic"
    debug_dir: Path | None = None
    line_kernel_scale: int = 40
    threshold_method: str = "adaptive"
    region_padding: int = 8

    def validate(self) -> None:
        if self.mode not in LAYOUT_ANALYSIS_MODES:
            raise ValueError(
                f"Unsupported layout analysis mode: {self.mode}"
            )
        if self.render_scale <= 0:
            raise ValueError("Layout render scale must be greater than 0.")
        if self.min_region_area < 1:
            raise ValueError("Layout min region area must be at least 1.")
        if not 0.0 <= self.merge_iou_threshold <= 1.0:
            raise ValueError("Layout merge IOU threshold must be between 0 and 1.")
        if self.classifier_mode not in LAYOUT_CLASSIFIER_MODES:
            raise ValueError(
                f"Unsupported layout classifier mode: {self.classifier_mode}"
            )
        if self.line_kernel_scale < 1:
            raise ValueError("Layout line kernel scale must be at least 1.")
        if self.threshold_method not in LAYOUT_THRESHOLD_METHODS:
            raise ValueError(
                f"Unsupported layout threshold method: {self.threshold_method}"
            )

    @property
    def debug_enabled(self) -> bool:
        return self.mode == "debug" and self.debug_dir is not None

