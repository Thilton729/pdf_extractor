from __future__ import annotations

import unittest

from pdf_extractor.normalizer import normalize_rows


class NormalizerTests(unittest.TestCase):
    def test_normalize_rows_infers_header_and_pads_cells(self) -> None:
        table = normalize_rows(
            [
                ["Name", "Age"],
                ["Alice", 30],
                ["Bob"],
                [None, None],
            ]
        )
        self.assertEqual(table.headers, ["Name", "Age"])
        self.assertEqual(table.rows, [["Alice", "30"], ["Bob", ""]])

    def test_normalize_rows_without_data_returns_empty_table(self) -> None:
        table = normalize_rows([[None], [""]])
        self.assertEqual(table.headers, [])
        self.assertEqual(table.rows, [])


if __name__ == "__main__":
    unittest.main()

