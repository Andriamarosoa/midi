from __future__ import annotations

import unittest

import numpy as np

from src.product.contracts import FEATURE_NAMES as PRODUCT_FEATURE_NAMES
from src.product.decoder import transition_feature_values
from src.v5.external_data import NoteEvent
from src.v6.transition_gate import (
    FEATURE_NAMES,
    build_transition_gate_model,
    extract_transition_candidates,
    harmonic_match_strength,
    stabilize_with_transition_gate,
)
from src.v6.relabel_transition_utility import utility_targets


class TransitionGateTests(unittest.TestCase):
    def test_product_feature_contract_matches_training(self) -> None:
        self.assertEqual(PRODUCT_FEATURE_NAMES, FEATURE_NAMES)

    def test_offline_and_product_feature_values_are_identical(self) -> None:
        frames = 3
        pitch = np.full((frames, 37), 0.01, dtype=np.float32)
        pitch[:, 20] = (0.8, 0.6, 0.2)
        pitch[:, 24] = (0.1, 0.3, 0.7)
        harmonic = np.zeros((frames, 20), dtype=np.float32)
        harmonic[2, 1] = 0.8
        stream_arrays = {
            name: np.asarray([0.0, 0.0, value], dtype=np.float32)
            for name, value in {
                "detected_onset": 1.0,
                "onset_confidence": 0.7,
                "onset_age": 0.0,
                "rms_level": 0.4,
                "rms_growth_ratio": 0.5,
                "spectral_flux": 0.6,
            }.items()
        }
        from src.v6.transition_gate import transition_feature_vector

        offline = transition_feature_vector(
            2, 60, 64, 1, np.asarray([0.8, 0.8, 0.9]), pitch,
            harmonic, stream_arrays, 40, 76, 5.8,
        )
        product = transition_feature_values(
            60, 64, 1, 0.9, pitch[2], pitch[1], harmonic[2],
            {name: float(values[2]) for name, values in stream_arrays.items()},
            40, 76, 5.8,
        )
        np.testing.assert_array_equal(offline, product)

    def test_utility_prefers_the_pitch_supported_after_transition(self) -> None:
        notes = [
            NoteEvent(0, 0.0, 0.1, 60),
            NoteEvent(1, 0.1, 0.4, 64),
        ]
        result = utility_targets(
            np.asarray([4410], dtype=np.int64),
            np.asarray([60], dtype=np.int16),
            np.asarray([64], dtype=np.int16),
            np.asarray([1], dtype=np.int32),
            notes,
        )
        self.assertEqual(result["label"].tolist(), [1.0])
        self.assertGreater(result["utility_margin"][0], 0.0)

    def test_utility_rejects_an_unsupported_harmonic_change(self) -> None:
        notes = [NoteEvent(0, 0.0, 0.4, 60)]
        result = utility_targets(
            np.asarray([4410], dtype=np.int64),
            np.asarray([60], dtype=np.int16),
            np.asarray([72], dtype=np.int16),
            np.asarray([-1], dtype=np.int32),
            notes,
        )
        self.assertEqual(result["label"].tolist(), [0.0])
        self.assertLess(result["utility_margin"][0], 0.0)

    def test_harmonic_match_uses_candidate_interval(self) -> None:
        amplitudes = np.asarray([1.0, 0.8, 0.2, 0.1], dtype=np.float32)
        strength, strongest, maximum = harmonic_match_strength(60, 72, amplitudes)
        self.assertAlmostEqual(strength, 0.8)
        self.assertEqual(strongest, 1.0)
        self.assertAlmostEqual(maximum, 0.8)
        self.assertEqual(harmonic_match_strength(60, 61, amplitudes)[0], 0.0)

    def test_only_stable_active_pitch_changes_become_candidates(self) -> None:
        frames = 9
        min_pitch = 40
        max_pitch = 76
        classes = max_pitch - min_pitch + 1
        pitch = np.full((frames, classes), 0.001, dtype=np.float32)
        desired = [60, 60, 64, 60, 60, 67, 67, 67, 67]
        for index, midi in enumerate(desired):
            pitch[index, midi - min_pitch] = 0.9
        active = np.full(frames, 0.9, dtype=np.float32)
        harmonic = np.zeros((frames, 20), dtype=np.float32)
        stream = {
            name: np.zeros(frames, dtype=np.float32)
            for name in (
                "detected_onset", "onset_confidence", "onset_age",
                "rms_level", "rms_growth_ratio", "spectral_flux",
            )
        }
        notes = [
            NoteEvent(0, 0.0, 0.05, 60),
            NoteEvent(1, 0.05, 0.20, 67),
        ]
        times = np.arange(1, frames + 1, dtype=np.float64) * 0.01
        active_sets = [
            tuple(note.pitch_midi for note in notes if note.start_s <= value < note.end_s)
            for value in times
        ]
        candidates, output_active, output_pitch = extract_transition_candidates(
            active, pitch, harmonic, stream, 0.5, notes, active_sets, times,
            min_pitch, max_pitch, hop_ms=10.0, required_frames=2,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].candidate_pitch, 67)
        self.assertEqual(candidates[0].label, 1)
        self.assertEqual(candidates[0].recent_onset_note_id, 1)
        self.assertTrue(output_active[-1])
        self.assertEqual(output_pitch[-1], 67)
        self.assertEqual(candidates[0].feature.shape, (len(FEATURE_NAMES),))

    def test_tiny_gate_is_exportable(self) -> None:
        model = build_transition_gate_model()
        output = model(
            np.zeros((2, len(FEATURE_NAMES)), dtype=np.float32), training=False
        )
        self.assertEqual(tuple(output.shape), (2, 1))
        self.assertLess(model.count_params(), 1_000)

    def test_zero_threshold_matches_v60_and_veto_is_not_retried(self) -> None:
        count = 9
        minimum = 40
        pitch = np.full((count, 3), 0.05, dtype=np.float32)
        pitch[:3, 0] = 0.9
        pitch[3:, 2] = 0.9
        active = np.full(count, 0.9, dtype=np.float32)
        harmonic = np.zeros((count, 6), dtype=np.float32)
        stream = {
            "detected_onset": np.zeros(count, dtype=np.float32),
            "onset_confidence": np.zeros(count, dtype=np.float32),
            "onset_age": np.ones(count, dtype=np.float32),
            "rms_level": np.zeros(count, dtype=np.float32),
            "rms_growth_ratio": np.zeros(count, dtype=np.float32),
            "spectral_flux": np.zeros(count, dtype=np.float32),
        }
        allow = stabilize_with_transition_gate(
            active, pitch, harmonic, stream, 0.5, 0.0,
            lambda value: np.ones((len(value), 1), dtype=np.float32),
            minimum, minimum + 2, 5.0,
        )
        reject = stabilize_with_transition_gate(
            active, pitch, harmonic, stream, 0.5, 0.5,
            lambda value: np.zeros((len(value), 1), dtype=np.float32),
            minimum, minimum + 2, 5.0,
        )
        self.assertEqual(allow[1].tolist(), [
            -1, 40, 40, 40, 42, 42, 42, 42, 42,
        ])
        self.assertEqual(reject[1].tolist(), [
            -1, 40, 40, 40, 40, 40, 40, 40, 40,
        ])
        self.assertEqual(len(allow[4]), 1)
        self.assertEqual(len(reject[4]), 1)
        self.assertTrue(reject[3][4])


if __name__ == "__main__":
    unittest.main()
