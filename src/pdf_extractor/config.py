"""Configuration helpers for OCR and layout reconstruction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layout_analyzer.config import LayoutConfig, LAYOUT_ANALYSIS_MODES


OCR_BACKENDS = ("auto", "tesseract", "rapidocr")
OCR_PROFILES = ("table_scan", "directory_scan", "form_scan")
HEADER_STRATEGIES = ("auto", "page", "carry-forward")


@dataclass(slots=True)
class ExtractionConfig:
    profile: str = "table_scan"
    ocr_backend: str = "auto"
    header_strategy: str = "auto"
    render_scale: float = 3.0
    threshold: int = 180
    min_confidence: float = 0.2
    row_y_tolerance: float = 18.0
    column_x_tolerance: float = 24.0
    tesseract_psm: int = 6
    debug_dir: Path | None = None
    layout_config: LayoutConfig = field(default_factory=LayoutConfig)


PROFILE_DEFAULTS: dict[str, ExtractionConfig] = {
    "table_scan": ExtractionConfig(
        profile="table_scan",
        ocr_backend="auto",
        header_strategy="auto",
        render_scale=3.0,
        threshold=180,
        min_confidence=0.2,
        row_y_tolerance=18.0,
        column_x_tolerance=28.0,
        tesseract_psm=6,
        layout_config=LayoutConfig(),
    ),
    "directory_scan": ExtractionConfig(
        profile="directory_scan",
        ocr_backend="auto",
        header_strategy="auto",
        render_scale=3.0,
        threshold=175,
        min_confidence=0.2,
        row_y_tolerance=18.0,
        column_x_tolerance=30.0,
        tesseract_psm=6,
        layout_config=LayoutConfig(),
    ),
    "form_scan": ExtractionConfig(
        profile="form_scan",
        ocr_backend="auto",
        header_strategy="auto",
        render_scale=2.5,
        threshold=170,
        min_confidence=0.25,
        row_y_tolerance=14.0,
        column_x_tolerance=22.0,
        tesseract_psm=11,
        layout_config=LayoutConfig(),
    ),
}


def build_extraction_config(
    *,
    profile: str = "table_scan",
    ocr_backend: str | None = None,
    header_strategy: str | None = None,
    render_scale: float | None = None,
    threshold: int | None = None,
    min_confidence: float | None = None,
    row_y_tolerance: float | None = None,
    column_x_tolerance: float | None = None,
    tesseract_psm: int | None = None,
    debug_dir: str | Path | None = None,
    layout_analysis: str | None = None,
    layout_render_scale: float | None = None,
    layout_min_region_area: int | None = None,
    layout_merge_iou_threshold: float | None = None,
    layout_line_kernel_scale: int | None = None,
    layout_threshold_method: str | None = None,
    layout_region_padding: int | None = None,
) -> ExtractionConfig:
    if profile not in PROFILE_DEFAULTS:
        raise ValueError(f"Unsupported extraction profile: {profile}")

    base = PROFILE_DEFAULTS[profile]
    config = ExtractionConfig(
        profile=base.profile,
        ocr_backend=base.ocr_backend,
        header_strategy=base.header_strategy,
        render_scale=base.render_scale,
        threshold=base.threshold,
        min_confidence=base.min_confidence,
        row_y_tolerance=base.row_y_tolerance,
        column_x_tolerance=base.column_x_tolerance,
        tesseract_psm=base.tesseract_psm,
        debug_dir=base.debug_dir,
        layout_config=LayoutConfig(
            enabled=base.layout_config.enabled,
            mode=base.layout_config.mode,
            render_scale=base.layout_config.render_scale,
            detect_tables=base.layout_config.detect_tables,
            min_region_area=base.layout_config.min_region_area,
            merge_iou_threshold=base.layout_config.merge_iou_threshold,
            classifier_mode=base.layout_config.classifier_mode,
            debug_dir=base.layout_config.debug_dir,
            line_kernel_scale=base.layout_config.line_kernel_scale,
            threshold_method=base.layout_config.threshold_method,
            region_padding=base.layout_config.region_padding,
        ),
    )

    if ocr_backend is not None:
        if ocr_backend not in OCR_BACKENDS:
            raise ValueError(f"Unsupported OCR backend: {ocr_backend}")
        config.ocr_backend = ocr_backend
    if header_strategy is not None:
        if header_strategy not in HEADER_STRATEGIES:
            raise ValueError(f"Unsupported header strategy: {header_strategy}")
        config.header_strategy = header_strategy
    if render_scale is not None:
        config.render_scale = render_scale
    if threshold is not None:
        config.threshold = threshold
    if min_confidence is not None:
        config.min_confidence = min_confidence
    if row_y_tolerance is not None:
        config.row_y_tolerance = row_y_tolerance
    if column_x_tolerance is not None:
        config.column_x_tolerance = column_x_tolerance
    if tesseract_psm is not None:
        config.tesseract_psm = tesseract_psm
    if debug_dir is not None:
        config.debug_dir = Path(debug_dir)
        config.layout_config.debug_dir = Path(debug_dir)
    if layout_analysis is not None:
        if layout_analysis not in LAYOUT_ANALYSIS_MODES:
            raise ValueError(f"Unsupported layout analysis mode: {layout_analysis}")
        config.layout_config.mode = layout_analysis
        config.layout_config.enabled = layout_analysis != "off"
    if layout_render_scale is not None:
        config.layout_config.render_scale = layout_render_scale
    if layout_min_region_area is not None:
        config.layout_config.min_region_area = layout_min_region_area
    if layout_merge_iou_threshold is not None:
        config.layout_config.merge_iou_threshold = layout_merge_iou_threshold
    if layout_line_kernel_scale is not None:
        config.layout_config.line_kernel_scale = layout_line_kernel_scale
    if layout_threshold_method is not None:
        config.layout_config.threshold_method = layout_threshold_method
    if layout_region_padding is not None:
        config.layout_config.region_padding = layout_region_padding
    config.layout_config.validate()

    return config


def load_config_file(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")

    allowed_keys = {
        "profile",
        "ocr_backend",
        "header_strategy",
        "render_scale",
        "threshold",
        "min_confidence",
        "row_y_tolerance",
        "column_x_tolerance",
        "tesseract_psm",
        "debug_dir",
        "layout_analysis",
        "layout_render_scale",
        "layout_min_region_area",
        "layout_merge_iou_threshold",
        "layout_line_kernel_scale",
        "layout_threshold_method",
        "layout_region_padding",
    }
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"Unsupported config keys in {path}: {', '.join(unknown_keys)}")

    return payload


def build_extraction_config_from_sources(
    *,
    config_path: str | Path | None = None,
    profile: str | None = None,
    ocr_backend: str | None = None,
    header_strategy: str | None = None,
    render_scale: float | None = None,
    threshold: int | None = None,
    min_confidence: float | None = None,
    row_y_tolerance: float | None = None,
    column_x_tolerance: float | None = None,
    tesseract_psm: int | None = None,
    debug_dir: str | Path | None = None,
    layout_analysis: str | None = None,
    layout_render_scale: float | None = None,
    layout_min_region_area: int | None = None,
    layout_merge_iou_threshold: float | None = None,
    layout_line_kernel_scale: int | None = None,
    layout_threshold_method: str | None = None,
    layout_region_padding: int | None = None,
) -> ExtractionConfig:
    file_config = load_config_file(config_path) if config_path is not None else {}

    resolved_profile = profile or str(file_config.get("profile", "table_scan"))

    return build_extraction_config(
        profile=resolved_profile,
        ocr_backend=ocr_backend if ocr_backend is not None else file_config.get("ocr_backend"),
        header_strategy=(
            header_strategy
            if header_strategy is not None
            else file_config.get("header_strategy")
        ),
        render_scale=render_scale if render_scale is not None else file_config.get("render_scale"),
        threshold=threshold if threshold is not None else file_config.get("threshold"),
        min_confidence=(
            min_confidence if min_confidence is not None else file_config.get("min_confidence")
        ),
        row_y_tolerance=(
            row_y_tolerance
            if row_y_tolerance is not None
            else file_config.get("row_y_tolerance")
        ),
        column_x_tolerance=(
            column_x_tolerance
            if column_x_tolerance is not None
            else file_config.get("column_x_tolerance")
        ),
        tesseract_psm=(
            tesseract_psm if tesseract_psm is not None else file_config.get("tesseract_psm")
        ),
        debug_dir=debug_dir if debug_dir is not None else file_config.get("debug_dir"),
        layout_analysis=(
            layout_analysis
            if layout_analysis is not None
            else file_config.get("layout_analysis")
        ),
        layout_render_scale=(
            layout_render_scale
            if layout_render_scale is not None
            else file_config.get("layout_render_scale")
        ),
        layout_min_region_area=(
            layout_min_region_area
            if layout_min_region_area is not None
            else file_config.get("layout_min_region_area")
        ),
        layout_merge_iou_threshold=(
            layout_merge_iou_threshold
            if layout_merge_iou_threshold is not None
            else file_config.get("layout_merge_iou_threshold")
        ),
        layout_line_kernel_scale=(
            layout_line_kernel_scale
            if layout_line_kernel_scale is not None
            else file_config.get("layout_line_kernel_scale")
        ),
        layout_threshold_method=(
            layout_threshold_method
            if layout_threshold_method is not None
            else file_config.get("layout_threshold_method")
        ),
        layout_region_padding=(
            layout_region_padding
            if layout_region_padding is not None
            else file_config.get("layout_region_padding")
        ),
    )
