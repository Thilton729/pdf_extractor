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

    def test_build_extraction_config_applies_overrides(self) -> None:
        config = build_extraction_config(
            profile="table_scan",
            ocr_backend="tesseract",
            render_scale=4.0,
            threshold=165,
            min_confidence=0.4,
            row_y_tolerance=12.0,
            column_x_tolerance=18.0,
            tesseract_psm=4,
            debug_dir="debug-artifacts",
        )
        self.assertEqual(config.ocr_backend, "tesseract")
        self.assertEqual(config.render_scale, 4.0)
        self.assertEqual(config.threshold, 165)
        self.assertEqual(config.min_confidence, 0.4)
        self.assertEqual(config.row_y_tolerance, 12.0)
        self.assertEqual(config.column_x_tolerance, 18.0)
        self.assertEqual(config.tesseract_psm, 4)
        self.assertEqual(config.debug_dir, Path("debug-artifacts"))

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
                '{"profile":"directory_scan","ocr_backend":"rapidocr","threshold":165,"debug_dir":"from-file"}',
                encoding="utf-8",
            )
            config = build_extraction_config_from_sources(
                config_path=config_path,
                threshold=190,
                debug_dir="from-cli",
            )
        self.assertEqual(config.profile, "directory_scan")
        self.assertEqual(config.ocr_backend, "rapidocr")
        self.assertEqual(config.threshold, 190)
        self.assertEqual(config.debug_dir, Path("from-cli"))


if __name__ == "__main__":
    unittest.main()
