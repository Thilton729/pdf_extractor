from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_extractor.config import (
    build_extraction_config,
    build_extraction_config_from_sources,
    load_config_file,
)


class ConfigTests(unittest.TestCase):
    def test_build_extraction_config_uses_profile_defaults(self) -> None:
        config = build_extraction_config(profile="form_scan")
        self.assertEqual(config.profile, "form_scan")
        self.assertEqual(config.tesseract_psm, 11)
        self.assertEqual(config.ocr_backend, "auto")
        self.assertEqual(config.header_strategy, "auto")

    def test_build_extraction_config_applies_overrides(self) -> None:
        config = build_extraction_config(
            profile="table_scan",
            ocr_backend="tesseract",
            header_strategy="carry-forward",
            render_scale=4.0,
            threshold=165,
            min_confidence=0.4,
            row_y_tolerance=12.0,
            column_x_tolerance=18.0,
            tesseract_psm=4,
            debug_dir="debug-artifacts",
            layout_analysis="debug",
            layout_render_scale=2.5,
            layout_min_region_area=700,
            layout_merge_iou_threshold=0.6,
            layout_line_kernel_scale=25,
            layout_threshold_method="otsu",
            layout_region_padding=12,
        )
        self.assertEqual(config.ocr_backend, "tesseract")
        self.assertEqual(config.header_strategy, "carry-forward")
        self.assertEqual(config.render_scale, 4.0)
        self.assertEqual(config.threshold, 165)
        self.assertEqual(config.min_confidence, 0.4)
        self.assertEqual(config.row_y_tolerance, 12.0)
        self.assertEqual(config.column_x_tolerance, 18.0)
        self.assertEqual(config.tesseract_psm, 4)
        self.assertEqual(config.debug_dir, Path("debug-artifacts"))
        self.assertEqual(config.layout_config.mode, "debug")
        self.assertEqual(config.layout_config.debug_dir, Path("debug-artifacts"))
        self.assertEqual(config.layout_config.render_scale, 2.5)
        self.assertEqual(config.layout_config.min_region_area, 700)
        self.assertEqual(config.layout_config.merge_iou_threshold, 0.6)
        self.assertEqual(config.layout_config.line_kernel_scale, 25)
        self.assertEqual(config.layout_config.threshold_method, "otsu")
        self.assertEqual(config.layout_config.region_padding, 12)

    def test_load_config_file_reads_json_object(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text('{"profile":"directory_scan","threshold":165}', encoding="utf-8")
            payload = load_config_file(config_path)
        self.assertEqual(payload["profile"], "directory_scan")
        self.assertEqual(payload["threshold"], 165)

    def test_build_extraction_config_from_sources_merges_file_and_cli(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                '{"profile":"directory_scan","ocr_backend":"rapidocr","header_strategy":"page","threshold":165,"debug_dir":"from-file","layout_analysis":"debug","layout_threshold_method":"otsu"}',
                encoding="utf-8",
            )
            config = build_extraction_config_from_sources(
                config_path=config_path,
                threshold=190,
                debug_dir="from-cli",
                layout_analysis="auto",
            )
        self.assertEqual(config.profile, "directory_scan")
        self.assertEqual(config.ocr_backend, "rapidocr")
        self.assertEqual(config.header_strategy, "page")
        self.assertEqual(config.threshold, 190)
        self.assertEqual(config.debug_dir, Path("from-cli"))
        self.assertEqual(config.layout_config.mode, "auto")
        self.assertEqual(config.layout_config.debug_dir, Path("from-cli"))
        self.assertEqual(config.layout_config.threshold_method, "otsu")


if __name__ == "__main__":
    unittest.main()
