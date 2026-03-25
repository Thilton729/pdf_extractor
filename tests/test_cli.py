from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pdf_extractor.cli import build_parser, main
from pdf_extractor.config import ExtractionConfig
from pdf_extractor.models import ExtractedDocument, TableData


class CliTests(unittest.TestCase):
    def test_parser_defaults_to_csv(self) -> None:
        args = build_parser().parse_args(["extract", "input.pdf", "--output", "out.csv"])
        self.assertEqual(args.format, "csv")
        self.assertIsNone(args.profile)
        self.assertIsNone(args.ocr_backend)
        self.assertIsNone(args.header_strategy)
        self.assertIsNone(args.layout_analysis)

    def test_main_returns_zero_on_success(self) -> None:
        document = ExtractedDocument(
            source_path="input.pdf",
            tables=[TableData(headers=["name"], rows=[["alice"]])],
        )
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "out.csv"
            with patch("pdf_extractor.cli.extract_tables", return_value=document) as extract_mock:
                exit_code = main(["extract", "input.pdf", "--output", str(output_path)])
            self.assertTrue(output_path.exists())
        extract_mock.assert_called_once()
        self.assertEqual(exit_code, 0)

    def test_main_builds_config_from_cli_options(self) -> None:
        document = ExtractedDocument(source_path="input.pdf", tables=[])
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "out.csv"
            debug_dir = Path(temp_dir) / "debug"
            with patch("pdf_extractor.cli.extract_tables", return_value=document) as extract_mock:
                main(
                    [
                        "extract",
                        "input.pdf",
                        "--output",
                        str(output_path),
                        "--profile",
                        "form_scan",
                        "--ocr-backend",
                        "tesseract",
                        "--render-scale",
                        "4.0",
                        "--header-strategy",
                        "carry-forward",
                        "--threshold",
                        "170",
                        "--min-confidence",
                        "0.35",
                        "--row-y-tolerance",
                        "12",
                        "--column-x-tolerance",
                        "20",
                        "--tesseract-psm",
                        "11",
                        "--debug-dir",
                        str(debug_dir),
                        "--layout-analysis",
                        "debug",
                        "--layout-render-scale",
                        "2.5",
                        "--layout-min-region-area",
                        "700",
                        "--layout-merge-iou-threshold",
                        "0.6",
                        "--layout-line-kernel-scale",
                        "25",
                        "--layout-threshold-method",
                        "otsu",
                        "--layout-region-padding",
                        "12",
                    ]
                )
        passed_config = extract_mock.call_args.kwargs["config"]
        self.assertIsInstance(passed_config, ExtractionConfig)
        self.assertEqual(passed_config.profile, "form_scan")
        self.assertEqual(passed_config.ocr_backend, "tesseract")
        self.assertEqual(passed_config.header_strategy, "carry-forward")
        self.assertEqual(passed_config.debug_dir, debug_dir)
        self.assertEqual(passed_config.layout_config.mode, "debug")
        self.assertEqual(passed_config.layout_config.render_scale, 2.5)
        self.assertEqual(passed_config.layout_config.min_region_area, 700)
        self.assertEqual(passed_config.layout_config.merge_iou_threshold, 0.6)
        self.assertEqual(passed_config.layout_config.line_kernel_scale, 25)
        self.assertEqual(passed_config.layout_config.threshold_method, "otsu")
        self.assertEqual(passed_config.layout_config.region_padding, 12)

    def test_main_exits_for_missing_input(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["extract", "missing.pdf", "--output", "out.csv"])
        self.assertEqual(context.exception.code, 1)

    def test_main_loads_config_file_and_allows_cli_override(self) -> None:
        document = ExtractedDocument(source_path="input.pdf", tables=[])
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "out.csv"
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                '{"profile":"directory_scan","ocr_backend":"rapidocr","header_strategy":"page","threshold":165,"layout_analysis":"debug"}',
                encoding="utf-8",
            )
            with patch("pdf_extractor.cli.extract_tables", return_value=document) as extract_mock:
                main(
                    [
                        "extract",
                        "input.pdf",
                        "--output",
                        str(output_path),
                        "--config",
                        str(config_path),
                        "--threshold",
                        "190",
                        "--layout-analysis",
                        "auto",
                    ]
                )
        passed_config = extract_mock.call_args.kwargs["config"]
        self.assertEqual(passed_config.profile, "directory_scan")
        self.assertEqual(passed_config.ocr_backend, "rapidocr")
        self.assertEqual(passed_config.header_strategy, "page")
        self.assertEqual(passed_config.threshold, 190)
        self.assertEqual(passed_config.layout_config.mode, "auto")


if __name__ == "__main__":
    unittest.main()
