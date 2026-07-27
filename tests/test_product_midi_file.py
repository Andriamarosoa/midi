from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.product.midi_file import _variable_length, write_midi


class MidiFileTests(unittest.TestCase):
    def test_variable_length_encoding(self) -> None:
        self.assertEqual(_variable_length(0), b"\x00")
        self.assertEqual(_variable_length(127), b"\x7f")
        self.assertEqual(_variable_length(128), b"\x81\x00")

    def test_writes_format_zero_with_closed_track(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "test.mid"
            write_midi(path, [
                {"kind": "note_on", "pitch": 60, "velocity": 100, "time_s": 0.0},
                {"kind": "note_off", "pitch": 60, "velocity": 0, "time_s": 0.5},
            ])
            payload = path.read_bytes()
            self.assertEqual(payload[:4], b"MThd")
            self.assertIn(b"MTrk", payload)
            self.assertTrue(payload.endswith(b"\x00\xff\x2f\x00"))


if __name__ == "__main__":
    unittest.main()
