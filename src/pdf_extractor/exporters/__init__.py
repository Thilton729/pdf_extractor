"""Export helpers for extracted table data."""

from __future__ import annotations

from pathlib import Path

from ..models import ExtractedDocument
from .csv_exporter import write_csv
from .sheets_exporter import write_google_sheets
from .xlsx_exporter import write_xlsx


def export_table(document: ExtractedDocument, output_path: str | Path, output_format: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "csv":
        write_csv(document, path)
        return
    if output_format == "xlsx":
        write_xlsx(document, path)
        return
    if output_format == "sheets":
        write_google_sheets(document, path)
        return

    raise ValueError(f"Unsupported export format: {output_format}")

