"""Map layout analysis output onto extraction settings."""

from __future__ import annotations

from ..models import PageLayout


def choose_profile(page_layout: PageLayout, current_profile: str | None = None) -> str:
    """Choose the extraction profile suggested by the page layout."""
    if page_layout.layout_type == "structured_table":
        return "table_scan"
    if page_layout.layout_type == "mixed":
        return current_profile or "table_scan"
    if page_layout.layout_type in {"text_heavy", "unknown"}:
        return current_profile or "table_scan"
    return current_profile or "table_scan"


def choose_mode(page_layout: PageLayout) -> str:
    """Choose the extraction mode suggested by the page layout."""
    if page_layout.layout_type == "structured_table":
        return "ocr"
    if page_layout.layout_type == "mixed":
        return "hybrid"
    if page_layout.layout_type == "text_heavy":
        return "text"
    return "hybrid"
