from __future__ import annotations

import unittest

import numpy as np

from src.stream.onset_detector import AdaptiveOnsetDetector


class AdaptiveOnsetDetectorTests(unittest.TestCase):
    def test_continuity_reset_preserves_calibration_and_suppresses_first_hop(self) -> None:
        detector = AdaptiveOnsetDetector(
            sample_rate=44100,
            hop_samples=256,
            calibration_s=0.05,
        )
        silence = np.zeros(256, dtype=np.float32)
        for _ in range(detector.calibration_hops):
            detector.process(silence)
        self.assertTrue(detector.calibrated)
        calibrated_count = detector.rms_stats.count
        previous_tick = detector.tick_index

        detector.reset_continuity()
        self.assertTrue(detector.calibrated)
        self.assertEqual(detector.rms_stats.count, calibrated_count)
        self.assertEqual(detector.tick_index, previous_tick)

        tone = np.ones(256, dtype=np.float32) * 0.5
        first = detector.process(tone)
        self.assertFalse(first.is_onset)
        self.assertTrue(first.calibrated)
        self.assertEqual(first.tick_index, previous_tick + 1)
        second = detector.process(tone)
        self.assertFalse(second.is_onset)
        self.assertEqual(second.tick_index, previous_tick + 2)

    def test_rearms_after_silent_calibration_and_energy_release(self) -> None:
        sample_rate = 44100
        hop = 256
        detector = AdaptiveOnsetDetector(
            sample_rate=sample_rate,
            hop_samples=hop,
            calibration_s=0.1,
            cooldown_ms=20.0,
            enable_peak_rearm=True,
        )
        silence = np.zeros(hop, dtype=np.float32)
        for _ in range(detector.calibration_hops):
            detector.process(silence)

        phase = np.arange(hop, dtype=np.float32)
        tone = np.sin(2.0 * np.pi * 220.0 * phase / sample_rate).astype(np.float32)
        onsets = 0
        for amplitude in ([0.2] * 5 + [0.1] * 5 + [0.03] * 5 + [0.0] * 8):
            onsets += int(detector.process(tone * amplitude).is_onset)
        for amplitude in ([0.2] * 5 + [0.1] * 5 + [0.03] * 5):
            onsets += int(detector.process(tone * amplitude).is_onset)
        self.assertGreaterEqual(onsets, 2)

    def test_robust_rearm_does_not_repeat_on_a_sustained_tone(self) -> None:
        sample_rate = 44100
        hop = 256
        detector = AdaptiveOnsetDetector(
            sample_rate=sample_rate,
            hop_samples=hop,
            calibration_s=0.05,
            enable_peak_rearm=True,
            robust_rearm=True,
            rearm_attack_ratio=3.5,
            require_joint_temporal_evidence=True,
        )
        silence = np.zeros(hop, dtype=np.float32)
        for _ in range(detector.calibration_hops):
            detector.process(silence)
        phase = np.arange(hop * 180, dtype=np.float32)
        tone = (
            0.2
            * np.sin(2.0 * np.pi * 220.0 * phase / sample_rate)
        ).astype(np.float32)

        onsets = [
            detector.process(tone[start:start + hop]).is_onset
            for start in range(0, len(tone), hop)
        ]

        self.assertEqual(sum(onsets), 1)
        self.assertTrue(detector.armed)

    def test_robust_rearm_detects_a_new_attack_after_a_guitar_tail(self) -> None:
        sample_rate = 44100
        hop = 256
        detector = AdaptiveOnsetDetector(
            sample_rate=sample_rate,
            hop_samples=hop,
            calibration_s=0.05,
            enable_peak_rearm=True,
            robust_rearm=True,
            rearm_attack_ratio=3.5,
            require_joint_temporal_evidence=True,
        )
        silence = np.zeros(hop, dtype=np.float32)
        for _ in range(detector.calibration_hops):
            detector.process(silence)
        phase = np.arange(hop, dtype=np.float32)
        tone = np.sin(
            2.0 * np.pi * 220.0 * phase / sample_rate
        ).astype(np.float32)
        envelope = (
            [0.2, 0.18]
            + [0.04] * detector.cooldown_hops
            + [0.2, 0.18]
        )

        onset_indices = [
            index
            for index, amplitude in enumerate(envelope)
            if detector.process(tone * amplitude).is_onset
        ]

        self.assertEqual(onset_indices, [0, len(envelope) - 2])


if __name__ == "__main__":
    unittest.main()
