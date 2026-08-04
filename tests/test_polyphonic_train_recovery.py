from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tensorflow as tf

from src.polyphonic.data import PolyphonicEpochPlan
from src.polyphonic.recovery import (
    RecoverySignatures,
    load_latest_recovery_checkpoint,
    save_recovery_checkpoint,
)
from src.polyphonic.train import (
    SerializableTrainingPolicy,
    _freeze_independent_note_backbone,
    _validate_continuation_config,
    _validate_continuation_epoch_plans,
    _persist_or_load_epoch_plans,
    _reset_chunk_randomness,
    _write_model_overview,
    run_recoverable_training,
)


class _ToyPlannedSequence:
    def __init__(
        self,
        *,
        examples: int = 8,
        batch_size: int = 2,
        non_finite: bool = False,
    ) -> None:
        self.batch_size = int(batch_size)
        self.workers = 1
        self.max_queue_size = 1
        self.features = np.linspace(
            -1.0, 1.0, examples * 2, dtype=np.float32
        ).reshape(examples, 2)
        target = (
            self.features[:, :1] * np.float32(0.4)
            - self.features[:, 1:] * np.float32(0.2)
        )
        if non_finite:
            target[:] = np.nan
        self.targets = {"frame": target, "onset": target.copy()}
        self._plan: PolyphonicEpochPlan | None = None

    def __len__(self) -> int:
        return len(self.features) // self.batch_size

    @property
    def plan_sha256(self) -> str:
        if self._plan is None:
            raise RuntimeError("No toy plan installed.")
        return self._plan.sha256

    def install_plan(
        self, plan: PolyphonicEpochPlan
    ) -> PolyphonicEpochPlan:
        self._plan = plan
        return plan

    def __getitem__(self, batch: int):
        if self._plan is None:
            raise RuntimeError("No toy plan installed.")
        start = int(batch) * self.batch_size
        end = start + self.batch_size
        indices = self._plan.order[start:end, 0]
        return (
            self.features[indices],
            {
                name: values[indices]
                for name, values in self.targets.items()
            },
        )


class _ToyBatchSlice(tf.keras.utils.Sequence):
    def __init__(
        self,
        sequence: _ToyPlannedSequence,
        start_batch: int,
        end_batch: int,
    ) -> None:
        super().__init__()
        self.sequence = sequence
        self.start_batch = int(start_batch)
        self.end_batch = int(end_batch)

    def __len__(self) -> int:
        return self.end_batch - self.start_batch

    def __getitem__(self, batch: int):
        return self.sequence[self.start_batch + int(batch)]

    def on_epoch_end(self) -> None:
        pass


class _ToyValidationSequence(tf.keras.utils.Sequence):
    def __init__(self) -> None:
        super().__init__()
        self.features = np.linspace(
            -0.75, 0.75, 8, dtype=np.float32
        ).reshape(4, 2)
        target = (
            self.features[:, :1] * np.float32(0.4)
            - self.features[:, 1:] * np.float32(0.2)
        )
        self.targets = {"frame": target, "onset": target.copy()}

    def __len__(self) -> int:
        return 2

    def __getitem__(self, batch: int):
        start = int(batch) * 2
        end = start + 2
        return (
            self.features[start:end],
            {
                name: values[start:end]
                for name, values in self.targets.items()
            },
        )


def _model() -> tf.keras.Model:
    tf.keras.utils.set_random_seed(123)
    inputs = tf.keras.Input(shape=(2,))
    features = tf.keras.layers.Dropout(0.25, name="dropout")(inputs)
    outputs = {
        "frame": tf.keras.layers.Dense(
            1, use_bias=False, name="frame"
        )(features),
        "onset": tf.keras.layers.Dense(
            1, use_bias=False, name="onset"
        )(features),
    }
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss={"frame": "mse", "onset": "mse"},
        metrics={
            "frame": [
                tf.keras.metrics.BinaryAccuracy(name="micro_f1")
            ]
        },
    )
    return model


def _plans(epochs: int, examples: int = 8) -> list[PolyphonicEpochPlan]:
    result: list[PolyphonicEpochPlan] = []
    for epoch in range(epochs):
        order = np.column_stack([
            np.roll(np.arange(examples, dtype=np.int32), epoch),
            np.zeros(examples, dtype=np.int32),
        ])
        result.append(
            PolyphonicEpochPlan(
                epoch,
                order,
                np.ones(examples, dtype=np.float32),
            )
        )
    return result


def _signatures() -> RecoverySignatures:
    return RecoverySignatures(
        plan_sha256="1" * 64,
        config_sha256="2" * 64,
        manifest_sha256="3" * 64,
        commit="deadbeef",
    )


def _policy() -> SerializableTrainingPolicy:
    return SerializableTrainingPolicy(
        early_stopping_patience=10,
        reduce_lr_patience=1,
        minimum_learning_rate=1e-5,
        reduce_min_delta=100.0,
    )


def _optimizer_values(model: tf.keras.Model) -> list[np.ndarray]:
    variables = model.optimizer.variables
    if callable(variables):
        variables = variables()
    return [np.asarray(variable.numpy()).copy() for variable in variables]


class PolyphonicTrainRecoveryTests(unittest.TestCase):
    def test_auxiliary_policy_monitors_independent_note_loss(self) -> None:
        policy = SerializableTrainingPolicy(
            early_stopping_patience=2,
            reduce_lr_patience=1,
            minimum_learning_rate=1e-5,
            early_monitor_metric="val_independent_note_loss",
            early_monitor_mode="min",
        )
        first = policy.advance(
            0,
            {
                "val_frame_micro_f1": 0.8,
                "val_independent_note_loss": 0.5,
                "val_loss": 0.5,
            },
            1e-3,
        )
        second = policy.advance(
            1,
            {
                "val_frame_micro_f1": 0.8,
                "val_independent_note_loss": 0.4,
                "val_loss": 0.4,
            },
            1e-3,
        )
        self.assertTrue(first.improved)
        self.assertTrue(second.improved)
        restored = SerializableTrainingPolicy.from_dict(policy.as_dict())
        self.assertEqual(restored.as_dict(), policy.as_dict())

    def test_frozen_backbone_requires_complete_weight_transfer(self) -> None:
        inputs = tf.keras.Input((3,), name="input")
        backbone = tf.keras.layers.Dense(4, name="backbone")(inputs)
        outputs = tf.keras.layers.Dense(
            2, name="independent_note"
        )(backbone)
        model = tf.keras.Model(inputs, outputs)
        trainable = _freeze_independent_note_backbone(
            model,
            {
                "transferred": ["backbone"],
                "skipped": ["independent_note"],
            },
        )
        self.assertEqual(trainable, ["independent_note"])
        self.assertFalse(model.get_layer("backbone").trainable)

        fresh = tf.keras.models.clone_model(model)
        with self.assertRaisesRegex(RuntimeError, "backbone"):
            _freeze_independent_note_backbone(
                fresh,
                {
                    "transferred": [],
                    "skipped": ["backbone", "independent_note"],
                },
            )

    def test_model_overview_is_compact_and_does_not_call_summary(self) -> None:
        class DummyModel:
            name = "compact-test"
            layers = [object(), object(), object()]
            inputs = [object(), object()]
            output_names = ["frame", "onset"]

            @staticmethod
            def count_params() -> int:
                return 1234

            @staticmethod
            def summary() -> None:
                raise AssertionError("model.summary() must not be called")

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            overview = _write_model_overview(DummyModel(), run_dir)
            persisted = json.loads(
                (run_dir / "model_overview.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(overview, persisted)
            self.assertEqual(persisted["parameter_count"], 1234)
            self.assertEqual(persisted["layer_count"], 3)
            self.assertEqual(persisted["input_count"], 2)
            self.assertEqual(
                persisted["output_names"], ["frame", "onset"]
            )

    def _run(
        self,
        root: Path,
        *,
        model: tf.keras.Model,
        sequence: _ToyPlannedSequence,
        plans: list[PolyphonicEpochPlan],
        recovery_snapshot=None,
        budget_minutes=None,
    ):
        with patch(
            "src.polyphonic.train.PlanBatchSlice", _ToyBatchSlice
        ):
            return run_recoverable_training(
                model=model,
                train_sequence=sequence,
                validation_sequence=_ToyValidationSequence(),
                epoch_plans=plans,
                run_dir=root,
                signatures=_signatures(),
                policy=_policy(),
                recovery_snapshot=recovery_snapshot,
                chunk_batches=2,
                log_every_batches=100,
                maximum_runtime_minutes=budget_minutes,
                workers=1,
            )

    def test_interrupted_resume_matches_continuous_adam_lr_history_best(
        self,
    ) -> None:
        plans = _plans(2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            continuous_dir = root / "continuous"
            resumed_dir = root / "resumed"

            continuous = self._run(
                continuous_dir,
                model=_model(),
                sequence=_ToyPlannedSequence(),
                plans=plans,
            )
            paused = self._run(
                resumed_dir,
                model=_model(),
                sequence=_ToyPlannedSequence(),
                plans=plans,
                budget_minutes=1e-12,
            )
            self.assertEqual(paused[0], "paused_for_time_budget")
            restored = load_latest_recovery_checkpoint(
                resumed_dir / "recovery",
                signatures=_signatures(),
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            resumed = self._run(
                resumed_dir,
                model=restored.model,
                sequence=_ToyPlannedSequence(),
                plans=plans,
                recovery_snapshot=restored,
            )

            self.assertEqual(continuous[0], "complete")
            self.assertEqual(resumed[0], "complete")
            for expected, actual in zip(
                continuous[1].get_weights(), resumed[1].get_weights()
            ):
                np.testing.assert_array_equal(expected, actual)
            for expected, actual in zip(
                _optimizer_values(continuous[1]),
                _optimizer_values(resumed[1]),
            ):
                np.testing.assert_array_equal(expected, actual)
            self.assertAlmostEqual(
                float(continuous[1].optimizer.learning_rate.numpy()),
                0.005,
                places=8,
            )
            self.assertAlmostEqual(
                float(resumed[1].optimizer.learning_rate.numpy()),
                0.005,
                places=8,
            )
            self.assertEqual(
                (continuous_dir / "history.csv").read_text(
                    encoding="utf-8"
                ),
                (resumed_dir / "history.csv").read_text(
                    encoding="utf-8"
                ),
            )
            continuous_best = tf.keras.models.load_model(
                continuous_dir / "best.keras", compile=True
            )
            resumed_best = tf.keras.models.load_model(
                resumed_dir / "best.keras", compile=True
            )
            for expected, actual in zip(
                continuous_best.get_weights(), resumed_best.get_weights()
            ):
                np.testing.assert_array_equal(expected, actual)
            self.assertEqual(
                continuous[2].state["callback_state"]["policy"],
                resumed[2].state["callback_state"]["policy"],
            )

    def test_budget_after_last_batch_defers_epoch_transaction(self) -> None:
        plans = _plans(1, examples=4)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paused = self._run(
                root,
                model=_model(),
                sequence=_ToyPlannedSequence(examples=4),
                plans=plans,
                budget_minutes=1e-12,
            )
            self.assertEqual(paused[0], "paused_for_time_budget")
            self.assertEqual(paused[2].state["epoch"], 0)
            self.assertEqual(paused[2].state["next_batch"], 2)
            self.assertFalse((root / "history.csv").exists())
            self.assertFalse((root / "last.keras").exists())
            self.assertFalse((root / "best.keras").exists())

            restored = load_latest_recovery_checkpoint(
                root / "recovery", signatures=_signatures()
            )
            assert restored is not None
            complete = self._run(
                root,
                model=restored.model,
                sequence=_ToyPlannedSequence(examples=4),
                plans=plans,
                recovery_snapshot=restored,
            )
            self.assertEqual(complete[0], "complete")
            with (root / "history.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                self.assertEqual(len(list(handle)), 2)
            self.assertTrue((root / "epochs" / "epoch-01.keras").is_file())
            self.assertTrue((root / "last.keras").is_file())
            self.assertTrue((root / "best.keras").is_file())
            self.assertTrue((root / "final.keras").is_file())

    def test_corrupt_newest_chunk_replays_from_previous_slot(self) -> None:
        plans = _plans(1, examples=4)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paused = self._run(
                root,
                model=_model(),
                sequence=_ToyPlannedSequence(examples=4),
                plans=plans,
                budget_minutes=1e-12,
            )
            Path(paused[2].model_path).write_bytes(b"corrupt")
            restored = load_latest_recovery_checkpoint(
                root / "recovery", signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.state["next_batch"], 0)
            complete = self._run(
                root,
                model=restored.model,
                sequence=_ToyPlannedSequence(examples=4),
                plans=plans,
                recovery_snapshot=restored,
            )
            self.assertEqual(complete[0], "complete")
            self.assertEqual(complete[2].state["epoch"], 1)

    def test_nan_does_not_replace_initial_valid_recovery(self) -> None:
        plans = _plans(1, examples=4)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FloatingPointError):
                self._run(
                    root,
                    model=_model(),
                    sequence=_ToyPlannedSequence(
                        examples=4, non_finite=True
                    ),
                    plans=plans,
                )
            restored = load_latest_recovery_checkpoint(
                root / "recovery", signatures=_signatures()
            )
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.state["generation"], 1)
            self.assertEqual(restored.state["epoch"], 0)
            self.assertEqual(restored.state["next_batch"], 0)
            status = json.loads(
                (root / "recovery" / "recovery-a.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["optimizer_iterations"], 0)

    def test_keras3_chunk_seed_does_not_retrace_train_function(self) -> None:
        class DummyModel:
            def __init__(self) -> None:
                self.train_function = object()
                self.make_calls = 0

            def _flatten_layers(self, **kwargs):
                return []

            def make_train_function(self, **kwargs):
                self.make_calls += 1

        model = DummyModel()
        original_train_function = model.train_function
        with patch(
            "src.polyphonic.train.keras.__version__", "3.12.0"
        ):
            _reset_chunk_randomness(model, 1234)
        self.assertIs(model.train_function, original_train_function)
        self.assertEqual(model.make_calls, 0)

    def test_epoch_transaction_replays_idempotently_after_boundary_crash(
        self,
    ) -> None:
        plans = _plans(1, examples=4)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            injected = {"done": False}

            def crash_before_boundary_commit(*args, **kwargs):
                if (
                    kwargs.get("epoch") == 1
                    and kwargs.get("next_batch") == 0
                    and not injected["done"]
                ):
                    injected["done"] = True
                    raise OSError("simulated boundary interruption")
                return save_recovery_checkpoint(*args, **kwargs)

            with patch(
                "src.polyphonic.train.save_recovery_checkpoint",
                side_effect=crash_before_boundary_commit,
            ):
                with self.assertRaisesRegex(
                    OSError, "boundary interruption"
                ):
                    self._run(
                        root,
                        model=_model(),
                        sequence=_ToyPlannedSequence(examples=4),
                        plans=plans,
                    )
            self.assertTrue(
                (root / "epoch_transactions" / "epoch-01.json").is_file()
            )
            self.assertTrue((root / "history.csv").is_file())

            restored = load_latest_recovery_checkpoint(
                root / "recovery", signatures=_signatures()
            )
            assert restored is not None
            self.assertEqual(restored.state["epoch"], 0)
            self.assertEqual(restored.state["next_batch"], 2)
            complete = self._run(
                root,
                model=restored.model,
                sequence=_ToyPlannedSequence(examples=4),
                plans=plans,
                recovery_snapshot=restored,
            )
            self.assertEqual(complete[0], "complete")
            with (root / "history.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                self.assertEqual(len(list(handle)), 2)
            policy = complete[2].state["callback_state"]["policy"]
            self.assertEqual(policy["completed_epochs"], 1)

    def test_all_epoch_plans_are_persisted_once_before_training(self) -> None:
        plans = _plans(3)

        class PlanProvider:
            def plan_for_epoch(self, epoch: int):
                return plans[int(epoch)]

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "epoch_plans.npz"
            loaded, digest = _persist_or_load_epoch_plans(
                path, PlanProvider(), len(plans)
            )
            self.assertTrue(path.is_file())
            self.assertEqual(
                [plan.sha256 for plan in loaded],
                [plan.sha256 for plan in plans],
            )
            self.assertTrue(all(not plan.order.flags.writeable for plan in loaded))
            first_bytes = path.read_bytes()
            loaded_again, digest_again = _persist_or_load_epoch_plans(
                path, PlanProvider(), len(plans)
            )
            self.assertEqual(path.read_bytes(), first_bytes)
            self.assertEqual(digest_again, digest)
            self.assertEqual(
                [plan.sha256 for plan in loaded_again],
                [plan.sha256 for plan in plans],
            )

    def test_continuation_config_only_allows_larger_epoch_target(self) -> None:
        source = {
            "dataset": {"manifest": "manifest.csv"},
            "train": {"epochs": 8, "batch_size": 64},
        }
        target = {
            "dataset": {"manifest": "manifest.csv"},
            "train": {"epochs": 12, "batch_size": 64},
        }
        self.assertEqual(_validate_continuation_config(source, target), 8)
        target["train"]["batch_size"] = 32
        with self.assertRaisesRegex(ValueError, "only by train.epochs"):
            _validate_continuation_config(source, target)

    def test_continuation_epoch_plans_retain_completed_prefix(self) -> None:
        source = _plans(2)
        target = _plans(3)
        _validate_continuation_epoch_plans(source, target, 2)
        changed = _plans(3)
        changed[1] = PolyphonicEpochPlan(
            1,
            np.flip(changed[1].order, axis=0).copy(),
            changed[1].augmentation_gains.copy(),
        )
        with self.assertRaisesRegex(ValueError, "changed completed"):
            _validate_continuation_epoch_plans(source, changed, 2)


if __name__ == "__main__":
    unittest.main()
