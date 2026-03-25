"""Heuristic page classifier for layout analysis V1."""

from __future__ import annotations

from ..config import LayoutConfig
from ..models import LayoutRegion, PageImage


def classify_page(
    page_image: PageImage,
    regions: list[LayoutRegion],
    line_result: dict[str, object],
    config: LayoutConfig,
) -> tuple[str, float, dict[str, object]]:
    """Classify a page using simple line/region heuristics."""
    table_regions = [region for region in regions if region.kind == "table"]
    line_density = float(line_result.get("line_density", 0.0))
    region_count = len(regions)

    if table_regions and line_density >= 0.01:
        confidence = min(0.95, 0.65 + min(line_density * 8, 0.2))
        return (
            "structured_table",
            confidence,
            {
                "recommended_profile": "table_scan",
                "prefer_ocr": True,
                "line_density": round(line_density, 4),
                "table_region_count": len(table_regions),
            },
        )

    if region_count > 0 and line_density > 0.002:
        return (
            "mixed",
            0.6,
            {
                "recommended_profile": "table_scan",
                "prefer_ocr": True,
                "line_density": round(line_density, 4),
                "table_region_count": len(table_regions),
            },
        )

    if region_count <= 1 and line_density < 0.002:
        return (
            "text_heavy",
            0.65,
            {
                "recommended_profile": "table_scan",
                "prefer_ocr": False,
                "line_density": round(line_density, 4),
            },
        )

    return (
        "unknown",
        0.4,
        {
            "recommended_profile": "table_scan",
            "prefer_ocr": bool(table_regions),
            "line_density": round(line_density, 4),
        },
    )
