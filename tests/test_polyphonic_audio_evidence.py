from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.polyphonic.audio_evidence import (
    PolyphonicAudioEvidencePolicy,
    offline_audio_activity_mask,
    offline_audio_evidence_masks,
)
from src.polyphonic.decoder import PolyphonicMidiEvent
from src.polyphonic.transcribe import transcribe
from src.stream.audio_activity_gate import CalibratedAudioActivityGate
from src.stream.onset_detector import AdaptiveOnsetDetector


class PolyphonicAudioEvidencePolicyTests(unittest.TestCase):
    sample_rate = 1000
    hop_samples = 10

    def test_offline_activity_mask_keeps_waveform_frame_zero(self) -> None:
        waveform = np.concatenate((
            np.full(self.hop_samples, 0.5, np.float32),
            np.zeros(self.hop_samples, np.float32),
        ))

        activity, report = offline_audio_activity_mask(
            waveform,
            sample_rate=self.sample_rate,
            hop_samples=self.hop_samples,
            frame_count=2,
            calibration_s=0.04,
        )

        self.assertEqual(activity.tolist(), [True, False])
        self.assertEqual(report["audio_hop_index"], 1)
        self.assertGreater(report["silent_priming_hops"], 0)
        self.assertFalse(report["label_leakage"])

        complete_only, _ = offline_audio_activity_mask(
            np.append(waveform, np.float32(0.25)),
            sample_rate=self.sample_rate,
            hop_samples=self.hop_samples,
            frame_count=2,
            calibration_s=0.04,
        )
        self.assertEqual(len(complete_only), 2)

    def test_offline_masks_accept_an_explicit_evidence_candidate(
        self,
    ) -> None:
        waveform = np.concatenate((
            np.full(self.hop_samples, 0.5, np.float32),
            np.zeros(self.hop_samples, np.float32),
        ))

        _, _, report = offline_audio_evidence_masks(
            waveform,
            sample_rate=self.sample_rate,
            hop_samples=self.hop_samples,
            frame_count=2,
            calibration_s=0.04,
            metadata={
                "audio_evidence": {
                    "fft_size": 128,
                    "onset_adapt_temporal_background": True,
                }
            },
        )

        self.assertTrue(
            report["onset_detector"]["adapt_temporal_background"]
        )

    def _policy(self) -> PolyphonicAudioEvidencePolicy:
        return PolyphonicAudioEvidencePolicy(
            self.sample_rate,
            self.hop_samples,
            fft_size=128,
            calibration_s=0.04,
        )

    def _tone(self, amplitude: float = 0.2) -> np.ndarray:
        phase = np.arange(self.hop_samples, dtype=np.float32)
        return (
            amplitude
            * np.sin(2.0 * np.pi * 100.0 * phase / self.sample_rate)
        ).astype(np.float32)

    def test_frontend_parameters_are_loaded_from_bundle_metadata(self) -> None:
        policy = PolyphonicAudioEvidencePolicy.from_metadata(
            self.sample_rate,
            self.hop_samples,
            {
                "audio_evidence": {
                    "fft_size": 128,
                    "onset_cooldown_ms": 40.0,
                    "onset_rearm_attack_ratio": 2.5,
                    "onset_adapt_temporal_background": True,
                }
            },
            calibration_s=0.04,
        )

        self.assertEqual(policy.onset_detector.cooldown_hops, 4)
        self.assertEqual(
            policy.onset_detector.rearm_attack_ratio,
            2.5,
        )
        self.assertTrue(
            policy.onset_detector.adapt_temporal_background
        )

    def test_matches_the_previous_live_detector_and_gate_policy(self) -> None:
        policy = self._policy()
        detector = AdaptiveOnsetDetector(
            self.sample_rate,
            self.hop_samples,
            fft_size=128,
            calibration_s=0.04,
            enable_peak_rearm=True,
            robust_rearm=True,
            rearm_attack_ratio=3.0,
            require_joint_temporal_evidence=True,
        )
        gate = CalibratedAudioActivityGate(
            self.sample_rate,
            self.hop_samples,
            calibration_s=0.04,
        )
        silence = np.zeros(self.hop_samples, np.float32)
        hops = [silence] * 4 + [self._tone(), self._tone(0.05), silence]

        for index, hop in enumerate(hops):
            evidence = policy.process(hop)
            expected_onset = detector.process(hop)
            expected_activity = gate.process_rms(expected_onset.rms)
            self.assertEqual(evidence.onset, expected_onset)
            self.assertEqual(evidence.activity, expected_activity)
            self.assertEqual(evidence.audio_hop_index, index)

    def test_robust_rearm_detects_overlapping_attacks_without_tail_repeats(
        self,
    ) -> None:
        policy = self._policy()
        policy.prime_silence()
        onsets: list[tuple[int, int]] = []

        for note_index in range(3):
            for hop_index, amplitude in enumerate(
                [0.2, 0.18] + [0.04] * 8
            ):
                evidence = policy.process(self._tone(amplitude))
                if evidence.onset.is_onset:
                    onsets.append((note_index, hop_index))

        self.assertEqual(onsets, [(0, 0), (1, 0), (2, 0)])

    def test_silent_priming_is_deterministic_and_keeps_first_audio_hop(self) -> None:
        first = self._policy()
        second = self._policy()

        self.assertEqual(first.prime_silence(), 4)
        self.assertEqual(second.prime_silence(), 4)
        self.assertEqual(first.audio_hop_index, -1)
        self.assertEqual(second.audio_hop_index, -1)

        first_result = first.process(self._tone())
        second_result = second.process(self._tone())
        self.assertEqual(first_result, second_result)
        self.assertEqual(first_result.audio_hop_index, 0)
        self.assertAlmostEqual(first_result.time_s, 0.01)
        self.assertTrue(first_result.calibrated)
        self.assertTrue(first_result.activity.active)
        self.assertTrue(first_result.onset.is_onset)

    def test_continuity_reset_preserves_calibration_thresholds_and_clock(self) -> None:
        policy = self._policy()
        policy.prime_silence()
        first = policy.process(self._tone())
        thresholds = policy.activity_diagnostics()
        self.assertTrue(first.activity.active)

        policy.reset_continuity()
        self.assertFalse(policy.activity_diagnostics()["active"])
        resumed = policy.process(self._tone())

        self.assertEqual(resumed.audio_hop_index, 1)
        self.assertTrue(resumed.calibrated)
        self.assertFalse(resumed.onset.is_onset)
        self.assertEqual(
            thresholds["open_threshold_dbfs"],
            resumed.activity.open_threshold_dbfs,
        )
        self.assertEqual(
            thresholds["close_threshold_dbfs"],
            resumed.activity.close_threshold_dbfs,
        )

    def test_full_reset_clears_calibration_priming_and_clock(self) -> None:
        policy = self._policy()
        policy.prime_silence()
        policy.process(self._tone())

        policy.reset()

        self.assertFalse(policy.calibrated)
        self.assertEqual(policy.audio_hop_index, -1)
        self.assertEqual(policy.synthetic_priming_hops, 0)


class PolyphonicTranscriptionEvidenceTests(unittest.TestCase):
    def test_transcription_primes_silence_without_dropping_first_music_hop(
        self,
    ) -> None:
        sample_rate = 1000
        hop_samples = 10
        phase = np.arange(hop_samples, dtype=np.float32)
        first_hop = (
            0.2 * np.sin(2.0 * np.pi * 100.0 * phase / sample_rate)
        ).astype(np.float32)
        waveform = np.concatenate((first_hop, np.zeros(hop_samples, np.float32)))

        class FakeBundle:
            def __init__(self, artifacts: Path) -> None:
                self.metadata = {
                    "sample_rate": sample_rate,
                    "hop_samples": hop_samples,
                    "max_window_samples": 20,
                }

        class FakeRuntime:
            def __init__(self, bundle: FakeBundle) -> None:
                pass

            def infer(self, window: np.ndarray, visible_samples: int):
                return SimpleNamespace(
                    frame_probability=np.asarray([0.9], np.float32),
                    onset_probability=np.asarray([0.9], np.float32),
                    harmonic_amplitude=np.zeros((1, 2), np.float32),
                    inference_ms=0.1,
                )

        class RecordingDecoder:
            def __init__(self) -> None:
                self.calls: list[tuple[bool, int]] = []

            def step(
                self,
                frame_probability,
                onset_probability,
                harmonic_amplitude,
                *,
                audio_active: bool,
                audio_hop_index: int,
                audio_onset: bool,
                audio_onset_hop_index: int | None,
            ) -> list[PolyphonicMidiEvent]:
                self.calls.append((audio_active, audio_hop_index))
                if len(self.calls) == 1 and audio_active:
                    return [PolyphonicMidiEvent(
                        "note_on", 60, 100, audio_hop_index
                    )]
                return []

            def panic(self) -> list[PolyphonicMidiEvent]:
                return []

        decoder = RecordingDecoder()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.mid"
            with (
                patch("src.polyphonic.transcribe.PolyphonicBundle", FakeBundle),
                patch(
                    "src.polyphonic.transcribe.TFLitePolyphonicModel",
                    FakeRuntime,
                ),
                patch("src.polyphonic.transcribe._decoder", return_value=decoder),
                patch("src.polyphonic.transcribe._audio", return_value=waveform),
                patch("src.polyphonic.transcribe.write_midi"),
            ):
                report = transcribe(
                    Path("input.wav"), output, Path("artifacts"), 0, 0
                )

        self.assertEqual(decoder.calls, [(True, 0), (False, 1)])
        self.assertEqual(report["note_on_events"], 1)
        self.assertEqual(report["silent_priming_hops"], 100)
        self.assertEqual(report["audio_evidence"]["audio_hop_index"], 1)


if __name__ == "__main__":
    unittest.main()
