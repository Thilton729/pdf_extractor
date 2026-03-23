from __future__ import annotations

import argparse
import json
from pathlib import Path

from pdf_extractor.config import build_extraction_config_from_sources
from pdf_extractor.extractor import extract_tables
from pdf_extractor.exporters.csv_exporter import write_csv
from pdf_extractor.models import TableData


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the extractor against the invoice_test_set bundle."
    )
    parser.add_argument(
        "--data-dir",
        default="data/invoice_test_set",
        help="Directory containing invoice PDFs and ground_truth.json.",
    )
    parser.add_argument(
        "--output-dir",
        default="sample_output/invoice_test_set_eval",
        help="Directory for extracted CSVs and summary output.",
    )
    parser.add_argument(
        "--config",
        default="configs/table-scan.json",
        help="Optional extractor JSON config.",
    )
    parser.add_argument(
        "--header-strategy",
        default="carry-forward",
        choices=("auto", "page", "carry-forward"),
        help="Header behavior to use during extraction.",
    )
    return parser.parse_args()


def load_ground_truth(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_best_items_table(document_tables: list[TableData], expected_items: int) -> TableData | None:
    if not document_tables:
        return None

    def score(table: TableData) -> tuple[float, float, float]:
        headers = [header.lower() for header in table.headers]
        header_hits = sum(
            any(keyword in header for header in headers)
            for keyword in ("item", "description", "qty", "quantity", "unit", "amount", "total")
        )
        row_delta = abs(len(table.rows) - expected_items)
        non_empty_rows = sum(any(cell.strip() for cell in row) for row in table.rows)
        return (header_hits, -row_delta, non_empty_rows)

    return max(document_tables, key=score)


def extract_text_tokens(table: TableData) -> list[str]:
    tokens = [cell.strip() for cell in table.headers if cell.strip()]
    for row in table.rows:
        tokens.extend(cell.strip() for cell in row if cell.strip())
    return tokens


def evaluate_invoice(entry: dict, document, output_dir: Path) -> dict:
    expected_items = len(entry["items"])
    table = pick_best_items_table(document.tables, expected_items)
    csv_path = output_dir / f"{Path(entry['file']).stem}.csv"
    write_csv(document, csv_path)

    result = {
        "file": entry["file"],
        "csv_path": str(csv_path),
        "table_count": len(document.tables),
        "selected_table_headers": table.headers if table else [],
        "selected_row_count": len(table.rows) if table else 0,
        "expected_item_count": expected_items,
        "item_count_delta": abs((len(table.rows) if table else 0) - expected_items),
        "invoice_no_found": False,
        "seller_name_found": False,
        "buyer_name_found": False,
        "notes_snippet_found": False,
    }

    if table is None:
        return result

    tokens = extract_text_tokens(table)
    token_blob = " ".join(tokens)
    result["invoice_no_found"] = entry["invoice_no"] in token_blob
    result["seller_name_found"] = entry["seller"]["name"] in token_blob
    result["buyer_name_found"] = entry["buyer"]["name"] in token_blob
    note_prefix = entry["notes"].split(".")[0]
    result["notes_snippet_found"] = note_prefix in token_blob
    return result


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ground_truth = load_ground_truth(data_dir / "ground_truth.json")
    config = build_extraction_config_from_sources(
        config_path=args.config,
        header_strategy=args.header_strategy,
    )

    results = []
    for entry in ground_truth:
        pdf_path = data_dir / entry["file"]
        document = extract_tables(pdf_path, config=config)
        results.append(evaluate_invoice(entry, document, output_dir))

    summary = {
        "config": {
            "config_path": args.config,
            "header_strategy": args.header_strategy,
        },
        "results": results,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    passed_item_count = sum(result["item_count_delta"] == 0 for result in results)
    found_invoice_numbers = sum(result["invoice_no_found"] for result in results)
    print(f"Processed {len(results)} invoices")
    print(f"Exact item-count matches: {passed_item_count}/{len(results)}")
    print(f"Invoice number found in selected table: {found_invoice_numbers}/{len(results)}")
    print(f"Summary written to {output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
