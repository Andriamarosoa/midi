from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from src.v5.external_data import NoteEvent, SourceRecording
from src.v6.onset_continuous_dataset import (
    PHASE_NAMES,
    ContinuousOnsetBuildConfig,
    extract_recording_frames,
    first_causal_frame_end,
    onset_frame_ends,
)
from src.v6.train_continuous_onset import event_counts
from src.v6.train_continuous_onset import OnsetSequence
from src.v6.onset_continuous_model import build_continuous_onset_model


class ContinuousOnsetDatasetTests(unittest.TestCase):
    def test_first_frame_is_strictly_causal_and_hop_aligned(self) -> None:
        self.assertEqual(first_causal_frame_end(0, 256), 256)
        self.assertEqual(first_causal_frame_end(255, 256), 256)
        self.assertEqual(first_causal_frame_end(256, 256), 512)

    def test_same_pitch_retrigger_keeps_two_note_id_events(self) -> None:
        notes = [
            NoteEvent(3, 0.10, 0.30, 60),
            NoteEvent(9, 0.32, 0.55, 60),
        ]
        frames = onset_frame_ends(
            notes, 44_100, 256, 2, 44_100, 40, 76
        )
        observed = {
            note.note_id for grouped in frames.values() for note in grouped
        }
        self.assertEqual(observed, {3, 9})
        self.assertEqual(sum(len(grouped) for grouped in frames.values()), 4)

    def test_extraction_uses_real_grid_and_no_negative_overwrites_onset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample_rate = 44_100
            waveform = np.zeros(sample_rate, dtype=np.float32)
            for start_s in (0.20, 0.60):
                start = int(round(start_s * sample_rate))
                waveform[start:start + 900] = np.hanning(1800)[:900].astype(np.float32)
            wav = root / "same_pitch.wav"
            sf.write(wav, waveform, sample_rate)
            jams = root / "same_pitch.jams"
            jams.write_text(json.dumps({
                "annotations": [{
                    "namespace": "note_midi",
                    "data": [
                        {"time": 0.20, "duration": 0.25, "value": 60},
                        {"time": 0.60, "duration": 0.25, "value": 60},
                    ],
                }],
            }), encoding="utf-8")
            recording = SourceRecording(
                dataset_id="test",
                source_id="same_pitch",
                audio_path=wav,
                annotation_path=jams,
                annotation_format="guitarset_jams",
                player_id="04",
                group_id="group",
                capture_id="mono",
                split="validation",
                license_id="test",
            )
            arrays, report = extract_recording_frames(
                recording,
                ContinuousOnsetBuildConfig(silence_per_recording=4),
            )
            self.assertEqual(arrays["audio"].shape[1], 512)
            self.assertTrue(np.all(arrays["frame_end_sample"] % 256 == 0))
            positive = arrays["onset"] > 0.5
            self.assertEqual(int(np.sum(positive)), 4)
            self.assertEqual(set(arrays["note_id"][positive].tolist()), {0, 1})
            self.assertTrue(np.all(arrays["phase"][positive] == PHASE_NAMES.index("onset")))
            self.assertEqual(report["unique_positive_notes"], 2)

    def test_event_match_is_causal_and_counts_retrigger(self) -> None:
        item = {
            "probabilities": np.asarray([0.1, 0.9, 0.1, 0.9]),
            "end_samples": np.asarray([256, 512, 3072, 3328]),
            "reference_samples": np.asarray([400, 3200]),
        }
        tp, fp, fn, latencies = event_counts(
            item, 0.5, 44_100, tolerance_ms=10.0, refractory_ms=20.0
        )
        self.assertEqual((tp, fp, fn), (2, 0, 0))
        self.assertTrue(all(value >= 0.0 for value in latencies))

    def test_small_model_trains_with_balanced_sequence(self) -> None:
        import tensorflow as tf

        tf.keras.utils.set_random_seed(7)
        arrays = {
            "audio": np.random.default_rng(7).normal(size=(8, 512)).astype(np.float32),
            "onset": np.asarray([1, 0, 1, 0, 1, 0, 1, 0], dtype=np.float32),
            "phase": np.asarray([0, 1, 0, 2, 0, 5, 0, 6], dtype=np.int8),
        }
        sequence = OnsetSequence(
            arrays, batch_size=4, gain=0.1, shuffle=False, balance=True, seed=7
        )
        model = build_continuous_onset_model(channels=4, dropout=0.0)
        model.compile(optimizer="adam", loss="binary_crossentropy")
        history = model.fit(sequence, epochs=1, verbose=0)
        self.assertIn("loss", history.history)
        self.assertEqual(model.output_shape, (None, 1))

    def test_temporal_pooling_preserves_a_standalone_exportable_output(self) -> None:
        model = build_continuous_onset_model(
            channels=4, dropout=0.0, pooling="temporal_bins"
        )
        output = model(np.zeros((2, 512, 1), dtype=np.float32), training=False)
        self.assertEqual(tuple(output.shape), (2, 1))
        self.assertLess(model.count_params(), 25_000)


if __name__ == "__main__":
    unittest.main()
