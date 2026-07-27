from __future__ import annotations

import unittest

from src.polyphonic.evaluate_events import NoteInterval
from src.polyphonic.event_diagnostics import diagnose_note_errors


class PolyphonicEventDiagnosticTests(unittest.TestCase):
    def test_separates_fragmentation_harmonics_and_unrelated_ghosts(self) -> None:
        reference = [
            NoteInterval(60, 0.0, 1.0),
            NoteInterval(64, 1.0, 2.0),
            NoteInterval(67, 3.0, 4.0),
        ]
        estimated = [
            NoteInterval(60, 0.01, 0.40),  # matched first fragment
            NoteInterval(60, 0.45, 0.95),  # same-pitch restart
            NoteInterval(72, 0.20, 0.60),  # octave harmonic ghost
            NoteInterval(88, 0.25, 0.55),  # fifth partial (+28 semitones)
            NoteInterval(64, 1.02, 2.10),  # matched, late offset
            NoteInterval(55, 2.50, 2.70),  # no truth active
        ]
        report = diagnose_note_errors(reference, estimated, [(0, 0), (1, 4)])

        self.assertEqual(report["false_positive_notes"], 4)
        self.assertEqual(report["missing_notes"], 1)
        self.assertEqual(report["same_pitch_during_reference"], 1)
        self.assertEqual(report["harmonic_interval_false_positives"], 2)
        self.assertEqual(report["false_positive_without_active_reference"], 1)
        self.assertEqual(report["fragmented_reference_notes"], 1)
        self.assertEqual(report["excess_fragments"], 1)
        self.assertEqual(
            report["false_positive_interval_counts"],
            {"0": 1, "12": 1, "28": 1},
        )
        self.assertAlmostEqual(
            report["matched_offset_timing"]["median_ms"], -250.0
        )


if __name__ == "__main__":
    unittest.main()
