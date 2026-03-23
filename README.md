# PDF Extractor

Lightweight Python scaffold for extracting table-like data from PDFs and exporting it to spreadsheet-friendly formats.

The first implemented path is PDF to CSV. Excel and Google Sheets are intentionally scaffolded but not yet implemented. The extractor now includes a tunable OCR pipeline for scanned PDFs with profile-based defaults, backend selection, and optional debug artifacts.

## Features

- Modular `src` layout with a small Python package
- CLI entrypoint for extracting data from a PDF
- Normalized intermediate table model
- Real CSV exporter
- Configurable OCR/layout pipeline for scanned PDFs
- Tesseract and RapidOCR support with automatic selection
- Profile-based defaults for tables, directories, and forms
- Optional debug artifact output for OCR tuning
- Placeholder exporters for Excel and Google Sheets
- Tests for CLI flow, normalization, and exporter behavior

## Current assumptions

- Targets digital/selectable-text PDFs first, with tunable OCR fallback for scanned PDFs
- Best suited for table-like layouts, not arbitrary page geometry

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

If you do not activate the virtualenv, use `.venv/bin/python` in the commands below instead of `python`.

For convenience, you can also run the project from the repository root with:

```bash
.venv/bin/python run_pdf_extractor.py extract input.pdf --output out.csv
```

## Usage

```bash
.venv/bin/python run_pdf_extractor.py extract data/input.pdf --output sample_output/out.csv --format csv
```

Scanned-PDF example with tuning/debug options:

```bash
.venv/bin/python run_pdf_extractor.py extract data/scanned.pdf \
  --output sample_output/scanned.csv \
  --profile table_scan \
  --ocr-backend auto \
  --render-scale 3.0 \
  --min-confidence 0.25 \
  --row-y-tolerance 18 \
  --column-x-tolerance 28 \
  --debug-dir sample_output/debug
```

Saved-config example:

```json
{
  "profile": "table_scan",
  "ocr_backend": "auto",
  "render_scale": 3.0,
  "threshold": 180,
  "min_confidence": 0.25,
  "row_y_tolerance": 18.0,
  "column_x_tolerance": 28.0,
  "tesseract_psm": 6
}
```

Run with a config file:

```bash
.venv/bin/python run_pdf_extractor.py extract data/scanned.pdf \
  --config configs/table-scan.json \
  --output sample_output/scanned.csv
```

CLI flags override config file values, so you can keep a reusable preset and tweak one or two settings per run.

Starter presets included in this repo:

- `configs/table-scan.json`
- `configs/directory-scan.json`
- `configs/form-scan.json`

### Profiles

- `table_scan`: general-purpose starting point for scanned tables
- `directory_scan`: useful for multi-column business directories
- `form_scan`: tighter grouping defaults for forms and sparse layouts

### Important tuning flags

- `--ocr-backend {auto,tesseract,rapidocr}`
- `--header-strategy {auto,page,carry-forward}`
- `--config`
- `--render-scale`
- `--threshold`
- `--min-confidence`
- `--row-y-tolerance`
- `--column-x-tolerance`
- `--tesseract-psm`
- `--debug-dir`

### Notes

- `csv` is implemented
- `xlsx` and `sheets` currently return a clear `NotImplementedError`
- When `--debug-dir` is set, the extractor writes page images, OCR output, and backend-selection summaries for tuning
- `--header-strategy carry-forward` is useful for multi-page digital-text tables where later pages repeat data rows but not column headers cleanly
- If `pdfplumber` or OCR dependencies are not installed, PDF extraction will fail with an actionable message

## Development

Run tests:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

Batch-evaluate the included invoice test set:

```bash
PYTHONPATH=src .venv/bin/python scripts/eval_invoice_test_set.py \
  --data-dir data/invoice_test_set \
  --output-dir sample_output/invoice_test_set_eval \
  --config configs/table-scan.json \
  --header-strategy carry-forward
```

## Next steps

- Add a real `.xlsx` exporter using `openpyxl`
- Add Google Sheets integration with credentials and API configuration
- Improve layout-specific reconstruction heuristics for dense scanned tables
- Add sample PDFs and golden-file tests
