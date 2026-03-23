from __future__ import annotations

import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


class RootLauncherTests(unittest.TestCase):
    def test_root_launcher_delegates_to_cli(self) -> None:
        launcher = Path(__file__).resolve().parent.parent / "run_pdf_extractor.py"
        with patch("pdf_extractor.cli.main", return_value=0) as cli_main:
            with self.assertRaises(SystemExit) as context:
                runpy.run_path(str(launcher), run_name="__main__")
        self.assertEqual(context.exception.code, 0)
        cli_main.assert_called_once()


if __name__ == "__main__":
    unittest.main()
