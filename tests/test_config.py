from __future__ import annotations

import unittest
from pathlib import Path

from pdf_extractor.config import build_extraction_config


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


if __name__ == "__main__":
    unittest.main()
