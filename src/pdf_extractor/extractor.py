"""PDF extraction entrypoints and backend wiring."""

from __future__ import annotations

from pathlib import Path

from .config import ExtractionConfig, build_extraction_config
from .models import ExtractedDocument
from .pdf_backends import PdfExtractionError, PdfPlumberExtractor


def extract_tables(
    pdf_path: str | Path, config: ExtractionConfig | None = None
) -> ExtractedDocument:
    """Extract normalized table data from a PDF path."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Input PDF does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.name}")

    extractor = PdfPlumberExtractor(config=config or build_extraction_config())
    try:
        return extractor.extract(path)
    except PdfExtractionError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise PdfExtractionError(f"Failed to extract data from {path}: {exc}") from exc
