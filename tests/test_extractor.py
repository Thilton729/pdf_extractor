from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pdf_extractor.config import build_extraction_config
from pdf_extractor.extractor import extract_tables


class ExtractorTests(unittest.TestCase):
    def test_extract_tables_requires_existing_pdf(self) -> None:
        with self.assertRaises(FileNotFoundError):
            extract_tables("missing.pdf")

    def test_extract_tables_requires_pdf_extension(self) -> None:
        with TemporaryDirectory() as temp_dir:
            text_path = Path(temp_dir) / "input.txt"
            text_path.write_text("not a pdf", encoding="utf-8")
            with self.assertRaises(ValueError):
                extract_tables(text_path)

    def test_extract_tables_passes_config_to_backend(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "input.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            config = build_extraction_config(profile="directory_scan", ocr_backend="tesseract")
            with patch("pdf_extractor.extractor.PdfPlumberExtractor") as extractor_cls:
                extractor_instance = extractor_cls.return_value
                extractor_instance.extract.return_value = object()
                extract_tables(pdf_path, config=config)
        extractor_cls.assert_called_once_with(config=config)


if __name__ == "__main__":
    unittest.main()
