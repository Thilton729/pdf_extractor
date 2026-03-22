"""Placeholder Excel exporter."""

from __future__ import annotations

from pathlib import Path

from ..models import ExtractedDocument


def write_xlsx(document: ExtractedDocument, output_path: str | Path) -> None:
    _ = (document, output_path)
    raise NotImplementedError(
        "XLSX export is not implemented yet. Add an openpyxl-based exporter in a follow-up step."
    )

