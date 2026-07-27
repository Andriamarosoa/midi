from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.polyphonic.export import export


class PolyphonicExportTests(unittest.TestCase):
    def test_export_refuses_unselected_checkpoint_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            output = root / "artifact"
            run.mkdir()
            with self.assertRaisesRegex(ValueError, "selected.keras"):
                export(run, output, examples=1)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
