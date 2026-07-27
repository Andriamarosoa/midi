from __future__ import annotations

import unittest

import numpy as np

from src.v5.external_data import NoteEvent
from src.v6.continuous_validate import (
    decode_events,
    frame_labels,
    stabilize_predictions,
)
from src.v6.continuous_onset_ablation import (
    stabilize_with_model_onset,
    strongest_harmonic_explains,
)


class ContinuousValidationTests(unittest.TestCase):
    def test_frame_labels_exclude_polyphony_but_keep_silence(self) -> None:
        notes = [
            NoteEvent(0, 0.0, 1.0, 60),
            NoteEvent(1, 0.5, 1.5, 64),
        ]
        pitches, evaluable, target = frame_labels(
            notes, np.asarray([0.25, 0.75, 1.25, 2.0]), 40, 76
        )
        self.assertEqual(pitches, [(60,), (60, 64), (64,), ()])
        self.assertEqual(evaluable.tolist(), [True, False, True, True])
        self.assertEqual(target.tolist(), [60, -1, 64, -1])

    def test_decoder_closes_on_pitch_change_and_inactivity(self) -> None:
        active = np.asarray([0, 1, 1, 1, 0], dtype=bool)
        pitch = np.asarray([60, 60, 64, 64, 64], dtype=np.int32)
        times = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5])
        events = decode_events(active, pitch, times, duration_s=0.6)
        self.assertEqual([event["pitch_midi"] for event in events], [60, 64])
        self.assertAlmostEqual(float(events[0]["start_s"]), 0.2)
        self.assertAlmostEqual(float(events[0]["end_s"]), 0.3)
        self.assertAlmostEqual(float(events[1]["end_s"]), 0.5)

    def test_stability_filters_one_hop_glitches_and_keeps_retrigger_path(self) -> None:
        active = np.asarray([0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0], dtype=bool)
        pitch = np.asarray([60, 60, 60, 64, 60, 60, 60, 60, 60, 60, 60])
        onset = np.asarray([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0], dtype=bool)
        stable_active, stable_pitch, retrigger = stabilize_predictions(
            active, pitch, onset, hop_ms=10.0, required_frames=2,
            minimum_retrigger_ms=20.0,
        )
        self.assertEqual(stable_pitch[3], 60)
        self.assertTrue(retrigger[5])
        self.assertTrue(stable_active[9])
        self.assertFalse(stable_active[10])

    def test_model_onset_gate_requires_attack_for_active_pitch_change(self) -> None:
        active = np.ones(8, dtype=bool)
        pitch = np.asarray([60, 60, 64, 64, 64, 67, 67, 67], dtype=np.int32)
        onset = np.asarray([0.0, 0.0, 0.1, 0.2, 0.1, 0.9, 0.1, 0.1])
        _, stable_pitch, _, _ = stabilize_with_model_onset(
            active, pitch, onset, onset_threshold=0.5, hop_ms=10.0,
            required_frames=2,
        )
        self.assertEqual(stable_pitch[4], 60)
        self.assertEqual(stable_pitch[6], 67)

    def test_external_retrigger_evidence_avoids_level_trigger_chatter(self) -> None:
        active = np.ones(20, dtype=bool)
        pitch = np.full(20, 60, dtype=np.int32)
        model_onset = np.full(20, 0.9, dtype=np.float32)
        external = np.zeros(20, dtype=bool)
        external[12] = True
        _, _, retrigger, _ = stabilize_with_model_onset(
            active,
            pitch,
            model_onset,
            onset_threshold=0.5,
            hop_ms=10.0,
            retrigger_onset=external,
            minimum_retrigger_ms=80.0,
        )
        self.assertEqual(np.flatnonzero(retrigger).tolist(), [12])

    def test_harmonic_gate_uses_only_strongest_predicted_overtone(self) -> None:
        amplitudes = np.asarray([1.0, 0.8, 0.2, 0.1], dtype=np.float32)
        self.assertTrue(strongest_harmonic_explains(60, 72, amplitudes))
        self.assertFalse(strongest_harmonic_explains(60, 79, amplitudes))


if __name__ == "__main__":
    unittest.main()
