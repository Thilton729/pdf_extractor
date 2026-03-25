"""Primitive detectors used by the layout analyzer."""

from .contours import detect_contours
from .lines import detect_lines
from .tables import detect_table_regions

__all__ = ["detect_contours", "detect_lines", "detect_table_regions"]
