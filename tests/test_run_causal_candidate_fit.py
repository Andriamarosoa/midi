from __future__ import annotations

import inspect
import os
from pathlib import Path
from dataclasses import replace
import tempfile
import unittest
from unittest.mock import patch

from src.polyphonic.causal_candidate_fit import (
    CandidateFitPreflight,
    CandidateFitRow,
    CandidateFitExecutionSpec,
    FEATURE_DIMENSION,
    V1_EXECUTION_SPEC,
    build_v1_logistic_model,
    canonical_candidate_order,
)
from src.polyphonic.run_causal_candidate_fit import (
    FIT_EXECUTE_ENV,
    PartitionArrays,
    _as_training_arrays,
    _fit_model_v1,
    _make_callbacks,
    _standardizer_json,
    _training_history_json,
    _weight_evidence,
    build_partition_arrays,
    run_v1_fit,
)


_DIGEST = "a" * 64


def _row(
    *,
    partition: str,
    dataset_id: str,
    target: int,
    index: int,
) -> CandidateFitRow:
    return CandidateFitRow(
        event_id=f"{partition}-{dataset_id}-{target}-{index}",
        partition=partition,
        dataset_id=dataset_id,
        source_id=f"source-{partition}-{dataset_id}-{target}",
        group_id=f"group-{partition}-{dataset_id}-{target}",
        capture_id=f"capture-{index}",
        leakage_group_key=f"leak-{partition}-{dataset_id}-{target}",
        target=target,
        frame_probability=0.1 + 0.05 * target + 0.01 * index,
        onset_probability=0.2 + 0.05 * target + 0.01 * index,
        candidate_score=0.3 + target + 0.01 * index,
        candidate_reason="model_onset" if target else "frame_fallback",
        harmonic_support=0.4 + 0.05 * target + 0.01 * index,
        audio_onset_available=True,
        audio_onset_recent=bool(target),
        active_polyphony=1 + target + index,
    )


def _preflight() -> CandidateFitPreflight:
    rows = [
        _row(
            partition=partition,
            dataset_id=dataset_id,
            target=target,
            index=index,
        )
        for partition in ("fit", "dev", "calibration")
        for index, (dataset_id, target) in enumerate((
            ("gaps_poly_mix", 0),
            ("gaps_poly_mix", 1),
            ("guitar_techs_poly_directinput", 0),
            ("guitar_techs_poly_directinput", 1),
            ("guitarset_poly_mix", 0),
            ("guitarset_poly_mix", 1),
        ))
    ]
    # This extra dev row shares its leakage group with the GAPS negative row,
    # making the partition-local weight vector observably differ from fit.
    rows.append(_row(
        partition="dev",
        dataset_id="gaps_poly_mix",
        target=0,
        index=99,
    ))
    rows[-1] = replace(rows[-1], leakage_group_key="leak-dev-gaps_poly_mix-0")
    return CandidateFitPreflight(
        rows=canonical_candidate_order(rows),
        candidate_events_sha256=_DIGEST,
        mining_report_sha256=_DIGEST,
        mining_protocol_sha256=_DIGEST,
    )


class RunCausalCandidateFitTests(unittest.TestCase):
    def test_runner_builds_local_weights_and_persists_fit_standardizer(self) -> None:
        standardizer, fit, dev, calibration = build_partition_arrays(_preflight())
        for partition in (fit, dev, calibration):
            self.assertIsInstance(partition, PartitionArrays)
            expected_rows = 7 if partition.partition == "dev" else 6
            self.assertEqual(len(partition.features), expected_rows)
            self.assertTrue(all(len(vector) == FEATURE_DIMENSION for vector in partition.features))
            self.assertAlmostEqual(sum(partition.weights), len(partition.rows))
            self.assertEqual(set(partition.targets), {0, 1})
        self.assertNotEqual(fit.weights, dev.weights)
        payload = _standardizer_json(standardizer)
        self.assertEqual(payload["causal_features"], [
            "frame_probability",
            "onset_probability",
            "candidate_score",
            "candidate_reason",
            "harmonic_support",
            "audio_onset_available",
            "audio_onset_recent",
            "active_polyphony",
        ])
        self.assertEqual(len(payload["mean"]), 5)
        self.assertEqual(len(payload["scale"]), 5)

    def test_runner_rejects_without_explicit_execution_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.dict(os.environ, {FIT_EXECUTE_ENV: ""}, clear=False):
                with self.assertRaisesRegex(RuntimeError, "DECODER_CANDIDATE_FIT_EXECUTE"):
                    run_v1_fit(
                        repository_root=root,
                        expected_runner_commit="b" * 40,
                        candidate_events_path=root / "missing-events.jsonl",
                        mining_report_path=root / "missing-report.json",
                        mining_protocol_path=root / "missing-protocol.json",
                        output_dir=root / "output",
                    )

    def test_runner_has_no_tunable_weights_or_validation_data_argument(self) -> None:
        signature = inspect.signature(run_v1_fit)
        self.assertEqual(
            tuple(signature.parameters),
            (
                "repository_root",
                "expected_runner_commit",
                "candidate_events_path",
                "mining_report_path",
                "mining_protocol_path",
                "output_dir",
            ),
        )
        source = inspect.getsource(run_v1_fit)
        fit_source = inspect.getsource(_fit_model_v1)
        self.assertIn("_fit_model_v1(", source)
        self.assertIn("sample_weight=w_fit", fit_source)
        self.assertIn("shuffle=execution_spec.shuffle", fit_source)
        self.assertNotIn("validation_data", source)
        self.assertIn("if dev_signal.passed", source)
        self.assertIs(V1_EXECUTION_SPEC.shuffle, False)

    def test_dev_callback_is_inference_only_and_restores_best_weights(self) -> None:
        class FakeCallback:
            pass

        class FakeCallbacks:
            Callback = FakeCallback

        class FakeKeras:
            callbacks = FakeCallbacks

        class FakeTensorFlow:
            keras = FakeKeras

        _, _, dev, _ = build_partition_arrays(_preflight())
        monitor = _make_callbacks(FakeTensorFlow, dev)
        import numpy as np

        class FakeModel:
            stop_training = False

            def __init__(self) -> None:
                self.restored = False

            def __call__(self, inputs, training: bool = False):
                self.assertFalse(training)
                return np.asarray([
                    [0.9 if row.target else 0.1] for row in dev.rows
                ], dtype=np.float32)

            def get_weights(self):
                return [np.asarray([1.0], dtype=np.float32)]

            def set_weights(self, weights) -> None:
                self.restored = True

        model = FakeModel()
        model.assertFalse = self.assertFalse
        monitor.model = model
        logs: dict[str, float] = {}
        monitor.on_train_begin()
        monitor.on_epoch_end(0, logs)
        monitor.on_train_end()
        self.assertEqual(monitor.best_epoch, 1)
        self.assertIn("v1_dev_weighted_bce", logs)
        self.assertTrue(model.restored)

    def test_synthetic_keras_fit_materializes_single_dense_input_and_report_evidence(self) -> None:
        """Exercise one real Keras epoch without opening project artifacts.

        This is deliberately below ``run_v1_fit``: that public entry point
        correctly rejects synthetic paths because it is bound to the one
        sealed V3 artifact.  The private training boundary is the same one
        used by that entry point, and this test catches Keras nested-tuple
        input ambiguity before the unique scientific fit.
        """

        try:
            import numpy as np
            import tensorflow as tf
        except ImportError:
            self.skipTest("TensorFlow is unavailable in this test environment.")
        try:
            tf.config.set_visible_devices([], "GPU")
        except RuntimeError:
            self.skipTest("TensorFlow GPU visibility was initialized by this environment.")
        _, fit, dev, calibration = build_partition_arrays(_preflight())
        x_fit, y_fit, w_fit = _as_training_arrays(fit)
        self.assertIsInstance(x_fit, np.ndarray)
        self.assertEqual(x_fit.dtype, np.float32)
        self.assertEqual(x_fit.shape, (len(fit.rows), FEATURE_DIMENSION))
        self.assertEqual(y_fit.dtype, np.float32)
        self.assertEqual(w_fit.dtype, np.float32)
        model = build_v1_logistic_model(tf, seed=47)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
            loss=tf.keras.losses.BinaryCrossentropy(),
        )
        synthetic_spec = CandidateFitExecutionSpec(
            seed=47,
            batch_size=2,
            learning_rate=0.01,
            maximum_epochs=1,
            patience=1,
            min_delta=1e-4,
            shuffle=False,
        )
        monitor, losses, duration = _fit_model_v1(
            model,
            tf,
            fit,
            dev,
            execution_spec=synthetic_spec,
            wall_timeout_seconds=60.0,
        )
        self.assertGreaterEqual(duration, 0.0)
        self.assertEqual(len(losses), 1)
        self.assertEqual(monitor.best_epoch, 1)
        history = _training_history_json(losses, monitor)
        self.assertEqual(len(history), 1)
        self.assertEqual(
            set(history[0]),
            {
                "epoch",
                "keras_fit_loss",
                "dev_weighted_bce",
                "dev_weighted_brier",
                "dev_auc_by_family",
            },
        )
        evidence = _weight_evidence((fit, dev, calibration))
        self.assertEqual(len(evidence), 18)
        self.assertEqual(
            set(evidence[0]),
            {
                "partition",
                "family",
                "target",
                "group_count",
                "row_count",
                "total_weight",
                "minimum_row_weight",
                "maximum_row_weight",
                "groups",
            },
        )


if __name__ == "__main__":
    unittest.main()
