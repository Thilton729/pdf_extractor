"""Placeholder Google Sheets exporter."""

from __future__ import annotations

from pathlib import Path

from ..models import ExtractedDocument


def write_google_sheets(document: ExtractedDocument, output_path: str | Path) -> None:
    _ = (document, output_path)
    raise NotImplementedError(
        "Google Sheets export is not implemented yet. Add API credentials and a Sheets client in a follow-up step."
    )

