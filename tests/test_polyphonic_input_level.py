from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.input_level import (
    CausalModelInputLeveler,
    offline_model_input_level_gains,
)


class CausalModelInputLevelerTests(unittest.TestCase):
    def _leveler(self) -> CausalModelInputLeveler:
        return CausalModelInputLeveler(
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=1.5,
            input_samples=20,
        )

    def test_first_audible_peak_initializes_session_gain(self) -> None:
        leveler = self._leveler()
        hop = np.full(10, 0.05, np.float32)

        result = leveler.process(hop, audio_active=True)

        self.assertTrue(result.initialized)
        self.assertGreater(result.gain_db, 10.0)
        self.assertLessEqual(result.gain_db, 18.0)

    def test_controller_parameters_are_loaded_from_bundle_metadata(self) -> None:
        leveler = CausalModelInputLeveler.from_metadata(
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=1.5,
            input_samples=20,
            metadata={
                "automatic_model_input_level": {
                    "target_capture_peak_dbfs": -15.0,
                    "minimum_gain_db": 0.0,
                    "maximum_gain_db": 9.0,
                    "model_headroom_peak": 0.95,
                }
            },
        )

        self.assertEqual(leveler.target_capture_peak_dbfs, -15.0)
        self.assertEqual(leveler.minimum_gain_db, 0.0)
        self.assertEqual(leveler.maximum_gain_db, 9.0)
        self.assertEqual(leveler.model_headroom_peak, 0.95)

    def test_louder_attack_reduces_gain_immediately(self) -> None:
        leveler = self._leveler()
        quiet = leveler.process(
            np.full(10, 0.05, np.float32), audio_active=True
        )
        loud = leveler.process(
            np.full(10, 0.5, np.float32), audio_active=True
        )

        self.assertLess(loud.gain_db, quiet.gain_db)
        self.assertEqual(loud.session_gain_db, 0.0)
        self.assertEqual(loud.gain_db, 0.0)

    def test_active_decay_cannot_pump_gain(self) -> None:
        leveler = self._leveler()
        loud = leveler.process(
            np.full(10, 0.5, np.float32), audio_active=True
        )
        tail = leveler.process(
            np.full(10, 0.01, np.float32), audio_active=True
        )

        self.assertAlmostEqual(
            tail.gain_db - loud.gain_db,
            0.0,
            places=6,
        )

    def test_stable_silence_recovers_session_gain_for_the_next_note(self) -> None:
        leveler = self._leveler()
        loud = leveler.process(
            np.full(10, 0.5, np.float32), audio_active=True
        )
        leveler.process(np.zeros(10, np.float32), audio_active=False)
        recovered = leveler.process(
            np.zeros(10, np.float32), audio_active=False
        )

        self.assertAlmostEqual(
            recovered.session_gain_db - loud.session_gain_db,
            0.01,
            places=6,
        )

    def test_silence_never_initializes_or_changes_gain(self) -> None:
        leveler = self._leveler()
        silence = np.zeros(10, np.float32)

        first = leveler.process(silence, audio_active=False)
        second = leveler.process(silence, audio_active=False)

        self.assertFalse(first.initialized)
        self.assertFalse(second.initialized)
        self.assertEqual(second.gain, 1.0)
        diagnostics = leveler.diagnostics()
        self.assertIsNone(diagnostics["minimum_applied_gain_db"])
        self.assertIsNone(diagnostics["maximum_applied_gain_db"])

    def test_offline_replay_returns_one_causal_gain_per_hop(self) -> None:
        waveform = np.concatenate((
            np.zeros(10, np.int16),
            np.full(10, 1000, np.int16),
            np.full(10, 10_000, np.int16),
        ))

        gains, report = offline_model_input_level_gains(
            waveform,
            np.asarray([False, True, True]),
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=1.5,
        )

        self.assertEqual(gains.shape, (3,))
        self.assertEqual(float(gains[0]), 1.0)
        self.assertGreater(float(gains[1]), 1.0)
        self.assertLess(float(gains[2]), float(gains[1]))
        self.assertFalse(report["label_leakage"])
        self.assertEqual(report["projected_clipped_hops"], 0)
        self.assertEqual(report["controller"]["minimum_gain_db"], 0.0)

    def test_offline_headroom_uses_the_complete_model_window(self) -> None:
        waveform = np.concatenate((
            np.full(10, 30_000, np.int16),
            np.full(10, 100, np.int16),
        ))

        _, report = offline_model_input_level_gains(
            waveform,
            np.asarray([False, True]),
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=0.5,
            input_samples=20,
        )

        self.assertEqual(report["window_hops"], 2)
        self.assertEqual(report["projected_clipped_hops"], 0)
        self.assertLessEqual(
            report["projected_model_window_peak"]["maximum"],
            0.981,
        )

    def test_amplification_only_session_keeps_safety_attenuation(self) -> None:
        waveform = np.full(20, 29_000, np.int16)

        _, report = offline_model_input_level_gains(
            waveform,
            np.asarray([True, True]),
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=1.5,
            input_samples=20,
            minimum_gain_db=0.0,
        )

        controller = report["controller"]
        self.assertEqual(controller["minimum_gain_db"], 0.0)
        self.assertEqual(controller["session_gain_db"], 0.0)
        self.assertLess(controller["minimum_applied_gain_db"], 0.0)
        self.assertEqual(report["projected_clipped_hops"], 0)

    def test_inactive_click_only_applies_temporary_safety_gain(self) -> None:
        leveler = CausalModelInputLeveler(
            sample_rate=1000,
            hop_samples=10,
            model_normalization_gain=0.5,
            input_samples=20,
        )
        leveler.process(
            np.full(10, 0.9, np.float32),
            audio_active=False,
        )
        limited = leveler.process(
            np.full(10, 0.01, np.float32),
            audio_active=True,
        )
        restored = leveler.process(
            np.full(10, 0.01, np.float32),
            audio_active=True,
        )

        self.assertEqual(limited.session_gain_db, 18.0)
        self.assertLess(limited.gain_db, limited.session_gain_db)
        self.assertAlmostEqual(restored.gain_db, 18.0, places=6)


if __name__ == "__main__":
    unittest.main()
