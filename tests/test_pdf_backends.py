from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pdf_extractor.config import build_extraction_config
from pdf_extractor.models import TableData
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

    def test_write_debug_overlays_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            extractor = PdfPlumberExtractor(
                config=build_extraction_config(debug_dir=temp_dir)
            )
            page_dir = Path(temp_dir) / "page_001"
            page_dir.mkdir(parents=True, exist_ok=True)

            from PIL import Image

            Image.new("RGB", (100, 80), "white").save(page_dir / "rendered_page.png")
            lines = [
                [
                    {"x0": 5.0, "y0": 5.0, "x1": 30.0, "y1": 20.0, "text": "Header", "score": 0.9},
                    {"x0": 40.0, "y0": 5.0, "x1": 65.0, "y1": 20.0, "text": "Value", "score": 0.9},
                ],
                [
                    {"x0": 5.0, "y0": 30.0, "x1": 30.0, "y1": 45.0, "text": "A", "score": 0.9},
                    {"x0": 40.0, "y0": 30.0, "x1": 65.0, "y1": 45.0, "text": "B", "score": 0.9},
                ],
            ]

            extractor._write_debug_overlays(
                page_index=1,
                backend_name="rapidocr",
                lines=lines,
                header_index=0,
                column_ranges=[(-float("inf"), 35.0), (35.0, float("inf"))],
            )

            self.assertTrue((page_dir / "rapidocr_tokens_overlay.png").exists())
            self.assertTrue((page_dir / "rapidocr_rows_overlay.png").exists())
            self.assertTrue((page_dir / "rapidocr_columns_overlay.png").exists())

    def test_should_carry_forward_headers_for_continuation_page(self) -> None:
        table = TableData(
            headers=[
                "27",
                "Dr. Matthew Curtis",
                "dr..matthew.curtis@example",
                ".0c0o1m-590-539-0515",
                "40021 Pratt Trail Suite 750...",
                "S9GK77IGQ8",
                "2024-06-17",
                "$2,297.52",
            ],
            rows=[["28", "Bryan Bowman", "example", "123", "Street", "INV", "2021-01-01", "$5.00"]],
        )
        prior_headers = [
            "ID",
            "Name",
            "Email",
            "Phone",
            "Address",
            "InvoiceNumber",
            "InvoiceDate",
            "AmountDue",
        ]
        self.assertTrue(self.extractor._should_carry_forward_headers(table, prior_headers))

    def test_normalize_page_table_carries_forward_headers(self) -> None:
        extractor = PdfPlumberExtractor(config=build_extraction_config(header_strategy="carry-forward"))
        raw_table = [
            [
                "27",
                "Dr. Matthew Curtis",
                "dr..matthew.curtis@example",
                ".0c0o1m-590-539-0515",
                "40021 Pratt Trail Suite 750...",
                "S9GK77IGQ8",
                "2024-06-17",
                "$2,297.52",
            ],
            ["28", "Bryan Bowman", "example", "123", "Street", "INV", "2021-01-01", "$5.00"],
        ]
        prior_headers = [
            "ID",
            "Name",
            "Email",
            "Phone",
            "Address",
            "InvoiceNumber",
            "InvoiceDate",
            "AmountDue",
        ]
        normalized = extractor._normalize_page_table(raw_table, prior_headers)
        self.assertEqual(normalized.headers, prior_headers)
        self.assertEqual(normalized.rows[0][0], "27")

    def test_merge_continuation_tables_combines_same_schema_item_tables(self) -> None:
        first = TableData(
            headers=["Description", "Qty", "Unit Price", "Line Total"],
            rows=[["Item 1", "1", "$10.00", "$10.00"]],
            source_page=1,
        )
        second = TableData(
            headers=["Description", "Qty", "Unit Price", "Line Total"],
            rows=[["Item 2", "2", "$10.00", "$20.00"]],
            source_page=2,
        )
        totals = TableData(
            headers=["Subtotal", "$30.00"],
            rows=[["Tax", "$2.00"]],
            source_page=2,
        )
        merged = self.extractor._merge_continuation_tables([first, second, totals])
        self.assertEqual(len(merged), 2)
        self.assertEqual(len(merged[0].rows), 2)
        self.assertEqual(merged[0].rows[1][0], "Item 2")
        self.assertEqual(merged[1].headers, ["Subtotal", "$30.00"])


if __name__ == "__main__":
    unittest.main()
