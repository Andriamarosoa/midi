from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h23_execution_capability as capability
from src.polyphonic import run_harmonic_censoring_h23_synthetic as runner
from src.polyphonic.harmonic_censoring_h23 import load_h23_harness_plan


class HarmonicCensoringH23DormantExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h23_harness_plan(cls.root)

    def _seal_payload(self) -> dict[str, object]:
        changed = sorted(
            (
                capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix(),
                capability.H23_RUNNER_SOURCE_RELATIVE_PATH.as_posix(),
            )
        )
        commit = "a" * 40
        return {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h23_synthetic_execution_authorization_seal",
            "status": "externally_approved_one_shot_synthetic_execution",
            "authorization": {
                "capability_issuance_authorized": True,
                "synthetic_execution_authorized": True,
                "scientific_execution_authorized": True,
                "P0_execution_authorized": True,
                "P1_execution_authorized": True,
                "P2_execution_authorized": True,
                "real_data_access_authorized": False,
                "training_authorized": False,
                "H17_population_used": False,
                "locked_test_used": False,
            },
            "bindings": {
                "H23_contract_raw_sha256": capability.H23_CONTRACT_SHA256,
                "capability_contract_raw_sha256": capability.H23_CAPABILITY_CONTRACT_SHA256,
                "fixture_manifest_sha256": capability.H23_FIXTURE_MANIFEST_SHA256,
                "resolved_test_manifest_sha256": capability.H23_RESOLVED_TEST_MANIFEST_SHA256,
                "reviewed_execution_commit": commit,
                "exact_changed_files": changed,
                "capability_source_blob": "b" * 40,
                "runner_source_blob": "c" * 40,
                "executor_claim_transcript_contract_raw_sha256": (
                    capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256
                ),
            },
            "runtime_identity": {
                "implementation": "CPython",
                "python_version": "3.11.9",
                "numpy_version": "1.26.4",
                "architecture": "arm64",
                "execution_device": "CPU",
                "thread_count": 1,
            },
            "one_shot_paths": {
                "success_destination": "tmp/h23/success",
                "terminal_record_destination": "tmp/h23/terminal",
                "authorization_marker": "tmp/h23/consumed.json",
                "transcript_path": "tmp/h23/transcript.jsonl",
            },
            "external_review": {
                "verdict": "APPROVED",
                "reviewed_execution_commit": commit,
                "authorization_seal_review_required": True,
            },
        }

    def _activation_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h23_synthetic_execution_activation",
            "status": "externally_reviewed_seal_activation",
            "authorization_seal": {
                "path": capability.H23_AUTHORIZATION_SEAL_RELATIVE_PATH.as_posix(),
                "raw_sha256": "d" * 64,
            },
            "bindings": {
                "implementation_commit": "a" * 40,
                "capability_source_blob": "b" * 40,
                "runner_source_blob": "c" * 40,
                "executor_claim_transcript_contract_raw_sha256": (
                    capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256
                ),
            },
            "external_review": {
                "verdict": "APPROVED",
                "authorization_seal_reviewed": True,
                "activation_commit_review_required": True,
            },
        }

    def test_activation_parser_pins_seal_and_implementation_without_self_hash(self) -> None:
        payload = self._activation_payload()
        parsed = capability.validate_h23_authorization_activation_payload(
            payload, raw_sha256="e" * 64
        )
        self.assertEqual(parsed.authorization_seal_sha256, "d" * 64)
        self.assertEqual(parsed.implementation_commit, "a" * 40)
        self.assertNotIn("activation_commit", payload)
        self.assertNotIn("activation_raw_sha256", payload)
        forged = self._activation_payload()
        forged["authorization_seal"]["path"] = "configs/other.json"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "not canonical"):
            capability.validate_h23_authorization_activation_payload(
                forged, raw_sha256="e" * 64
            )

    def test_future_seal_parser_requires_all_six_rights(self) -> None:
        contract_raw = (
            self.root / capability.H23_CAPABILITY_CONTRACT_RELATIVE_PATH
        ).read_bytes()
        self.assertEqual(
            hashlib.sha256(contract_raw).hexdigest(),
            capability.H23_CAPABILITY_CONTRACT_SHA256,
        )
        payload = self._seal_payload()
        parsed = capability.validate_h23_authorization_seal_payload(
            payload, raw_sha256="d" * 64
        )
        self.assertEqual(parsed.reviewed_execution_commit, "a" * 40)
        for right in (
            "capability_issuance_authorized",
            "synthetic_execution_authorized",
            "scientific_execution_authorized",
            "P0_execution_authorized",
            "P1_execution_authorized",
            "P2_execution_authorized",
        ):
            forged = self._seal_payload()
            forged["authorization"][right] = False  # type: ignore[index]
            with self.subTest(right=right), self.assertRaisesRegex(
                PermissionError, right
            ):
                capability.validate_h23_authorization_seal_payload(
                    forged, raw_sha256="d" * 64
                )

    def test_seal_accepts_exact_diff_when_unchanged_runner_is_blob_bound(self) -> None:
        payload = self._seal_payload()
        payload["bindings"]["exact_changed_files"] = [  # type: ignore[index]
            capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix()
        ]
        parsed = capability.validate_h23_authorization_seal_payload(
            payload, raw_sha256="d" * 64
        )
        self.assertEqual(
            parsed.exact_changed_files,
            (capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix(),),
        )
        self.assertEqual(parsed.capability_source_blob, "b" * 40)
        self.assertEqual(parsed.runner_source_blob, "c" * 40)
        self.assertEqual(
            parsed.executor_claim_transcript_contract_raw_sha256,
            capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256,
        )

    def test_seal_parser_rejects_training_locked_test_and_path_escape(self) -> None:
        for name in ("training_authorized", "locked_test_used", "H17_population_used"):
            payload = self._seal_payload()
            payload["authorization"][name] = True  # type: ignore[index]
            with self.subTest(name=name), self.assertRaises(PermissionError):
                capability.validate_h23_authorization_seal_payload(
                    payload, raw_sha256="d" * 64
                )
        payload = self._seal_payload()
        payload["one_shot_paths"]["success_destination"] = "../escape"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "inside the repository"):
            capability.validate_h23_authorization_seal_payload(
                payload, raw_sha256="d" * 64
            )

    def test_current_factory_refuses_before_plan_resolution(self) -> None:
        self.assertTrue(
            (self.root / capability.H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH).is_file()
        )
        self.assertTrue(
            (self.root / capability.H23_AUTHORIZATION_SEAL_RELATIVE_PATH).is_file()
        )
        with mock.patch.dict(
            "os.environ",
            {capability.H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV: ""},
            clear=False,
        ), mock.patch.object(capability, "load_h23_harness_plan") as load_plan:
            with self.assertRaisesRegex(ValueError, "lowercase hexadecimal length 40"):
                capability.issue_h23_synthetic_execution_capability(self.root)
        load_plan.assert_not_called()

    def test_canonical_activation_and_seal_are_cross_bound_but_not_injected(self) -> None:
        activation_path = self.root / capability.H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH
        seal_path = self.root / capability.H23_AUTHORIZATION_SEAL_RELATIVE_PATH
        activation_raw = activation_path.read_bytes()
        seal_raw = seal_path.read_bytes()
        activation = capability.validate_h23_authorization_activation_payload(
            json.loads(activation_raw),
            raw_sha256=hashlib.sha256(activation_raw).hexdigest(),
        )
        seal = capability.validate_h23_authorization_seal_payload(
            json.loads(seal_raw), raw_sha256=hashlib.sha256(seal_raw).hexdigest()
        )
        self.assertEqual(activation.authorization_seal_sha256, seal.raw_sha256)
        self.assertEqual(activation.implementation_commit, seal.reviewed_execution_commit)
        self.assertEqual(activation.capability_source_blob, seal.capability_source_blob)
        self.assertEqual(activation.runner_source_blob, seal.runner_source_blob)
        self.assertEqual(
            activation.executor_claim_transcript_contract_raw_sha256,
            seal.executor_claim_transcript_contract_raw_sha256,
        )
        self.assertEqual(
            seal.reviewed_execution_commit,
            "1025ac56706312718e93f9078fdf9c341276c8ea",
        )
        changed = tuple(
            sorted(
                line
                for line in capability._git(
                    self.root,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    seal.reviewed_execution_commit,
                ).splitlines()
                if line
            )
        )
        self.assertEqual(seal.exact_changed_files, changed)
        self.assertEqual(len(changed), 5)
        self.assertEqual(
            capability._git(
                self.root,
                "rev-parse",
                f"{seal.reviewed_execution_commit}:"
                f"{capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix()}",
            ),
            seal.capability_source_blob,
        )
        self.assertEqual(
            capability._git(
                self.root,
                "rev-parse",
                f"{seal.reviewed_execution_commit}:"
                f"{capability.H23_RUNNER_SOURCE_RELATIVE_PATH.as_posix()}",
            ),
            seal.runner_source_blob,
        )
        self.assertEqual(
            hashlib.sha256(activation_raw).hexdigest(),
            "81d0f0d6739e082745ae646a57ad31b17a62b5007dd4c0f718701c03dfe25906",
        )
        self.assertNotIn(capability.H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV, __import__("os").environ)

        with mock.patch.dict(
            "os.environ",
            {},
            clear=True,
        ), mock.patch.object(capability, "load_h23_harness_plan") as load_plan:
            with self.assertRaisesRegex(PermissionError, "no OS-bound reviewed activation"):
                capability.issue_h23_synthetic_execution_capability(self.root)
        load_plan.assert_not_called()

    def test_OS_bound_activation_HEAD_mismatch_refuses_before_plan_resolution(self) -> None:
        def git_result(repository: Path, *arguments: str) -> str:
            del repository
            if arguments == ("status", "--porcelain"):
                return ""
            if arguments == ("rev-parse", "HEAD"):
                return "b" * 40
            raise AssertionError(f"unexpected git arguments: {arguments!r}")

        with mock.patch.dict(
            "os.environ",
            {capability.H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV: "a" * 40},
            clear=True,
        ), mock.patch.object(capability, "_git", side_effect=git_result), mock.patch.object(
            capability, "load_h23_harness_plan"
        ) as load_plan:
            with self.assertRaisesRegex(ValueError, "HEAD does not match"):
                capability.issue_h23_synthetic_execution_capability(self.root)
        load_plan.assert_not_called()

    def test_manual_copy_replace_pickle_and_structural_forgery_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "factory-only"):
            capability.AttestedH23SyntheticExecutionCapability(  # type: ignore[call-arg]
                None,
                contract_sha256="0" * 64,
                capability_contract_sha256="0" * 64,
                fixture_manifest_sha256="0" * 64,
                resolved_test_manifest_sha256="0" * 64,
                approved_harness_git_blob="0" * 40,
                implementation_commit="0" * 40,
                authorization_seal_sha256="0" * 64,
                success_destination=Path("success"),
                terminal_record_destination=Path("terminal"),
                authorization_marker=Path("marker"),
            )
        forged = object.__new__(capability.AttestedH23SyntheticExecutionCapability)
        with self.assertRaises(PermissionError):
            capability.require_attested_h23_synthetic_execution_capability(forged)
        with self.assertRaises(TypeError):
            copy.copy(forged)
        with self.assertRaises(TypeError):
            copy.deepcopy(forged)
        with self.assertRaises(TypeError):
            pickle.dumps(forged)
        with self.assertRaises(TypeError):
            replace(forged)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            capability.require_attested_h23_synthetic_execution_capability(
                {"synthetic_execution_authorized": True}
            )
        self.assertFalse(hasattr(capability, "_CAPABILITY_CONSTRUCTOR_TOKEN"))
        self.assertFalse(hasattr(capability, "_register_identity"))
        self.assertFalse(hasattr(capability, "_CAPABILITIES"))

    def _results(self, count: int, *, fail_last: bool = False):
        return tuple(
            runner.H23AdministrativeTestResult(
                test_id=item.test_id,
                phase=item.phase,
                passed=not (fail_last and index == count - 1),
                evidence={"synthetic_administrative_test": True, "index": index},
            )
            for index, item in enumerate(self.plan.tests[:count])
        )

    def test_P0_failure_is_authoritative_with_exact_not_run_suffix(self) -> None:
        results = self._results(5, fail_last=True)
        terminal = runner.build_h23_scientific_terminal_record(
            self.plan, results
        )
        self.assertFalse(terminal["authoritative"])
        self.assertNotIn("global_go_status", terminal)
        self.assertEqual(
            terminal["proposed_global_go_status"], runner.H23_P0_KILL_STATUS
        )
        self.assertEqual(terminal["first_failed_test_id"], self.plan.tests[4].test_id)
        self.assertEqual(len(terminal["executed_results"]), 5)
        self.assertEqual(len(terminal["not_run_tests"]), 67)
        self.assertTrue(
            all(
                item["status"] == runner.H23_NOT_RUN_STATUS
                for item in terminal["not_run_tests"]
            )
        )
        self.assertFalse(terminal["training_authorized"])

    def test_success_requires_all_72_and_failure_must_be_last_prefix_item(self) -> None:
        with self.assertRaisesRegex(ValueError, "success requires all 72"):
            runner.build_h23_scientific_terminal_record(
                self.plan, self._results(5)
            )
        results = list(self._results(5))
        results[2] = runner.H23AdministrativeTestResult(
            test_id=results[2].test_id,
            phase=results[2].phase,
            passed=False,
            evidence={},
        )
        with self.assertRaisesRegex(ValueError, "first failed test"):
            runner.build_h23_scientific_terminal_record(
                self.plan, results
            )
        success = runner.build_h23_scientific_terminal_record(
            self.plan, self._results(72)
        )
        self.assertFalse(success["authoritative"])
        self.assertNotIn("global_go_status", success)
        self.assertEqual(
            success["proposed_global_go_status"], runner.H23_POSITIVE_STATUS
        )
        self.assertEqual(success["not_run_tests"], [])

    def test_P1_and_P2_failures_are_readiness_failures_not_P0_kills(self) -> None:
        first_by_phase = {}
        for index, item in enumerate(self.plan.tests):
            first_by_phase.setdefault(item.phase, index)
        for phase in ("P1", "P2"):
            count = first_by_phase[phase] + 1
            terminal = runner.build_h23_scientific_terminal_record(
                self.plan,
                self._results(count, fail_last=True),
            )
            with self.subTest(phase=phase):
                self.assertEqual(
                    terminal["proposed_global_go_status"],
                    runner.H23_READINESS_FAILURE_STATUS,
                )
                self.assertNotEqual(
                    terminal["proposed_global_go_status"], runner.H23_P0_KILL_STATUS
                )

    def test_operational_incident_is_never_a_scientific_verdict(self) -> None:
        terminal = runner.build_h23_operational_terminal_record(
            self.plan,
            self._results(4),
            error_type="TimeoutError",
            error_message="synthetic administrative timeout",
        )
        self.assertFalse(terminal["authoritative"])
        self.assertNotIn("global_go_status", terminal)
        self.assertEqual(
            terminal["proposed_global_go_status"], runner.H23_INCONCLUSIVE_STATUS
        )
        self.assertIsNone(terminal["scientific_verdict"])
        self.assertFalse(terminal["training_authorized"])

    def test_terminal_finalizer_accepts_no_caller_results_or_transcript_path(self) -> None:
        self.assertFalse(hasattr(runner, "publish_h23_terminal_record_atomically"))
        self.assertTrue(capability.H23_CONSUMPTION_CLAIM_IMPLEMENTED)
        with self.assertRaises(TypeError):
            capability.claim_h23_synthetic_execution_capability(object())
        with self.assertRaises(TypeError):
            runner.finalize_and_publish_h23_terminal_record(self.root, object())
        with self.assertRaises(TypeError):
            runner.finalize_and_publish_h23_terminal_record(  # type: ignore[call-arg]
                self.root, object(), [], Path("caller.jsonl")
            )

    def test_runner_is_implemented_but_old_activation_keeps_it_dormant(self) -> None:
        self.assertTrue(runner.PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED)
        with self.assertRaises(TypeError):
            runner.run_authorized_h23_synthetic_execution(self.root, object())
        with mock.patch.object(capability, "load_h23_harness_plan") as load_plan:
            with mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(PermissionError, "no OS-bound reviewed activation"):
                    runner.main([])
        load_plan.assert_not_called()

    def test_modules_have_no_scientific_or_project_data_imports(self) -> None:
        for module_path in (
            self.root / capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH,
            self.root / capability.H23_RUNNER_SOURCE_RELATIVE_PATH,
        ):
            source = module_path.read_text(encoding="utf-8")
            self.assertNotIn("import numpy", source)
            self.assertNotIn("import tensorflow", source)
            self.assertNotIn("from .data import", source)
            self.assertNotIn("from .decoder import", source)
        capability_source = (
            self.root / capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH
        ).read_text(encoding="utf-8")
        self.assertIn("registered[1] != binding(value)", capability_source)
        runner_source = (
            self.root / capability.H23_RUNNER_SOURCE_RELATIVE_PATH
        ).read_text(encoding="utf-8")
        self.assertIn("claim_h23_synthetic_execution_capability", runner_source)
        self.assertNotIn("_legacy_finalize_and_publish", runner_source)


if __name__ == "__main__":
    unittest.main()
