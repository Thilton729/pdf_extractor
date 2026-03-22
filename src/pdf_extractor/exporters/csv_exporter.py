"""CSV export implementation."""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import ExtractedDocument


def write_csv(document: ExtractedDocument, output_path: str | Path) -> None:
    path = Path(output_path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)

        if not document.tables:
            writer.writerow(["message"])
            writer.writerow(["No table-like data found in the PDF."])
            return

        for index, table in enumerate(document.tables):
            if index > 0:
                writer.writerow([])
            if table.title:
                writer.writerow([table.title])
            if table.headers:
                writer.writerow(table.headers)
            writer.writerows(table.rows)

