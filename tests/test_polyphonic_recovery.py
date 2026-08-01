from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.polyphonic.model import (
    ClassWeightedBinaryCrossentropy,
    PolyphonicHarmonicOffsetLoss,
    PolyphonicMaskedHarmonicAmplitudeLoss,
    PolyphonicMaskedHarmonicPresenceBrier,
    PolyphonicMaskedHarmonicPresenceF1,
    PolyphonicMaskedHarmonicPresenceLoss,
    build_polyphonic_model,
)
from src.polyphonic.recovery import (
    RecoverySignatureMismatch,
    RecoverySignatures,
    file_sha256,
    load_latest_recovery_checkpoint,
    save_recovery_checkpoint,
)


def _signatures(*, commit: str = "01234567") -> RecoverySignatures:
    return RecoverySignatures(
        plan_sha256="1" * 64,
        config_sha256="2" * 64,
        manifest_sha256="3" * 64,
        commit=commit,
    )


def _model() -> tf.keras.Model:
    tf.keras.utils.set_random_seed(7)
    inputs = tf.keras.Input(shape=(2,))
    outputs = tf.keras.layers.Dense(1)(inputs)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss="mse",
    )
    return model


def _train_batch(model: tf.keras.Model) -> None:
    features = np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    targets = np.asarray([[1.0], [0.0]], dtype=np.float32)
    model.train_on_batch(features, targets)


class PolyphonicRecoveryTests(unittest.TestCase):
    def test_presence_head_loss_metrics_and_optimizer_resume(self) -> None:
        model = build_polyphonic_model(
            pitch_classes=2,
            input_samples=512,
            channels=4,
            tcn_blocks=1,
            dropout=0.0,
            dense_units=8,
            harmonic_count=1,
            harmonic_presence_head=True,
        )
        model.compile(
            optimizer=tf.keras.optimizers.Adam(1e-4),
            loss={
                "frame": ClassWeightedBinaryCrossentropy([1.0, 1.0]),
                "onset": ClassWeightedBinaryCrossentropy([1.0, 1.0]),
                "harmonic_amplitude": (
                    PolyphonicMaskedHarmonicAmplitudeLoss(
                        1, normalize_by_supervised_count=True
                    )
                ),
                "harmonic_offset_cents": PolyphonicHarmonicOffsetLoss(
                    1, normalize_by_supervised_count=True
                ),
                "harmonic_presence": PolyphonicMaskedHarmonicPresenceLoss(1),
            },
            metrics={
                "harmonic_presence": [
                    PolyphonicMaskedHarmonicPresenceF1(1),
                    PolyphonicMaskedHarmonicPresenceBrier(1),
                ]
            },
        )
        inputs = {
            "audio": np.zeros((1, 512, 1), np.float32),
            "time_mask": np.ones((1, 512), np.float32),
        }
        targets = {
            "frame": np.zeros((1, 2), np.float32),
            "onset": np.zeros((1, 2), np.float32),
            "harmonic_amplitude": np.zeros((1, 2, 2), np.float32),
            "harmonic_offset_cents": np.zeros((1, 2, 3), np.float32),
            "harmonic_presence": np.asarray(
                [[[1.0, 1.0], [0.0, 1.0]]], np.float32
            ),
        }
        model.train_on_batch(inputs, targets)
        original_variables = [
            np.asarray(variable.numpy()).copy()
            for variable in model.optimizer.variables()
        ]
        with tempfile.TemporaryDirectory() as temporary:
            save_recovery_checkpoint(
                temporary,
                model,
                epoch=0,
                next_batch=1,
                signatures=_signatures(),
            )
            restored = load_latest_recovery_checkpoint(
                temporary, signatures=_signatures()
            )
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(
            int(restored.model.optimizer.iterations.numpy()), 1
        )
        restored_variables = [
            np.asarray(variable.numpy())
            for variable in restored.model.optimizer.variables()
        ]
        self.assertEqual(len(restored_variables), len(original_variables))
        for expected, actual in zip(original_variables, restored_variables):
            np.testing.assert_array_equal(expected, actual)

    def test_alternates_a_b_and_loads_latest_compiled_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = _model()
            _train_batch(model)
            first = save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=1,
                signatures=_signatures(),
                callback_state={"best": 0.8, "wait": 1},
            )
            _train_batch(model)
            second = save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=2,
                signatures=_signatures(),
                callback_state={"best": 0.7, "wait": 0},
            )

            self.assertEqual((first.slot, second.slot), ("a", "b"))
            self.assertEqual(first.state["generation"], 1)
            self.assertEqual(second.state["generation"], 2)
            self.assertTrue((root / "recovery-a.keras").is_file())
            self.assertTrue((root / "recovery-b.keras").is_file())
            self.assertFalse(first.state["locked_test_used"])
            self.assertEqual(
                first.state["model_sha256"], file_sha256(first.model_path)
            )

            restored = load_latest_recovery_checkpoint(
                root, signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.state["generation"], 2)
            self.assertEqual(restored.state["next_batch"], 2)
            self.assertIsNotNone(restored.model.optimizer)
            self.assertEqual(
                int(restored.model.optimizer.iterations.numpy()), 2
            )

    def test_corrupt_newest_model_falls_back_to_previous_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = _model()
            _train_batch(model)
            save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=1,
                signatures=_signatures(),
            )
            _train_batch(model)
            latest = save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=2,
                signatures=_signatures(),
            )
            latest.model_path.write_bytes(b"corrupt")

            restored = load_latest_recovery_checkpoint(
                root, signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.state["generation"], 1)
            self.assertEqual(restored.state["next_batch"], 1)
            self.assertEqual(
                int(restored.model.optimizer.iterations.numpy()), 1
            )

    def test_incompatible_training_signature_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = _model()
            _train_batch(model)
            save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=1,
                signatures=_signatures(),
            )

            with self.assertRaisesRegex(
                RecoverySignatureMismatch, "commit"
            ):
                load_latest_recovery_checkpoint(
                    root, signatures=_signatures(commit="89abcdef")
                )
            with self.assertRaises(RecoverySignatureMismatch):
                save_recovery_checkpoint(
                    root,
                    model,
                    epoch=0,
                    next_batch=2,
                    signatures=_signatures(commit="89abcdef"),
                )

    def test_optimizer_state_and_iterations_continue_after_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = _model()
            for _ in range(3):
                _train_batch(model)
            saved = save_recovery_checkpoint(
                root,
                model,
                epoch=1,
                next_batch=3,
                signatures=_signatures(),
                callback_state={"early_stopping": {"best": 0.5, "wait": 2}},
            )

            state = json.loads(saved.state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["optimizer_iterations"], 3)
            self.assertAlmostEqual(state["learning_rate"], 0.01, places=6)
            self.assertEqual(
                state["callback_state"]["early_stopping"]["wait"], 2
            )

            restored = load_latest_recovery_checkpoint(
                root, signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(
                int(restored.model.optimizer.iterations.numpy()), 3
            )
            _train_batch(restored.model)
            self.assertEqual(
                int(restored.model.optimizer.iterations.numpy()), 4
            )

    def test_learning_rate_mismatch_falls_back_to_previous_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = _model()
            _train_batch(model)
            first = save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=1,
                signatures=_signatures(),
            )
            _train_batch(model)
            latest = save_recovery_checkpoint(
                root,
                model,
                epoch=0,
                next_batch=2,
                signatures=_signatures(),
            )
            latest_state = json.loads(
                latest.state_path.read_text(encoding="utf-8")
            )
            latest_state["learning_rate"] = 0.5
            latest.state_path.write_text(
                json.dumps(latest_state),
                encoding="utf-8",
            )

            restored = load_latest_recovery_checkpoint(
                root, signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.state["generation"], 1)
            self.assertEqual(restored.state["next_batch"], 1)
            self.assertEqual(restored.model_path, first.model_path)


if __name__ == "__main__":
    unittest.main()
