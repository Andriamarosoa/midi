from __future__ import annotations

import unittest
from pathlib import Path

from src.polyphonic.audit_sources import (
    AnnotationRecording,
    _activity_durations,
    audit_notes,
)
from src.v5.external_data import NoteEvent


class PolyphonicAuditTests(unittest.TestCase):
    def test_activity_duration_counts_true_overlap(self) -> None:
        notes = [
            NoteEvent(0, 0.0, 1.0, 60),
            NoteEvent(1, 0.5, 1.5, 64),
            NoteEvent(2, 1.5, 2.0, 67),
        ]

        maximum, active_duration, polyphonic_duration = _activity_durations(notes)

        self.assertEqual(maximum, 2)
        self.assertAlmostEqual(active_duration, 2.0)
        self.assertAlmostEqual(polyphonic_duration, 0.5)

    def test_adjacent_notes_are_not_polyphonic(self) -> None:
        notes = [
            NoteEvent(0, 0.0, 0.5, 60),
            NoteEvent(1, 0.5, 1.0, 64),
        ]

        maximum, _, polyphonic_duration = _activity_durations(notes)

        self.assertEqual(maximum, 1)
        self.assertEqual(polyphonic_duration, 0.0)

    def test_scope_accounting_keeps_out_of_range_notes_visible(self) -> None:
        recording = AnnotationRecording(
            dataset="test",
            subset="unit",
            recording_id="scope",
            split="train",
            annotation_path=Path("scope.mid"),
            annotation_format="midi",
        )
        notes = [
            NoteEvent(0, 0.0, 1.0, 39),
            NoteEvent(1, 0.0, 1.0, 40),
            NoteEvent(2, 0.0, 1.0, 76),
            NoteEvent(3, 0.0, 1.0, 77),
        ]

        result = audit_notes(recording, notes)

        self.assertEqual(result.notes_in_scope, 2)
        self.assertEqual(result.notes_below_scope, 1)
        self.assertEqual(result.notes_above_scope, 1)
        self.assertEqual(result.maximum_polyphony, 4)


if __name__ == "__main__":
    unittest.main()
