from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import numpy as np

from src.dataset.build_stream_dataset import NoteEvent
from src.polyphonic.dataset_builder import (
    build_frame_labels,
    build_harmonic_tables,
    build_note_tables,
)
from src.v5.external_data import NoteEvent as GenericNoteEvent


def _note(note_id: int, start: float, end: float, pitch: int) -> NoteEvent:
    return NoteEvent(
        note_id=note_id,
        channel=0,
        start_s=start,
        end_s=end,
        pitch_midi=pitch,
        fundamental_hz=440.0,
        detected_attack_time_s=start,
        attack_confidence=1.0,
    )


class PolyphonicDatasetBuilderTests(unittest.TestCase):
    def test_note_table_accepts_midi_without_string_channel(self) -> None:
        notes = [GenericNoteEvent(0, 0.0, 0.5, 60)]
        tables = build_note_tables(notes, 4, np.ones(4, dtype=bool))
        self.assertEqual(tables["note_channel"].tolist(), [-1])
        self.assertEqual(tables["note_evaluation_valid"].tolist(), [1])

    def test_chord_becomes_multi_hot_without_creating_new_semantics(self) -> None:
        labels = build_frame_labels(
            [_note(0, 0.0, 1.0, 60), _note(1, 0.0, 1.0, 64)],
            frame_count=3,
            sample_rate=4,
            hop_size=1,
            midi_min=40,
            midi_max=76,
        )

        expected = (1 << (60 - 40)) | (1 << (64 - 40))
        self.assertEqual(int(labels["active_bits"][0]), expected)
        self.assertEqual(int(labels["onset_bits"][0]), expected)
        self.assertEqual(int(labels["polyphony"][0]), 2)
        self.assertEqual(set(labels["slot_note_id"][0, :2]), {0, 1})

    def test_out_of_scope_audio_is_masked_not_taught_as_silence(self) -> None:
        labels = build_frame_labels(
            [_note(0, 0.0, 1.0, 80)],
            frame_count=3,
            sample_rate=4,
            hop_size=1,
        )

        self.assertTrue(np.all(labels["valid"] == 0))
        self.assertTrue(np.all(labels["outside_scope"] == 1))

    def test_impossible_or_duplicate_activity_is_excluded(self) -> None:
        notes = [_note(index, 0.0, 1.0, 40 + index) for index in range(7)]
        labels = build_frame_labels(
            notes,
            frame_count=3,
            sample_rate=4,
            hop_size=1,
        )
        self.assertTrue(np.all(labels["valid"] == 0))

        duplicate = build_frame_labels(
            [_note(0, 0.0, 1.0, 60), _note(1, 0.0, 1.0, 60)],
            frame_count=3,
            sample_rate=4,
            hop_size=1,
        )
        self.assertTrue(np.all(duplicate["duplicate_pitch"] == 1))
        self.assertTrue(np.all(duplicate["valid"] == 0))

    def test_harmonics_match_channel_and_time_not_incompatible_note_id(self) -> None:
        notes = [
            _note(0, 1.0, 1.5, 60),
            NoteEvent(1, 1, 0.0, 0.5, 64, 329.63, 0.0, 1.0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "harmonics.csv"
            csv_path.write_text(
                "note_id,channel,start_s,end_s,fundamental_hz,harmonic_number,"
                "expected_hz,measured_hz,amplitude\n"
                "0,1,0.0,0.5,329.6276,1,329.6276,329.6276,0.8\n"
                "1,0,1.0,1.5,261.6256,1,261.6256,261.6256,0.5\n",
                encoding="utf-8",
            )

            tables = build_harmonic_tables(notes, csv_path, maximum_harmonics=2)

        self.assertEqual(tables["note_harmonic_valid"].tolist(), [1, 1])
        self.assertEqual(tables["note_harmonic_present"][:, 0].tolist(), [1, 1])


if __name__ == "__main__":
    unittest.main()
