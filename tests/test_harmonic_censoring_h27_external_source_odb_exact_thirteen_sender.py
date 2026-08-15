from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SENDER = ROOT / "scripts/h27_prepare_exact_thirteen_source_odb_delivery.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_sender_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_sender_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def identity(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "git_blob_sha1": blob(raw),
        "size_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


class TestH27ExternalSourceOdbExactThirteenSender(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h27_exact_thirteen_sender", SENDER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.binding = json.loads(BINDING.read_bytes())
        cls.seal = json.loads(SEAL.read_bytes())

    def test_sender_binding_and_seal_are_closed_and_exact(self) -> None:
        for path in (SENDER, BINDING, SEAL):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.binding["sender"], identity(SENDER))
        self.assertEqual(self.seal["sender"], identity(SENDER))
        self.assertEqual(self.seal["identity_binding"], identity(BINDING))
        self.assertEqual(set(self.binding), {
            "schema_version", "binding_id", "status", "sender",
            "approved_receiver_commit", "receiver", "receiver_identity_binding",
            "receiver_identity_binding_external_seal", "approved_contract",
            "approved_contract_external_seal", "identity_graph", "preparation_binding",
            "prepared_object_invariants", "normative_order", "current_state", "next_action",
        })
        self.assertEqual(set(self.seal), {
            "schema_version", "seal_id", "status", "identity_binding", "sender",
            "approved_receiver_commit", "receiver", "receiver_identity_binding",
            "receiver_identity_binding_external_seal", "approved_contract",
            "approved_contract_external_seal", "future_platform_exact",
            "future_acknowledgement_environment_exact", "future_arguments_forbidden",
            "future_sender_head_exact", "future_sender_branch_exact",
            "future_sender_worktree_clean_required", "future_git_repository_selector_prefix_exact",
            "future_git_environment", "future_checkout_file_reads_forbidden",
            "future_receiver_source_loaded_from_exact_reviewed_git_blob",
            "future_receiver_source_parsed_without_execution", "future_object_count_exact",
            "future_aggregate_raw_size_bytes",
            "future_all_thirteen_sender_blobs_rehashed_and_byte_equal_to_receiver_payloads",
            "future_receiver_identity_revalidated_after_all_thirteen_checks",
            "future_ssh_invocation_exact", "future_ssh_invocation_constructed_only",
            "future_ssh_execution_forbidden",
            "future_receiver_source_transport_forbidden_until_separate_review",
            "future_normative_order", "sender_externally_reviewed",
            "sender_preparation_executed", "ssh_invoked", "receiver_transported",
            "mac_acknowledgement_set", "object_delivery_executed", "source_odb_changed",
            "target_odb_changed", "import_executed", "detach_executed",
            "downstream_executed", "science_or_locked_test", "next_action",
        })
        for key in (
            "future_arguments_forbidden", "future_sender_worktree_clean_required",
            "future_checkout_file_reads_forbidden",
            "future_receiver_source_loaded_from_exact_reviewed_git_blob",
            "future_receiver_source_parsed_without_execution",
            "future_all_thirteen_sender_blobs_rehashed_and_byte_equal_to_receiver_payloads",
            "future_receiver_identity_revalidated_after_all_thirteen_checks",
            "future_ssh_invocation_constructed_only", "future_ssh_execution_forbidden",
            "future_receiver_source_transport_forbidden_until_separate_review",
        ):
            self.assertTrue(self.seal[key])
        for key in (
            "sender_externally_reviewed", "sender_preparation_executed", "ssh_invoked",
            "receiver_transported", "mac_acknowledgement_set", "object_delivery_executed",
            "source_odb_changed", "target_odb_changed", "import_executed",
            "detach_executed", "downstream_executed", "science_or_locked_test",
        ):
            self.assertFalse(self.seal[key])

    def test_git_environment_and_literal_repository_prefix_are_fail_closed(self) -> None:
        inherited = {
            "PATH": "safe", "GIT_DIR": "redirect", "git_object_directory": "redirect",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath",
        }
        cleaned = self.module.clean_git_environment(inherited)
        self.assertEqual(cleaned, {
            "PATH": "safe", "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
        })
        completed = subprocess.CompletedProcess([], 0, stdout=b"payload", stderr=b"")
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            result = self.module.run_git(("cat-file", "blob", "a" * 40))
        self.assertEqual(result.stdout, b"payload")
        command = run.call_args.args[0]
        self.assertEqual(tuple(command[: len(self.module.GIT_PREFIX)]), self.module.GIT_PREFIX)
        self.assertEqual(command[-3:], ["cat-file", "blob", "a" * 40])
        self.assertEqual(
            {key for key in run.call_args.kwargs["env"] if key.upper().startswith("GIT_")},
            {"GIT_TERMINAL_PROMPT", "GIT_NO_LAZY_FETCH"},
        )

    def test_exact_sender_state_requires_head_branch_and_cleanliness(self) -> None:
        good = [
            subprocess.CompletedProcess([], 0, stdout=(self.module.EXPECTED_HEAD + "\n").encode(), stderr=b""),
            subprocess.CompletedProcess([], 0, stdout=(self.module.EXPECTED_BRANCH + "\n").encode(), stderr=b""),
            subprocess.CompletedProcess([], 0, stdout=b"", stderr=b""),
        ]
        with mock.patch.object(self.module, "run_git", side_effect=good):
            self.module.verify_exact_sender_state()
        bad = list(good)
        bad[2] = subprocess.CompletedProcess([], 0, stdout=b"?? drift\n", stderr=b"")
        with mock.patch.object(self.module, "run_git", side_effect=bad):
            with self.assertRaisesRegex(PermissionError, "not clean"):
                self.module.verify_exact_sender_state()

    def test_receiver_and_all_thirteen_source_blobs_match_from_git_odb(self) -> None:
        receiver, aggregate = self.module.verify_receiver_graph_and_objects()
        self.assertEqual(len(receiver), self.module.RECEIVER["size_bytes"])
        self.assertEqual(hashlib.sha256(receiver).hexdigest(), self.module.RECEIVER["raw_sha256"])
        self.assertEqual(aggregate, 75730)

    def test_preparation_constructs_exact_transport_but_never_invokes_it(self) -> None:
        receiver = b"#!/usr/bin/env python3\n"
        events: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_exact_sender_state"),
            mock.patch.object(
                self.module, "verify_receiver_graph_and_objects",
                side_effect=lambda: (events.append("payloads_complete") or (receiver, 75730)),
            ),
            mock.patch.object(
                self.module, "require_identity",
                side_effect=lambda raw, expected: events.append("receiver_revalidated"),
            ) as revalidate,
            mock.patch.object(
                self.module, "validate_exact_ssh_invocation",
                side_effect=lambda: events.append("ssh_tuple_validated"),
            ) as validate_ssh,
            mock.patch.object(self.module.subprocess, "run") as run,
        ):
            prepared = self.module.prepare_exact_transport()
        run.assert_not_called()
        revalidate.assert_called_once_with(receiver, self.module.RECEIVER)
        validate_ssh.assert_called_once_with()
        self.assertEqual(events, [
            "payloads_complete", "receiver_revalidated", "ssh_tuple_validated",
        ])
        self.assertEqual(prepared.command, self.module.SSH_COMMAND)
        self.assertEqual(prepared.command_text, self.module.SSH_COMMAND_TEXT)
        self.assertEqual(prepared.receiver_source, receiver)
        self.assertFalse(prepared.transport_executed)
        self.assertFalse(prepared.summary()["ssh_invocation_exact"].startswith("git "))
        self.assertFalse(prepared.summary()["transport_executed"])

    def test_ack_is_local_preparation_only_and_zero_arguments(self) -> None:
        with (
            mock.patch.object(self.module.platform, "system", return_value="Windows"),
            mock.patch.object(self.module.os, "environ", {self.module.ACK_ENV: "1"}),
            mock.patch.object(self.module.sys, "argv", ["sender.py"]),
        ):
            self.module.require_platform_ack_and_zero_arguments()
        with (
            mock.patch.object(self.module.platform, "system", return_value="Windows"),
            mock.patch.object(self.module.os, "environ", {}),
            mock.patch.object(self.module.sys, "argv", ["sender.py"]),
        ):
            with self.assertRaisesRegex(PermissionError, self.module.ACK_ENV):
                self.module.require_platform_ack_and_zero_arguments()

    def test_sender_contains_no_ssh_execution_or_retry_path(self) -> None:
        tree = SENDER.read_text(encoding="utf-8")
        self.assertNotIn("def retry", tree.lower())
        self.assertNotIn("def cleanup", tree.lower())
        self.assertNotIn("def rollback", tree.lower())
        self.assertNotIn("def repair", tree.lower())
        self.assertNotIn("shell=True", tree)
        self.assertNotIn("Popen(", tree)
        self.assertNotIn("check_call(", tree)
        self.assertNotIn("check_output(", tree)


if __name__ == "__main__":
    unittest.main()
