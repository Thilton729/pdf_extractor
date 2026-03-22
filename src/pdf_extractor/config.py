"""Configuration helpers for OCR and layout reconstruction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OCR_BACKENDS = ("auto", "tesseract", "rapidocr")
OCR_PROFILES = ("table_scan", "directory_scan", "form_scan")


@dataclass(slots=True)
class ExtractionConfig:
    profile: str = "table_scan"
    ocr_backend: str = "auto"
    render_scale: float = 3.0
    threshold: int = 180
    min_confidence: float = 0.2
    row_y_tolerance: float = 18.0
    column_x_tolerance: float = 24.0
    tesseract_psm: int = 6
    debug_dir: Path | None = None


PROFILE_DEFAULTS: dict[str, ExtractionConfig] = {
    "table_scan": ExtractionConfig(
        profile="table_scan",
        ocr_backend="auto",
        render_scale=3.0,
        threshold=180,
        min_confidence=0.2,
        row_y_tolerance=18.0,
        column_x_tolerance=28.0,
        tesseract_psm=6,
    ),
    "directory_scan": ExtractionConfig(
        profile="directory_scan",
        ocr_backend="auto",
        render_scale=3.0,
        threshold=175,
        min_confidence=0.2,
        row_y_tolerance=18.0,
        column_x_tolerance=30.0,
        tesseract_psm=6,
    ),
    "form_scan": ExtractionConfig(
        profile="form_scan",
        ocr_backend="auto",
        render_scale=2.5,
        threshold=170,
        min_confidence=0.25,
        row_y_tolerance=14.0,
        column_x_tolerance=22.0,
        tesseract_psm=11,
    ),
}


def build_extraction_config(
    *,
    profile: str = "table_scan",
    ocr_backend: str | None = None,
    render_scale: float | None = None,
    threshold: int | None = None,
    min_confidence: float | None = None,
    row_y_tolerance: float | None = None,
    column_x_tolerance: float | None = None,
    tesseract_psm: int | None = None,
    debug_dir: str | Path | None = None,
) -> ExtractionConfig:
    if profile not in PROFILE_DEFAULTS:
        raise ValueError(f"Unsupported extraction profile: {profile}")

    base = PROFILE_DEFAULTS[profile]
    config = ExtractionConfig(
        profile=base.profile,
        ocr_backend=base.ocr_backend,
        render_scale=base.render_scale,
        threshold=base.threshold,
        min_confidence=base.min_confidence,
        row_y_tolerance=base.row_y_tolerance,
        column_x_tolerance=base.column_x_tolerance,
        tesseract_psm=base.tesseract_psm,
        debug_dir=base.debug_dir,
    )

    if ocr_backend is not None:
        if ocr_backend not in OCR_BACKENDS:
            raise ValueError(f"Unsupported OCR backend: {ocr_backend}")
        config.ocr_backend = ocr_backend
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
        "render_scale",
        "threshold",
        "min_confidence",
        "row_y_tolerance",
        "column_x_tolerance",
        "tesseract_psm",
        "debug_dir",
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
    render_scale: float | None = None,
    threshold: int | None = None,
    min_confidence: float | None = None,
    row_y_tolerance: float | None = None,
    column_x_tolerance: float | None = None,
    tesseract_psm: int | None = None,
    debug_dir: str | Path | None = None,
) -> ExtractionConfig:
    file_config = load_config_file(config_path) if config_path is not None else {}

    resolved_profile = profile or str(file_config.get("profile", "table_scan"))

    return build_extraction_config(
        profile=resolved_profile,
        ocr_backend=ocr_backend if ocr_backend is not None else file_config.get("ocr_backend"),
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
    )
