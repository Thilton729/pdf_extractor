from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pdf_extractor.config import build_extraction_config
from pdf_extractor.pdf_backends import PdfPlumberExtractor


class PdfBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PdfPlumberExtractor(config=build_extraction_config())

    def test_split_zip_and_website(self) -> None:
        zip_code, website = self.extractor._split_zip_and_website("10001https://example.com")
        self.assertEqual(zip_code, "10001")
        self.assertEqual(website, "https://example.com")

    def test_split_name_phone_address(self) -> None:
        name, phone, address = self.extractor._split_name_phone_address(
            "MAXBURST,Inc./WebDesignCo+1212-651-187127West30thSt"
        )
        self.assertEqual(name, "MAXBURST,Inc./WebDesignCo")
        self.assertEqual(phone, "+1212-651-1871")
        self.assertEqual(address, "27West30thSt")

    def test_parse_directory_row_builds_six_columns(self) -> None:
        row = self.extractor._parse_directory_row(
            [
                {"text": "Beluga Labs +1855-823-584:2445thAvenue"},
                {"text": "10001http://belugalabs.com"},
            ]
        )
        self.assertEqual(row[0], "Beluga Labs")
        self.assertEqual(row[1], "")
        self.assertEqual(row[2], "+1855-823-584")
        self.assertEqual(row[3], "2445thAvenue")
        self.assertEqual(row[4], "10001")
        self.assertEqual(row[5], "http://belugalabs.com")

    def test_normalize_phone_moves_extra_digits_to_address(self) -> None:
        row = self.extractor._parse_directory_row(
            [
                {"text": "ReachAbove Media +1347-996-655103-20117thStr"},
                {"text": "11419https://example.com"},
            ]
        )
        self.assertEqual(row[2], "+1347-996-6551")
        self.assertEqual(row[3], "0320117thStr")

    def test_parse_tesseract_tsv_filters_empty_and_low_confidence_rows(self) -> None:
        content = "\t".join(
            ["level", "page_num", "block_num", "par_num", "line_num", "word_num", "left", "top", "width", "height", "conf", "text"]
        )
        content += "\n"
        content += "\t".join(["5", "1", "1", "1", "1", "1", "10", "20", "30", "40", "95", "Header"])
        content += "\n"
        content += "\t".join(["5", "1", "1", "1", "1", "2", "50", "20", "30", "40", "10", "noise"])
        content += "\n"
        content += "\t".join(["5", "1", "1", "1", "1", "3", "90", "20", "30", "40", "-1", ""])
        content += "\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            tsv_path = Path(temp_dir) / "sample.tsv"
            tsv_path.write_text(content, encoding="utf-8")
            items = self.extractor._parse_tesseract_tsv(tsv_path)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][1], "Header")

    def test_assign_line_to_columns_uses_header_ranges(self) -> None:
        ranges = [(-float("inf"), 15.0), (15.0, 30.0), (30.0, float("inf"))]
        row = self.extractor._assign_line_to_columns(
            [
                {"x0": 1.0, "x1": 10.0, "text": "A"},
                {"x0": 16.0, "x1": 22.0, "text": "B"},
                {"x0": 31.0, "x1": 40.0, "text": "C"},
            ],
            ranges,
        )
        self.assertEqual(row, ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
