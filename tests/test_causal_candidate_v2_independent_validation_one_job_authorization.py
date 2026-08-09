from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from src.polyphonic import causal_candidate_v2_independent_validation_one_job_authorization as authorization
from src.polyphonic import run_causal_candidate_v2_independent_validation_execution as runner


class IndependentV2OneJobAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = self.root / authorization.AUTHORIZATION_REQUEST_RELATIVE_PATH
        request.parent.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / authorization.AUTHORIZATION_REQUEST_RELATIVE_PATH
        request.write_bytes(source.read_bytes())
        self.head = "e" * 40
        self._previous_force_cpu = os.environ.get("MIDI_FORCE_CPU")
        self.addCleanup(self._restore_force_cpu)
        self._registry_before = set(runner._ONE_JOB_CAPABILITIES)
        self.addCleanup(self._clean_registry)

    def _clean_registry(self) -> None:
        for key in set(runner._ONE_JOB_CAPABILITIES) - self._registry_before:
            runner._ONE_JOB_CAPABILITIES.pop(key, None)
            runner._CLAIMED_ONE_JOB_CAPABILITIES.pop(key, None)

    def _restore_force_cpu(self) -> None:
        if self._previous_force_cpu is None:
            os.environ.pop("MIDI_FORCE_CPU", None)
        else:
            os.environ["MIDI_FORCE_CPU"] = self._previous_force_cpu

    @staticmethod
    def _canonical(payload: object) -> bytes:
        return (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")

    def _approval_payload(self, **overrides):
        payload = {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_external_review_approval",
            "authorization_request_sha256": authorization.AUTHORIZATION_REQUEST_SHA256,
            "reviewed_runner_commit": authorization.REVIEWED_RUNNER_COMMIT,
            "authorized_execution_commit": self.head,
            "approved_for_exactly_one_execution": True,
            "locked_test_used": False,
        }
        payload.update(overrides)
        return payload

    def _write_approval(self, payload=None, *, raw=None) -> Path:
        path = self.root / authorization.EXTERNAL_APPROVAL_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw if raw is not None else self._canonical(payload or self._approval_payload()))
        return path

    def _git_patches(self, *, head=None, clean=True, changed=None, runner_unchanged=True):
        return (
            mock.patch.object(authorization, "_git_head", return_value=head or self.head),
            mock.patch.object(authorization, "_git_worktree_clean", return_value=clean),
            mock.patch.object(
                authorization,
                "_git_diff_names",
                return_value=authorization.AUTHORIZATION_STEP_PATHS if changed is None else frozenset(changed),
            ),
            mock.patch.object(authorization, "_runner_blob_unchanged", return_value=runner_unchanged),
            mock.patch.object(authorization, "_tensorflow_imported", return_value=False),
        )

    def test_module_import_is_tensorflow_free(self) -> None:
        code = (
            "import sys; "
            "import src.polyphonic.causal_candidate_v2_independent_validation_one_job_authorization; "
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

    def test_sealed_request_is_exact_canonical_json(self) -> None:
        payload = authorization.load_sealed_authorization_request(self.root)
        self.assertEqual(payload["reviewed_runner_commit"], authorization.REVIEWED_RUNNER_COMMIT)
        path = self.root / authorization.AUTHORIZATION_REQUEST_RELATIVE_PATH
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), authorization.AUTHORIZATION_REQUEST_SHA256)

    def test_missing_or_mutated_request_fails(self) -> None:
        path = self.root / authorization.AUTHORIZATION_REQUEST_RELATIVE_PATH
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            authorization.load_sealed_authorization_request(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            authorization.load_sealed_authorization_request(self.root)

    def test_approval_absent_fails_before_marker_or_runner(self) -> None:
        marker = self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH
        with mock.patch.object(runner, "run_authorized_independent_v2") as run:
            with self.assertRaisesRegex(RuntimeError, "approval file is absent"):
                authorization.execute_externally_approved_independent_v2_once(self.root)
        self.assertFalse(marker.exists())
        run.assert_not_called()


class IndependentV2Attempt2AuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = self.root / authorization.ATTEMPT2_AUTHORIZATION_REQUEST_RELATIVE_PATH
        request.parent.mkdir(parents=True)
        source = (
            Path(__file__).resolve().parents[1]
            / authorization.ATTEMPT2_AUTHORIZATION_REQUEST_RELATIVE_PATH
        )
        request.write_bytes(source.read_bytes())
        self.head = "a" * 40
        self.old_marker = self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH
        self.old_marker.parent.mkdir(parents=True, exist_ok=True)
        self.old_marker.write_bytes(b"historical-attempt1-marker-must-remain")
        self.old_approval = self.root / authorization.EXTERNAL_APPROVAL_RELATIVE_PATH
        self.old_approval.write_bytes(b"historical-attempt1-approval-must-not-authorize-attempt2")
        self._previous_force_cpu = os.environ.get("MIDI_FORCE_CPU")
        self.addCleanup(self._restore_force_cpu)
        self._registry_before = set(runner._ONE_JOB_CAPABILITIES)
        self.addCleanup(self._clean_registry)

    def _clean_registry(self) -> None:
        for key in set(runner._ONE_JOB_CAPABILITIES) - self._registry_before:
            runner._ONE_JOB_CAPABILITIES.pop(key, None)
            runner._CLAIMED_ONE_JOB_CAPABILITIES.pop(key, None)

    def _restore_force_cpu(self) -> None:
        if self._previous_force_cpu is None:
            os.environ.pop("MIDI_FORCE_CPU", None)
        else:
            os.environ["MIDI_FORCE_CPU"] = self._previous_force_cpu

    @staticmethod
    def _canonical(payload: object) -> bytes:
        return (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")

    def _approval_payload(self, **overrides):
        payload = {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_attempt2_external_review_approval",
            "authorization_request_sha256": authorization.ATTEMPT2_AUTHORIZATION_REQUEST_SHA256,
            "reviewed_runner_commit": authorization.ATTEMPT2_REVIEWED_RUNNER_COMMIT,
            "authorized_execution_commit": self.head,
            "approved_for_exactly_one_execution": True,
            "locked_test_used": False,
        }
        payload.update(overrides)
        return payload

    def _write_approval(self, payload=None, *, raw=None) -> Path:
        path = self.root / authorization.ATTEMPT2_EXTERNAL_APPROVAL_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            raw if raw is not None else self._canonical(payload or self._approval_payload())
        )
        return path

    def _git_patches(self, *, head=None, clean=True, changed=None, runner_unchanged=True):
        return (
            mock.patch.object(authorization, "_git_head", return_value=head or self.head),
            mock.patch.object(authorization, "_git_worktree_clean", return_value=clean),
            mock.patch.object(
                authorization,
                "_attempt2_git_diff_names",
                return_value=(
                    authorization.ATTEMPT2_AUTHORIZATION_STEP_PATHS
                    if changed is None
                    else frozenset(changed)
                ),
            ),
            mock.patch.object(
                authorization,
                "_attempt2_runner_blob_unchanged",
                return_value=runner_unchanged,
            ),
            mock.patch.object(authorization, "_tensorflow_imported", return_value=False),
        )

    def test_request_is_exact_and_attempt1_state_does_not_authorize_attempt2(self) -> None:
        payload = authorization.load_sealed_attempt2_authorization_request(self.root)
        request = self.root / authorization.ATTEMPT2_AUTHORIZATION_REQUEST_RELATIVE_PATH
        self.assertEqual(
            hashlib.sha256(request.read_bytes()).hexdigest(),
            authorization.ATTEMPT2_AUTHORIZATION_REQUEST_SHA256,
        )
        self.assertEqual(
            payload["prior_attempt_classification"],
            "premetric_infrastructure_failure",
        )
        self.assertTrue(payload["prior_authorization_consumed"])
        self.assertTrue(self.old_marker.is_file())
        self.assertTrue(self.old_approval.is_file())

    def test_attempt2_approval_absent_fails_before_attempt2_marker(self) -> None:
        marker = self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH
        with mock.patch.object(runner, "run_authorized_independent_v2") as run:
            with self.assertRaisesRegex(RuntimeError, "attempt2.*approval file is absent"):
                authorization.execute_externally_approved_independent_v2_attempt2_once(
                    self.root
                )
        self.assertFalse(marker.exists())
        self.assertTrue(self.old_marker.is_file())
        run.assert_not_called()

    def test_attempt1_approval_cannot_authorize_attempt2(self) -> None:
        attempt1_payload = {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_external_review_approval",
            "authorization_request_sha256": authorization.AUTHORIZATION_REQUEST_SHA256,
            "reviewed_runner_commit": authorization.REVIEWED_RUNNER_COMMIT,
            "authorized_execution_commit": self.head,
            "approved_for_exactly_one_execution": True,
            "locked_test_used": False,
        }
        self._write_approval(attempt1_payload)
        with self.assertRaisesRegex(ValueError, "attempt2.*values are not sealed"):
            authorization.execute_externally_approved_independent_v2_attempt2_once(
                self.root
            )
        self.assertFalse(
            (self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH).exists()
        )

    def test_attempt2_wrong_commit_fails_before_marker(self) -> None:
        self._write_approval()
        patches = self._git_patches(head="b" * 40)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            with self.assertRaisesRegex(ValueError, "does not authorize current HEAD"):
                authorization.execute_externally_approved_independent_v2_attempt2_once(
                    self.root
                )
        self.assertFalse(
            (self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH).exists()
        )

    def test_attempt2_happy_path_claims_distinct_marker_and_calls_runner_once(self) -> None:
        approval_path = self._write_approval()
        marker = self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH
        captured = []

        def run(root, capability):
            self.assertTrue(marker.is_file())
            self.assertTrue(self.old_marker.is_file())
            self.assertIn(id(capability), runner._ONE_JOB_CAPABILITIES)
            captured.append(capability)
            return {"synthetic_attempt2": True}

        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(
                    runner, "run_authorized_independent_v2", side_effect=run
                ) as mocked:
            result = authorization.execute_externally_approved_independent_v2_attempt2_once(
                self.root
            )
        self.assertEqual(result, {"synthetic_attempt2": True})
        mocked.assert_called_once()
        capability = captured[0]
        self.assertEqual(capability.runner_commit, self.head)
        self.assertEqual(capability.job_id, authorization.ATTEMPT2_JOB_ID)
        self.assertEqual(capability.destination, authorization.ATTEMPT2_DESTINATION)
        self.assertEqual(capability.device, "cpu")
        self.assertEqual(capability.wall_timeout_seconds, 900)
        self.assertTrue(capability.stop_after_report)
        self.assertFalse(capability.locked_test_used)
        marker_payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(
            marker_payload["authorization_request_sha256"],
            authorization.ATTEMPT2_AUTHORIZATION_REQUEST_SHA256,
        )
        self.assertEqual(
            marker_payload["external_approval_sha256"],
            hashlib.sha256(approval_path.read_bytes()).hexdigest(),
        )
        self.assertTrue(marker_payload["prior_authorization_consumed"])

    def test_attempt2_marker_is_o_excl_and_persistent_after_failure(self) -> None:
        self._write_approval()
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(
                    runner,
                    "run_authorized_independent_v2",
                    side_effect=RuntimeError("synthetic attempt2 post-claim failure"),
                ) as run:
            with self.assertRaisesRegex(RuntimeError, "post-claim failure"):
                authorization.execute_externally_approved_independent_v2_attempt2_once(
                    self.root
                )
            marker = self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH
            self.assertTrue(marker.is_file())
            with self.assertRaises(FileExistsError):
                authorization.execute_externally_approved_independent_v2_attempt2_once(
                    self.root
                )
        run.assert_called_once()


class IndependentV2OneJobAuthorizationContinuationTests(unittest.TestCase):
    setUp = IndependentV2OneJobAuthorizationTests.setUp
    _clean_registry = IndependentV2OneJobAuthorizationTests._clean_registry
    _restore_force_cpu = IndependentV2OneJobAuthorizationTests._restore_force_cpu
    _canonical = staticmethod(IndependentV2OneJobAuthorizationTests._canonical)
    _approval_payload = IndependentV2OneJobAuthorizationTests._approval_payload
    _write_approval = IndependentV2OneJobAuthorizationTests._write_approval
    _git_patches = IndependentV2OneJobAuthorizationTests._git_patches

    def test_malformed_or_mismatched_approval_fails_before_marker(self) -> None:
        cases = (
            (None, b"{\n", "valid UTF-8 JSON"),
            ({"authorization_request_sha256": "0" * 64}, None, "values are not sealed"),
            ({"reviewed_runner_commit": "0" * 40}, None, "values are not sealed"),
        )
        for overrides, raw, message in cases:
            with self.subTest(message=message):
                path = self.root / authorization.EXTERNAL_APPROVAL_RELATIVE_PATH
                path.unlink(missing_ok=True)
                payload = self._approval_payload(**(overrides or {}))
                self._write_approval(payload, raw=raw)
                with self.assertRaisesRegex(ValueError, message):
                    authorization.execute_externally_approved_independent_v2_once(self.root)
                self.assertFalse((self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH).exists())

    def test_git_boundary_rejects_wrong_head_dirty_runner_or_diff(self) -> None:
        self._write_approval()
        cases = (
            ({"head": "f" * 40}, "current HEAD"),
            ({"clean": False}, "clean worktree"),
            ({"runner_unchanged": False}, "runner changed"),
            ({"changed": {"unexpected.py"}}, "unexpected changed file set"),
        )
        for options, message in cases:
            with self.subTest(message=message):
                marker = self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH
                marker.unlink(missing_ok=True)
                patches = self._git_patches(**options)
                with patches[0], patches[1], patches[2], patches[3], patches[4]:
                    with self.assertRaisesRegex((ValueError, RuntimeError), message):
                        authorization.execute_externally_approved_independent_v2_once(self.root)
                self.assertFalse(marker.exists())

    def test_happy_path_builds_exact_capability_after_marker_and_calls_once(self) -> None:
        approval_path = self._write_approval()
        marker = self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH
        captured = []

        def run(root, capability):
            self.assertTrue(marker.is_file())
            self.assertIn(id(capability), runner._ONE_JOB_CAPABILITIES)
            self.assertIs(runner._ONE_JOB_CAPABILITIES[id(capability)](), capability)
            self.assertEqual(os.environ.get("MIDI_FORCE_CPU"), "1")
            captured.append(capability)
            return {"synthetic": True}

        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(runner, "run_authorized_independent_v2", side_effect=run) as mocked:
            result = authorization.execute_externally_approved_independent_v2_once(self.root)
        self.assertEqual(result, {"synthetic": True})
        mocked.assert_called_once()
        capability = captured[0]
        self.assertEqual(capability.runner_commit, self.head)
        self.assertEqual(capability.execution_contract_sha256, authorization.EXECUTION_CONTRACT_SHA256)
        self.assertEqual(capability.device, "cpu")
        self.assertEqual(capability.wall_timeout_seconds, 900)
        self.assertEqual(capability.job_id, authorization.JOB_ID)
        self.assertEqual(capability.destination, authorization.DESTINATION)
        self.assertTrue(capability.stop_after_report)
        self.assertFalse(capability.locked_test_used)
        self.assertTrue(capability.single_execution_authorization)
        self.assertEqual(os.environ.get("MIDI_FORCE_CPU"), "1")
        marker_payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(marker_payload["authorization_request_sha256"], authorization.AUTHORIZATION_REQUEST_SHA256)
        self.assertEqual(marker_payload["external_approval_sha256"], hashlib.sha256(approval_path.read_bytes()).hexdigest())
        self.assertEqual(marker_payload["authorized_execution_commit"], self.head)

    def test_marker_is_o_excl_persistent_and_prevents_second_invocation(self) -> None:
        self._write_approval()
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(runner, "run_authorized_independent_v2", side_effect=RuntimeError("post-claim failure")) as run:
            with self.assertRaisesRegex(RuntimeError, "post-claim failure"):
                authorization.execute_externally_approved_independent_v2_once(self.root)
            marker = self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH
            self.assertTrue(marker.is_file())
            with self.assertRaises(FileExistsError):
                authorization.execute_externally_approved_independent_v2_once(self.root)
        run.assert_called_once()

    def test_tensorflow_preimport_fails_after_persistent_claim_before_runner(self) -> None:
        self._write_approval()
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], \
                mock.patch.object(authorization, "_tensorflow_imported", return_value=True), \
                mock.patch.object(runner, "run_authorized_independent_v2") as run:
            with self.assertRaisesRegex(RuntimeError, "TensorFlow was imported"):
                authorization.execute_externally_approved_independent_v2_once(self.root)
        self.assertTrue((self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH).is_file())
        run.assert_not_called()


class IndependentV2Attempt3AuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = self.root / authorization.ATTEMPT3_AUTHORIZATION_REQUEST_RELATIVE_PATH
        request.parent.mkdir(parents=True)
        source = (
            Path(__file__).resolve().parents[1]
            / authorization.ATTEMPT3_AUTHORIZATION_REQUEST_RELATIVE_PATH
        )
        request.write_bytes(source.read_bytes())
        self.head = "c" * 40
        for marker_path in (
            authorization.PERSISTENT_CLAIM_RELATIVE_PATH,
            authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH,
        ):
            marker = self.root / marker_path
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_bytes(b"historical-consumed-marker")
        for approval_path in (
            authorization.EXTERNAL_APPROVAL_RELATIVE_PATH,
            authorization.ATTEMPT2_EXTERNAL_APPROVAL_RELATIVE_PATH,
        ):
            approval = self.root / approval_path
            approval.parent.mkdir(parents=True, exist_ok=True)
            approval.write_bytes(b"historical-approval-without-attempt3-authority")
        self._previous_force_cpu = os.environ.get("MIDI_FORCE_CPU")
        self.addCleanup(self._restore_force_cpu)
        self._registry_before = set(runner._ONE_JOB_CAPABILITIES)
        self.addCleanup(self._clean_registry)

    def _clean_registry(self) -> None:
        for key in set(runner._ONE_JOB_CAPABILITIES) - self._registry_before:
            runner._ONE_JOB_CAPABILITIES.pop(key, None)
            runner._CLAIMED_ONE_JOB_CAPABILITIES.pop(key, None)

    def _restore_force_cpu(self) -> None:
        if self._previous_force_cpu is None:
            os.environ.pop("MIDI_FORCE_CPU", None)
        else:
            os.environ["MIDI_FORCE_CPU"] = self._previous_force_cpu

    @staticmethod
    def _canonical(payload: object) -> bytes:
        return (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")

    def _approval_payload(self, **overrides):
        payload = {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_attempt3_external_review_approval",
            "authorization_request_sha256": authorization.ATTEMPT3_AUTHORIZATION_REQUEST_SHA256,
            "reviewed_runner_commit": authorization.ATTEMPT3_REVIEWED_RUNNER_COMMIT,
            "authorized_execution_commit": self.head,
            "approved_for_exactly_one_execution": True,
            "locked_test_used": False,
        }
        payload.update(overrides)
        return payload

    def _write_approval(self, payload=None) -> Path:
        path = self.root / authorization.ATTEMPT3_EXTERNAL_APPROVAL_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self._canonical(payload or self._approval_payload()))
        return path

    def _git_patches(self, *, head=None, clean=True, changed=None, runner_unchanged=True):
        return (
            mock.patch.object(authorization, "_git_head", return_value=head or self.head),
            mock.patch.object(authorization, "_git_worktree_clean", return_value=clean),
            mock.patch.object(
                authorization,
                "_attempt3_git_diff_names",
                return_value=(
                    authorization.ATTEMPT3_AUTHORIZATION_STEP_PATHS
                    if changed is None
                    else frozenset(changed)
                ),
            ),
            mock.patch.object(
                authorization,
                "_attempt3_runner_blob_unchanged",
                return_value=runner_unchanged,
            ),
            mock.patch.object(authorization, "_tensorflow_imported", return_value=False),
        )

    def test_request_seals_both_failures_and_unconsumed_scientific_cohort(self) -> None:
        payload = authorization.load_sealed_attempt3_authorization_request(self.root)
        request = self.root / authorization.ATTEMPT3_AUTHORIZATION_REQUEST_RELATIVE_PATH
        self.assertEqual(
            hashlib.sha256(request.read_bytes()).hexdigest(),
            authorization.ATTEMPT3_AUTHORIZATION_REQUEST_SHA256,
        )
        self.assertTrue(payload["attempt1_authorization_consumed"])
        self.assertTrue(payload["attempt2_authorization_consumed"])
        self.assertEqual(payload["attempt1_classification"], "premetric_infrastructure_failure")
        self.assertEqual(payload["attempt2_classification"], "premetric_infrastructure_failure")
        self.assertFalse(payload["scientific_cohort_consumed"])
        self.assertFalse(payload["ab_metrics_produced"])
        self.assertFalse(payload["ab_metrics_observed"])
        self.assertTrue(payload["worker_registry_materialized"])

    def test_old_markers_and_approvals_never_authorize_attempt3(self) -> None:
        self.assertTrue((self.root / authorization.PERSISTENT_CLAIM_RELATIVE_PATH).is_file())
        self.assertTrue((self.root / authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH).is_file())
        marker3 = self.root / authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH
        with self.assertRaisesRegex(RuntimeError, "attempt3.*approval file is absent"):
            authorization.execute_externally_approved_independent_v2_attempt3_once(self.root)
        self.assertFalse(marker3.exists())

        old_payloads = (
            {
                "schema_version": 1,
                "purpose": "causal_candidate_v2_independent_validation_external_review_approval",
                "authorization_request_sha256": authorization.AUTHORIZATION_REQUEST_SHA256,
                "reviewed_runner_commit": authorization.REVIEWED_RUNNER_COMMIT,
                "authorized_execution_commit": self.head,
                "approved_for_exactly_one_execution": True,
                "locked_test_used": False,
            },
            {
                "schema_version": 1,
                "purpose": "causal_candidate_v2_independent_validation_attempt2_external_review_approval",
                "authorization_request_sha256": authorization.ATTEMPT2_AUTHORIZATION_REQUEST_SHA256,
                "reviewed_runner_commit": authorization.ATTEMPT2_REVIEWED_RUNNER_COMMIT,
                "authorized_execution_commit": self.head,
                "approved_for_exactly_one_execution": True,
                "locked_test_used": False,
            },
        )
        for payload in old_payloads:
            with self.subTest(purpose=payload["purpose"]):
                self._write_approval(payload)
                with self.assertRaisesRegex(ValueError, "attempt3.*values are not sealed"):
                    authorization.execute_externally_approved_independent_v2_attempt3_once(
                        self.root
                    )
                self.assertFalse(marker3.exists())

    def test_worker_registry_absent_or_wrong_fails_before_marker(self) -> None:
        self._write_approval()
        marker = self.root / authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            with self.assertRaisesRegex(RuntimeError, "registry is absent"):
                authorization.execute_externally_approved_independent_v2_attempt3_once(
                    self.root
                )
        self.assertFalse(marker.exists())

        registry = self.root / authorization.ATTEMPT3_WORKER_REGISTRY_RELATIVE_PATH
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_bytes(b"synthetic wrong registry bytes")
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                authorization.execute_externally_approved_independent_v2_attempt3_once(
                    self.root
                )
        self.assertFalse(marker.exists())

    def test_good_synthetic_registry_is_byte_checked_without_tensorflow(self) -> None:
        registry = self.root / authorization.ATTEMPT3_WORKER_REGISTRY_RELATIVE_PATH
        registry.parent.mkdir(parents=True, exist_ok=True)
        raw = b"synthetic registry only; no project asset"
        registry.write_bytes(raw)
        with mock.patch.object(
            authorization,
            "ATTEMPT3_WORKER_REGISTRY_SHA256",
            hashlib.sha256(raw).hexdigest(),
        ):
            checked = authorization._require_attempt3_worker_registry(self.root)
        self.assertEqual(checked, registry.resolve())
        self.assertNotIn("tensorflow", sys.modules)

    def test_git_boundary_rejects_wrong_head_diff_or_runner_before_marker(self) -> None:
        self._write_approval()
        cases = (
            ({"head": "d" * 40}, "current HEAD"),
            ({"changed": {"unexpected.py"}}, "unexpected changed file set"),
            ({"runner_unchanged": False}, "runner changed"),
        )
        for options, message in cases:
            with self.subTest(message=message):
                patches = self._git_patches(**options)
                with patches[0], patches[1], patches[2], patches[3], patches[4]:
                    with self.assertRaisesRegex((ValueError, RuntimeError), message):
                        authorization.execute_externally_approved_independent_v2_attempt3_once(
                            self.root
                        )
                self.assertFalse(
                    (self.root / authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH).exists()
                )

    def test_happy_path_checks_registry_before_marker_and_calls_runner_once(self) -> None:
        approval = self._write_approval()
        marker = self.root / authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH
        order = []
        captured = []

        def check_registry(root):
            self.assertFalse(marker.exists())
            order.append("registry")
            return root / authorization.ATTEMPT3_WORKER_REGISTRY_RELATIVE_PATH

        original_marker = authorization._create_attempt3_persistent_claim_marker

        def create_marker(*args, **kwargs):
            order.append("marker")
            return original_marker(*args, **kwargs)

        def run(root, capability):
            order.append("runner")
            self.assertTrue(marker.is_file())
            captured.append(capability)
            return {"synthetic_attempt3": True}

        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(authorization, "_require_attempt3_worker_registry", side_effect=check_registry), \
                mock.patch.object(authorization, "_create_attempt3_persistent_claim_marker", side_effect=create_marker), \
                mock.patch.object(runner, "run_authorized_independent_v2", side_effect=run) as mocked:
            result = authorization.execute_externally_approved_independent_v2_attempt3_once(
                self.root
            )
        self.assertEqual(result, {"synthetic_attempt3": True})
        self.assertEqual(order, ["registry", "marker", "runner"])
        mocked.assert_called_once()
        capability = captured[0]
        self.assertEqual(capability.job_id, authorization.ATTEMPT3_JOB_ID)
        self.assertEqual(capability.destination, authorization.ATTEMPT3_DESTINATION)
        self.assertEqual(capability.runner_commit, self.head)
        marker_payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(
            marker_payload["external_approval_sha256"],
            hashlib.sha256(approval.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            marker_payload["worker_registry_sha256"],
            authorization.ATTEMPT3_WORKER_REGISTRY_SHA256,
        )

    def test_attempt3_marker_is_o_excl_and_persistent_after_failure(self) -> None:
        self._write_approval()
        patches = self._git_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                mock.patch.object(authorization, "_require_attempt3_worker_registry"), \
                mock.patch.object(
                    runner,
                    "run_authorized_independent_v2",
                    side_effect=RuntimeError("synthetic attempt3 post-claim failure"),
                ) as run:
            with self.assertRaisesRegex(RuntimeError, "post-claim failure"):
                authorization.execute_externally_approved_independent_v2_attempt3_once(
                    self.root
                )
            marker = self.root / authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH
            self.assertTrue(marker.is_file())
            with self.assertRaises(FileExistsError):
                authorization.execute_externally_approved_independent_v2_attempt3_once(
                    self.root
                )
        run.assert_called_once()


class IndependentV2Attempt4AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "worker" / "repository"; self.root.mkdir(parents=True)
        target = self.root / authorization.ATTEMPT4_AUTHORIZATION_REQUEST_RELATIVE_PATH
        target.parent.mkdir(parents=True)
        target.write_bytes((Path(__file__).resolve().parents[1] / authorization.ATTEMPT4_AUTHORIZATION_REQUEST_RELATIVE_PATH).read_bytes())
        self.old = os.environ.get("MIDI_DATA_ROOT"); self.addCleanup(self._restore)

    def _restore(self):
        if self.old is None: os.environ.pop("MIDI_DATA_ROOT", None)
        else: os.environ["MIDI_DATA_ROOT"] = self.old

    def test_attempt4_request_records_three_consumed_premetric_attempts(self):
        payload = authorization.load_sealed_attempt4_authorization_request(self.root)
        self.assertTrue(payload["attempt3_authorization_consumed"])
        self.assertEqual(payload["attempt3_classification"], "premetric_infrastructure_failure_asset_path_resolution")
        self.assertFalse(payload["scientific_cohort_consumed"])
        self.assertEqual(payload["data_root_strategy"], "worker_root/data")

    def test_attempt4_request_and_approval_reject_bool_int_aliases_and_old_purposes(self):
        request = dict(authorization.load_sealed_attempt4_authorization_request(self.root))
        for field, value in (("stop_after_report", 1), ("schema_version", True), ("wall_timeout_seconds", True)):
            bad=dict(request); bad[field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "values are not sealed"):
                authorization._require_exact_attempt4_request(bad)
        base = {"schema_version": 1, "purpose": "causal_candidate_v2_independent_validation_attempt4_external_review_approval", "authorization_request_sha256": authorization.ATTEMPT4_AUTHORIZATION_REQUEST_SHA256, "reviewed_runner_commit": authorization.ATTEMPT4_REVIEWED_RUNNER_COMMIT, "authorized_execution_commit": "a" * 40, "approved_for_exactly_one_execution": True, "locked_test_used": False}
        path = self.root / authorization.ATTEMPT4_EXTERNAL_APPROVAL_RELATIVE_PATH; path.parent.mkdir(parents=True, exist_ok=True)
        for change in ({"approved_for_exactly_one_execution": 1}, {"locked_test_used": 0}, {"purpose": "causal_candidate_v2_independent_validation_external_review_approval"}, {"purpose": "causal_candidate_v2_independent_validation_attempt2_external_review_approval"}, {"purpose": "causal_candidate_v2_independent_validation_attempt3_external_review_approval"}):
            payload = dict(base); payload.update(change); path.write_bytes(self._canonical(payload))
            with self.assertRaisesRegex(ValueError, "values are not sealed"):
                authorization._load_attempt4_external_approval(self.root, authorization.load_sealed_attempt4_authorization_request(self.root))

    def test_old_markers_do_not_authorize_and_absent_attempt4_approval_creates_no_marker(self):
        for relative in (authorization.PERSISTENT_CLAIM_RELATIVE_PATH, authorization.ATTEMPT2_PERSISTENT_CLAIM_RELATIVE_PATH, authorization.ATTEMPT3_PERSISTENT_CLAIM_RELATIVE_PATH):
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("consumed")
        with self.assertRaisesRegex(RuntimeError, "attempt4.*approval file is absent"):
            authorization.execute_externally_approved_independent_v2_attempt4_once(self.root)
        self.assertFalse((self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH).exists())

    @staticmethod
    def _canonical(payload):
        return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()

    def test_absent_data_root_and_conflicting_environment_fail_before_marker(self):
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        with self.assertRaisesRegex(RuntimeError, "data root"):
            authorization._require_attempt4_data_root_and_items(self.root)
        self.assertFalse(marker.exists())
        (self.root.parent / "data").mkdir()
        os.environ["MIDI_DATA_ROOT"] = str(self.root.parent / "other")
        with self.assertRaisesRegex(RuntimeError, "conflicts"):
            authorization._require_attempt4_data_root_and_items(self.root)
        self.assertFalse(marker.exists())

    def test_good_data_root_is_fixed_before_tensorflow_free_manifest_stage(self):
        data_root = self.root.parent / "data"; data_root.mkdir()
        sentinel = object()
        with mock.patch.object(authorization, "_tensorflow_imported", return_value=False), \
             mock.patch("src.polyphonic.run_causal_candidate_v2_independent_validation.load_sealed_independent_v2_validation_cohort", side_effect=RuntimeError("manifest-stage")):
            with self.assertRaisesRegex(RuntimeError, "manifest-stage"):
                authorization._require_attempt4_data_root_and_items(self.root)
        self.assertEqual(os.environ["MIDI_DATA_ROOT"], str(data_root))
        self.assertIsNotNone(sentinel)

    def test_attempt4_marker_is_o_excl_and_persistent(self):
        first = authorization._create_attempt4_marker(self.root, "a" * 64, "b" * 40)
        self.assertTrue(first.is_file())
        with self.assertRaises(FileExistsError):
            authorization._create_attempt4_marker(self.root, "a" * 64, "b" * 40)

    def _synthetic_items(self):
        data = self.root.parent / "data"; data.mkdir(exist_ok=True)
        items = []
        datasets = ("gaps_poly_mix", "guitar_techs_poly_directinput", "guitar_techs_poly_micamp")
        for index in range(30):
            audio = data / f"audio-{index}.npy"; label = data / f"label-{index}.npz"
            audio.touch(); label.touch()
            items.append(SimpleNamespace(key=f"key-{index}", dataset_id=datasets[index // 10], audio_path=audio, labels_path=label))
        return data, items

    def _preflight_with_items(self, items, keys=None):
        from src.polyphonic import manifest_snapshot, run_causal_candidate_v2_independent_validation as cohort_module
        from src.polyphonic import causal_candidate_v2_independent_asset_evidence as evidence
        cohort = SimpleNamespace(recording_keys=tuple(keys or [x.key for x in items]))
        snapshot = SimpleNamespace(items=tuple(items))
        with mock.patch.object(cohort_module, "load_sealed_independent_v2_validation_cohort", return_value=cohort), \
             mock.patch.object(cohort_module, "require_sealed_independent_v2_validation_cohort", side_effect=lambda value: value), \
             mock.patch.object(manifest_snapshot, "load_manifest_snapshot", return_value=snapshot), \
             mock.patch.object(evidence, "canonical_recording_key", side_effect=lambda item: item.key), \
             mock.patch.object(authorization, "_tensorflow_imported", return_value=False):
            return authorization._require_attempt4_data_root_and_items(self.root)

    def test_exact_thirty_paths_pass_without_content_reads(self):
        data, items = self._synthetic_items()
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("asset content read")), \
             mock.patch.object(Path, "open", side_effect=AssertionError("asset Path.open")), \
             mock.patch("builtins.open", side_effect=AssertionError("asset builtins.open")), \
             mock.patch.object(authorization.hashlib, "sha256", side_effect=AssertionError("asset content hash")):
            resolved, selected = self._preflight_with_items(items)
        self.assertEqual(resolved, data)
        self.assertEqual(len(selected), 30)

    def test_incorrect_expected_production_data_root_fails_before_marker(self):
        (self.root.parent / "data").mkdir()
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        with self.assertRaisesRegex(RuntimeError, "production data root differs"):
            authorization._require_attempt4_data_root_and_items(
                self.root,
                expected_production_data_root="/Users/amcarene/midi-worker/not-the-sealed-data-root",
            )
        self.assertFalse(marker.exists())

    def test_nonsymlink_noncanonical_data_root_fails_before_marker(self):
        data = self.root.parent / "data"
        data.mkdir()
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        original_resolve = Path.resolve

        def noncanonical_resolve(path, strict=False):
            if path == data:
                return data.parent / "different-canonical-data"
            return original_resolve(path, strict=strict)

        with mock.patch.object(Path, "is_symlink", autospec=True, return_value=False), \
             mock.patch.object(Path, "resolve", autospec=True, side_effect=noncanonical_resolve), \
             self.assertRaisesRegex(RuntimeError, "data root"):
            authorization._require_attempt4_data_root_and_items(self.root)
        self.assertFalse(marker.exists())

    def test_missing_key_bad_count_and_missing_asset_fail_before_marker(self):
        _, items = self._synthetic_items()
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        with self.assertRaisesRegex(RuntimeError, "recording key"):
            self._preflight_with_items(items, keys=[x.key for x in items[:-1]] + ["missing"])
        items[0].dataset_id = "guitarset_poly_mix"
        with self.assertRaisesRegex(RuntimeError, "dataset counts"):
            self._preflight_with_items(items)
        items[0].dataset_id = "gaps_poly_mix"; items[0].audio_path.unlink()
        with self.assertRaisesRegex(RuntimeError, "audio path"):
            self._preflight_with_items(items)
        self.assertFalse(marker.exists())

    def test_tensorflow_detection_fails_before_marker(self):
        data = self.root.parent / "data"; data.mkdir(exist_ok=True)
        with mock.patch.object(authorization, "_tensorflow_imported", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "TensorFlow"):
                authorization._require_attempt4_data_root_and_items(self.root)
        self.assertFalse((self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH).exists())

    def test_registry_absent_and_wrong_sha_fail_before_attempt4_marker(self):
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        with self.assertRaisesRegex(RuntimeError, "registry is absent"):
            authorization._require_attempt3_worker_registry(self.root)
        registry = self.root / authorization.ATTEMPT3_WORKER_REGISTRY_RELATIVE_PATH
        registry.parent.mkdir(parents=True, exist_ok=True); registry.write_bytes(b"wrong")
        with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
            authorization._require_attempt3_worker_registry(self.root)
        self.assertFalse(marker.exists())

    def test_label_absent_and_path_escape_fail_before_marker(self):
        data, items = self._synthetic_items(); marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        items[0].labels_path.unlink()
        with self.assertRaisesRegex(RuntimeError, "label path"):
            self._preflight_with_items(items)
        items[0].labels_path.touch(); outside = self.root / "outside.npy"; outside.touch(); items[0].audio_path = outside
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            self._preflight_with_items(items)
        self.assertFalse(marker.exists()); self.assertTrue(data.is_dir())

    def test_label_path_escape_fails_before_marker(self):
        _, items = self._synthetic_items()
        marker = self.root / authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        outside = self.root / "outside-label.npz"
        outside.touch()
        items[0].labels_path = outside
        with self.assertRaisesRegex(RuntimeError, "label path escapes worker data root"):
            self._preflight_with_items(items)
        self.assertFalse(marker.exists())

    def test_attempt4_happy_order_and_exact_capability(self):
        order=[]; captured=[]; commit="c"*40
        def step(name, value=None):
            def call(*args, **kwargs): order.append(name); return value
            return call
        with mock.patch.object(authorization, "load_sealed_attempt4_authorization_request", side_effect=step("request", {"expected_production_data_root": str(authorization.ATTEMPT4_PRODUCTION_DATA_ROOT)})), \
             mock.patch.object(authorization, "_load_attempt4_external_approval", side_effect=step("approval", ({"authorized_execution_commit": commit}, "d"*64))), \
             mock.patch.object(authorization, "_verify_attempt4_git_boundary", side_effect=step("git", commit)), \
             mock.patch.object(authorization, "_require_attempt3_worker_registry", side_effect=step("registry", self.root)), \
             mock.patch.object(authorization, "_require_attempt4_data_root_and_items", side_effect=step("data", (self.root, tuple()))), \
             mock.patch.object(authorization, "_create_attempt4_marker", side_effect=step("marker", self.root)), \
             mock.patch.object(authorization, "_tensorflow_imported", return_value=False), \
             mock.patch.object(runner, "run_authorized_independent_v2", side_effect=lambda root, cap: (order.append("runner"), captured.append(cap), {"ok":True})[-1]):
            result=authorization.execute_externally_approved_independent_v2_attempt4_once(self.root)
        self.assertEqual(result,{"ok":True}); self.assertEqual(order,["request","approval","git","registry","data","marker","runner"])
        cap=captured[0]; self.assertEqual((cap.runner_commit,cap.execution_contract_sha256,cap.device,cap.wall_timeout_seconds,cap.job_id,cap.destination,cap.stop_after_report,cap.locked_test_used,cap.single_execution_authorization),(commit,authorization.EXECUTION_CONTRACT_SHA256,"cpu",900,authorization.ATTEMPT4_JOB_ID,authorization.ATTEMPT4_DESTINATION,True,False,True))

    def test_midi_data_root_textual_alias_is_rejected(self):
        data=self.root.parent/"data"; data.mkdir(exist_ok=True)
        os.environ["MIDI_DATA_ROOT"] = str(data / ".." / "data")
        with self.assertRaisesRegex(RuntimeError, "conflicts"):
            authorization._require_attempt4_data_root_and_items(self.root)

    def test_tensorflow_appearing_during_path_preflight_is_rejected(self):
        _, items=self._synthetic_items()
        from src.polyphonic import manifest_snapshot, run_causal_candidate_v2_independent_validation as cm
        from src.polyphonic import causal_candidate_v2_independent_asset_evidence as ev
        cohort=SimpleNamespace(recording_keys=tuple(x.key for x in items)); snapshot=SimpleNamespace(items=tuple(items))
        with mock.patch.object(cm,"load_sealed_independent_v2_validation_cohort",return_value=cohort), mock.patch.object(cm,"require_sealed_independent_v2_validation_cohort",side_effect=lambda x:x), mock.patch.object(manifest_snapshot,"load_manifest_snapshot",return_value=snapshot), mock.patch.object(ev,"canonical_recording_key",side_effect=lambda x:x.key), mock.patch.object(authorization,"_tensorflow_imported",side_effect=[False,True]):
            with self.assertRaisesRegex(RuntimeError,"during attempt4"):
                authorization._require_attempt4_data_root_and_items(self.root)

    def test_attempt4_git_boundary_cases_fail(self):
        approval={"authorized_execution_commit":"a"*40}
        cases=(("b"*40,True,authorization.ATTEMPT4_AUTHORIZATION_STEP_PATHS,True,"current HEAD"),("a"*40,False,authorization.ATTEMPT4_AUTHORIZATION_STEP_PATHS,True,"clean worktree"),("a"*40,True,frozenset({"bad"}),True,"unexpected changed"),("a"*40,True,authorization.ATTEMPT4_AUTHORIZATION_STEP_PATHS,False,"runner changed"))
        for head,clean,names,runner_ok,message in cases:
            with self.subTest(message=message), mock.patch.object(authorization,"_git_head",return_value=head), mock.patch.object(authorization,"_git_worktree_clean",return_value=clean), mock.patch.object(authorization,"_git",return_value="\n".join(names)), mock.patch("subprocess.run") as run:
                run.side_effect=[SimpleNamespace(stdout=b"same"),SimpleNamespace(stdout=b"same" if runner_ok else b"different")]
                with self.assertRaisesRegex((ValueError,RuntimeError),message): authorization._verify_attempt4_git_boundary(self.root,approval)

    def test_data_root_and_asset_symlinks_are_rejected(self):
        data=self.root.parent/"data"; data.mkdir()
        original_is_symlink=Path.is_symlink
        with mock.patch.object(Path,"is_symlink",autospec=True,side_effect=lambda path: path==data or original_is_symlink(path)):
            with self.assertRaisesRegex(RuntimeError,"data root"):
                authorization._require_attempt4_data_root_and_items(self.root)
        _,items=self._synthetic_items()
        for field in ("audio_path","labels_path"):
            flagged=getattr(items[0],field)
            with self.subTest(field=field), mock.patch.object(Path,"is_symlink",autospec=True,side_effect=lambda path, flagged=flagged: path==flagged or original_is_symlink(path)), self.assertRaisesRegex(RuntimeError,"path"):
                self._preflight_with_items(items)

    def test_marker_parent_symlink_is_rejected(self):
        parent=(self.root/authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH).parent
        parent.parent.mkdir(parents=True,exist_ok=True)
        original_is_symlink=Path.is_symlink
        with mock.patch.object(Path,"is_symlink",autospec=True,side_effect=lambda path: path==parent or original_is_symlink(path)), self.assertRaisesRegex(ValueError,"marker directory"):
             authorization._create_attempt4_marker(self.root,"a"*64,"b"*40)

    def test_post_claim_failure_persists_marker_and_blocks_retry(self):
        commit="c"*40
        request={"expected_production_data_root":str(authorization.ATTEMPT4_PRODUCTION_DATA_ROOT)}
        marker=self.root/authorization.ATTEMPT4_PERSISTENT_CLAIM_RELATIVE_PATH
        with mock.patch.object(authorization,"load_sealed_attempt4_authorization_request",return_value=request), mock.patch.object(authorization,"_load_attempt4_external_approval",return_value=({"authorized_execution_commit":commit},"d"*64)), mock.patch.object(authorization,"_verify_attempt4_git_boundary",return_value=commit), mock.patch.object(authorization,"_require_attempt3_worker_registry"), mock.patch.object(authorization,"_require_attempt4_data_root_and_items"), mock.patch.object(authorization,"_tensorflow_imported",return_value=False), mock.patch.object(runner,"run_authorized_independent_v2",side_effect=RuntimeError("synthetic attempt4 post-claim failure")) as run:
            with self.assertRaisesRegex(RuntimeError,"post-claim failure"):
                authorization.execute_externally_approved_independent_v2_attempt4_once(self.root)
            self.assertTrue(marker.is_file())
            with self.assertRaises(FileExistsError):
                authorization.execute_externally_approved_independent_v2_attempt4_once(self.root)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
