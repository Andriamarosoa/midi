from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from src.polyphonic.provisional_resolution_age1 import (
    AGE1_OBSERVATION_AVAILABLE,
    TARGET_MATCHABLE,
    Age1SignalRecord,
    Age1TargetRecord,
)
from src.polyphonic.provisional_resolution_age1_h11 import (
    EXECUTION_INVALID,
    MAXIMUM_OPERATIONAL_ERROR_MESSAGE_CHARS,
    MAXIMUM_OPERATIONAL_TRACEBACK_FRAMES,
    OPERATIONAL_PHASES,
    H11DecodedRecording,
    H11Recording,
    claim_one_shot_authorization,
    orchestrate_h11_discovery,
    process_h11_recording,
    publish_h11_success_atomically,
    require_h11_cohort,
    require_raw_sha256s,
    run_h11_once,
)
from src.polyphonic.provisional_resolution_age1_metrics import H7SyntheticMetricReport


MANIFEST = "b" * 64
PLAN = "a" * 64


@dataclass(frozen=True)
class Event:
    kind: str
    pitch: int
    frame_index: int
    reason: str = "model_onset"


def cohort() -> tuple[H11Recording, ...]:
    return tuple(
        H11Recording(
            recording_key=f"recording-{index:03d}",
            corpus_category=("gaps_poly_mix" if index % 2 else "guitarset_poly_mix"),
            leakage_group_key=f"group-{index % 31:02d}",
            partition="dev",
            audio_size_bytes=10,
            audio_sha256="1" * 64,
            labels_size_bytes=20,
            labels_sha256="2" * 64,
            source_manifest_sha256=MANIFEST,
            source_partition_plan_sha256=PLAN,
        )
        for index in range(101)
    )


def metric_report() -> H7SyntheticMetricReport:
    return H7SyntheticMetricReport(
        status="age1_persistence_signal_not_demonstrated",
        eligible_rows=101,
        global_s1_auc=0.5,
        descriptive_s0_auc=0.5,
        descriptive_d1_auc=0.5,
        d1_orientation="higher_D1_predicts_true_noteon_persistence",
        bootstrap=None,
        per_corpus=(),
        attrition={"emitted_noteons_initially_considered": 101},
    )


class Adapter:
    def __init__(self, *, fail_at: str | None = None, pending: int = 0, mismatch: bool = False):
        self.fail_at = fail_at
        self.pending = pending
        self.mismatch = mismatch
        self.trace: list[tuple[str, str]] = []
        self.inference_calls = 0
        self.prediction_ids: list[int] = []

    def verify_provenance(self, recording):
        self.trace.append(("verify", recording.recording_key))
        if self.fail_at == recording.recording_key:
            raise RuntimeError("synthetic failure")

    class _Opened:
        def __init__(self, outer, recording): self.outer, self.recording = outer, recording
        def __enter__(self):
            self.outer.trace.append(("open", self.recording.recording_key)); return self
        def __exit__(self, *_): self.outer.trace.append(("close", self.recording.recording_key))

    def open_recording(self, recording): return self._Opened(self, recording)

    def infer_once(self, opened):
        self.inference_calls += 1
        self.trace.append(("infer", opened.recording.recording_key))
        return object()

    def decode_once(self, opened, predictions, recording):
        self.prediction_ids.append(id(predictions))
        self.trace.append(("decode", recording.recording_key))
        return H11DecodedRecording(
            emitted_events=(Event("note_on", 60, 0),),
            signals=(Age1SignalRecord(0, 60, 0.4, AGE1_OBSERVATION_AVAILABLE, 0.5, 0.5 - 0.4),),
            pending_age1=self.pending,
        )

    def extract_targets(self, opened, emitted_events):
        self.trace.append(("target", opened.recording.recording_key))
        pitch = 61 if self.mismatch else 60
        return (Age1TargetRecord(0, pitch, 1, TARGET_MATCHABLE),)


class H11OrchestrationTests(unittest.TestCase):
    @staticmethod
    def _marker(path: Path) -> None:
        path.write_text(json.dumps({
            "contract_sha256": "c" * 64,
            "purpose": "provisional_resolution_age1_h7_discovery_one_shot_authorization",
            "scientific_execution_authorized": True,
            "single_use": True,
        }), encoding="utf-8")

    def test_exact_cohort_is_canonical_and_group_safe(self):
        checked = require_h11_cohort(
            tuple(reversed(cohort())), forbidden_groups=(),
            expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
        )
        self.assertEqual(len(checked), 101)
        self.assertEqual(len({item.leakage_group_key for item in checked}), 31)
        self.assertEqual([item.recording_key for item in checked], sorted(item.recording_key for item in checked))

    def test_extra_missing_duplicate_and_forbidden_fail_closed(self):
        base = cohort()
        cases = (base[:-1], base + (base[0],), base[:-1] + (base[0],))
        for values in cases:
            with self.subTest(size=len(values)), self.assertRaises(RuntimeError):
                require_h11_cohort(values, forbidden_groups=(), expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN)
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            require_h11_cohort(base, forbidden_groups=("group-00",), expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN)

    def test_one_recording_order_and_same_single_prediction(self):
        adapter = Adapter()
        consumed = []
        phases = []
        rows, summary = process_h11_recording(
            cohort()[0],
            adapter,
            mark_consumed=lambda item: consumed.append(item.recording_key),
            record_phase=lambda phase, recording, index: phases.append(
                (phase, None if recording is None else recording.recording_key, index)
            ),
            recording_index=0,
        )
        self.assertEqual(consumed, [cohort()[0].recording_key])
        self.assertEqual([phase for phase, _key, _index in phases], [
            "opening", "inference", "decoder", "target", "reconciliation",
        ])
        self.assertTrue(all(index == 0 for _phase, _key, index in phases))
        self.assertEqual([name for name, _ in adapter.trace], ["verify", "open", "infer", "decode", "target", "close"])
        self.assertEqual(adapter.inference_calls, 1)
        self.assertEqual(len(adapter.prediction_ids), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["emitted_noteons"], 1)

    def test_pending_and_join_mismatch_abort_before_metric(self):
        for adapter in (Adapter(pending=1), Adapter(mismatch=True)):
            metric = Mock(return_value=metric_report())
            with self.assertRaises(RuntimeError):
                orchestrate_h11_discovery(
                    cohort(), adapter, metric, forbidden_groups=(),
                    expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
                    mark_consumed=lambda _item: None,
                )
            metric.assert_not_called()

    def test_complete_101_calls_metric_exactly_once(self):
        adapter = Adapter()
        metric = Mock(return_value=metric_report())
        summary, report = orchestrate_h11_discovery(
            cohort(), adapter, metric, forbidden_groups=(),
            expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
            mark_consumed=lambda _item: None,
        )
        self.assertEqual(summary.processed_recordings, 101)
        self.assertEqual(summary.leakage_groups, 31)
        self.assertEqual(adapter.inference_calls, 101)
        metric.assert_called_once()
        self.assertEqual(report.status, "age1_persistence_signal_not_demonstrated")

    def test_partial_failure_has_no_retry_and_no_metric(self):
        adapter = Adapter(fail_at="recording-003")
        metric = Mock(return_value=metric_report())
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            orchestrate_h11_discovery(
                cohort(), adapter, metric, forbidden_groups=(),
                expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
                mark_consumed=lambda _item: None,
            )
        self.assertEqual(sum(key == "recording-003" for name, key in adapter.trace if name == "verify"), 1)
        metric.assert_not_called()

    def test_authorization_marker_absence_and_atomic_single_claim(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "authorization.json"
            with self.assertRaises(PermissionError):
                claim_one_shot_authorization(marker, expected_contract_sha256="c" * 64)
            marker.write_text(json.dumps({
                "contract_sha256": "c" * 64,
                "purpose": "provisional_resolution_age1_h7_discovery_one_shot_authorization",
                "scientific_execution_authorized": True,
                "single_use": True,
            }), encoding="utf-8")
            claimed = claim_one_shot_authorization(marker, expected_contract_sha256="c" * 64)
            self.assertFalse(marker.exists())
            self.assertTrue(claimed.is_file())
            with self.assertRaises(PermissionError):
                claim_one_shot_authorization(marker, expected_contract_sha256="c" * 64)

    def test_sealed_hash_mismatch_precedes_loader(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "input.bin"
            path.write_bytes(b"sealed")
            digest = hashlib.sha256(b"sealed").hexdigest()
            require_raw_sha256s({"checkpoint": path}, {"checkpoint": digest})
            path.write_bytes(b"changed")
            model_loader = Mock()
            with self.assertRaisesRegex(RuntimeError, "checkpoint"):
                require_raw_sha256s({"checkpoint": path}, {"checkpoint": digest})
            model_loader.assert_not_called()

    def test_atomic_publication_only_after_complete_success(self):
        adapter = Adapter()
        summary, report = orchestrate_h11_discovery(
            cohort(), adapter, lambda _rows: metric_report(), forbidden_groups=(),
            expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
            mark_consumed=lambda _item: None,
        )
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "final"
            publish_h11_success_atomically(destination, summary, report, {"status": "completed"})
            self.assertTrue((destination / "h7_metric_report.json").is_file())
            self.assertEqual(sorted(path.name for path in destination.iterdir()), [
                "attrition.json", "execution_provenance.json", "grouped_rows.json", "h7_metric_report.json",
            ])

    def test_one_shot_failure_consumes_after_boundary_and_leaves_no_final_result(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "authorization.json"
            destination = Path(root) / "final"
            self._marker(marker)
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                run_h11_once(
                    marker_path=marker, expected_contract_sha256="c" * 64,
                    destination=destination, recordings=cohort(),
                    adapter=Adapter(fail_at="recording-003"),
                    metric_callable=lambda _rows: metric_report(), forbidden_groups=(),
                    expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
                )
            self.assertFalse(destination.exists())
            failure = destination.with_suffix(".failure.json")
            self.assertTrue(failure.is_file())
            self.assertTrue(json.loads(failure.read_text())["h8_discovery_consumed"])
            self.assertFalse(marker.exists())

    def test_future_failure_provenance_records_phase_and_redacts_science(self):
        class InferenceFailure(Adapter):
            def infer_once(self, opened):
                raise RuntimeError("S1=0.91 target=1 AUC=0.88")

        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "authorization.json"
            destination = Path(root) / "final"
            self._marker(marker)
            with self.assertRaisesRegex(RuntimeError, "S1=0.91"):
                run_h11_once(
                    marker_path=marker,
                    expected_contract_sha256="c" * 64,
                    destination=destination,
                    recordings=cohort(),
                    adapter=InferenceFailure(),
                    metric_callable=lambda _rows: metric_report(),
                    forbidden_groups=(),
                    expected_manifest_sha256=MANIFEST,
                    expected_plan_sha256=PLAN,
                )
            claimed = marker.with_suffix(".json.claimed")
            phase = json.loads(claimed.with_suffix(".claimed.phase.json").read_text())
            failure = json.loads(destination.with_suffix(".failure.json").read_text())
            self.assertEqual(phase["phase"], "inference")
            self.assertEqual(phase["recording_index"], 0)
            self.assertEqual(phase["recording_key"], "recording-000")
            self.assertEqual(failure["phase"], "inference")
            self.assertEqual(failure["error_type"], "RuntimeError")
            self.assertEqual(
                failure["error_message"],
                "[redacted_non_operational_exception_message]",
            )
            self.assertLessEqual(len(failure["error_message"]), MAXIMUM_OPERATIONAL_ERROR_MESSAGE_CHARS)
            self.assertLessEqual(len(failure["operational_traceback"]), MAXIMUM_OPERATIONAL_TRACEBACK_FRAMES)
            rendered = json.dumps(failure).lower()
            for forbidden in ("s1=", "target=", "auc=", "0.91", "0.88"):
                self.assertNotIn(forbidden, rendered)
            for frame in failure["operational_traceback"]:
                self.assertEqual(set(frame), {"file", "function", "line"})

    def test_success_phase_provenance_reaches_publication_without_science(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "authorization.json"
            destination = Path(root) / "final"
            self._marker(marker)
            run_h11_once(
                marker_path=marker,
                expected_contract_sha256="c" * 64,
                destination=destination,
                recordings=cohort(),
                adapter=Adapter(),
                metric_callable=lambda _rows: metric_report(),
                forbidden_groups=(),
                expected_manifest_sha256=MANIFEST,
                expected_plan_sha256=PLAN,
            )
            phase_path = marker.with_suffix(".json.claimed.phase.json")
            payload = json.loads(phase_path.read_text())
            self.assertEqual(payload["phase"], "publication")
            self.assertIsNone(payload["recording_index"])
            self.assertIsNone(payload["recording_key"])
            self.assertEqual(set(OPERATIONAL_PHASES), {
                "opening", "inference", "decoder", "target", "reconciliation",
                "metrics", "publication",
            })

    def test_one_shot_success_claims_and_publishes_once(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "authorization.json"
            destination = Path(root) / "final"
            self._marker(marker)
            summary, _ = run_h11_once(
                marker_path=marker, expected_contract_sha256="c" * 64,
                destination=destination, recordings=cohort(), adapter=Adapter(),
                metric_callable=lambda _rows: metric_report(), forbidden_groups=(),
                expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
            )
            self.assertEqual(summary.processed_recordings, 101)
            self.assertTrue(destination.is_dir())
            with self.assertRaises(PermissionError):
                run_h11_once(
                    marker_path=marker, expected_contract_sha256="c" * 64,
                    destination=Path(root) / "second", recordings=cohort(), adapter=Adapter(),
                    metric_callable=lambda _rows: metric_report(), forbidden_groups=(),
                    expected_manifest_sha256=MANIFEST, expected_plan_sha256=PLAN,
                )


class H11ContractTests(unittest.TestCase):
    def test_accepted_chain_and_terminal_flags_are_non_executing(self):
        root = Path(__file__).resolve().parents[1]
        contract_path = root / "configs" / "provisional_resolution_age1_persistence_h11_execution_contract.json"
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
        chain = payload["accepted_chain"]
        self.assertEqual(chain["h10_commit"], "bc878204451c45c3f5bb849bbf01de0de290f23a")
        for key, filename in (
            ("h8_cohort_sha256", "provisional_resolution_age1_persistence_h8_selected_cohort.json"),
            ("h8_preparation_sha256", "provisional_resolution_age1_persistence_h8_preparation.json"),
            ("h10_contract_sha256", "provisional_resolution_age1_persistence_h10_synthetic_metric_conformance.json"),
        ):
            self.assertEqual(chain[key], hashlib.sha256((root / "configs" / filename).read_bytes()).hexdigest())
        self.assertTrue(all(value is False for value in payload["terminal_flags"].values()))
        self.assertEqual(payload["runtime"]["numpy"], "1.26.4")
        self.assertEqual(payload["runtime"]["tensorflow"], "2.15.1")


if __name__ == "__main__":
    unittest.main()
