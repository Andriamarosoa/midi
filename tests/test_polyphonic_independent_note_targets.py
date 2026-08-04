from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from src.polyphonic.data import PolyphonicSequence
from src.polyphonic.independent_note_targets import (
    build_independent_note_targets,
)


def _frame_arrays(
    *,
    active_classes: tuple[int, ...] = (0,),
    valid: bool = True,
    slot_pitch: tuple[int, ...] = (0, -1),
    slot_note_id: tuple[int, ...] = (0, -1),
    supervised: np.ndarray | None = None,
    present: np.ndarray | None = None,
    amplitude: np.ndarray | None = None,
    reliability: np.ndarray | None = None,
    offset_cents: np.ndarray | None = None,
    fundamental_offset_cents: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    note_count = (
        max(
            (note_id for note_id in slot_note_id if note_id >= 0),
            default=0,
        )
        + 1
    )
    harmonic_count = 3
    if supervised is None:
        supervised = np.zeros((note_count, harmonic_count), np.uint8)
    if present is None:
        present = np.zeros_like(supervised, dtype=np.uint8)
    if amplitude is None:
        amplitude = np.zeros_like(supervised, dtype=np.float32)
    if reliability is None:
        reliability = np.zeros_like(supervised, dtype=np.float32)
    if offset_cents is None:
        offset_cents = np.zeros_like(supervised, dtype=np.float32)
    if fundamental_offset_cents is None:
        fundamental_offset_cents = np.zeros(note_count, dtype=np.float32)

    bits = sum(1 << pitch_class for pitch_class in active_classes)
    return {
        "active_bits": np.asarray([bits], np.uint64),
        "onset_bits": np.asarray([bits], np.uint64),
        "valid": np.asarray([valid], np.uint8),
        "slot_pitch": np.asarray([slot_pitch], np.int16),
        "slot_note_id": np.asarray([slot_note_id], np.int32),
        "note_harmonic_supervised": np.asarray(supervised, np.uint8),
        "note_harmonic_present": np.asarray(present, np.uint8),
        "note_harmonic_amplitude": np.asarray(amplitude, np.float32),
        "note_harmonic_reliability": np.asarray(reliability, np.float32),
        "note_harmonic_offset_cents": np.asarray(
            offset_cents, dtype=np.float32
        ),
        "note_fundamental_offset_cents": np.asarray(
            fundamental_offset_cents, dtype=np.float32
        ),
        "note_harmonic_valid": np.ones(note_count, np.uint8),
    }


class IndependentNoteTargetTests(unittest.TestCase):
    def test_present_supervised_partial_creates_weighted_negative(self) -> None:
        arrays = _frame_arrays(
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.asarray([[0.0, 0.5, 0.0]], np.float32),
            reliability=np.asarray([[0.0, 0.8, 0.0]], np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertEqual(built.target[0], 1.0)
        self.assertEqual(built.weight[0], 1.0)
        self.assertEqual(built.target[12], 0.0)
        self.assertAlmostEqual(float(built.weight[12]), 0.4, places=6)
        self.assertEqual(int(np.count_nonzero(built.weight)), 2)

    def test_real_active_note_wins_over_coincident_harmonic(self) -> None:
        arrays = _frame_arrays(
            active_classes=(0, 12),
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.asarray([[0.0, 1.0, 0.0]], np.float32),
            reliability=np.asarray([[0.0, 1.0, 0.0]], np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertEqual(built.target[12], 1.0)
        self.assertEqual(built.weight[12], 1.0)

    def test_measured_offset_moves_negative_to_nearest_midi_class(self) -> None:
        arrays = _frame_arrays(
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.asarray([[0.0, 0.5, 0.0]], np.float32),
            reliability=np.asarray([[0.0, 0.8, 0.0]], np.float32),
            offset_cents=np.asarray([[0.0, 80.0, 0.0]], np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertEqual(built.weight[12], 0.0)
        self.assertAlmostEqual(float(built.weight[13]), 0.4, places=6)

    def test_absolute_partial_offset_is_not_double_counted_with_fundamental(self) -> None:
        arrays = _frame_arrays(
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.asarray([[0.0, 0.5, 0.0]], np.float32),
            reliability=np.asarray([[0.0, 0.8, 0.0]], np.float32),
            offset_cents=np.asarray([[0.0, 30.0, 0.0]], np.float32),
            fundamental_offset_cents=np.asarray([40.0], np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertAlmostEqual(float(built.weight[12]), 0.4, places=6)
        self.assertEqual(built.weight[13], 0.0)

    def test_absent_or_unsupervised_partial_stays_masked(self) -> None:
        arrays = _frame_arrays(
            supervised=np.asarray([[0, 0, 1]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.ones((1, 3), np.float32),
            reliability=np.ones((1, 3), np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        # H2 is present but not supervised; H3 is supervised but absent.
        self.assertEqual(built.weight[12], 0.0)
        self.assertEqual(built.weight[19], 0.0)
        self.assertEqual(int(np.count_nonzero(built.weight)), 1)

    def test_unavailable_harmonic_schema_keeps_only_real_positives(self) -> None:
        arrays = _frame_arrays(active_classes=(2,))
        del arrays["note_harmonic_supervised"]
        del arrays["note_harmonic_reliability"]

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertEqual(built.target[2], 1.0)
        self.assertEqual(built.weight[2], 1.0)
        self.assertEqual(int(np.count_nonzero(built.weight)), 1)

    def test_invalid_frame_masks_positives_and_negatives(self) -> None:
        arrays = _frame_arrays(
            valid=False,
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.ones((1, 3), np.float32),
            reliability=np.ones((1, 3), np.float32),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertFalse(np.any(built.target))
        self.assertFalse(np.any(built.weight))

    def test_multiple_fundamentals_keep_strongest_negative_confidence(self) -> None:
        # H3 of class 0 and H2 of class 7 both align with class 19.
        arrays = _frame_arrays(
            active_classes=(0, 7),
            slot_pitch=(0, 7),
            slot_note_id=(0, 1),
            supervised=np.asarray(
                [[0, 0, 1], [0, 1, 0]], np.uint8
            ),
            present=np.asarray(
                [[0, 0, 1], [0, 1, 0]], np.uint8
            ),
            amplitude=np.asarray(
                [[0.0, 0.0, 0.5], [0.0, 0.9, 0.0]], np.float32
            ),
            reliability=np.asarray(
                [[0.0, 0.0, 0.4], [0.0, 0.8, 0.0]], np.float32
            ),
        )

        built = build_independent_note_targets(
            arrays, 0, pitch_classes=24
        )

        self.assertAlmostEqual(float(built.weight[19]), 0.72, places=6)

    def test_sequence_packs_target_then_weight_only_when_enabled(self) -> None:
        arrays = _frame_arrays(
            supervised=np.asarray([[0, 1, 0]], np.uint8),
            present=np.asarray([[0, 1, 0]], np.uint8),
            amplitude=np.asarray([[0.0, 0.5, 0.0]], np.float32),
            reliability=np.asarray([[0.0, 0.8, 0.0]], np.float32),
        )
        waveform = np.linspace(-0.5, 0.5, 8, dtype=np.float32)
        corpus = SimpleNamespace(
            pitch_classes=24,
            harmonic_count=3,
            hop_size=4,
            labels=[SimpleNamespace(arrays=arrays)],
            audio=lambda recording_index: waveform,
        )
        common = dict(
            corpus=corpus,
            batch_size=1,
            input_samples=8,
            normalization_gain=1.0,
            seed=7,
            refs=np.asarray([[0, 0]], np.int32),
        )

        _, default_targets = PolyphonicSequence(**common)[0]
        _, enabled_targets = PolyphonicSequence(
            **common, independent_note_target=True
        )[0]

        self.assertNotIn("independent_note", default_targets)
        packed = enabled_targets["independent_note"]
        self.assertEqual(packed.shape, (1, 48))
        self.assertEqual(packed[0, 0], 1.0)
        self.assertEqual(packed[0, 12], 0.0)
        self.assertEqual(packed[0, 24], 1.0)
        self.assertAlmostEqual(float(packed[0, 24 + 12]), 0.4, places=6)


if __name__ == "__main__":
    unittest.main()
