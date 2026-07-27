from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import tensorflow as tf

from src.v5.cache import CachedFile, NPZRamCache
from src.v5.dataloader import V5Sequence
from src.v5.dataset import GlobalSampleIndex
from src.v5.losses import (
    AmplitudeWeightedHarmonicOffsetLoss,
    MaskedHarmonicAmplitudeLoss,
)
from src.v5.model import build_pitch_model


class HarmonicModelTests(unittest.TestCase):
    def test_masked_losses_ignore_unknown_and_weak_partials(self) -> None:
        amplitude_loss = MaskedHarmonicAmplitudeLoss(harmonic_count=2)
        amplitude_target = tf.constant([[0.8, 0.2, 1.0, 0.0]])
        amplitude_prediction = tf.constant([[0.5, 1.0]])
        self.assertAlmostEqual(
            float(amplitude_loss(amplitude_target, amplitude_prediction)),
            0.3,
            places=6,
        )

        offset_loss = AmplitudeWeightedHarmonicOffsetLoss(
            harmonic_count=2,
            scale_cents=35.0,
        )
        offset_target = tf.constant([[10.0, -20.0, 1.0, 1.0, 1.0, 0.0]])
        offset_prediction = tf.constant([[0.0, 35.0]])
        self.assertAlmostEqual(
            float(offset_loss(offset_target, offset_prediction)),
            10.0 / 35.0,
            places=6,
        )

    def test_sequence_packs_harmonic_targets(self) -> None:
        arrays = {
            "audio": np.ones((2, 64), dtype=np.float32) * 0.1,
            "visible_window": np.asarray([32, 64], dtype=np.int32),
            "prediction_age_ms": np.asarray([1.0, 2.0], dtype=np.float32),
            "pitch_midi": np.asarray([60, 64], dtype=np.int16),
            "active": np.ones(2, dtype=np.float32),
            "harmonic_amplitude": np.asarray(
                [[1.0, 0.25], [1.0, 0.5]], dtype=np.float32
            ),
            "harmonic_offset_cents": np.asarray(
                [[1.0, -2.0], [3.0, -4.0]], dtype=np.float32
            ),
            "harmonic_label_valid": np.ones((2, 2), dtype=np.float32),
        }
        cache = NPZRamCache([])
        cache.files = [
            CachedFile(
                source_id="test",
                player_id="00",
                npz_path=Path("test.npz"),
                arrays=arrays,
            )
        ]
        index = GlobalSampleIndex(cache, 40, 76)
        sequence = V5Sequence(
            cache,
            index,
            batch_size=2,
            min_pitch=40,
            gain=1.0,
            seed=42,
            shuffle=False,
            harmonic_targets=True,
            harmonic_count=2,
        )

        inputs, targets = sequence[0]

        self.assertEqual(inputs["audio"].shape, (2, 64, 1))
        self.assertEqual(targets["pitch"].tolist(), [20, 24])
        self.assertEqual(targets["harmonic_amplitude"].shape, (2, 4))
        self.assertEqual(targets["harmonic_offset_cents"].shape, (2, 6))

    def test_auxiliary_model_round_trip(self) -> None:
        config = SimpleNamespace(
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            pooling="hybrid",
            harmonic_auxiliary=True,
            harmonic_count=2,
            harmonic_offset_scale_cents=35.0,
        )
        model = build_pitch_model(config, pitch_classes=4, input_samples=64)
        inputs = {
            "audio": np.zeros((1, 64, 1), dtype=np.float32),
            "time_mask": np.ones((1, 64), dtype=np.float32),
        }
        predictions = model(inputs, training=False)
        self.assertEqual(set(predictions), {
            "pitch", "harmonic_amplitude", "harmonic_offset_cents",
        })
        self.assertEqual(tuple(predictions["pitch"].shape), (1, 4))
        self.assertEqual(tuple(predictions["harmonic_amplitude"].shape), (1, 2))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.keras"
            model.save(path)
            restored = tf.keras.models.load_model(path, compile=False)
            restored_predictions = restored(inputs, training=False)

        self.assertEqual(set(restored_predictions), set(predictions))


if __name__ == "__main__":
    unittest.main()
