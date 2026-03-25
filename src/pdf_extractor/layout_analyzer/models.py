"""Models for layout analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


BBox = tuple[int, int, int, int]


@dataclass(slots=True)
class PageImage:
    """Rendered page image plus metadata used during layout analysis."""

    page_number: int
    image: Any
    width: int
    height: int
    dpi: int


@dataclass(slots=True)
class LayoutRegion:
    """Detected page region with a coarse semantic label."""

    kind: str
    bbox: BBox
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)


@dataclass(slots=True)
class PageLayout:
    """Layout analysis result for a single page."""

    page_number: int
    layout_type: str
    confidence: float
    regions: list[LayoutRegion] = field(default_factory=list)
    hints: dict[str, Any] = field(default_factory=dict)

    def get_regions_by_kind(self, kind: str) -> list[LayoutRegion]:
        return [region for region in self.regions if region.kind == kind]


@dataclass(slots=True)
class DocumentLayout:
    """Aggregated layout analysis result for a document."""

    pages: list[PageLayout] = field(default_factory=list)
    document_type: str = "unknown"
    confidence: float = 0.0
    hints: dict[str, Any] = field(default_factory=dict)

