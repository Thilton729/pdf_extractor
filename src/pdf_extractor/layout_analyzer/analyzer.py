"""Orchestrator for V1 layout analysis."""

from __future__ import annotations

from collections import Counter

from .classifiers.heuristic_classifier import classify_page
from .config import LayoutConfig
from .detectors.contours import detect_contours
from .detectors.lines import detect_lines
from .detectors.tables import detect_table_regions
from .models import DocumentLayout, PageImage, PageLayout
from .preprocess import prepare_analysis_layers
from .strategies.routing import choose_mode, choose_profile


class LayoutAnalyzer:
    """Analyze page structure and emit routing hints."""

    def analyze_page(self, page: PageImage, config: LayoutConfig) -> PageLayout:
        config.validate()
        layers = prepare_analysis_layers(page.image, config)
        line_result = detect_lines(layers["binary"], config)
        contour_boxes = detect_contours(layers["binary"], config)
        regions = detect_table_regions(line_result, contour_boxes, config)
        layout_type, confidence, hints = classify_page(page, regions, line_result, config)
        hints = dict(hints)
        page_layout = PageLayout(
            page_number=page.page_number,
            layout_type=layout_type,
            confidence=confidence,
            regions=regions,
            hints=hints,
        )
        page_layout.hints["recommended_mode"] = choose_mode(page_layout)
        page_layout.hints["recommended_profile"] = choose_profile(
            page_layout, str(hints.get("recommended_profile") or "table_scan")
        )
        return page_layout

    def analyze_document(
        self, pages: list[PageImage], config: LayoutConfig
    ) -> DocumentLayout:
        page_layouts = [self.analyze_page(page, config) for page in pages]
        if not page_layouts:
            return DocumentLayout()

        dominant_type, dominant_count = Counter(
            layout.layout_type for layout in page_layouts
        ).most_common(1)[0]
        confidence = dominant_count / len(page_layouts)
        document_layout = DocumentLayout(
            pages=page_layouts,
            document_type=dominant_type,
            confidence=confidence,
            hints={},
        )
        dominant_page = page_layouts[0]
        document_layout.hints["recommended_profile"] = choose_profile(
            dominant_page, dominant_page.hints.get("recommended_profile", "table_scan")
        )
        document_layout.hints["recommended_mode"] = choose_mode(dominant_page)
        return document_layout
