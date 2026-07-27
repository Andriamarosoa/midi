from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import tensorflow as tf

from src.v5.cache import CachedFile, NPZRamCache
from src.v5.losses import (
    AmplitudeWeightedHarmonicOffsetLoss,
    MaskedHarmonicAmplitudeLoss,
)
from src.v5.model import build_pitch_model
from src.v6.dataloader import V6Sequence
from src.v6.dataset import GlobalSampleIndex
from src.v6.evaluate import (
    binary_metrics,
    generate_v6_reports,
    select_f1_threshold,
)


def _cache() -> NPZRamCache:
    arrays = {
        "audio": np.ones((4, 64), dtype=np.float32) * 0.1,
        "visible_window": np.asarray([32, 64, 32, 64], dtype=np.int32),
        "prediction_age_ms": np.asarray([1.0, -1.0, 2.0, 20.0], dtype=np.float32),
        "pitch_midi": np.asarray([60, -1, 64, 60], dtype=np.int16),
        "active": np.asarray([1.0, 0.0, 1.0, 0.0], dtype=np.float32),
        "onset": np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        "release_phase": np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        "note_id": np.asarray([1, -1, 2, 1], dtype=np.int32),
        "channel": np.zeros(4, dtype=np.int8),
        "harmonic_present": np.ones((4, 2), dtype=np.float32),
        "harmonic_amplitude": np.asarray(
            [[1.0, 0.5], [0.0, 0.0], [1.0, 0.25], [1.0, 0.5]],
            dtype=np.float32,
        ),
        "harmonic_offset_cents": np.zeros((4, 2), dtype=np.float32),
        "harmonic_label_valid": np.ones((4, 2), dtype=np.float32),
    }
    cache = NPZRamCache([])
    cache.files = [
        CachedFile(
            source_id="test",
            player_id="05",
            npz_path=Path("test.npz"),
            arrays=arrays,
            dataset_id="guitarset_mono_mix",
        )
    ]
    return cache


class V6ActiveTests(unittest.TestCase):
    def test_sequence_masks_pitch_and_harmonics_when_inactive(self) -> None:
        cache = _cache()
        index = GlobalSampleIndex(cache, 40, 76)
        sequence = V6Sequence(
            cache,
            index,
            batch_size=4,
            min_pitch=40,
            gain=1.0,
            seed=42,
            shuffle=False,
            activity_weights=np.asarray([2.0, 3.0], dtype=np.float32),
            onset_targets=True,
            onset_weights=np.asarray([0.5, 4.0], dtype=np.float32),
            harmonic_targets=True,
            harmonic_count=2,
        )
        inputs, targets, weights = sequence[0]

        self.assertEqual(inputs["audio"].shape, (4, 64, 1))
        self.assertEqual(targets["pitch"].tolist(), [20, 0, 24, 0])
        self.assertEqual(targets["active"].reshape(-1).tolist(), [1.0, 0.0, 1.0, 0.0])
        self.assertEqual(weights["pitch"].tolist(), [1.0, 0.0, 1.0, 0.0])
        self.assertEqual(weights["active"].tolist(), [3.0, 2.0, 3.0, 2.0])
        self.assertEqual(targets["onset"].reshape(-1).tolist(), [1.0, 0.0, 0.0, 0.0])
        self.assertEqual(weights["onset"].tolist(), [4.0, 0.5, 0.5, 0.5])
        valid = targets["harmonic_amplitude"][:, 2:]
        self.assertTrue(np.all(valid[[1, 3]] == 0.0))
        self.assertTrue(np.all(valid[[0, 2]] == 1.0))

    def test_model_active_head_round_trip_and_metric_names(self) -> None:
        config = SimpleNamespace(
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            pooling="hybrid",
            harmonic_auxiliary=True,
            harmonic_count=2,
            harmonic_offset_scale_cents=35.0,
            active_auxiliary=True,
            onset_auxiliary=True,
        )
        model = build_pitch_model(config, pitch_classes=37, input_samples=64)
        self.assertEqual(
            set(model.output_names),
            {
                "pitch",
                "harmonic_amplitude",
                "harmonic_offset_cents",
                "active",
                "onset",
            },
        )
        common_audio = np.linspace(-0.2, 0.2, 64, dtype=np.float32)[None, :, None]
        full_mask = np.ones((1, 64), dtype=np.float32)
        short_mask = np.concatenate([
            np.zeros((1, 32), dtype=np.float32),
            np.ones((1, 32), dtype=np.float32),
        ], axis=1)
        full_onset = model(
            {"audio": common_audio, "time_mask": full_mask}, training=False
        )["onset"]
        short_onset = model(
            {"audio": common_audio, "time_mask": short_mask}, training=False
        )["onset"]
        np.testing.assert_allclose(full_onset, short_onset, rtol=0.0, atol=1e-7)
        cache = _cache()
        sequence = V6Sequence(
            cache,
            GlobalSampleIndex(cache, 40, 76),
            batch_size=4,
            min_pitch=40,
            gain=1.0,
            seed=42,
            shuffle=False,
            onset_targets=True,
            harmonic_targets=True,
            harmonic_count=2,
        )
        model.compile(
            optimizer=tf.keras.optimizers.Adam(1e-3),
            loss={
                "pitch": tf.keras.losses.SparseCategoricalCrossentropy(),
                "active": tf.keras.losses.BinaryCrossentropy(),
                "onset": tf.keras.losses.BinaryCrossentropy(),
                "harmonic_amplitude": MaskedHarmonicAmplitudeLoss(2),
                "harmonic_offset_cents": AmplitudeWeightedHarmonicOffsetLoss(2),
            },
            metrics={
                "active": [tf.keras.metrics.AUC(curve="PR", name="auc_pr")],
                "onset": [tf.keras.metrics.AUC(curve="PR", name="auc_pr")],
            },
            weighted_metrics={
                "pitch": [tf.keras.metrics.SparseCategoricalAccuracy(name="top1")],
            },
        )
        history = model.fit(sequence, validation_data=sequence, epochs=1, verbose=0)
        self.assertIn("val_active_auc_pr", history.history)
        self.assertIn("val_onset_auc_pr", history.history)
        self.assertIn("val_pitch_top1", history.history)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.keras"
            model.save(path)
            restored = tf.keras.models.load_model(path, compile=False)
            predictions = restored(sequence[0][0], training=False)
        self.assertEqual(set(predictions), set(model.output_names))

    def test_validation_threshold_prefers_high_precision_f1_tie(self) -> None:
        probabilities = np.asarray([0.9, 0.8, 0.7, 0.1], dtype=np.float32)
        targets = np.asarray([1.0, 0.0, 1.0, 0.0], dtype=np.float32)
        threshold, metrics = select_f1_threshold(probabilities, targets)
        self.assertAlmostEqual(threshold, 0.7, places=6)
        self.assertEqual(metrics["tp"], 2)
        self.assertEqual(metrics["fp"], 1)
        direct = binary_metrics(probabilities, targets, threshold)
        self.assertAlmostEqual(metrics["f1"], direct["f1"], places=7)

    def test_complete_v6_report_path(self) -> None:
        pitch = np.full((4, 37), 1e-4, dtype=np.float32)
        pitch[0, 20] = 0.99
        pitch[1, 0] = 0.99
        pitch[2, 24] = 0.99
        pitch[3, 0] = 0.99
        predictions = {
            "active": np.asarray([[0.9], [0.2], [0.8], [0.7]], dtype=np.float32),
            "onset": np.asarray([[0.95], [0.1], [0.2], [0.3]], dtype=np.float32),
            "pitch": pitch,
            "harmonic_amplitude": np.asarray(
                [[1.0, 0.5], [0.0, 0.0], [1.0, 0.25], [0.0, 0.0]],
                dtype=np.float32,
            ),
            "harmonic_offset_cents": np.zeros((4, 2), dtype=np.float32),
        }
        targets = {
            "active": np.asarray([[1.0], [0.0], [1.0], [0.0]], dtype=np.float32),
            "onset": np.asarray([[1.0], [0.0], [0.0], [0.0]], dtype=np.float32),
            "pitch": np.asarray([20, 0, 24, 0], dtype=np.int32),
            "harmonic_amplitude": np.asarray(
                [
                    [1.0, 0.5, 1.0, 1.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [1.0, 0.25, 1.0, 1.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
                dtype=np.float32,
            ),
            "harmonic_offset_cents": np.zeros((4, 4), dtype=np.float32),
        }
        metadata = {
            "prediction_age_ms": np.asarray([11.6, -1.0, 23.2, 20.0]),
            "visible_window": np.asarray([512, 512, 1024, 1024]),
            "pitch_midi": np.asarray([60, -1, 64, -1]),
            "player_id": np.asarray(["05"] * 4),
            "source_id": np.asarray(["source"] * 4),
            "dataset_id": np.asarray(["guitarset_mono_mix"] * 4),
            "release_phase": np.asarray([0.0, 0.0, 0.0, 1.0]),
        }

        with tempfile.TemporaryDirectory() as directory:
            report = generate_v6_reports(
                directory,
                predictions,
                targets,
                metadata,
                min_pitch=40,
                active_threshold=0.75,
                evaluated_checkpoint="best.keras",
                harmonic_count=2,
                onset_threshold=0.8,
            )
            reports = Path(directory) / "reports"
            self.assertTrue((reports / "v6_metrics.json").exists())
            self.assertTrue((reports / "active_release_phase.csv").exists())
            self.assertEqual(report["active"]["fp"], 0)
            self.assertEqual(report["pitch_on_true_active"]["samples"], 2)
            self.assertAlmostEqual(report["joint"]["joint_frame_accuracy"], 1.0)
            self.assertEqual(report["harmonics_on_true_active"]["samples"], 2)
            self.assertEqual(report["onset"]["tp"], 1)
            self.assertEqual(report["onset"]["fp"], 0)
            self.assertTrue((reports / "onset_metrics.json").exists())


if __name__ == "__main__":
    unittest.main()
