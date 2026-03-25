"""PDF extraction backends."""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import ExtractionConfig
from .layout_analyzer import LayoutAnalyzer, PageImage
from .layout_analyzer.debug import (
    save_document_summary,
    save_layout_summary,
    save_preprocess_layers,
    save_region_overlay,
)
from .layout_analyzer.preprocess import prepare_analysis_layers
from .models import ExtractedDocument, TableData
from .normalizer import normalize_rows


class PdfExtractionError(RuntimeError):
    """Raised when extraction cannot be completed."""


class PdfPlumberExtractor:
    """Default backend for digital-text PDFs with OCR fallback for scanned pages."""

    def __init__(self, config: ExtractionConfig) -> None:
        self.config = config
        self.layout_analyzer = LayoutAnalyzer()

    def extract(self, pdf_path: Path) -> ExtractedDocument:
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - depends on local env
            raise PdfExtractionError(
                "pdfplumber is required for PDF extraction. Install dependencies with "
                "`pip install -r requirements.txt`."
            ) from exc

        tables: list[TableData] = []
        prior_headers: list[str] | None = None
        metadata = {
            "profile": self.config.profile,
            "ocr_backend": self.config.ocr_backend,
            "header_strategy": self.config.header_strategy,
            "layout_analysis": self.config.layout_config.mode,
        }
        if self.config.debug_dir is not None:
            metadata["debug_dir"] = str(self.config.debug_dir)

        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                page_tables = page.extract_tables() or []
                for raw_table in page_tables:
                    normalized = self._normalize_page_table(raw_table, prior_headers)
                    if normalized.headers or normalized.rows:
                        normalized.source_page = page_index
                        tables.append(normalized)
                        if normalized.headers:
                            prior_headers = normalized.headers

                if page_tables:
                    continue

                text = page.extract_text() or ""
                fallback_table = self._extract_text_table(text, page_index)
                if fallback_table is not None:
                    tables.append(fallback_table)
                    continue

                ocr_table = self._extract_ocr_table(pdf_path, page_index)
                if ocr_table is not None:
                    tables.append(ocr_table)

        tables = self._merge_continuation_tables(tables)
        return ExtractedDocument(source_path=str(pdf_path), tables=tables, metadata=metadata)

    def _merge_continuation_tables(self, tables: list[TableData]) -> list[TableData]:
        if not tables:
            return tables

        merged: list[TableData] = [tables[0]]
        for table in tables[1:]:
            previous = merged[-1]
            if self._should_merge_tables(previous, table):
                previous.rows.extend(table.rows)
                continue
            merged.append(table)
        return merged

    def _should_merge_tables(self, left: TableData, right: TableData) -> bool:
        if not left.headers or not right.headers:
            return False
        if left.headers != right.headers:
            return False
        if len(left.headers) < 3:
            return False
        if not left.rows or not right.rows:
            return False

        left_page = left.source_page or 0
        right_page = right.source_page or 0
        if right_page < left_page:
            return False
        if right_page - left_page > 1:
            return False

        return self._is_line_item_table(left) and self._is_line_item_table(right)

    def _is_line_item_table(self, table: TableData) -> bool:
        headers = [header.lower() for header in table.headers]
        header_hits = sum(
            any(keyword in header for header in headers)
            for keyword in ("description", "item", "qty", "quantity", "unit", "price", "total")
        )
        return header_hits >= 3

    def _normalize_page_table(
        self, raw_table: list[list[object | None]], prior_headers: list[str] | None
    ) -> TableData:
        normalized = normalize_rows(raw_table)
        if not prior_headers:
            return normalized

        strategy = self.config.header_strategy
        if strategy == "page":
            return normalized

        if strategy == "carry-forward" and self._should_carry_forward_headers(
            normalized, prior_headers
        ):
            combined_rows = [normalized.headers, *normalized.rows] if normalized.headers else normalized.rows
            width = len(prior_headers)
            carried_rows = [self._pad_row(row, width) for row in combined_rows]
            return TableData(headers=list(prior_headers), rows=carried_rows)

        if strategy == "auto" and self._should_carry_forward_headers(normalized, prior_headers):
            combined_rows = [normalized.headers, *normalized.rows] if normalized.headers else normalized.rows
            width = len(prior_headers)
            carried_rows = [self._pad_row(row, width) for row in combined_rows]
            return TableData(headers=list(prior_headers), rows=carried_rows)

        return normalized

    def _should_carry_forward_headers(
        self, table: TableData, prior_headers: list[str]
    ) -> bool:
        if not prior_headers or not table.headers:
            return False

        if len(table.headers) != len(prior_headers):
            return False

        prior_alpha = sum(any(char.isalpha() for char in cell) for cell in prior_headers)
        current_alpha = sum(any(char.isalpha() for char in cell) for cell in table.headers)
        current_numeric_heavy = sum(sum(char.isdigit() for char in cell) >= 2 for cell in table.headers)

        return current_alpha < prior_alpha and current_numeric_heavy >= 2

    def _pad_row(self, row: list[str], width: int) -> list[str]:
        return row + [""] * (width - len(row))

    def _extract_text_table(self, text: str, page_index: int) -> TableData | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return None

        raw_rows: list[list[str]] = []
        for line in lines:
            cells = [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]
            if len(cells) > 1:
                raw_rows.append(cells)

        if len(raw_rows) < 2:
            return None

        normalized = normalize_rows(raw_rows)
        normalized.source_page = page_index
        return normalized

    def _extract_ocr_table(self, pdf_path: Path, page_index: int) -> TableData | None:
        image = self._render_page_image(pdf_path, page_index)
        page_layout = self._analyze_page_layout(page_index, image)
        active_profile = self.config.profile
        row_tolerance = self.config.row_y_tolerance
        column_tolerance = self.config.column_x_tolerance
        if page_layout is not None:
            active_profile = str(
                page_layout.hints.get("recommended_profile", self.config.profile)
            )
            row_tolerance = float(
                page_layout.hints.get("row_y_tolerance", self.config.row_y_tolerance)
            )
            column_tolerance = float(
                page_layout.hints.get(
                    "column_x_tolerance", self.config.column_x_tolerance
                )
            )

        candidates: list[tuple[str, TableData]] = []

        if self.config.ocr_backend in ("auto", "tesseract"):
            candidate = self._extract_tesseract_table(
                pdf_path,
                page_index,
                image,
                active_profile=active_profile,
                row_tolerance=row_tolerance,
                column_tolerance=column_tolerance,
            )
            if candidate is not None:
                candidates.append(("tesseract", candidate))
            elif self.config.ocr_backend == "tesseract":
                raise PdfExtractionError("Tesseract OCR was selected but no usable output was produced.")

        if self.config.ocr_backend in ("auto", "rapidocr"):
            candidate = self._extract_rapidocr_table(
                pdf_path,
                page_index,
                image,
                active_profile=active_profile,
                row_tolerance=row_tolerance,
                column_tolerance=column_tolerance,
            )
            if candidate is not None:
                candidates.append(("rapidocr", candidate))
            elif self.config.ocr_backend == "rapidocr":
                raise PdfExtractionError("RapidOCR was selected but no usable output was produced.")

        if not candidates:
            return None

        scored_candidates = [
            {"backend": backend, "score": self._score_table_quality(table)}
            for backend, table in candidates
        ]
        if self.config.debug_dir is not None:
            self._write_debug_json(
                page_index,
                "candidate_scores.json",
                {
                    "pdf_path": str(pdf_path),
                    "profile": active_profile,
                    "backend": self.config.ocr_backend,
                    "layout_type": page_layout.layout_type if page_layout is not None else None,
                    "candidates": scored_candidates,
                },
            )

        best_backend, best_table = max(candidates, key=lambda item: self._score_table_quality(item[1]))
        if self.config.debug_dir is not None:
            self._write_debug_json(
                page_index,
                "selected_backend.json",
                {"backend": best_backend, "score": self._score_table_quality(best_table)},
            )
        return best_table

    def _extract_rapidocr_table(
        self,
        pdf_path: Path,
        page_index: int,
        image: Any,
        *,
        active_profile: str,
        row_tolerance: float,
        column_tolerance: float,
    ) -> TableData | None:
        try:
            import numpy as np
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - depends on local env
            if self.config.ocr_backend == "rapidocr":
                raise PdfExtractionError(
                    "RapidOCR support requires `rapidocr-onnxruntime`. "
                    "Install dependencies with `pip install -r requirements.txt`."
                ) from exc
            return None

        ocr = RapidOCR()
        result, _ = ocr(np.array(image))
        if not result:
            return None

        if self.config.debug_dir is not None:
            self._write_debug_json(page_index, "rapidocr.json", {"items": result})

        return self._items_to_table(
            pdf_path=pdf_path,
            page_index=page_index,
            items=result,
            backend_name="rapidocr",
            active_profile=active_profile,
            row_tolerance=row_tolerance,
            column_tolerance=column_tolerance,
        )

    def _extract_tesseract_table(
        self,
        pdf_path: Path,
        page_index: int,
        image: Any,
        *,
        active_profile: str,
        row_tolerance: float,
        column_tolerance: float,
    ) -> TableData | None:
        if shutil.which("tesseract") is None:
            return None

        try:
            from PIL import ImageOps
        except ImportError:
            return None

        processed = ImageOps.autocontrast(image.convert("L"))
        processed = processed.point(
            lambda value: 255 if value > self.config.threshold else 0, mode="1"
        ).convert("L")

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / f"page_{page_index}.png"
            output_base = Path(temp_dir) / f"page_{page_index}_ocr"
            processed.save(image_path)

            try:
                subprocess.run(
                    [
                        "tesseract",
                        str(image_path),
                        str(output_base),
                        "--psm",
                        str(self.config.tesseract_psm),
                        "-l",
                        "eng",
                        "tsv",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError):
                return None

            tsv_path = output_base.with_suffix(".tsv")
            items = self._parse_tesseract_tsv(tsv_path)

            if self.config.debug_dir is not None:
                self._write_debug_image(page_index, "tesseract_preprocessed.png", processed)
                self._write_debug_file(page_index, "tesseract.tsv", tsv_path.read_text(encoding="utf-8"))

        if not items:
            return None

        return self._items_to_table(
            pdf_path=pdf_path,
            page_index=page_index,
            items=items,
            backend_name="tesseract",
            active_profile=active_profile,
            row_tolerance=row_tolerance,
            column_tolerance=column_tolerance,
        )

    def _items_to_table(
        self,
        *,
        pdf_path: Path,
        page_index: int,
        items: list[list[object]],
        backend_name: str,
        active_profile: str,
        row_tolerance: float,
        column_tolerance: float,
    ) -> TableData | None:
        lines = self._group_ocr_lines(items, row_tolerance=row_tolerance)
        if len(lines) < 2:
            return None

        header_index = self._detect_header_line_index(lines)
        headers: list[str] = []
        body_lines = lines
        column_ranges: list[tuple[float, float]] | None = None
        reconstruction = "linewise"

        if header_index is not None:
            header_line = lines[header_index]
            headers = [str(item["text"]).strip() for item in header_line]
            column_ranges = self._build_column_ranges(header_line)
            body_lines = lines[header_index + 1 :]
            reconstruction = "header_guided"

        if headers and [header.lower() for header in headers] == [
            "name",
            "email",
            "phone",
            "address",
            "zip code",
            "website",
        ]:
            raw_rows = [self._parse_directory_row(line) for line in body_lines]
            reconstruction = "directory_scan"
        elif headers and column_ranges is not None:
            raw_rows = [
                self._assign_line_to_columns(
                    line, column_ranges, column_tolerance=column_tolerance
                )
                for line in body_lines
            ]
        else:
            raw_rows = [[str(item["text"]).strip() for item in line] for line in body_lines]

        normalized = normalize_rows(raw_rows if not headers else [headers, *raw_rows])
        normalized.source_page = page_index

        if self.config.debug_dir is not None:
            self._write_debug_overlays(
                page_index=page_index,
                backend_name=backend_name,
                lines=lines,
                header_index=header_index,
                column_ranges=column_ranges,
            )
            self._write_debug_json(
                page_index,
                f"{backend_name}_summary.json",
                {
                    "pdf_path": str(pdf_path),
                    "backend": backend_name,
                    "profile": active_profile,
                    "header_index": header_index,
                    "headers": headers,
                    "line_count": len(lines),
                    "reconstruction": reconstruction,
                    "row_y_tolerance": row_tolerance,
                    "column_x_tolerance": column_tolerance,
                    "config": asdict(self.config),
                },
            )

        return normalized if normalized.headers or normalized.rows else None

    def _render_page_image(self, pdf_path: Path, page_index: int) -> Any:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:  # pragma: no cover - depends on local env
            raise PdfExtractionError(
                "Scanned-PDF OCR support requires `pypdfium2`. Install dependencies with "
                "`pip install -r requirements.txt`."
            ) from exc

        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[page_index - 1]
        render_scale = self.config.render_scale
        if self.config.layout_config.enabled:
            render_scale = max(render_scale, self.config.layout_config.render_scale)
        image = page.render(scale=render_scale).to_pil()
        if self.config.debug_dir is not None:
            self._write_debug_image(page_index, "rendered_page.png", image)
        return image

    def _analyze_page_layout(self, page_index: int, image: Any):
        if not self.config.layout_config.enabled:
            return None

        page_image = PageImage(
            page_number=page_index,
            image=image,
            width=image.width,
            height=image.height,
            dpi=int(round(self.config.layout_config.render_scale * 72)),
        )
        page_layout = self.layout_analyzer.analyze_page(page_image, self.config.layout_config)

        if self.config.layout_config.debug_enabled and self.config.layout_config.debug_dir is not None:
            layers = prepare_analysis_layers(image, self.config.layout_config)
            save_preprocess_layers(page_index, layers, self.config.layout_config.debug_dir)
            save_region_overlay(
                page_index,
                image,
                page_layout.regions,
                self.config.layout_config.debug_dir,
            )
            save_layout_summary(page_layout, self.config.layout_config.debug_dir)
            save_document_summary(
                self.layout_analyzer.analyze_document([page_image], self.config.layout_config),
                self.config.layout_config.debug_dir,
            )

        return page_layout

    def _parse_tesseract_tsv(self, tsv_path: Path) -> list[list[object]]:
        items: list[list[object]] = []
        if not tsv_path.exists():
            return items

        with tsv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                text = (row.get("text") or "").strip()
                conf_text = (row.get("conf") or "").strip()
                if not text:
                    continue

                try:
                    confidence = float(conf_text) / 100.0
                except ValueError:
                    confidence = -1.0

                if confidence < self.config.min_confidence:
                    continue

                left = float(row["left"])
                top = float(row["top"])
                width = float(row["width"])
                height = float(row["height"])
                points = [
                    [left, top],
                    [left + width, top],
                    [left + width, top + height],
                    [left, top + height],
                ]
                items.append([points, text, confidence])

        return items

    def _score_table_quality(self, table: TableData) -> float:
        expected_directory_headers = [
            "name",
            "email",
            "phone",
            "address",
            "zip code",
            "website",
        ]
        cells = list(table.headers)
        for row in table.rows:
            cells.extend(row)

        non_empty_cells = [cell for cell in cells if cell.strip()]
        if not non_empty_cells:
            return float("-inf")

        alpha_rich = sum(any(char.isalpha() for char in cell) for cell in non_empty_cells)
        one_char = sum(len(cell.strip()) <= 1 for cell in non_empty_cells)
        noisy = sum(("\t" in cell) or ("\n" in cell) for cell in non_empty_cells)
        punctuation_only = sum(
            all(not char.isalnum() for char in cell.strip()) for cell in non_empty_cells
        )
        rows_with_data = sum(any(cell.strip() for cell in row) for row in table.rows)
        balanced_rows = sum(1 for row in table.rows if len([cell for cell in row if cell.strip()]) >= 3)

        score = 0.0
        score += rows_with_data * 3
        score += balanced_rows * 3
        score += len(table.headers) * 2
        score += alpha_rich * 0.5
        score -= one_char * 2
        score -= noisy * 10
        score -= punctuation_only * 3

        if table.headers and sum(any(char.isalpha() for char in cell) for cell in table.headers) >= 3:
            score += 15
        if [header.lower() for header in table.headers] == expected_directory_headers:
            score += 40

        return score

    def _group_ocr_lines(
        self, ocr_result: list[list[object]], *, row_tolerance: float | None = None
    ) -> list[list[dict[str, object]]]:
        items: list[dict[str, object]] = []
        for entry in ocr_result:
            points, text, score = entry
            if not text:
                continue
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            items.append(
                {
                    "text": str(text).strip(),
                    "score": float(score),
                    "x0": min(xs),
                    "x1": max(xs),
                    "y0": min(ys),
                    "y1": max(ys),
                    "yc": (min(ys) + max(ys)) / 2,
                }
            )

        items.sort(key=lambda item: (float(item["yc"]), float(item["x0"])))
        lines: list[list[dict[str, object]]] = []
        tolerance = self.config.row_y_tolerance if row_tolerance is None else row_tolerance

        for item in items:
            if not lines:
                lines.append([item])
                continue

            current_avg = sum(float(line_item["yc"]) for line_item in lines[-1]) / len(lines[-1])
            if abs(float(item["yc"]) - current_avg) <= tolerance:
                lines[-1].append(item)
            else:
                lines.append([item])

        for line in lines:
            line.sort(key=lambda item: float(item["x0"]))
        return lines

    def _detect_header_line_index(self, lines: list[list[dict[str, object]]]) -> int | None:
        best_index: int | None = None
        best_score = 0.0
        search_window = min(5, len(lines))

        for index in range(search_window):
            line = lines[index]
            texts = [str(item["text"]).strip() for item in line]
            non_empty = [text for text in texts if text]
            if len(non_empty) < 3:
                continue

            alpha_rich = sum(any(char.isalpha() for char in text) for text in non_empty)
            avg_length = sum(len(text) for text in non_empty) / len(non_empty)
            numeric_heavy = sum(sum(char.isdigit() for char in text) >= 3 for text in non_empty)
            score = alpha_rich * 3 + len(non_empty) * 2 + avg_length - numeric_heavy * 2

            if score > best_score and alpha_rich >= 3:
                best_score = score
                best_index = index

        return best_index

    def _build_column_ranges(self, header_line: list[dict[str, object]]) -> list[tuple[float, float]]:
        if not header_line:
            return []

        centers = [(float(item["x0"]) + float(item["x1"])) / 2 for item in header_line]
        boundaries: list[float] = []
        for idx in range(len(centers) - 1):
            boundaries.append((centers[idx] + centers[idx + 1]) / 2)

        ranges: list[tuple[float, float]] = []
        left = float("-inf")
        for boundary in boundaries:
            ranges.append((left, boundary))
            left = boundary
        ranges.append((left, float("inf")))
        return ranges

    def _assign_line_to_columns(
        self,
        line: list[dict[str, object]],
        column_ranges: list[tuple[float, float]],
        *,
        column_tolerance: float | None = None,
    ) -> list[str]:
        cells = ["" for _ in column_ranges]
        tolerance = (
            self.config.column_x_tolerance
            if column_tolerance is None
            else column_tolerance
        )
        for item in line:
            x_center = (float(item["x0"]) + float(item["x1"])) / 2
            assigned_index = None
            for idx, (x_min, x_max) in enumerate(column_ranges):
                if x_min <= x_center < x_max:
                    assigned_index = idx
                    break

            if assigned_index is None:
                distances = [
                    min(abs(x_center - x_min), abs(x_center - x_max))
                    for x_min, x_max in column_ranges
                ]
                if distances:
                    nearest = min(range(len(distances)), key=distances.__getitem__)
                    if distances[nearest] <= tolerance:
                        assigned_index = nearest

            if assigned_index is None:
                continue

            text = str(item["text"]).strip()
            if cells[assigned_index]:
                cells[assigned_index] = f"{cells[assigned_index]} {text}".strip()
            else:
                cells[assigned_index] = text

        return cells

    def _parse_directory_row(self, line: list[dict[str, object]]) -> list[str]:
        texts = [str(item["text"]).strip() for item in line]
        if not texts:
            return []

        if len(texts) == 1:
            left_text = texts[0]
            right_text = ""
        else:
            left_text = " ".join(texts[:-1]).strip()
            right_text = texts[-1]

        zip_code, website = self._split_zip_and_website(right_text)
        name, phone, address = self._split_name_phone_address(left_text)
        phone, overflow = self._normalize_phone(phone)
        if overflow:
            address = f"{overflow}{address}".strip()
        return [name, "", phone, address, zip_code, website]

    def _split_zip_and_website(self, text: str) -> tuple[str, str]:
        if not text:
            return "", ""

        match = re.match(r"^\s*(\d{4,6})(.*)$", text)
        if not match:
            return "", text.strip()

        zip_code = match.group(1).strip()
        website = match.group(2).strip()
        return zip_code, website

    def _split_name_phone_address(self, text: str) -> tuple[str, str, str]:
        if not text:
            return "", "", ""

        compact = re.sub(r"\s+", " ", text).strip()
        phone_start = re.search(r"(?=\+?\d[\d\-\(\)'\.:]{6,})", compact)
        if not phone_start:
            return compact, "", ""

        name = compact[: phone_start.start()].strip(" -,:")
        remainder = compact[phone_start.start() :].strip()

        address_start = self._find_address_start(remainder)
        if address_start is None:
            return name, remainder.strip(" -,:") or remainder, ""

        phone = remainder[:address_start].strip(" -,:")
        address = remainder[address_start:].strip(" -,:")
        return name, phone, address

    def _normalize_phone(self, phone: str) -> tuple[str, str]:
        if not phone:
            return "", ""

        digits = "".join(char for char in phone if char.isdigit())
        if len(digits) < 11:
            return phone.strip(), ""

        normalized_digits = digits[:11]
        overflow = digits[11:]
        formatted = (
            f"+{normalized_digits[0]}{normalized_digits[1:4]}-"
            f"{normalized_digits[4:7]}-{normalized_digits[7:11]}"
        )
        return formatted, overflow

    def _find_address_start(self, text: str) -> int | None:
        best_start: int | None = None
        best_score = -math.inf
        for start, address_digit_len in self._address_start_candidates(text):
            phone_candidate = text[:start].strip(" -,:")
            if any(char.isalpha() for char in phone_candidate):
                continue
            digit_count = sum(char.isdigit() for char in phone_candidate)
            if not 7 <= digit_count <= 15:
                continue

            score = 100 - abs(11 - digit_count) * 15
            score -= address_digit_len
            if phone_candidate.startswith("+"):
                score += 5
            if phone_candidate.endswith(tuple("0123456789")):
                score += 5
            if ":" in phone_candidate or "." in phone_candidate:
                score -= 20

            if score > best_score:
                best_score = score
                best_start = start

        return best_start

    def _address_start_candidates(self, text: str) -> list[tuple[int, int]]:
        candidates: list[tuple[int, int]] = []
        for start, char in enumerate(text):
            if not char.isdigit():
                continue

            end = start
            while end < len(text) and text[end].isdigit() and (end - start) < 5:
                end += 1

            if end == len(text):
                continue
            if not text[end].isalpha():
                continue

            digit_len = end - start
            if 1 <= digit_len <= 5 and start > 6:
                candidates.append((start, digit_len))

        return candidates

    def _debug_page_dir(self, page_index: int) -> Path | None:
        if self.config.debug_dir is None:
            return None
        page_dir = self.config.debug_dir / f"page_{page_index:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)
        return page_dir

    def _write_debug_file(self, page_index: int, filename: str, content: str) -> None:
        page_dir = self._debug_page_dir(page_index)
        if page_dir is None:
            return
        (page_dir / filename).write_text(content, encoding="utf-8")

    def _write_debug_json(self, page_index: int, filename: str, payload: dict[str, Any]) -> None:
        self._write_debug_file(page_index, filename, json.dumps(payload, indent=2, default=str))

    def _write_debug_image(self, page_index: int, filename: str, image: Any) -> None:
        page_dir = self._debug_page_dir(page_index)
        if page_dir is None:
            return
        image.save(page_dir / filename)

    def _write_debug_overlays(
        self,
        *,
        page_index: int,
        backend_name: str,
        lines: list[list[dict[str, object]]],
        header_index: int | None,
        column_ranges: list[tuple[float, float]] | None,
    ) -> None:
        page_dir = self._debug_page_dir(page_index)
        if page_dir is None:
            return

        rendered_path = page_dir / "rendered_page.png"
        if not rendered_path.exists():
            return

        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return

        base_image = Image.open(rendered_path).convert("RGB")
        self._draw_token_overlay(base_image, page_dir / f"{backend_name}_tokens_overlay.png", lines)
        self._draw_row_overlay(
            base_image,
            page_dir / f"{backend_name}_rows_overlay.png",
            lines,
            header_index,
        )
        if column_ranges is not None:
            self._draw_column_overlay(
                base_image,
                page_dir / f"{backend_name}_columns_overlay.png",
                column_ranges,
            )

    def _draw_token_overlay(self, base_image: Any, output_path: Path, lines: list[list[dict[str, object]]]) -> None:
        from PIL import ImageDraw

        image = base_image.copy()
        draw = ImageDraw.Draw(image, "RGBA")
        palette = [
            (231, 76, 60, 110),
            (52, 152, 219, 110),
            (46, 204, 113, 110),
            (241, 196, 15, 110),
            (155, 89, 182, 110),
        ]

        for line_index, line in enumerate(lines):
            color = palette[line_index % len(palette)]
            outline = color[:3] + (255,)
            for item in line:
                draw.rectangle(
                    [
                        float(item["x0"]),
                        float(item["y0"]),
                        float(item["x1"]),
                        float(item["y1"]),
                    ],
                    outline=outline,
                    width=2,
                )
        image.save(output_path)

    def _draw_row_overlay(
        self,
        base_image: Any,
        output_path: Path,
        lines: list[list[dict[str, object]]],
        header_index: int | None,
    ) -> None:
        from PIL import ImageDraw

        image = base_image.copy()
        draw = ImageDraw.Draw(image, "RGBA")

        for line_index, line in enumerate(lines):
            x0 = min(float(item["x0"]) for item in line)
            x1 = max(float(item["x1"]) for item in line)
            y0 = min(float(item["y0"]) for item in line)
            y1 = max(float(item["y1"]) for item in line)
            fill = (52, 152, 219, 50)
            outline = (41, 128, 185, 180)
            if header_index is not None and line_index == header_index:
                fill = (46, 204, 113, 65)
                outline = (39, 174, 96, 220)
            draw.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=2)

        image.save(output_path)

    def _draw_column_overlay(
        self,
        base_image: Any,
        output_path: Path,
        column_ranges: list[tuple[float, float]],
    ) -> None:
        from PIL import ImageDraw

        image = base_image.copy()
        draw = ImageDraw.Draw(image, "RGBA")
        width, height = image.size
        palette = [
            (231, 76, 60, 40),
            (52, 152, 219, 40),
            (46, 204, 113, 40),
            (241, 196, 15, 40),
            (155, 89, 182, 40),
            (26, 188, 156, 40),
        ]

        for index, (x_min, x_max) in enumerate(column_ranges):
            left = 0 if math.isinf(x_min) and x_min < 0 else max(0, int(x_min))
            right = width if math.isinf(x_max) else min(width, int(x_max))
            if right <= left:
                continue
            fill = palette[index % len(palette)]
            draw.rectangle([left, 0, right, height], fill=fill)
            draw.line([left, 0, left, height], fill=(44, 62, 80, 180), width=2)
            draw.line([right, 0, right, height], fill=(44, 62, 80, 180), width=2)

        image.save(output_path)
