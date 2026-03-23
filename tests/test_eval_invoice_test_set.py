from __future__ import annotations

import unittest

from pdf_extractor.models import TableData
from scripts.eval_invoice_test_set import extract_text_tokens, pick_best_items_table


class EvalInvoiceTestSetTests(unittest.TestCase):
    def test_pick_best_items_table_prefers_expected_row_count_and_headers(self) -> None:
        weak = TableData(headers=["A", "B"], rows=[["x"], ["y"]])
        strong = TableData(
            headers=["Description", "Qty", "Unit Price", "Amount"],
            rows=[["item1"], ["item2"], ["item3"]],
        )
        selected = pick_best_items_table([weak, strong], expected_items=3)
        self.assertIs(selected, strong)

    def test_extract_text_tokens_flattens_headers_and_rows(self) -> None:
        table = TableData(headers=["ID", "Amount"], rows=[["1", "$5.00"], ["2", "$7.00"]])
        self.assertEqual(
            extract_text_tokens(table),
            ["ID", "Amount", "1", "$5.00", "2", "$7.00"],
        )


if __name__ == "__main__":
    unittest.main()
