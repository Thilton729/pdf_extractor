"""Debug artifact helpers for layout analysis."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .models import DocumentLayout, PageLayout


def save_preprocess_layers(
    page_number: int, layers: dict[str, np.ndarray], debug_dir: str | Path
) -> None:
    """Save preprocess layers for a page."""
    page_dir = _page_dir(debug_dir, page_number)
    for name, image in layers.items():
        _write_image(page_dir / f"page_{page_number:03d}_{name}.png", image)


def save_region_overlay(
    page_number: int,
    image: Any,
    regions: list[Any],
    debug_dir: str | Path,
) -> None:
    """Save a labeled region overlay image."""
    page_dir = _page_dir(debug_dir, page_number)
    canvas = _to_bgr(image)
    for region in regions:
        x1, y1, x2, y2 = region.bbox
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{region.kind}:{region.confidence:.2f}"
        cv2.putText(
            canvas,
            label,
            (x1, max(12, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 0, 0),
            1,
            cv2.LINE_AA,
        )
    _write_image(page_dir / f"page_{page_number:03d}_regions.png", canvas)


def save_layout_summary(page_layout: PageLayout, debug_dir: str | Path) -> None:
    """Save JSON summary for a page layout result."""
    page_dir = _page_dir(debug_dir, page_layout.page_number)
    payload = _to_jsonable(page_layout)
    (page_dir / f"page_{page_layout.page_number:03d}_layout.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )


def save_document_summary(document_layout: DocumentLayout, debug_dir: str | Path) -> None:
    """Save JSON summary for a document layout result."""
    debug_path = Path(debug_dir)
    debug_path.mkdir(parents=True, exist_ok=True)
    (debug_path / "document_layout.json").write_text(
        json.dumps(_to_jsonable(document_layout), indent=2, default=str),
        encoding="utf-8",
    )


def _page_dir(debug_dir: str | Path, page_number: int) -> Path:
    page_dir = Path(debug_dir) / f"page_{page_number:03d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    return page_dir


def _write_image(path: Path, image: np.ndarray) -> None:
    cv2.imwrite(str(path), image)


def _to_bgr(image: Any) -> np.ndarray:
    if isinstance(image, np.ndarray):
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image.copy()
    if hasattr(image, "convert"):
        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    raise ValueError("Unsupported image type for debug output.")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
