from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from pdf_extractor.layout_analyzer import LayoutAnalyzer, LayoutConfig, PageImage
from pdf_extractor.layout_analyzer.classifiers.heuristic_classifier import classify_page
from pdf_extractor.layout_analyzer.debug import (
    save_layout_summary,
    save_preprocess_layers,
    save_region_overlay,
)
from pdf_extractor.layout_analyzer.detectors.contours import detect_contours
from pdf_extractor.layout_analyzer.detectors.lines import detect_lines
from pdf_extractor.layout_analyzer.detectors.tables import detect_table_regions
from pdf_extractor.layout_analyzer.models import LayoutRegion, PageLayout
from pdf_extractor.layout_analyzer.preprocess import prepare_analysis_layers
from pdf_extractor.layout_analyzer.strategies.routing import choose_mode, choose_profile


class LayoutAnalyzerTests(unittest.TestCase):
    def test_layout_config_validates(self) -> None:
        config = LayoutConfig(mode="debug", threshold_method="otsu")
        config.validate()

    def test_prepare_analysis_layers_preserves_dimensions(self) -> None:
        image = np.full((120, 200, 3), 255, dtype=np.uint8)
        layers = prepare_analysis_layers(image, LayoutConfig())
        self.assertEqual(layers["gray"].shape, (120, 200))
        self.assertEqual(layers["binary"].shape, (120, 200))

    def test_detect_lines_reports_density_for_grid(self) -> None:
        image = np.full((200, 300), 0, dtype=np.uint8)
        for y in (20, 80, 140, 180):
            cv2.line(image, (10, y), (290, y), 255, 2)
        for x in (20, 100, 180, 260):
            cv2.line(image, (x, 10), (x, 190), 255, 2)
        result = detect_lines(image, LayoutConfig())
        self.assertGreater(result["line_density"], 0.0)
        self.assertTrue(result["horizontal_lines"])
        self.assertTrue(result["vertical_lines"])

    def test_detect_contours_finds_block_regions(self) -> None:
        image = np.zeros((200, 300), dtype=np.uint8)
        cv2.rectangle(image, (20, 20), (140, 80), 255, -1)
        cv2.rectangle(image, (160, 110), (280, 180), 255, -1)
        boxes = detect_contours(image, LayoutConfig(min_region_area=500))
        self.assertGreaterEqual(len(boxes), 2)

    def test_detect_table_regions_returns_table_region(self) -> None:
        image = np.full((220, 320), 0, dtype=np.uint8)
        for y in (30, 80, 130, 180):
            cv2.line(image, (20, y), (300, y), 255, 2)
        for x in (30, 110, 190, 270):
            cv2.line(image, (x, 20), (x, 200), 255, 2)
        config = LayoutConfig(min_region_area=400)
        line_result = detect_lines(image, config)
        contours = detect_contours(image, config)
        regions = detect_table_regions(line_result, contours, config)
        self.assertTrue(regions)
        self.assertEqual(regions[0].kind, "table")

    def test_classifier_maps_regions_and_lines(self) -> None:
        page = PageImage(page_number=1, image=np.zeros((10, 10, 3), dtype=np.uint8), width=10, height=10, dpi=144)
        regions = [LayoutRegion(kind="table", bbox=(0, 0, 9, 9), confidence=0.9)]
        layout_type, confidence, hints = classify_page(
            page,
            regions,
            {"line_density": 0.03},
            LayoutConfig(),
        )
        self.assertEqual(layout_type, "structured_table")
        self.assertGreater(confidence, 0.6)
        self.assertEqual(hints["recommended_profile"], "table_scan")

    def test_routing_maps_page_types(self) -> None:
        layout = PageLayout(page_number=1, layout_type="mixed", confidence=0.6)
        self.assertEqual(choose_profile(layout), "table_scan")
        self.assertEqual(choose_mode(layout), "hybrid")

    def test_analyzer_returns_page_layout(self) -> None:
        image = np.full((220, 320, 3), 255, dtype=np.uint8)
        for y in (30, 80, 130, 180):
            cv2.line(image, (20, y), (300, y), (0, 0, 0), 2)
        for x in (30, 110, 190, 270):
            cv2.line(image, (x, 20), (x, 200), (0, 0, 0), 2)
        analyzer = LayoutAnalyzer()
        page = PageImage(page_number=1, image=image, width=320, height=220, dpi=144)
        result = analyzer.analyze_page(page, LayoutConfig())
        self.assertEqual(result.page_number, 1)
        self.assertIn(result.layout_type, {"structured_table", "mixed", "unknown"})

    def test_debug_helpers_write_artifacts(self) -> None:
        image = np.full((120, 200, 3), 255, dtype=np.uint8)
        layers = prepare_analysis_layers(image, LayoutConfig())
        layout = PageLayout(
            page_number=1,
            layout_type="structured_table",
            confidence=0.8,
            regions=[LayoutRegion(kind="table", bbox=(10, 10, 100, 80), confidence=0.9)],
            hints={"recommended_profile": "table_scan"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            save_preprocess_layers(1, layers, temp_dir)
            save_region_overlay(1, image, layout.regions, temp_dir)
            save_layout_summary(layout, temp_dir)
            page_dir = Path(temp_dir) / "page_001"
            self.assertTrue((page_dir / "page_001_original.png").exists())
            self.assertTrue((page_dir / "page_001_regions.png").exists())
            summary = json.loads((page_dir / "page_001_layout.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["layout_type"], "structured_table")


if __name__ == "__main__":
    unittest.main()
