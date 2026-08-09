from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.polyphonic.causal_candidate_fit import (
    BOOLEAN_FEATURES,
    CAUSAL_FEATURES,
    CandidateFitContract,
    CandidateFitRow,
    ENCODED_FEATURES,
    FEATURE_DIMENSION,
    FAMILIES,
    FitStandardizer,
    NUMERIC_FEATURES,
    ONE_HOT_FEATURES,
    V1_EXECUTION_SPEC,
    assess_dev_signal,
    build_v1_logistic_model,
    canonical_candidate_order,
    choose_calibration_threshold,
    fit_standardizer,
    group_balanced_weights,
    preflight_sealed_candidate_artifact,
    transform_rows,
    verify_saved_model_parity,
)


_DIGEST = "a" * 64
_COMMIT = "b" * 40


def _payload(
    *,
    partition: str,
    dataset_id: str,
    target: int,
    event_id: str,
    group: str,
    reason: str = "model_onset",
    offset: float = 0.0,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "partition": partition,
        "dataset_id": dataset_id,
        "source_id": f"source-{event_id}",
        "group_id": f"group-{group}",
        "capture_id": "capture",
        "leakage_group_key": group,
        "causal_noteon_target": target,
        "frame_probability": 0.15 + 0.1 * target + offset,
        "onset_probability": 0.25 + 0.1 * target + offset,
        "candidate_score": 0.5 + target + offset,
        "candidate_reason": reason,
        "harmonic_support": 0.35 + 0.1 * target + offset,
        "audio_onset_available": True,
        "audio_onset_recent": bool(target),
        "active_polyphony": 1 + target,
        "gate_eligible": True,
        "post_gate_selected": True,
        "emitted_noteon": True,
    }


def _six_cells(partition: str) -> list[CandidateFitRow]:
    values: list[CandidateFitRow] = []
    datasets = (
        "gaps_poly_mix",
        "guitar_techs_poly_directinput",
        "guitarset_poly_mix",
    )
    for dataset_index, dataset_id in enumerate(datasets):
        for target in (0, 1):
            values.append(CandidateFitRow.from_json(_payload(
                partition=partition,
                dataset_id=dataset_id,
                target=target,
                event_id=f"{partition}-{dataset_index}-{target}",
                group=f"{partition}-group-{dataset_index}-{target}",
                reason=(
                    "model_onset" if target
                    else "frame_fallback"
                ),
                offset=0.01 * (dataset_index * 2 + target),
            )))
    return values


class CausalCandidateFitTests(unittest.TestCase):
    def test_cpu_configuration_masks_any_tensorflow_gpu_in_a_fresh_process(self) -> None:
        code = (
            "from src.polyphonic.causal_candidate_fit import "
            "configure_deterministic_cpu_tensorflow; "
            "tf = configure_deterministic_cpu_tensorflow(); "
            "assert not tf.config.list_logical_devices('GPU')"
        )
        environment = dict(os.environ)
        environment["MIDI_FORCE_CPU"] = "1"
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_projection_is_exactly_twelve_pre_gate_values(self) -> None:
        self.assertEqual(CAUSAL_FEATURES, (
            "frame_probability",
            "onset_probability",
            "candidate_score",
            "candidate_reason",
            "harmonic_support",
            "audio_onset_available",
            "audio_onset_recent",
            "active_polyphony",
        ))
        self.assertEqual(len(NUMERIC_FEATURES), 5)
        self.assertEqual(len(BOOLEAN_FEATURES), 2)
        self.assertEqual(len(ONE_HOT_FEATURES), 5)
        self.assertEqual(len(ENCODED_FEATURES), FEATURE_DIMENSION)
        rows = _six_cells("fit")
        standardizer = fit_standardizer(rows)
        vector = standardizer.transform(rows[0])
        self.assertEqual(len(vector), 12)
        self.assertEqual(vector[5:7], (1.0, 0.0))
        self.assertEqual(vector[7:], (0.0, 0.0, 1.0, 0.0, 0.0))

    def test_execution_spec_freezes_the_reproducible_non_shuffled_budget(self) -> None:
        self.assertEqual(V1_EXECUTION_SPEC.seed, 47)
        self.assertEqual(V1_EXECUTION_SPEC.batch_size, 64)
        self.assertEqual(V1_EXECUTION_SPEC.learning_rate, 0.01)
        self.assertEqual(V1_EXECUTION_SPEC.maximum_epochs, 40)
        self.assertEqual(V1_EXECUTION_SPEC.patience, 5)
        self.assertEqual(V1_EXECUTION_SPEC.min_delta, 1e-4)
        self.assertIs(V1_EXECUTION_SPEC.shuffle, False)

    def test_standardizer_is_fit_only_and_rejects_zero_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "fit rows only"):
            fit_standardizer(_six_cells("dev"))
        row = CandidateFitRow.from_json(_payload(
            partition="fit",
            dataset_id="gaps_poly_mix",
            target=0,
            event_id="constant",
            group="constant",
        ))
        with self.assertRaisesRegex(ValueError, "scales"):
            fit_standardizer((row, row))

    def test_canonical_order_rejects_duplicate_event_ids(self) -> None:
        first, second = _six_cells("fit")[:2]
        duplicate = CandidateFitRow(
            event_id=first.event_id,
            partition=second.partition,
            dataset_id=second.dataset_id,
            source_id=second.source_id,
            group_id=second.group_id,
            capture_id=second.capture_id,
            leakage_group_key=second.leakage_group_key,
            target=second.target,
            frame_probability=second.frame_probability,
            onset_probability=second.onset_probability,
            candidate_score=second.candidate_score,
            candidate_reason=second.candidate_reason,
            harmonic_support=second.harmonic_support,
            audio_onset_available=second.audio_onset_available,
            audio_onset_recent=second.audio_onset_recent,
            active_polyphony=second.active_polyphony,
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            canonical_candidate_order((first, duplicate))

    def test_group_weights_equalize_cells_and_pair_direct_mic(self) -> None:
        rows = _six_cells("fit")
        rows.append(CandidateFitRow.from_json(_payload(
            partition="fit",
            dataset_id="guitar_techs_poly_micamp",
            target=0,
            event_id="fit-gtech-mic-negative",
            group="fit-group-1-0",
            reason="legacy",
            offset=0.08,
        )))
        weights = group_balanced_weights(rows)
        self.assertAlmostEqual(sum(weights), len(rows))
        totals: dict[tuple[str, int], float] = {}
        for row, weight in zip(rows, weights):
            key = (row.family, row.target)
            totals[key] = totals.get(key, 0.0) + weight
        self.assertEqual(set(totals), {
            (family, target) for family in FAMILIES for target in (0, 1)
        })
        for value in totals.values():
            self.assertAlmostEqual(value, len(rows) / 6.0)
        direct = next(
            weight for row, weight in zip(rows, weights)
            if row.event_id == "fit-1-0"
        )
        mic = next(
            weight for row, weight in zip(rows, weights)
            if row.event_id == "fit-gtech-mic-negative"
        )
        self.assertAlmostEqual(direct, mic)

    def test_dev_and_calibration_use_partition_local_weights(self) -> None:
        dev = _six_cells("dev")
        probabilities = tuple(0.1 if row.target == 0 else 0.9 for row in dev)
        signal = assess_dev_signal(dev, probabilities)
        self.assertTrue(signal.passed)
        self.assertLess(signal.weighted_bce, 0.69314718056)
        self.assertLess(signal.weighted_brier, 0.25)
        self.assertEqual(set(signal.roc_auc_by_family), set(FAMILIES))
        self.assertTrue(all(value == 1.0 for value in signal.roc_auc_by_family.values()))

        calibration = _six_cells("calibration")
        decision = choose_calibration_threshold(
            calibration,
            tuple(0.1 if row.target == 0 else 0.9 for row in calibration),
        )
        self.assertAlmostEqual(decision.threshold, 0.11)
        self.assertLess(decision.weighted_brier, 0.25)
        self.assertEqual(len(decision.rows), 99)

    def test_preflight_rehashes_rows_report_and_partition_counts(self) -> None:
        rows = [
            _payload(
                partition=partition,
                dataset_id=dataset,
                target=target,
                event_id=f"{partition}-{dataset}-{target}",
                group=f"{partition}-{dataset}-{target}",
                offset=0.01 * index,
            )
            for partition in ("fit", "dev", "calibration")
            for index, (dataset, target) in enumerate((
                ("gaps_poly_mix", 0),
                ("gaps_poly_mix", 1),
                ("guitar_techs_poly_directinput", 0),
                ("guitar_techs_poly_directinput", 1),
                ("guitarset_poly_mix", 0),
                ("guitarset_poly_mix", 1),
            ))
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events_path = root / "candidate_events.jsonl"
            report_path = root / "mining_report.json"
            protocol_path = root / "sealed_v3_protocol.json"
            events_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in reversed(rows))
                + "\n",
                encoding="utf-8",
            )
            report_path.write_text(json.dumps({
                "schema_version": 1,
                "purpose": "synthetic_train_only_mining",
                "status": "complete_non_authorizing",
                "locked_test_used": False,
                "fit_authorized": False,
                "implementation_commit": _COMMIT,
                "protocol": {"manifest_sha256": _DIGEST},
            }, sort_keys=True), encoding="utf-8")
            protocol_path.write_text(
                '{"schema_version":3,"purpose":"synthetic_train_only_mining"}\n',
                encoding="utf-8",
            )
            contract = CandidateFitContract(
                candidate_events_sha256=hashlib.sha256(events_path.read_bytes()).hexdigest(),
                mining_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                mining_protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                implementation_commit=_COMMIT,
                mining_purpose="synthetic_train_only_mining",
                partition_counts={
                    "fit": (3, 3),
                    "dev": (3, 3),
                    "calibration": (3, 3),
                },
                required_protocol_digests={"manifest_sha256": _DIGEST},
            )
            result = preflight_sealed_candidate_artifact(
                events_path, report_path, protocol_path, contract
            )
            self.assertEqual(len(result.rows), 18)
            self.assertEqual(
                [row.event_id for row in result.rows],
                sorted(
                    row.event_id for row in result.rows
                    if row.partition == "fit"
                )
                + sorted(
                    row.event_id for row in result.rows
                    if row.partition == "dev"
                )
                + sorted(
                    row.event_id for row in result.rows
                    if row.partition == "calibration"
                ),
            )
            events_path.write_text(events_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                preflight_sealed_candidate_artifact(
                    events_path, report_path, protocol_path, contract
                )

    def test_preflight_rejects_a_changed_mining_protocol_before_rows(self) -> None:
        rows = [
            _payload(
                partition=partition,
                dataset_id=dataset,
                target=target,
                event_id=f"{partition}-{dataset}-{target}",
                group=f"{partition}-{dataset}-{target}",
            )
            for partition in ("fit", "dev", "calibration")
            for dataset, target in (
                ("gaps_poly_mix", 0),
                ("gaps_poly_mix", 1),
                ("guitar_techs_poly_directinput", 0),
                ("guitar_techs_poly_directinput", 1),
                ("guitarset_poly_mix", 0),
                ("guitarset_poly_mix", 1),
            )
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events_path = root / "candidate_events.jsonl"
            report_path = root / "mining_report.json"
            protocol_path = root / "sealed_v3_protocol.json"
            events_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
                encoding="utf-8",
            )
            report_path.write_text(json.dumps({
                "schema_version": 1,
                "purpose": "synthetic_train_only_mining",
                "status": "complete_non_authorizing",
                "locked_test_used": False,
                "fit_authorized": False,
                "implementation_commit": _COMMIT,
                "protocol": {"manifest_sha256": _DIGEST},
            }, sort_keys=True), encoding="utf-8")
            protocol_path.write_text('{"version":3}\n', encoding="utf-8")
            contract = CandidateFitContract(
                candidate_events_sha256=hashlib.sha256(events_path.read_bytes()).hexdigest(),
                mining_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                mining_protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                implementation_commit=_COMMIT,
                mining_purpose="synthetic_train_only_mining",
                partition_counts={
                    "fit": (3, 3),
                    "dev": (3, 3),
                    "calibration": (3, 3),
                },
                required_protocol_digests={"manifest_sha256": _DIGEST},
            )
            protocol_path.write_text('{"version":4}\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "mining protocol SHA-256"):
                preflight_sealed_candidate_artifact(
                    events_path, report_path, protocol_path, contract
                )

    def test_candidate_row_rejects_validation_and_post_gate_absence(self) -> None:
        validation = _payload(
            partition="validation",
            dataset_id="gaps_poly_mix",
            target=0,
            event_id="invalid",
            group="invalid",
        )
        with self.assertRaisesRegex(ValueError, "train-only"):
            CandidateFitRow.from_json(validation)
        row = _payload(
            partition="fit",
            dataset_id="gaps_poly_mix",
            target=0,
            event_id="not-emitted",
            group="not-emitted",
        )
        row["emitted_noteon"] = False
        with self.assertRaisesRegex(ValueError, "emitted"):
            CandidateFitRow.from_json(row)
        row = _payload(
            partition="fit",
            dataset_id="gaps_poly_mix",
            target=0,
            event_id="boolean-schema",
            group="boolean-schema",
        )
        row["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "schema_version"):
            CandidateFitRow.from_json(row)

    def test_logistic_model_has_one_sigmoid_output_without_fit(self) -> None:
        try:
            import tensorflow as tf
        except ImportError:
            self.skipTest("TensorFlow unavailable")
        model = build_v1_logistic_model(tf)
        self.assertEqual(model.output_shape, (None, 1))
        self.assertEqual(model.layers[-1].activation.__name__, "sigmoid")
        self.assertEqual(model.layers[-1].units, 1)

    def test_serialization_parity_never_overwrites_and_never_fits(self) -> None:
        test_case = self

        class FakeModel:
            def __call__(self, inputs, training: bool = False):
                test_case.assertFalse(training)
                return inputs.sum(axis=1, keepdims=True)

            def save(self, path: str) -> None:
                Path(path).write_text("synthetic-only", encoding="utf-8")

        model = FakeModel()

        class FakeModels:
            @staticmethod
            def load_model(path: str, *, compile: bool):
                test_case.assertFalse(compile)
                test_case.assertEqual(
                    Path(path).read_text(encoding="utf-8"), "synthetic-only"
                )
                return model

        class FakeKeras:
            models = FakeModels

        class FakeTensorFlow:
            keras = FakeKeras

        with tempfile.TemporaryDirectory() as temporary:
            model_path = Path(temporary) / "head.keras"
            parity = verify_saved_model_parity(
                model,
                ((0.0,) * FEATURE_DIMENSION, (1.0,) * FEATURE_DIMENSION),
                model_path,
                FakeTensorFlow,
            )
            self.assertEqual(parity.maximum_absolute_error, 0.0)
            self.assertEqual(parity.model_path, model_path.resolve())
            with self.assertRaises(FileExistsError):
                verify_saved_model_parity(
                    model,
                    ((0.0,) * FEATURE_DIMENSION,),
                    model_path,
                    FakeTensorFlow,
                )


if __name__ == "__main__":
    unittest.main()
