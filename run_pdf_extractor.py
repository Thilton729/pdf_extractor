#!/usr/bin/env python3
"""Root-level launcher for running the extractor without changing directories."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from pdf_extractor.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
