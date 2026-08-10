from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
import unittest

from src.polyphonic.provisional_resolution_age1 import (
    AGE1_OBSERVATION_AVAILABLE,
    AGE1_OBSERVATION_UNAVAILABLE,
    TARGET_EXCLUDED_INVALID_FRAME,
    TARGET_MATCHABLE,
    Age1ScientificRow,
    PassiveAge1SignalCollector,
)
from src.polyphonic.decoder import PolyphonicMidiEvent
from src.polyphonic.provisional_resolution_age1_metrics import (
    AGE1_SIGNAL_DEMONSTRATED,
    AGE1_SIGNAL_EXECUTION_INVALID,
    AGE1_SIGNAL_INSUFFICIENT,
    AGE1_SIGNAL_NOT_DEMONSTRATED,
    AGE1_SIGNAL_SINGLE_CLASS,
    AUC_UNAVAILABLE_SINGLE_CLASS,
    BOOTSTRAP_REPLICATE_COUNT,
    BOOTSTRAP_SEED,
    D1_ORIENTATION,
    GROUP_RESAMPLING_INCONCLUSIVE,
    MINIMUM_VALID_AGE1_OBSERVATION_COUNT,
    MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT,
    GroupedAge1EvaluationRow,
    UndefinedRocAucError,
    binary_roc_auc,
    evaluate_h7_synthetic_metrics,
    expand_group_sample,
    grouped_roc_auc_bootstrap,
    primary_h7_verdict,
)


def _row(
    index: int,
    target: int,
    score: float,
    *,
    group: str,
    recording: str | None = None,
    corpus: str = "synthetic-a",
    age1_status: str = AGE1_OBSERVATION_AVAILABLE,
    target_status: str = TARGET_MATCHABLE,
) -> GroupedAge1EvaluationRow:
    s0 = 0.5
    scientific = Age1ScientificRow(
        frame_index=index,
        pitch=60 + index % 12,
        S0=s0,
        S1=(score if age1_status == AGE1_OBSERVATION_AVAILABLE else None),
        D1=(score - s0 if age1_status == AGE1_OBSERVATION_AVAILABLE else None),
        age1_status=age1_status,
        true_noteon=(target if target_status == TARGET_MATCHABLE else None),
        target_status=target_status,
    )
    return GroupedAge1EvaluationRow(
        recording_key=recording or f"recording-{index // 4}",
        corpus_category=corpus,
        leakage_group_key=group,
        scientific_row=scientific,
    )


def _balanced_rows(count: int = 240) -> tuple[GroupedAge1EvaluationRow, ...]:
    return tuple(
        _row(
            index,
            index % 2,
            0.8 if index % 2 else 0.2,
            group=f"group-{(index // 2) % 4}",
            recording=f"recording-{index % 12}",
            corpus="synthetic-a" if (index // 2) % 4 < 2 else "synthetic-b",
        )
        for index in range(count)
    )


class ProvisionalResolutionAge1H10MetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.contract_path = cls.root / "configs/provisional_resolution_age1_persistence_h10_synthetic_metric_conformance.json"

    def test_end_of_stream_pending_is_invalid_without_mutation_or_reclassification(self) -> None:
        collector = PassiveAge1SignalCollector()
        collector.observe_emitted_noteons(
            [PolyphonicMidiEvent("note_on", 60, 100, 4, "legacy")],
            frame_probability=[0.8],
            midi_min=60,
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "age1_signal_execution_invalid: unresolved_age1_pending_at_end_of_recording",
        ):
            collector.require_no_pending_age1_at_end()
        self.assertEqual(collector.pending_count, 1)
        self.assertEqual(collector.records, ())

        collector.observe_frame(frame_index=5, frame_probability=[0.3], midi_min=60)
        collector.require_no_pending_age1_at_end()
        self.assertEqual(collector.records[0].age1_status, AGE1_OBSERVATION_AVAILABLE)

        skipped = PassiveAge1SignalCollector()
        skipped.observe_emitted_noteons(
            [PolyphonicMidiEvent("note_on", 60, 100, 4, "legacy")],
            frame_probability=[0.8],
            midi_min=60,
        )
        skipped.observe_frame(frame_index=6, frame_probability=[0.3], midi_min=60)
        skipped.require_no_pending_age1_at_end()
        self.assertEqual(skipped.records[0].age1_status, AGE1_OBSERVATION_UNAVAILABLE)

    def test_grouped_wrapper_is_metadata_only_and_fail_closed(self) -> None:
        value = _row(0, 0, 0.2, group="shared", recording="direct")
        self.assertEqual(
            tuple(field.name for field in fields(GroupedAge1EvaluationRow)),
            ("recording_key", "corpus_category", "leakage_group_key", "scientific_row"),
        )
        for kwargs in (
            {"recording_key": ""},
            {"corpus_category": " "},
            {"leakage_group_key": ""},
            {"leakage_group_key": " padded "},
        ):
            payload = {
                "recording_key": value.recording_key,
                "corpus_category": value.corpus_category,
                "leakage_group_key": value.leakage_group_key,
                "scientific_row": value.scientific_row,
            }
            payload.update(kwargs)
            with self.assertRaisesRegex(ValueError, "non-empty"):
                GroupedAge1EvaluationRow(**payload)

    def test_exact_roc_auc_ordering_ties_and_failures(self) -> None:
        self.assertEqual(binary_roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertEqual(binary_roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]), 0.0)
        self.assertEqual(binary_roc_auc([0, 1], [0.5, 0.5]), 0.5)
        self.assertEqual(binary_roc_auc([1, 1, 0, 0], [0.9, 0.5, 0.5, 0.1]), 0.875)
        with self.assertRaisesRegex(UndefinedRocAucError, AUC_UNAVAILABLE_SINGLE_CLASS):
            binary_roc_auc([1, 1], [0.2, 0.8])
        for score in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaisesRegex(ValueError, "finite"):
                binary_roc_auc([0, 1], [0.1, score])

    def test_eligibility_minimum_and_single_class_statuses_are_exact(self) -> None:
        short = tuple(
            _row(index, index % 2, 0.8 if index % 2 else 0.2, group=f"g-{index % 2}")
            for index in range(MINIMUM_VALID_AGE1_OBSERVATION_COUNT - 1)
        )
        self.assertEqual(evaluate_h7_synthetic_metrics(short).status, AGE1_SIGNAL_INSUFFICIENT)
        single = tuple(_row(index, 1, 0.8, group=f"g-{index % 3}") for index in range(200))
        self.assertEqual(evaluate_h7_synthetic_metrics(single).status, AGE1_SIGNAL_SINGLE_CLASS)

    def test_group_sampling_uses_group_ids_and_preserves_full_multiplicity(self) -> None:
        rows = (
            _row(0, 0, 0.1, group="shared", recording="direct"),
            _row(1, 1, 0.9, group="shared", recording="mic"),
            _row(2, 0, 0.2, group="small", recording="other"),
        )
        expanded = expand_group_sample(rows, ("shared", "shared", "small"))
        self.assertEqual(len(expanded), 5)
        self.assertEqual([row.recording_key for row in expanded[:4]], ["direct", "mic", "direct", "mic"])
        self.assertEqual([row.leakage_group_key for row in expanded], ["shared", "shared", "shared", "shared", "small"])

    def test_fixed_group_bootstrap_and_report_are_deterministic_and_order_invariant(self) -> None:
        rows = _balanced_rows()
        first = evaluate_h7_synthetic_metrics(rows)
        second = evaluate_h7_synthetic_metrics(tuple(reversed(rows)))
        self.assertEqual(first.canonical_json_bytes(), second.canonical_json_bytes())
        self.assertEqual(first.status, AGE1_SIGNAL_DEMONSTRATED)
        self.assertEqual(first.global_s1_auc, 1.0)
        self.assertEqual(first.bootstrap.requested_replicates, BOOTSTRAP_REPLICATE_COUNT)
        self.assertEqual(first.bootstrap.valid_replicates, BOOTSTRAP_REPLICATE_COUNT)
        self.assertEqual(first.bootstrap.seed, BOOTSTRAP_SEED)
        self.assertEqual(first.bootstrap.rng, "numpy.random.Generator(numpy.random.PCG64)")
        self.assertEqual(first.bootstrap.percentile_method, "numpy.percentile(method=linear)")
        self.assertEqual((first.bootstrap.lower_95, first.bootstrap.upper_95), (1.0, 1.0))
        self.assertEqual(first.d1_orientation, D1_ORIENTATION)

    def test_single_class_group_replicates_become_inconclusive_without_retry(self) -> None:
        rows = tuple(
            [_row(index, 0, 0.2, group="negative") for index in range(100)]
            + [_row(100 + index, 1, 0.8, group="positive") for index in range(100)]
        )
        result = grouped_roc_auc_bootstrap(rows)
        self.assertEqual(result.requested_replicates, 10_000)
        self.assertLess(result.valid_replicates, MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT)
        self.assertEqual(result.status, GROUP_RESAMPLING_INCONCLUSIVE)
        self.assertIsNone(result.lower_95)
        self.assertIsNone(result.upper_95)

    def test_large_group_and_small_groups_remain_group_weighted(self) -> None:
        rows = tuple(
            [_row(index, index % 2, 0.8 if index % 2 else 0.2, group="large") for index in range(200)]
            + [_row(300 + index, index % 2, 0.8 if index % 2 else 0.2, group="small-a") for index in range(10)]
            + [_row(400 + index, index % 2, 0.8 if index % 2 else 0.2, group="small-b") for index in range(10)]
        )
        duplicated_small = expand_group_sample(rows, ("small-a", "small-a", "small-b"))
        self.assertEqual(len(duplicated_small), 30)
        self.assertEqual(sum(row.leakage_group_key == "small-a" for row in duplicated_small), 20)
        result = grouped_roc_auc_bootstrap(rows)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.valid_replicates, 10_000)
        self.assertEqual((result.lower_95, result.upper_95), (1.0, 1.0))

    def test_primary_verdict_boundaries_and_secondary_metrics_are_non_gating(self) -> None:
        self.assertEqual(primary_h7_verdict(0.60, 0.5000001), AGE1_SIGNAL_DEMONSTRATED)
        self.assertEqual(primary_h7_verdict(0.5999999, 0.9), AGE1_SIGNAL_NOT_DEMONSTRATED)
        self.assertEqual(primary_h7_verdict(0.9, 0.50), AGE1_SIGNAL_NOT_DEMONSTRATED)
        self.assertEqual(primary_h7_verdict(0.9, 0.5000001), AGE1_SIGNAL_DEMONSTRATED)

    def test_per_corpus_single_class_is_reported_and_non_gating(self) -> None:
        rows = list(_balanced_rows())
        rows.extend(
            _row(1000 + index, 1, 0.9, group="single-corpus-group", corpus="single-corpus")
            for index in range(20)
        )
        report = evaluate_h7_synthetic_metrics(tuple(rows))
        single = next(item for item in report.per_corpus if item.corpus_category == "single-corpus")
        self.assertEqual(single.status, AUC_UNAVAILABLE_SINGLE_CLASS)
        self.assertIsNone(single.auc)
        self.assertEqual(report.status, AGE1_SIGNAL_DEMONSTRATED)

    def test_attrition_reconciles_exactly_without_end_pending_category(self) -> None:
        rows = (
            _row(0, 1, 0.8, group="g"),
            _row(1, 0, 0.2, group="g", age1_status=AGE1_OBSERVATION_UNAVAILABLE),
            _row(2, 0, 0.2, group="g", target_status=TARGET_EXCLUDED_INVALID_FRAME),
        )
        report = evaluate_h7_synthetic_metrics(rows)
        attrition = report.attrition
        self.assertEqual(attrition["emitted_noteons_initially_considered"], 3)
        self.assertEqual(attrition["noteons_with_exact_age1_observation"], 1)
        self.assertEqual(attrition["noteons_unavailable_due_to_decoder_clock_skip"], 1)
        self.assertEqual(attrition["noteons_excluded_as_ambiguous_or_unmatchable"], 1)
        self.assertEqual(attrition["malformed_or_nonfinite_signal_cases"], 0)
        self.assertEqual(
            attrition["emitted_noteons_initially_considered"],
            sum(value for key, value in attrition.items() if key != "emitted_noteons_initially_considered"),
        )
        malformed = evaluate_h7_synthetic_metrics(
            rows,
            malformed_or_nonfinite_signal_cases=1,
        )
        self.assertEqual(malformed.status, AGE1_SIGNAL_EXECUTION_INVALID)
        self.assertIsNone(malformed.global_s1_auc)
        self.assertEqual(malformed.attrition["emitted_noteons_initially_considered"], 4)

    def test_h10_contract_is_synthetic_only_and_does_not_reference_asset_paths(self) -> None:
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "provisional_resolution_age1_persistence_h10_synthetic_metric_engine_ready")
        self.assertEqual(contract["verdict"], "age1_persistence_h10_synthetic_metric_conformance_demonstrated")
        self.assertEqual(contract["accepted_h9_commit"], "963cf72c8e60e2d669e659de037f910658637984")
        self.assertEqual(contract["bootstrap"]["replicate_count"], 10000)
        self.assertEqual(contract["bootstrap"]["seed"], 721629268)
        self.assertEqual(contract["bootstrap"]["minimum_valid_replicates"], 9500)
        self.assertEqual(contract["eligibility"]["minimum_valid_age1_observations"], 200)
        for value in contract["terminal_flags"].values():
            self.assertFalse(value)
        raw = self.contract_path.read_text(encoding="utf-8").lower()
        for forbidden in ("audio_path", "labels_path", "tensorflow", "checkpoint"):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
