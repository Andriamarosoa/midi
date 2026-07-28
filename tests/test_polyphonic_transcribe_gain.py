from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.polyphonic.transcribe import (
    _octave_up_model_window,
    _remap_octave_up_outputs,
    transcribe,
)


class PolyphonicTranscribeGainTests(unittest.TestCase):
    def test_octave_up_window_is_causal_pair_decimation(self) -> None:
        source = np.arange(16, dtype=np.float32)
        transformed = _octave_up_model_window(source, 8)
        np.testing.assert_allclose(
            transformed,
            np.arange(0.5, 16.0, 2.0, dtype=np.float32),
        )

    def test_octave_up_outputs_are_remapped_down_twelve_classes(self) -> None:
        frame = np.arange(37, dtype=np.float32)
        onset = frame + 100.0
        harmonic = np.repeat(frame[:, None], 2, axis=1)
        mapped_frame, mapped_onset, mapped_harmonic = (
            _remap_octave_up_outputs(frame, onset, harmonic)
        )
        np.testing.assert_allclose(mapped_frame[:25], frame[12:])
        np.testing.assert_allclose(mapped_onset[:25], onset[12:])
        np.testing.assert_allclose(mapped_harmonic[:25], harmonic[12:])
        np.testing.assert_allclose(mapped_frame[25:], 0.0)
        np.testing.assert_allclose(mapped_onset[25:], 0.0)
        np.testing.assert_allclose(mapped_harmonic[25:], 0.0)

    def test_manual_gain_precedes_evidence_ring_and_runtime(self) -> None:
        waveform = np.asarray([0.1, -0.2, 0.3, -0.4], np.float32)
        evidence_hops: list[np.ndarray] = []
        runtime_windows: list[tuple[np.ndarray, int]] = []

        class FakeBundle:
            def __init__(self, artifacts: Path) -> None:
                self.metadata = {
                    "sample_rate": 1000,
                    "hop_samples": 4,
                    "max_window_samples": 8,
                    "normalization_gain": 1.0,
                }

        class FakeRuntime:
            def __init__(self, bundle: FakeBundle) -> None:
                pass

            def infer(self, window: np.ndarray, visible_samples: int):
                runtime_windows.append((window.copy(), visible_samples))
                return SimpleNamespace(
                    frame_probability=np.zeros(1, np.float32),
                    onset_probability=np.zeros(1, np.float32),
                    harmonic_amplitude=np.zeros((1, 2), np.float32),
                    inference_ms=0.1,
                )

        class FakeEvidencePolicy:
            def __init__(self, *args, **kwargs) -> None:
                self.index = -1

            @classmethod
            def from_metadata(cls, *args, **kwargs):
                return cls()

            def prime_silence(self) -> int:
                return 250

            def process(self, values: np.ndarray):
                self.index += 1
                evidence_hops.append(values.copy())
                return SimpleNamespace(
                    audio_hop_index=self.index,
                    activity=SimpleNamespace(active=True),
                    onset=SimpleNamespace(is_onset=False),
                )

            def diagnostics(self) -> dict[str, object]:
                return {"calibrated": True}

        class FakeDecoder:
            def step(self, *args, **kwargs):
                return []

            def panic(self):
                return []

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.mid"
            with (
                patch(
                    "src.polyphonic.transcribe.PolyphonicBundle",
                    FakeBundle,
                ),
                patch(
                    "src.polyphonic.transcribe.TFLitePolyphonicModel",
                    FakeRuntime,
                ),
                patch(
                    "src.polyphonic.transcribe.PolyphonicAudioEvidencePolicy",
                    FakeEvidencePolicy,
                ),
                patch(
                    "src.polyphonic.transcribe._decoder",
                    return_value=FakeDecoder(),
                ),
                patch(
                    "src.polyphonic.transcribe._audio",
                    return_value=waveform,
                ),
                patch("src.polyphonic.transcribe.write_midi"),
            ):
                report = transcribe(
                    Path("input.wav"),
                    output,
                    Path("artifacts"),
                    0,
                    0,
                    auto_level=False,
                    audio_gain=2.0,
                )

        expected = waveform * 2.0
        np.testing.assert_allclose(evidence_hops, [expected])
        np.testing.assert_allclose(runtime_windows[-1][0][-4:], expected)
        np.testing.assert_allclose(runtime_windows[-1][0][:-4], 0.0)
        self.assertEqual(runtime_windows[-1][1], 8)
        self.assertEqual(report["capture_gain"], 2.0)
        self.assertEqual(report["gain_induced_clipped_samples"], 0)
        self.assertEqual(
            report["audio_active_note_coverage"]["empty_active_audio_hops"],
            1,
        )
        self.assertEqual(
            report["audio_active_note_coverage"]["with_active_notes_hops"],
            0,
        )
        self.assertAlmostEqual(
            report["audio_active_note_coverage"][
                "longest_empty_active_audio_ms"
            ],
            4.0,
        )


if __name__ == "__main__":
    unittest.main()
