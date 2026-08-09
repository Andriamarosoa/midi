from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
import weakref

from src.polyphonic import run_causal_candidate_v2_independent_validation_execution as runner


class IndependentV2ExecutionRunnerTests(unittest.TestCase):
    @staticmethod
    def _hierarchy(recordings, groups):
        metrics = {name: 0.0 for name in runner.REPORT_METRICS}
        return {view: {"global": dict(metrics), "per_dataset": {x: dict(metrics) for x in runner.REPORT_DATASETS}, "per_recording": {x: dict(metrics) for x in recordings}, "per_independent_leakage_group": {x: dict(metrics) for x in groups}} for view in runner.REPORT_VIEWS}
    def test_import_has_no_tensorflow_or_scientific_modules(self) -> None:
        code = (
            "import sys; "
            "import src.polyphonic.run_causal_candidate_v2_independent_validation_execution; "
            "raise SystemExit(int('tensorflow' in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_is_fail_closed_without_one_job_capability(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.main([])

    def test_forged_capability_is_rejected(self) -> None:
        forged = runner.IndependentV2OneJobCapability(
            runner_commit="0" * 40,
            execution_contract_sha256="0" * 64,
            device="cpu",
            wall_timeout_seconds=900,
            job_id="forged",
            destination="tmp/fresh",
            stop_after_report=True,
            locked_test_used=False,
            single_execution_authorization=True,
        )
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.require_sealed_one_job_capability(forged)

    def test_authorized_path_rejects_before_scientific_execution(self) -> None:
        forged = runner.IndependentV2OneJobCapability(
            runner_commit="0" * 40,
            execution_contract_sha256="0" * 64,
            device="cpu",
            wall_timeout_seconds=900,
            job_id="forged",
            destination="tmp/fresh",
            stop_after_report=True,
            locked_test_used=False,
            single_execution_authorization=True,
        )
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.run_authorized_independent_v2(Path(__file__).resolve().parents[1], forged)

    def test_state_machine_is_one_shot(self) -> None:
        state = runner.OneShotStateMachine()
        state.advance(runner.OneShotPhase.SCIENTIFIC_ASSET_OPENED)
        state.advance(runner.OneShotPhase.INFERENCE_STARTED)
        state.advance(runner.OneShotPhase.AB_METRIC_PRODUCED)
        state.advance(runner.OneShotPhase.COHORT_CONSUMED)
        self.assertTrue(state.cohort_consumed)
        with self.assertRaisesRegex(RuntimeError, "cannot return"):
            state.advance(runner.OneShotPhase.PRE_SCIENCE)

    def test_report_schema_rejects_missing_metric_and_guitarset(self) -> None:
        base = {
            "views": runner.REPORT_VIEWS,
            "granularity": runner.REPORT_GRANULARITIES,
            "datasets": runner.REPORT_DATASETS,
            "recording_count": 30,
            "independent_group_count": 20,
            "metrics": runner.REPORT_METRICS,
            "provenance": runner.REPORT_PROVENANCE,
            "locked_test_used": False,
            "numeric_values": {name: 0.0 for name in runner.REPORT_METRICS},
            "recording_identities": [f"recording-{i}" for i in range(30)],
            "independent_leakage_groups": [f"group-{i}" for i in range(20)],
        }
        base["hierarchy"] = self._hierarchy(base["recording_identities"], base["independent_leakage_groups"])
        runner.validate_future_report(base)
        broken = dict(base)
        broken["metrics"] = runner.REPORT_METRICS[:-1]
        with self.assertRaisesRegex(ValueError, "metrics"):
            runner.validate_future_report(broken)
        broken = dict(base)
        broken["datasets"] = runner.REPORT_DATASETS + ("guitarset_poly_mix",)
        with self.assertRaisesRegex(ValueError, "GuitarSet"):
            runner.validate_future_report(broken)

    def test_report_schema_rejects_nonfinite(self) -> None:
        report = {
            "views": runner.REPORT_VIEWS, "granularity": runner.REPORT_GRANULARITIES,
            "datasets": runner.REPORT_DATASETS, "recording_count": 30,
            "independent_group_count": 20, "metrics": runner.REPORT_METRICS,
            "provenance": runner.REPORT_PROVENANCE, "locked_test_used": False,
            "numeric_values": {runner.REPORT_METRICS[0]: float("nan")},
        }
        with self.assertRaisesRegex(ValueError, "non-finite"):
            runner.validate_future_report(report)

    def test_hierarchical_report_is_fail_closed(self) -> None:
        recordings = [f"recording-{i}" for i in range(30)]
        groups = [f"group-{i}" for i in range(20)]
        metric_map = {name: 0.0 for name in runner.REPORT_METRICS}
        hierarchy = {
            view: {
                "global": dict(metric_map),
                "per_dataset": {name: dict(metric_map) for name in runner.REPORT_DATASETS},
                "per_recording": {name: dict(metric_map) for name in recordings},
                "per_independent_leakage_group": {name: dict(metric_map) for name in groups},
            } for view in runner.REPORT_VIEWS
        }
        base = {
            "views": runner.REPORT_VIEWS, "granularity": runner.REPORT_GRANULARITIES,
            "datasets": runner.REPORT_DATASETS, "recording_count": 30, "independent_group_count": 20,
            "metrics": runner.REPORT_METRICS, "provenance": runner.REPORT_PROVENANCE,
            "locked_test_used": False, "numeric_values": metric_map,
            "recording_identities": recordings, "independent_leakage_groups": groups, "hierarchy": hierarchy,
        }
        runner.validate_future_report(base)
        broken = dict(base)
        broken_hierarchy = dict(hierarchy)
        broken_hierarchy["reference"] = dict(hierarchy["reference"])
        broken_global = dict(hierarchy["reference"]["global"])
        broken_global.pop(runner.REPORT_METRICS[0])
        broken_hierarchy["reference"]["global"] = broken_global
        broken["hierarchy"] = broken_hierarchy
        with self.assertRaisesRegex(ValueError, "metric map"):
            runner.validate_future_report(broken)
        broken = dict(base)
        broken_hierarchy = dict(hierarchy)
        broken_hierarchy["candidate"] = dict(hierarchy["candidate"])
        broken_per_dataset = dict(hierarchy["candidate"]["per_dataset"])
        broken_per_dataset["guitarset_poly_mix"] = dict(metric_map)
        broken_hierarchy["candidate"]["per_dataset"] = broken_per_dataset
        broken["hierarchy"] = broken_hierarchy
        with self.assertRaisesRegex(ValueError, "identities"):
            runner.validate_future_report(broken)
        broken = dict(base)
        broken_hierarchy = dict(hierarchy)
        broken_hierarchy["candidate"] = dict(hierarchy["candidate"])
        broken_hierarchy["candidate"].pop("per_recording")
        broken["hierarchy"] = broken_hierarchy
        with self.assertRaisesRegex(ValueError, "granularity"):
            runner.validate_future_report(broken)

    def test_frozen_artifact_hashes_reject_mutation(self) -> None:
        raw = b"synthetic"
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            runner.validate_frozen_artifact_hashes({name: raw for name in runner.FROZEN_ARTIFACT_NAMES})
        broken = {name: raw for name in runner.FROZEN_ARTIFACT_NAMES}
        broken[runner.FROZEN_ARTIFACT_NAMES[0]] = b"changed"
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            runner.validate_frozen_artifact_hashes(broken)

    @staticmethod
    def _items():
        rows = []
        for index in range(10):
            rows.append(SimpleNamespace(
                dataset_id="gaps_poly_mix", group_id=f"gaps-{index}",
                player_id=f"p{index}", source_id=f"gaps-source-{index}",
                capture_id="mix", split="validation",
            ))
            for dataset, capture in (
                ("guitar_techs_poly_directinput", "di"),
                ("guitar_techs_poly_micamp", "mic"),
            ):
                rows.append(SimpleNamespace(
                    dataset_id=dataset, group_id=f"tech-{index}", player_id="",
                    source_id=f"tech-source-{index}", capture_id=capture,
                    split="validation",
                ))
        return tuple(rows)

    def _sealed_execution(self, *, item_override=None, report_override=None, probe_overrides=None, accumulate_error=False):
        from src.polyphonic import causal_candidate_v2_independent_validation_execution_contract as execution_contract
        from src.polyphonic import causal_candidate_v2_independent_asset_evidence as asset_evidence
        from src.polyphonic import run_causal_candidate_v2_independent_validation as independent
        from src.polyphonic.decoder_candidate_provenance import leakage_group_key

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        destination = root / "fresh-result"
        paths = runner.IndependentV2ExecutionPaths(
            repository_root=root, manifest_path=root / "manifest.csv",
            asset_evidence_path=root / "evidence.json", checkpoint_path=root / "checkpoint.keras",
            model_path=root / "model.keras", standardizer_path=root / "standardizer.json",
            audio_evidence_config_path=root / "audio.json", evaluation_config_path=root / "evaluation.yaml",
            reference_decoder_config_path=root / "decoder.json", destination=destination,
            lock_path=root / "active.lock",
        )
        cap = runner.IndependentV2OneJobCapability(
            runner_commit="a" * 40, execution_contract_sha256="b" * 64,
            device="cpu", wall_timeout_seconds=900, job_id="one-job",
            destination=str(destination), stop_after_report=True,
            locked_test_used=False, single_execution_authorization=True,
        )
        runner._ONE_JOB_CAPABILITIES[id(cap)] = weakref.ref(cap)
        self.addCleanup(runner._ONE_JOB_CAPABILITIES.pop, id(cap), None)
        decision_rules = {
            "automatic_promotion": False,
            "all_rules_must_pass_for_positive_independent_evidence": True,
            "per_dataset_causal_false_noteons_must_not_increase": True,
            "retriggers_and_excess_fragments_must_not_increase": True,
            "guitarset_claim_forbidden": True,
        }
        contract = execution_contract.IndependentV2ExecutionContract(
            contract_sha256="b" * 64,
            closed_independent_protocol_sha256=execution_contract.INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256,
            asset_evidence_sha256=execution_contract.INDEPENDENT_V2_ASSET_EVIDENCE_SHA256,
            asset_evidence_builder_protocol_sha256=execution_contract.INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256,
            recording_count=30, independent_group_count=20, wall_timeout_seconds=900,
            threshold=0.31, candidate_gate_placement="post_ranking_pre_noteon",
            decision_rules=tuple(decision_rules.items()),
        )
        sealed_items = self._items()
        items = tuple(item_override if item_override is not None else sealed_items)
        keys = tuple(asset_evidence.canonical_recording_key(item) for item in sealed_items)
        groups = tuple(sorted({leakage_group_key(item) for item in sealed_items}))
        cohort = SimpleNamespace(
            recording_keys=keys, leakage_groups=groups,
            historical_selection_sha256="c" * 64,
        )
        snapshot = SimpleNamespace(items=sealed_items, manifest_sha256="d" * 64)
        events = []

        class Lease:
            def __enter__(self): events.append("lease_enter"); destination.mkdir(); return self
            def __exit__(self, *args): events.append("lease_exit")

        class Probe:
            head = "a" * 40
            clean = True
            destination_present = False
            active = False
            def git_head(self, unused): events.append("git_head"); return self.head
            def worktree_clean(self, unused): return self.clean
            def read_bytes(self, path): events.append(("read", path.name)); return b"sealed"
            def destination_exists(self, unused): return self.destination_present
            def heavy_job_active(self, unused): return self.active
            def acquire_lease(self, unused_lock, unused_destination): return Lease()
        probe = Probe()
        for name, value in (probe_overrides or {}).items():
            setattr(probe, name, value)

        recordings = list(keys)
        metric_map = {name: 0.0 for name in runner.REPORT_METRICS}
        base_report = {
            "views": runner.REPORT_VIEWS, "granularity": runner.REPORT_GRANULARITIES,
            "datasets": runner.REPORT_DATASETS, "recording_count": 30,
            "independent_group_count": 20, "metrics": runner.REPORT_METRICS,
            "provenance": runner.REPORT_PROVENANCE, "locked_test_used": False,
            "numeric_values": dict(metric_map), "recording_identities": recordings,
            "independent_leakage_groups": list(groups),
            "hierarchy": self._hierarchy(recordings, groups),
            "decision_inputs": {"reference": {"sealed": "reference"}, "candidate": {"sealed": "candidate"}},
            "provenance_values": {"forged": True},
        }

        class Adapter:
            def manifest_snapshot(self, path): events.append("snapshot"); return snapshot
            def items(self, actual_cohort, actual_snapshot):
                events.append("items")
                self.outer.assertIs(actual_cohort, cohort); self.outer.assertIs(actual_snapshot, snapshot)
                return items
            def open_exact_item(self, item): events.append(("open", asset_evidence.canonical_recording_key(item))); return item
            def infer_once(self, opened): value = object(); events.append(("infer", opened, value)); return value
            def audio_masks_once(self, opened): value = object(); events.append(("masks", opened, value)); return value
            def decode_ab(self, prediction, masks):
                value = {"prediction": prediction, "masks": masks}; events.append(("decode", prediction, masks, value)); return value
            def accumulate(self, result):
                events.append(("accumulate", result))
                if accumulate_error: raise RuntimeError("accumulate failed")
            def final_report(self): events.append("final_report"); return dict(report_override or base_report)
        adapter = Adapter(); adapter.outer = self

        patches = [
            mock.patch.object(runner, "_require_execution_contract", return_value=contract),
            mock.patch.object(runner, "validate_frozen_artifact_hashes", side_effect=lambda values: events.append(("artifact_hashes", tuple(values)))),
            mock.patch.object(runner, "evaluate_future_report_decision", side_effect=lambda reference, candidate, rules: (events.append(("decision", reference, candidate, rules)) or {"all_rules_passed": True, "classification": "positive_independent_evidence_non_promotional", "automatic_promotion": False, "checks": {"sealed": True}})),
            mock.patch.object(independent, "load_sealed_independent_v2_validation_cohort", side_effect=lambda repository_root, manifest_path: (events.append(("cohort_load", repository_root, manifest_path)) or cohort)),
            mock.patch.object(independent, "require_sealed_independent_v2_validation_cohort", side_effect=lambda value: value),
            mock.patch.object(independent, "validation_asset_evidence_requirement", return_value=object()),
            mock.patch.object(asset_evidence, "load_independent_v2_validation_asset_evidence", side_effect=lambda path, actual_cohort, requirement: (events.append(("evidence_load", path)) or object())),
            mock.patch.object(asset_evidence, "validate_independent_v2_validation_asset_evidence", side_effect=lambda persisted, actual_cohort, actual_snapshot, requirement: (events.append("evidence_validate") or object())),
            mock.patch.object(asset_evidence, "verify_independent_v2_validation_audio_asset_for_item", side_effect=lambda evidence, item: events.append(("verify_audio", asset_evidence.canonical_recording_key(item)))),
            mock.patch.object(asset_evidence, "verify_independent_v2_validation_label_asset_for_item", side_effect=lambda evidence, item: events.append(("verify_label", asset_evidence.canonical_recording_key(item)))),
        ]
        for patch in patches: patch.start(); self.addCleanup(patch.stop)
        return paths, cap, probe, adapter, events, base_report

    def test_direct_orchestrator_runs_exact_sealed_sequence(self) -> None:
        paths, cap, probe, adapter, events, _ = self._sealed_execution()
        original = runner.OneShotStateMachine.advance
        def observed(state, phase): events.append(("phase", phase)); return original(state, phase)
        with mock.patch.object(runner.OneShotStateMachine, "advance", observed):
            report = runner._run_sealed_independent_v2_execution(
                paths, cap, system_probe=probe, scientific_adapter=adapter,
            )
        self.assertEqual(report["terminal_state"], "REPORT_WRITTEN")
        self.assertTrue(report["cohort_consumed"])
        self.assertFalse(report["decision"]["automatic_promotion"])
        self.assertNotIn("forged", report["provenance_values"])
        self.assertEqual(report["provenance_values"]["git_commit"], "a" * 40)
        self.assertTrue((paths.destination / "independent_v2_execution_report.json").is_file())
        self.assertEqual(sum(event == "final_report" for event in events), 1)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] == "infer" for event in events), 30)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] == "masks" for event in events), 30)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] == "decode" for event in events), 30)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] == "read" for event in events), 6)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] == "decision" for event in events), 1)
        for index, event in enumerate(events):
            if isinstance(event, tuple) and event[0] == "decode":
                prior_infer = next(row for row in reversed(events[:index]) if isinstance(row, tuple) and row[0] == "infer")
                prior_masks = next(row for row in reversed(events[:index]) if isinstance(row, tuple) and row[0] == "masks")
                self.assertIs(event[1], prior_infer[2]); self.assertIs(event[2], prior_masks[2])
        self.assertLess(events.index("lease_enter"), next(i for i, event in enumerate(events) if isinstance(event, tuple) and event[0] == "open"))
        first_open = next(i for i, event in enumerate(events) if isinstance(event, tuple) and event[0] == "open")
        first_infer = next(i for i, event in enumerate(events) if isinstance(event, tuple) and event[0] == "infer")
        first_decode = next(i for i, event in enumerate(events) if isinstance(event, tuple) and event[0] == "decode")
        first_accumulate = next(i for i, event in enumerate(events) if isinstance(event, tuple) and event[0] == "accumulate")
        self.assertLess(events.index(("phase", runner.OneShotPhase.SCIENTIFIC_ASSET_OPENED)), first_open)
        self.assertEqual(sum(isinstance(event, tuple) and event[0] in {"verify_audio", "verify_label"} for event in events[:first_open]), 60)
        self.assertLess(events.index(("phase", runner.OneShotPhase.INFERENCE_STARTED)), first_infer)
        self.assertLess(events.index(("phase", runner.OneShotPhase.AB_METRIC_PRODUCED)), first_accumulate)
        self.assertLess(first_decode, events.index(("phase", runner.OneShotPhase.AB_METRIC_PRODUCED)))

    def test_direct_orchestrator_rejects_runtime_preflight_variants(self) -> None:
        cases = (
            ({"head": "f" * 40}, "runner commit"),
            ({"clean": False}, "runtime preflight"),
            ({"destination_present": True}, "runtime preflight"),
            ({"active": True}, "runtime preflight"),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                paths, cap, probe, adapter, events, _ = self._sealed_execution(probe_overrides=overrides)
                with self.assertRaisesRegex((ValueError, RuntimeError), message):
                    runner._run_sealed_independent_v2_execution(paths, cap, system_probe=probe, scientific_adapter=adapter)
                self.assertFalse(any(isinstance(event, tuple) and event[0] == "open" for event in events))

    def test_direct_orchestrator_rejects_wrong_cohort_before_science(self) -> None:
        original = self._items()
        variants = (original[:-1], original + (original[-1],), tuple(reversed(original)))
        for variant in variants:
            with self.subTest(count=len(variant)):
                paths, cap, probe, adapter, events, _ = self._sealed_execution(item_override=variant)
                with self.assertRaisesRegex(RuntimeError, "sealed cohort"):
                    runner._run_sealed_independent_v2_execution(paths, cap, system_probe=probe, scientific_adapter=adapter)
                self.assertNotIn("lease_enter", events)

    def test_direct_orchestrator_rejects_destination_mismatch(self) -> None:
        paths, cap, probe, adapter, events, _ = self._sealed_execution()
        paths = runner.IndependentV2ExecutionPaths(**{
            **paths.__dict__, "destination": paths.destination.parent / "different",
        })
        with self.assertRaisesRegex(ValueError, "destination differs"):
            runner._run_sealed_independent_v2_execution(paths, cap, system_probe=probe, scientific_adapter=adapter)
        self.assertNotIn("lease_enter", events)

    def test_production_lease_is_atomic_and_never_reuses_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "active.lock"
            destination = root / "result"
            with runner._ProductionRunLease(lock, destination):
                self.assertTrue(lock.is_file()); self.assertTrue(destination.is_dir())
                with self.assertRaises(FileExistsError):
                    with runner._ProductionRunLease(lock, root / "other"):
                        pass
            self.assertFalse(lock.exists())
            with self.assertRaises(FileExistsError):
                with runner._ProductionRunLease(lock, destination):
                    pass

    def test_production_metric_projection_uses_canonical_causal_keys(self) -> None:
        projected = runner._ProductionScientificAdapter._metric_map({
            "onset": {
                "estimated_notes": 3, "matched_notes": 2,
                "false_positive_notes": 1, "missing_notes": 1,
                "precision": 2 / 3, "recall": 2 / 3, "f1": 2 / 3,
            },
            "strictly_causal_noteon": {"global": {
                "false_noteons": 1, "false_noteons_per_min": 2.5,
                "recall_within_max_latency": 0.75,
                "latency_p50_ms": 5.0, "latency_p90_ms": 10.0,
            }},
            "diagnostics": {"excess_fragments": 0}, "retriggers": 0,
            "low_midi_40_51": {"false_positive_notes": 1},
            "gate_eligible_count": 4, "gate_rejected_count": 1,
        })
        self.assertEqual(projected["causal_false_noteons_per_minute"], 2.5)
        self.assertEqual(tuple(projected), runner.REPORT_METRICS)

    def test_ab_result_is_consumed_before_accumulation_failure(self) -> None:
        paths, cap, probe, adapter, events, _ = self._sealed_execution(accumulate_error=True)
        phases = []
        original = runner.OneShotStateMachine.advance
        def observed(state, phase): phases.append(phase); return original(state, phase)
        with mock.patch.object(runner.OneShotStateMachine, "advance", observed):
            with self.assertRaisesRegex(RuntimeError, "accumulate failed"):
                runner._run_sealed_independent_v2_execution(paths, cap, system_probe=probe, scientific_adapter=adapter)
        self.assertIn(runner.OneShotPhase.AB_METRIC_PRODUCED, phases)
        self.assertNotIn(runner.OneShotPhase.REPORT_WRITTEN, phases)

    def test_public_entry_rejects_forged_capability_before_builders(self) -> None:
        forged = runner.IndependentV2OneJobCapability(
            runner_commit="0" * 40, execution_contract_sha256="0" * 64,
            device="cpu", wall_timeout_seconds=900, job_id="forged",
            destination="tmp/fresh", stop_after_report=True,
            locked_test_used=False, single_execution_authorization=True,
        )
        with mock.patch.object(runner, "_build_production_execution_paths") as build:
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                runner.run_authorized_independent_v2(Path.cwd(), forged)
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
