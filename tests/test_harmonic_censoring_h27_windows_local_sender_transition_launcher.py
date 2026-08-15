from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/h27_windows_local_sender_transition_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_windows_local_sender_transition_launcher_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_windows_local_sender_transition_launcher_identity_binding_external_seal.json"
EXECUTION_WORKTREE = Path(r"C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2")


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


class TestH27WindowsLocalSenderTransitionLauncher(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h27_windows_transition_launcher", LAUNCHER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.binding = json.loads(BINDING.read_bytes())
        cls.seal = json.loads(SEAL.read_bytes())

    def test_launcher_binding_seal_and_key_sets_are_exact(self) -> None:
        for path in (LAUNCHER, BINDING, SEAL):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.binding["launcher"], identity(LAUNCHER))
        self.assertEqual(self.seal["launcher"], identity(LAUNCHER))
        self.assertEqual(self.seal["identity_binding"], identity(BINDING))
        self.assertEqual(set(self.binding), {
            "schema_version", "binding_id", "status", "launcher",
            "approved_contract_commit", "approved_contract",
            "approved_contract_external_seal", "approved_sender", "review_topology",
            "execution_binding", "implementation_invariants", "normative_order",
            "current_state", "next_action",
        })
        self.assertEqual(set(self.seal), {
            "schema_version", "seal_id", "status", "identity_binding", "launcher",
            "approved_contract_commit", "approved_contract",
            "approved_contract_external_seal", "future_launcher_source_exact",
            "future_launcher_checkout_file_read_forbidden", "future_platform_exact",
            "future_acknowledgement_environment_exact", "future_arguments_forbidden",
            "future_execution_worktree_exact", "future_initial_head_exact",
            "future_historical_head_exact", "future_symbolic_head_exact",
            "future_remote_tracking_ref_exact", "future_network_git_operations_forbidden",
            "future_graph_blob_count_exact",
            "future_initial_snapshot_and_immediate_revalidation_required",
            "future_historical_reset_count_exact", "future_sender_invocation_count_exact",
            "future_sender_terminal_status_exact", "future_transport_executed_false_required",
            "future_restoration_attempt_count_exact",
            "future_pre_effect_tracked_raw_bytes_retained_in_memory",
            "future_original_tracked_raw_bytes_restored_by_exclusive_fsynced_atomic_sibling_replaces",
            "future_original_index_raw_bytes_restored_atomically",
            "future_exact_restored_state_required", "future_pre_effect_failure_not_consumed",
            "future_head_and_branch_reflogs_append_exactly_two_sealed_resets",
            "future_all_other_reflogs_unchanged_and_orig_head_exact",
            "future_post_effect_failure_consumed", "future_retry_forbidden",
            "future_restoration_failure_manual_intervention",
            "future_ssh_subprocess_forbidden", "future_normative_order",
            "launcher_externally_reviewed", "transition_acknowledgement_set",
            "historical_reset_executed", "sender_preparation_executed",
            "restoration_executed", "ssh_invoked", "remote_acknowledgement_set",
            "object_delivery_executed", "source_odb_changed", "target_odb_changed",
            "import_executed", "detach_executed", "downstream_executed",
            "science_or_locked_test", "next_action",
        })

    def test_git_environment_prefix_and_network_block_are_closed(self) -> None:
        cleaned = self.module.clean_git_environment({
            "PATH": "safe", "GIT_DIR": "bad", "git_index_file": "bad",
        })
        self.assertEqual(cleaned, {
            "PATH": "safe", "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
        })
        with self.assertRaisesRegex(PermissionError, "network"):
            self.module.run_git(("push", "origin"))
        completed = subprocess.CompletedProcess([], 0, stdout=b"ok", stderr=b"")
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            self.module.run_git(("rev-parse", "HEAD"))
        command = run.call_args.args[0]
        self.assertEqual(tuple(command[:len(self.module.GIT_PREFIX)]), self.module.GIT_PREFIX)

    def test_execution_worktree_is_still_exact_and_graph_loads_from_odb(self) -> None:
        head = subprocess.check_output(["git", "-C", str(EXECUTION_WORKTREE), "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "-C", str(EXECUTION_WORKTREE), "symbolic-ref", "-q", "HEAD"], text=True).strip()
        status = subprocess.check_output([
            "git", "-C", str(EXECUTION_WORKTREE), "status", "--porcelain=v1", "--untracked-files=all",
        ])
        self.assertEqual(head, self.module.INITIAL)
        self.assertEqual(branch, self.module.BRANCH)
        self.assertEqual(status, b"")
        graph = self.module.load_prevalidated_graph()
        self.assertEqual(len(graph), 10)
        self.assertEqual(len(graph[self.module.SENDER_OID]), 13580)

    def test_success_order_has_two_resets_one_sender_and_restores(self) -> None:
        events: list[str] = []
        snapshot = {"index_raw": b"index", "tracked_snapshot": (("tracked",),)}
        graph = {self.module.SENDER_OID: b"sender"}
        sender_report = {
            "status": "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP",
        }
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments", side_effect=lambda: events.append("ack")),
            mock.patch.object(self.module, "require_paths_and_locks", side_effect=lambda: events.append("paths")),
            mock.patch.object(self.module, "require_no_conflicting_process", side_effect=lambda: events.append("process")),
            mock.patch.object(self.module, "capture_snapshot", side_effect=lambda: (events.append("snapshot") or snapshot)),
            mock.patch.object(self.module, "load_prevalidated_graph", side_effect=lambda: (events.append("graph") or graph)),
            mock.patch.object(self.module, "reset_hard_once", side_effect=lambda commit: events.append("reset:" + commit)),
            mock.patch.object(self.module, "basic_state", side_effect=lambda *_args: events.append("historical") or {}),
            mock.patch.object(self.module, "execute_sender_once", side_effect=lambda raw: events.append("sender") or sender_report),
            mock.patch.object(self.module, "restore_tracked_raw_once", side_effect=lambda entries: events.append("tracked")),
            mock.patch.object(self.module, "restore_index_raw_once", side_effect=lambda raw: events.append("index")),
            mock.patch.object(self.module, "verify_restored", side_effect=lambda snap: events.append("restored")),
        ):
            report = self.module.run_one_shot_transition()
        self.assertEqual(events, [
            "ack", "paths", "process", "snapshot", "graph", "snapshot",
            "reset:" + self.module.HISTORICAL, "historical", "process", "sender",
            "reset:" + self.module.INITIAL, "tracked", "index", "restored",
        ])
        self.assertEqual(report["status"], "H27_WINDOWS_LOCAL_SENDER_TRANSITION_TERMINAL_SUCCESS_RESTORED_STOP")
        self.assertFalse(report["transport_executed"])
        self.assertFalse(report["ssh_invoked"])

    def test_pre_effect_failure_does_not_reset(self) -> None:
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "require_paths_and_locks"),
            mock.patch.object(self.module, "require_no_conflicting_process"),
            mock.patch.object(self.module, "capture_snapshot", side_effect=PermissionError("pre")),
            mock.patch.object(self.module, "reset_hard_once") as reset,
        ):
            with self.assertRaisesRegex(PermissionError, "pre"):
                self.module.run_one_shot_transition()
        reset.assert_not_called()

    def test_sender_failure_restores_once_and_never_retries_sender(self) -> None:
        snapshot = {"index_raw": b"index", "tracked_snapshot": (("tracked",),)}
        graph = {self.module.SENDER_OID: b"sender"}
        resets: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "require_paths_and_locks"),
            mock.patch.object(self.module, "require_no_conflicting_process"),
            mock.patch.object(self.module, "capture_snapshot", return_value=snapshot),
            mock.patch.object(self.module, "load_prevalidated_graph", return_value=graph),
            mock.patch.object(self.module, "reset_hard_once", side_effect=lambda commit: resets.append(commit)),
            mock.patch.object(self.module, "basic_state", return_value={}),
            mock.patch.object(self.module, "execute_sender_once", side_effect=RuntimeError("sender")) as sender,
            mock.patch.object(self.module, "restore_tracked_raw_once") as restore_tracked,
            mock.patch.object(self.module, "restore_index_raw_once") as restore_index,
            mock.patch.object(self.module, "verify_restored") as verify,
        ):
            with self.assertRaises(self.module.ConsumedTransitionFailure):
                self.module.run_one_shot_transition()
        self.assertEqual(resets, [self.module.HISTORICAL, self.module.INITIAL])
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(restore_tracked.call_count, 1)
        self.assertEqual(restore_index.call_count, 1)
        self.assertEqual(verify.call_count, 1)

    def test_restoration_failure_is_terminal_without_second_attempt(self) -> None:
        snapshot = {"index_raw": b"index", "tracked_snapshot": (("tracked",),)}
        graph = {self.module.SENDER_OID: b"sender"}
        resets: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "require_paths_and_locks"),
            mock.patch.object(self.module, "require_no_conflicting_process"),
            mock.patch.object(self.module, "capture_snapshot", return_value=snapshot),
            mock.patch.object(self.module, "load_prevalidated_graph", return_value=graph),
            mock.patch.object(self.module, "reset_hard_once", side_effect=lambda commit: resets.append(commit)),
            mock.patch.object(self.module, "basic_state", return_value={}),
            mock.patch.object(self.module, "execute_sender_once", return_value={"status": "ok"}),
            mock.patch.object(self.module, "restore_tracked_raw_once") as restore_tracked,
            mock.patch.object(self.module, "restore_index_raw_once", side_effect=OSError("restore")) as restore_index,
            mock.patch.object(self.module, "verify_restored") as verify,
        ):
            with self.assertRaises(self.module.RestorationFailure):
                self.module.run_one_shot_transition()
        self.assertEqual(resets, [self.module.HISTORICAL, self.module.INITIAL])
        self.assertEqual(restore_tracked.call_count, 1)
        self.assertEqual(restore_index.call_count, 1)
        verify.assert_not_called()

    def test_sender_report_is_strict_and_never_ssh(self) -> None:
        report = {
            "status": "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP",
            "transport_executed": False, "remote_acknowledgement_set": False,
            "object_delivery_executed": False, "source_odb_changed": False,
            "target_odb_changed": False, "science_or_locked_test": False,
        }
        completed = subprocess.CompletedProcess(
            [], 0,
            stdout=(json.dumps(report, separators=(",", ":")) + "\n").encode(),
            stderr=b"",
        )
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            self.assertEqual(self.module.execute_sender_once(b"sender")["status"], report["status"])
        self.assertEqual(run.call_args.args[0], [self.module.PYTHON_EXACT, "-"])
        self.assertNotIn("ssh", " ".join(run.call_args.args[0]).lower())

    def test_reflog_append_is_exactly_the_two_sealed_resets(self) -> None:
        before = b"existing\n"
        identity = b"Codex <codex@example.invalid> 1 +0000"
        after = before + b"".join((
            (
                f"{self.module.INITIAL} {self.module.HISTORICAL} ".encode("ascii")
                + identity
                + f"\treset: moving to {self.module.HISTORICAL}\n".encode("ascii")
            ),
            (
                f"{self.module.HISTORICAL} {self.module.INITIAL} ".encode("ascii")
                + identity
                + f"\treset: moving to {self.module.INITIAL}\n".encode("ascii")
            ),
        ))
        self.module.require_exact_reset_reflog_append(before, after, "test")
        with self.assertRaises(self.module.RestorationFailure):
            self.module.require_exact_reset_reflog_append(before, after + b"extra\n", "test")

    def test_raw_restoration_is_binary_exact_on_windows(self) -> None:
        raw = b"DIRC\x00\n\r\n\x1a\xff"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "index"
            index.write_bytes(b"old")
            index_temp = root / "index.restore.tmp"
            tracked = root / "tracked.bin"
            tracked.write_bytes(b"old")
            entry = (("tracked.bin", "100644", "0" * 40, "regular", len(raw), hashlib.sha256(raw).hexdigest(), raw),)
            with (
                mock.patch.object(self.module, "INDEX_PATH", index),
                mock.patch.object(self.module, "INDEX_TEMP", index_temp),
                mock.patch.object(self.module, "WORKTREE", root),
            ):
                self.module.restore_index_raw_once(raw)
                self.module.restore_tracked_raw_once(entry)
            self.assertEqual(index.read_bytes(), raw)
            self.assertEqual(tracked.read_bytes(), raw)

    def test_launcher_source_has_no_retry_or_ssh_execution(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8").lower()
        for forbidden in ("def retry", "def cleanup", "def repair", "def rollback", "popen(", "shell=true"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn('["ssh"', source)
        self.assertNotIn("('ssh'", source)


if __name__ == "__main__":
    unittest.main()
