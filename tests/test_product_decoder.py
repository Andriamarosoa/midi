from __future__ import annotations

import unittest

import numpy as np

from src.product.decoder import StreamingTransitionDecoder


def stream(onset: float = 0.0) -> dict[str, float]:
    return {
        "detected_onset": onset,
        "onset_confidence": onset,
        "onset_age": 0.0 if onset else 1.0,
        "rms_level": 0.5,
        "rms_growth_ratio": onset,
        "spectral_flux": onset,
    }


class ProductDecoderTests(unittest.TestCase):
    def make_decoder(self, gate_value: float) -> StreamingTransitionDecoder:
        return StreamingTransitionDecoder(
            gate_predict=lambda values: np.full(
                (len(values), 1), gate_value, dtype=np.float32
            ),
            min_pitch=40,
            max_pitch=42,
            active_threshold=0.5,
            transition_threshold=0.2,
            hop_ms=5.8,
            required_frames=2,
        )

    @staticmethod
    def probabilities(pitch: int) -> np.ndarray:
        values = np.full(3, 0.05, dtype=np.float32)
        values[pitch - 40] = 0.9
        return values

    def test_note_on_pitch_change_and_note_off_are_stable(self) -> None:
        decoder = self.make_decoder(1.0)
        frames = []
        for active, pitch in (
            (0.9, 40), (0.9, 40), (0.9, 42), (0.9, 42),
            (0.1, 42), (0.1, 42),
        ):
            frames.append(decoder.step(
                active, self.probabilities(pitch), np.zeros(6), stream()
            ))
        self.assertEqual(frames[1].events[0].kind, "note_on")
        self.assertEqual([value.kind for value in frames[3].events], [
            "note_off", "note_on",
        ])
        self.assertEqual(frames[3].pitch, 42)
        self.assertEqual(frames[5].events[0].kind, "note_off")
        self.assertFalse(frames[5].active)

    def test_vetoed_transition_is_not_retried_until_raw_pitch_changes(self) -> None:
        decoder = self.make_decoder(0.0)
        decisions = []
        for pitch in (40, 40, 42, 42, 42, 42):
            decisions.append(decoder.step(
                0.9, self.probabilities(pitch), np.zeros(6), stream()
            ))
        self.assertTrue(decisions[3].transition_veto)
        self.assertEqual(sum(
            value.transition_score is not None for value in decisions
        ), 1)
        self.assertEqual(decisions[-1].pitch, 40)

    def test_same_midi_onset_retriggers_after_minimum_gap(self) -> None:
        decoder = self.make_decoder(1.0)
        outputs = []
        for index in range(18):
            outputs.append(decoder.step(
                0.9,
                self.probabilities(40),
                np.zeros(6),
                stream(1.0 if index == 17 else 0.0),
            ))
        self.assertTrue(outputs[-1].retrigger)
        self.assertEqual([value.kind for value in outputs[-1].events], [
            "note_off", "note_on",
        ])

    def test_skip_holds_note_and_defers_onset_evidence(self) -> None:
        decoder = self.make_decoder(1.0)
        decoder.step(0.9, self.probabilities(40), np.zeros(6), stream())
        note_on = decoder.step(
            0.9, self.probabilities(40), np.zeros(6), stream()
        )
        self.assertEqual(note_on.pitch, 40)
        for _ in range(12):
            decoder.step(0.9, self.probabilities(40), np.zeros(6), stream())
        skipped = decoder.skip(stream(1.0))
        self.assertEqual(skipped.pitch, 40)
        self.assertEqual(skipped.events, ())
        resumed = decoder.step(
            0.9, self.probabilities(40), np.zeros(6), stream()
        )
        self.assertTrue(resumed.retrigger)


if __name__ == "__main__":
    unittest.main()
