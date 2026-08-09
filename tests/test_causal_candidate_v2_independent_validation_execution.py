from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from src.polyphonic import run_causal_candidate_v2_independent_validation_execution as runner


class IndependentV2ExecutionRunnerTests(unittest.TestCase):
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

    def test_phase_order_is_frozen(self) -> None:
        self.assertEqual(runner.phase_order()[:4], ("authorization", "contract", "runtime", "cohort"))
        self.assertEqual(runner.phase_order()[-3:], ("ab", "metrics", "report"))

    def test_phase_callbacks_are_observed_in_order(self) -> None:
        observed = []
        hooks = runner.IndependentV2ExecutionHooks(
            **{name: (lambda name=name: observed.append(name)) for name in runner.phase_order()}
        )
        self.assertEqual(runner.run_phase_sequence(hooks), runner.phase_order())
        self.assertEqual(tuple(observed), runner.phase_order())

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

    def test_frozen_artifact_hashes_reject_mutation(self) -> None:
        raw = b"synthetic"
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            runner.validate_frozen_artifact_hashes({name: raw for name in runner.FROZEN_ARTIFACT_NAMES})
        broken = {name: raw for name in runner.FROZEN_ARTIFACT_NAMES}
        broken[runner.FROZEN_ARTIFACT_NAMES[0]] = b"changed"
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            runner.validate_frozen_artifact_hashes(broken)


if __name__ == "__main__":
    unittest.main()
