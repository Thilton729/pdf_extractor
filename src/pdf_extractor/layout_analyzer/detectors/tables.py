"""Table-region detection helpers."""

from __future__ import annotations

from ..config import LayoutConfig
from ..models import LayoutRegion


def detect_table_regions(
    line_result: dict[str, object],
    contours: list[tuple[int, int, int, int]],
    config: LayoutConfig,
) -> list[LayoutRegion]:
    """Turn line and contour signals into probable table regions."""
    if not config.detect_tables:
        return []

    line_density = float(line_result.get("line_density", 0.0))
    line_boxes = [
        *line_result.get("horizontal_lines", []),
        *line_result.get("vertical_lines", []),
    ]

    regions: list[LayoutRegion] = []
    for bbox in contours:
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        if width < 40 or height < 20:
            continue

        overlap_hits = sum(
            1 for line_box in line_boxes if _intersection_ratio(bbox, line_box) >= 0.1
        )
        rectangularity = min(width, height) / max(width, height) if max(width, height) else 0.0
        if overlap_hits == 0 and line_density < 0.01:
            continue
        if width < 100 and overlap_hits < 2:
            continue

        confidence = min(
            0.95,
            0.35 + min(line_density * 10, 0.35) + min(overlap_hits * 0.08, 0.24),
        )
        regions.append(
            LayoutRegion(
                kind="table",
                bbox=bbox,
                confidence=confidence,
                metadata={
                    "detector_source": ["lines", "contours", "tables"],
                    "line_overlap_count": overlap_hits,
                    "line_density": round(line_density, 4),
                    "aspect_ratio": round(width / max(height, 1), 4),
                    "rectangularity": round(rectangularity, 4),
                },
            )
        )

    return _merge_regions(regions, config.merge_iou_threshold, config.region_padding)


def _merge_regions(
    regions: list[LayoutRegion], threshold: float, padding: int
) -> list[LayoutRegion]:
    merged: list[LayoutRegion] = []
    for region in sorted(regions, key=lambda item: (item.bbox[1], item.bbox[0])):
        candidate = _pad_region(region, padding)
        for idx, existing in enumerate(merged):
            if _iou(candidate.bbox, existing.bbox) >= threshold:
                merged[idx] = _combine_regions(existing, candidate)
                break
        else:
            merged.append(candidate)
    return merged


def _pad_region(region: LayoutRegion, padding: int) -> LayoutRegion:
    x1, y1, x2, y2 = region.bbox
    return LayoutRegion(
        kind=region.kind,
        bbox=(max(0, x1 - padding), max(0, y1 - padding), x2 + padding, y2 + padding),
        confidence=region.confidence,
        metadata=dict(region.metadata),
    )


def _combine_regions(left: LayoutRegion, right: LayoutRegion) -> LayoutRegion:
    x1 = min(left.bbox[0], right.bbox[0])
    y1 = min(left.bbox[1], right.bbox[1])
    x2 = max(left.bbox[2], right.bbox[2])
    y2 = max(left.bbox[3], right.bbox[3])
    sources = set(left.metadata.get("detector_source", [])) | set(
        right.metadata.get("detector_source", [])
    )
    return LayoutRegion(
        kind=left.kind,
        bbox=(x1, y1, x2, y2),
        confidence=max(left.confidence, right.confidence),
        metadata={"detector_source": sorted(sources)},
    )


def _intersection_ratio(
    left: tuple[int, int, int, int], right: tuple[int, int, int, int]
) -> float:
    ix1 = max(left[0], right[0])
    iy1 = max(left[1], right[1])
    ix2 = min(left[2], right[2])
    iy2 = min(left[3], right[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    left_area = max(1, (left[2] - left[0]) * (left[3] - left[1]))
    return intersection / left_area


def _iou(
    left: tuple[int, int, int, int], right: tuple[int, int, int, int]
) -> float:
    ix1 = max(left[0], right[0])
    iy1 = max(left[1], right[1])
    ix2 = min(left[2], right[2])
    iy2 = min(left[3], right[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    left_area = max(1, (left[2] - left[0]) * (left[3] - left[1]))
    right_area = max(1, (right[2] - right[0]) * (right[3] - right[1]))
    return intersection / float(left_area + right_area - intersection)
