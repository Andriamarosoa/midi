from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from src.product.engine import GuitarMidiEngine
from src.product.tflite_runtime import PitchPrediction


class FakePitchModel:
    def infer(self, waveform: np.ndarray, visible_window: int) -> PitchPrediction:
        pitch = np.full(37, 0.001, dtype=np.float32)
        pitch[20] = 0.95
        return PitchPrediction(
            active_probability=0.9,
            pitch_probability=pitch,
            harmonic_amplitude=np.zeros(20, dtype=np.float32),
            harmonic_offset_cents=np.zeros(20, dtype=np.float32),
            inference_ms=0.1,
        )


class ProductEngineTests(unittest.TestCase):
    def make_engine(self) -> GuitarMidiEngine:
        bundle = SimpleNamespace(metadata={
            "sample_rate": 44100,
            "hop_samples": 256,
            "max_window_samples": 4096,
            "progressive_windows": [512, 1024, 2048, 4096],
            "min_pitch": 40,
            "max_pitch": 76,
            "active_threshold": 0.15,
            "transition_threshold": 0.2,
            "stability_frames": 2,
            "minimum_retrigger_ms": 80.0,
        })
        return GuitarMidiEngine(
            bundle,
            FakePitchModel(),
            lambda values: np.ones((len(values), 1), dtype=np.float32),
            calibration_s=0.001,
        )

    def test_calibration_suppresses_midi_then_stable_note_starts(self) -> None:
        engine = self.make_engine()
        frames = [
            engine.process_hop(np.zeros(256, dtype=np.float32))
            for _ in range(5)
        ]
        self.assertIsNone(frames[0].prediction)
        self.assertTrue(frames[3].calibrated)
        self.assertEqual(frames[4].decoder.pitch, 60)
        self.assertEqual(frames[4].decoder.events[0].kind, "note_on")

    def test_invalid_hop_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.make_engine().process_hop(np.zeros(128, dtype=np.float32))

    def test_continuity_reset_preserves_calibration_after_audio_gap(self) -> None:
        engine = self.make_engine()
        for _ in range(5):
            engine.process_hop(np.zeros(256, dtype=np.float32))
        tick_before = engine.onset_detector.tick_index
        samples_before = engine.total_samples

        engine.reset_continuity()

        self.assertTrue(engine.onset_detector.calibrated)
        self.assertEqual(engine.onset_detector.tick_index, tick_before)
        self.assertEqual(engine.total_samples, samples_before)
        self.assertEqual(engine.ring.available, 0)
        self.assertEqual(engine.decoder.current, -1)
        first = engine.process_hop(np.zeros(256, dtype=np.float32))
        self.assertTrue(first.calibrated)
        self.assertIsNone(first.prediction)
        self.assertEqual(first.visible_window, 256)
        second = engine.process_hop(np.zeros(256, dtype=np.float32))
        self.assertTrue(second.calibrated)
        self.assertIsNotNone(second.prediction)
        self.assertEqual(second.visible_window, 512)


if __name__ == "__main__":
    unittest.main()
