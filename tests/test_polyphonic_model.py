from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf
import h5py

from src.polyphonic.keras_compat import (
    _normalize_h5_paths,
    load_polyphonic_checkpoint,
)
from src.polyphonic.model import (
    ClassWeightedBinaryCrossentropy,
    MicroF1,
    PolyphonicHarmonicOffsetLoss,
    PolyphonicMaskedHarmonicAmplitudeLoss,
    build_polyphonic_model,
    transfer_compatible_weights,
)


class PolyphonicModelTests(unittest.TestCase):
    def test_last_causal_step_selects_latest_frontend_state(self) -> None:
        input_samples = 64
        channels = 2
        model = build_polyphonic_model(
            pitch_classes=2,
            input_samples=input_samples,
            channels=channels,
            tcn_blocks=0,
            dropout=0.0,
            dense_units=4,
            harmonic_count=1,
        )
        frontend_steps = 4
        frontend_channels = channels * 2
        temporal_ramp = np.repeat(
            np.arange(frontend_steps, dtype=np.float32)[None, :, None],
            frontend_channels,
            axis=2,
        )

        selected = model.get_layer("last_causal_step")(temporal_ramp).numpy()

        self.assertEqual(selected.shape, (1, 1, frontend_channels))
        np.testing.assert_array_equal(
            selected,
            np.full((1, 1, frontend_channels), frontend_steps - 1, np.float32),
        )

    def test_model_outputs_independent_pitch_heads(self) -> None:
        model = build_polyphonic_model(
            pitch_classes=3, input_samples=512, channels=8, tcn_blocks=1,
            dense_units=16, harmonic_count=2,
        )
        outputs = model({
            "audio": np.zeros((2, 512, 1), np.float32),
            "time_mask": np.ones((2, 512), np.float32),
        }, training=False)

        self.assertEqual(outputs["frame"].shape, (2, 3))
        self.assertEqual(outputs["onset"].shape, (2, 3))
        self.assertEqual(outputs["harmonic_amplitude"].shape, (2, 3, 2))
        self.assertEqual(outputs["harmonic_offset_cents"].shape, (2, 3, 2))

    def test_dual_stream_model_has_normal_and_compressed_causal_inputs(self) -> None:
        model = build_polyphonic_model(
            pitch_classes=6,
            input_samples=1024,
            normal_window_samples=512,
            compressed_bass_branch=True,
            bass_channels=2,
            bass_dense_units=4,
            bass_pitch_classes=3,
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            harmonic_count=2,
        )
        outputs = model(
            {
                "audio": np.zeros((2, 1024, 1), np.float32),
                "time_mask": np.ones((2, 1024), np.float32),
            },
            training=False,
        )

        self.assertEqual(model.get_layer("normal_recent_audio").output.shape[1], 512)
        self.assertEqual(model.get_layer("bass_input_compress").output.shape[1], 512)
        self.assertEqual(outputs["frame"].shape, (2, 6))
        self.assertEqual(outputs["onset"].shape, (2, 6))

    def test_dual_stream_zero_residual_preserves_transferred_model(self) -> None:
        tf.keras.utils.set_random_seed(456)
        source = build_polyphonic_model(
            pitch_classes=6,
            input_samples=512,
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            harmonic_count=2,
        )
        target = build_polyphonic_model(
            pitch_classes=6,
            input_samples=1024,
            normal_window_samples=512,
            compressed_bass_branch=True,
            bass_channels=2,
            bass_dense_units=4,
            bass_pitch_classes=3,
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            harmonic_count=2,
        )
        recent = np.linspace(-0.5, 0.5, 512, dtype=np.float32)
        source_inputs = {
            "audio": recent[None, :, None],
            "time_mask": np.ones((1, 512), np.float32),
        }
        target_inputs = {
            "audio": np.concatenate(
                [np.zeros(512, np.float32), recent]
            )[None, :, None],
            "time_mask": np.concatenate(
                [np.zeros(512, np.float32), np.ones(512, np.float32)]
            )[None, :],
        }
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "source.keras"
            source.save(checkpoint)
            report = transfer_compatible_weights(target, checkpoint)

        self.assertIn("frame_main_logits", report["transferred"])
        self.assertIn("onset_main_logits", report["transferred"])
        expected = source(source_inputs, training=False)
        actual = target(target_inputs, training=False)
        for name in expected:
            np.testing.assert_allclose(
                expected[name].numpy(),
                actual[name].numpy(),
                rtol=1e-6,
                atol=1e-6,
            )

    def test_dual_stream_requires_double_length_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "twice"):
            build_polyphonic_model(
                input_samples=768,
                normal_window_samples=512,
                compressed_bass_branch=True,
            )

    def test_masked_harmonic_losses_ignore_unlabelled_pitch_classes(self) -> None:
        amplitude_true = tf.constant([[[1.0, 0.5, 1.0, 1.0], [0, 0, 0, 0]]])
        amplitude_pred = tf.constant([[[0.0, 0.5], [100.0, 100.0]]])
        amp_loss = PolyphonicMaskedHarmonicAmplitudeLoss(2)(
            amplitude_true, amplitude_pred
        )
        self.assertAlmostEqual(float(amp_loss), 0.5)

        offset_true = tf.constant([[[10.0, 0.0, 1.0, 0.0, 1.0, 0.0]]])
        offset_pred = tf.constant([[[0.0, 100.0]]])
        offset_loss = PolyphonicHarmonicOffsetLoss(2, 10.0)(
            offset_true, offset_pred
        )
        self.assertAlmostEqual(float(offset_loss), 1.0)

    def test_weighted_bce_and_micro_f1_are_serializable(self) -> None:
        loss = ClassWeightedBinaryCrossentropy([1.0, 2.0])
        value = loss(tf.constant([[1.0, 0.0]]), tf.constant([[0.5, 0.5]]))
        self.assertGreater(float(value), 0.0)
        metric = MicroF1()
        metric.update_state(
            tf.constant([[1.0, 0.0]]), tf.constant([[0.9, 0.1]])
        )
        self.assertAlmostEqual(float(metric.result()), 1.0)

    def test_custom_losses_use_keras3_compatible_reduction(self) -> None:
        losses = (
            ClassWeightedBinaryCrossentropy([1.0, 2.0]),
            PolyphonicMaskedHarmonicAmplitudeLoss(2),
            PolyphonicHarmonicOffsetLoss(2),
        )
        for loss in losses:
            self.assertEqual(loss.reduction, "sum_over_batch_size")
            self.assertEqual(
                loss.get_config()["reduction"], "sum_over_batch_size"
            )

    def test_keras2_archive_rebuild_preserves_predictions(self) -> None:
        tf.keras.utils.set_random_seed(123)
        model = build_polyphonic_model(
            pitch_classes=3,
            input_samples=512,
            channels=8,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=16,
            harmonic_count=2,
            harmonic_offset_scale_cents=20.0,
        )
        inputs = {
            "audio": np.linspace(
                -0.5, 0.5, 512, dtype=np.float32
            )[None, :, None],
            "time_mask": np.ones((1, 512), np.float32),
        }
        expected = model(inputs, training=False)
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "legacy.keras"
            model.save(checkpoint)
            restored = load_polyphonic_checkpoint(checkpoint)
            actual = restored(inputs, training=False)
        for name in expected:
            np.testing.assert_allclose(
                expected[name].numpy(),
                actual[name].numpy(),
                rtol=1e-6,
                atol=1e-6,
            )

    def test_windows_h5_paths_are_normalized_for_linux(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.weights.h5"
            destination = Path(temporary) / "normalized.weights.h5"
            with h5py.File(source, "w") as weights:
                weights.create_dataset(
                    r"layers\conv1d/vars/0",
                    data=np.ones((2, 3), np.float32),
                )
            self.assertTrue(_normalize_h5_paths(source, destination))
            with h5py.File(destination, "r") as weights:
                self.assertIn("layers/conv1d/vars/0", weights)
                np.testing.assert_array_equal(
                    weights["layers/conv1d/vars/0"][()],
                    np.ones((2, 3), np.float32),
                )


if __name__ == "__main__":
    unittest.main()
