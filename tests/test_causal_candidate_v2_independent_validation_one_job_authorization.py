from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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


if __name__ == "__main__":
    unittest.main()
