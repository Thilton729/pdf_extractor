from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_extractor.exporters import export_table
from pdf_extractor.models import ExtractedDocument, TableData


class ExporterTests(unittest.TestCase):
    def test_csv_export_writes_rows(self) -> None:
        document = ExtractedDocument(
            source_path="input.pdf",
            tables=[TableData(headers=["Name", "Age"], rows=[["Alice", "30"]])],
        )
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "out.csv"
            export_table(document, output_path, "csv")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").splitlines(),
                ["Name,Age", "Alice,30"],
            )

    def test_stub_exporters_fail_clearly(self) -> None:
        document = ExtractedDocument(source_path="input.pdf", tables=[])
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(NotImplementedError):
                export_table(document, Path(temp_dir) / "out.xlsx", "xlsx")
            with self.assertRaises(NotImplementedError):
                export_table(document, Path(temp_dir) / "ignored", "sheets")

    def test_unknown_format_is_rejected(self) -> None:
        document = ExtractedDocument(source_path="input.pdf", tables=[])
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                export_table(document, Path(temp_dir) / "out.txt", "txt")


if __name__ == "__main__":
    unittest.main()

