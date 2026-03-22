"""Helpers for shaping raw extracted rows into a consistent tabular form."""

from __future__ import annotations

from .models import TableData


def normalize_rows(raw_rows: list[list[object | None]]) -> TableData:
    """Normalize ragged rows and infer a header row when possible."""
    cleaned_rows: list[list[str]] = []

    for raw_row in raw_rows:
        cleaned = [str(cell).strip() if cell is not None else "" for cell in raw_row]
        if any(cell for cell in cleaned):
            cleaned_rows.append(cleaned)

    if not cleaned_rows:
        return TableData(headers=[], rows=[])

    width = max(len(row) for row in cleaned_rows)
    padded_rows = [row + [""] * (width - len(row)) for row in cleaned_rows]

    header_candidate = padded_rows[0]
    data_rows = padded_rows[1:] if len(padded_rows) > 1 else []

    has_header = any(cell for cell in header_candidate) and any(
        any(cell for cell in row) for row in data_rows
    )

    if has_header:
        return TableData(headers=header_candidate, rows=data_rows)

    return TableData(headers=[], rows=padded_rows)

