"""Command line interface for PDF extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import (
    OCR_BACKENDS,
    HEADER_STRATEGIES,
    OCR_PROFILES,
    build_extraction_config_from_sources,
)
from .constants import DEFAULT_EXPORT_FORMAT, SUPPORTED_FORMATS
from .extractor import extract_tables
from .exporters import export_table
from .pdf_backends import PdfExtractionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-extractor",
        description="Extract table-like data from a PDF into spreadsheet-friendly formats.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract", help="Extract data from a PDF and export it."
    )
    extract_parser.add_argument("pdf_path", help="Path to the input PDF.")
    extract_parser.add_argument(
        "--output",
        required=True,
        help="Where to write the exported file.",
    )
    extract_parser.add_argument(
        "--format",
        default=DEFAULT_EXPORT_FORMAT,
        choices=SUPPORTED_FORMATS,
        help="Export format.",
    )
    extract_parser.add_argument(
        "--config",
        help="Optional JSON config file for OCR/layout tuning. CLI flags override file values.",
    )
    extract_parser.add_argument(
        "--profile",
        choices=OCR_PROFILES,
        help="OCR/layout tuning profile for scanned PDFs.",
    )
    extract_parser.add_argument(
        "--ocr-backend",
        choices=OCR_BACKENDS,
        help="OCR backend for scanned PDFs.",
    )
    extract_parser.add_argument(
        "--header-strategy",
        choices=HEADER_STRATEGIES,
        help="Header handling for multi-page or repeated tables.",
    )
    extract_parser.add_argument(
        "--render-scale",
        type=float,
        help="PDF page render scale for OCR image generation.",
    )
    extract_parser.add_argument(
        "--threshold",
        type=int,
        help="Binary threshold used during scanned-PDF preprocessing.",
    )
    extract_parser.add_argument(
        "--min-confidence",
        type=float,
        help="Minimum OCR confidence to keep a detected token, between 0 and 1.",
    )
    extract_parser.add_argument(
        "--row-y-tolerance",
        type=float,
        help="Vertical grouping tolerance when assembling OCR tokens into rows.",
    )
    extract_parser.add_argument(
        "--column-x-tolerance",
        type=float,
        help="Horizontal tolerance for assigning OCR tokens to inferred columns.",
    )
    extract_parser.add_argument(
        "--tesseract-psm",
        type=int,
        help="Tesseract page segmentation mode to use for scanned PDFs.",
    )
    extract_parser.add_argument(
        "--debug-dir",
        help="Optional directory for OCR/debug artifacts such as images, TSV, and summaries.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "extract":
        parser.error(f"Unsupported command: {args.command}")

    try:
        config = build_extraction_config_from_sources(
            config_path=args.config,
            profile=args.profile,
            ocr_backend=args.ocr_backend,
            header_strategy=args.header_strategy,
            render_scale=args.render_scale,
            threshold=args.threshold,
            min_confidence=args.min_confidence,
            row_y_tolerance=args.row_y_tolerance,
            column_x_tolerance=args.column_x_tolerance,
            tesseract_psm=args.tesseract_psm,
            debug_dir=args.debug_dir,
        )
        document = extract_tables(args.pdf_path, config=config)
        export_table(document, Path(args.output), args.format)
    except (FileNotFoundError, ValueError, PdfExtractionError, NotImplementedError) as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")

    return 0
