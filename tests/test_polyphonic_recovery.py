from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tensorflow as tf

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
