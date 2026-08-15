from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_windows_local_sender_transition_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_windows_local_sender_transition_contract_external_seal.json"
EXECUTION_WORKTREE = Path(r"C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2")
INITIAL = "61dc4b496a454b596fca6ac361504f441e987aab"
HISTORICAL = "c0bb8d20862f80cabc72ea64a5d437750b7c12e8"
BRANCH = "refs/heads/codex/independent-note-neural-v2"


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


class TestH27WindowsLocalSenderTransitionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_bytes())
        cls.seal = json.loads(SEAL.read_bytes())

    def test_contract_and_seal_are_exact_lf_and_closed(self) -> None:
        for path in (CONTRACT, SEAL):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.seal["contract"], identity(CONTRACT))
        self.assertEqual(set(self.contract), {
            "schema_version", "contract_id", "status", "purpose",
            "approved_sender_commit", "approved_sender",
            "approved_sender_identity_binding",
            "approved_sender_identity_binding_external_seal", "review_topology",
            "future_launcher_source", "platform_exact",
            "future_acknowledgement_environment_exact", "future_arguments_forbidden",
            "worktree_exact", "repository_selector_prefix_exact",
            "git_subprocess_environment", "initial_state", "historical_state",
            "pre_effect_snapshot", "permitted_transition_effect", "sender_preparation",
            "mandatory_restoration", "restored_state_invariants",
            "expected_local_administrative_delta", "failure_policy",
            "future_fail_closed_order", "current_state", "next_action",
        })
        self.assertEqual(set(self.seal), {
            "schema_version", "seal_id", "status", "contract",
            "approved_sender_commit", "approved_sender", "review_auxiliary_branch_exact",
            "review_auxiliary_worktree_exact", "execution_branch_exact",
            "execution_worktree_exact",
            "execution_worktree_preserved_at_61dc_until_reviewed_launcher_execution",
            "future_launcher_loaded_only_from_exact_reviewed_git_blob_over_python_stdin",
            "future_launcher_auxiliary_checkout_file_read_forbidden",
            "future_platform_exact", "future_acknowledgement_environment_exact",
            "future_arguments_forbidden", "future_worktree_exact",
            "future_initial_head_branch_and_local_ref_exact",
            "future_remote_tracking_ref_exact", "future_remote_network_reverification_forbidden",
            "future_historical_head_and_local_ref_exact",
            "future_symbolic_head_must_remain_exact", "future_git_environment",
            "future_pre_effect_index_raw_bytes_and_tracked_byte_manifest_retained",
            "future_pre_effect_tracked_raw_bytes_retained_in_memory",
            "future_sender_contract_graph_loaded_and_rehashed_before_first_effect",
            "future_historical_reset_exact", "future_sender_invocation_exact",
            "future_sender_invocation_count_exact", "future_sender_terminal_status_exact",
            "future_transport_executed_false_required", "future_ssh_execution_forbidden",
            "future_restoration_attempt_exactly_once_after_any_post_effect_outcome",
            "future_restore_reset_exact",
            "future_original_index_raw_bytes_restored_by_exclusive_fsynced_atomic_sibling_replace",
            "future_original_tracked_raw_bytes_restored_by_exclusive_fsynced_atomic_sibling_replaces",
            "future_restored_branch_head_ref_index_tracked_bytes_and_status_exact",
            "future_remote_tracking_ref_unchanged",
            "future_reflog_and_orig_head_are_the_only_permitted_persistent_administrative_delta",
            "future_pre_effect_failure_does_not_consume_transition",
            "future_post_effect_failure_consumes_transition",
            "future_single_restoration_attempt_only",
            "future_retry_cleanup_repair_and_rollback_claim_forbidden",
            "future_normative_order", "launcher_implemented",
            "transition_acknowledgement_set", "historical_reset_executed",
            "sender_preparation_executed", "restoration_executed", "ssh_invoked",
            "remote_acknowledgement_set", "object_delivery_executed",
            "source_odb_changed", "target_odb_changed", "import_executed",
            "detach_executed", "downstream_executed", "science_or_locked_test",
            "next_action",
        })

    def test_auxiliary_topology_preserves_the_exact_execution_worktree(self) -> None:
        topology = self.contract["review_topology"]
        self.assertEqual(topology, {
            "auxiliary_branch_exact": "refs/heads/codex/h27-windows-transition-contract",
            "auxiliary_worktree_exact": r"C:\Users\user\Desktop\midi\tmp\local\worktrees\h27-windows-transition-contract",
            "auxiliary_branch_base_exact": INITIAL,
            "execution_branch_exact": BRANCH,
            "execution_worktree_exact": str(EXECUTION_WORKTREE),
            "execution_head_must_remain_exact_until_reviewed_launcher_execution": INITIAL,
            "execution_worktree_must_not_receive_contract_or_launcher_checkout_files": True,
        })
        head = subprocess.check_output(["git", "-C", str(EXECUTION_WORKTREE), "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "-C", str(EXECUTION_WORKTREE), "symbolic-ref", "-q", "HEAD"], text=True).strip()
        status = subprocess.check_output([
            "git", "-C", str(EXECUTION_WORKTREE), "status", "--porcelain=v1", "--untracked-files=all",
        ])
        self.assertEqual(head, INITIAL)
        self.assertEqual(branch, BRANCH)
        self.assertEqual(status, b"")

    def test_transition_sender_and_restoration_are_exactly_bounded(self) -> None:
        self.assertEqual(self.contract["initial_state"]["head_exact"], INITIAL)
        self.assertEqual(self.contract["initial_state"]["local_branch_ref_exact"], INITIAL)
        self.assertEqual(self.contract["historical_state"]["head_exact"], HISTORICAL)
        self.assertEqual(self.contract["historical_state"]["local_branch_ref_exact"], HISTORICAL)
        self.assertEqual(self.contract["restored_state_invariants"]["head_exact"], INITIAL)
        self.assertEqual(
            self.contract["permitted_transition_effect"]["first_effect_exact"],
            f"git --no-optional-locks --no-replace-objects -C {EXECUTION_WORKTREE} reset --hard {HISTORICAL}",
        )
        self.assertEqual(
            self.contract["mandatory_restoration"]["restore_operation_exact"],
            f"git --no-optional-locks --no-replace-objects -C {EXECUTION_WORKTREE} reset --hard {INITIAL}",
        )
        sender = self.contract["sender_preparation"]
        self.assertEqual(sender["invocation_count_exact"], 1)
        self.assertEqual(sender["terminal_status_exact"], "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP")
        self.assertTrue(sender["transport_executed_false_required"])
        self.assertTrue(sender["ssh_subprocess_forbidden"])
        self.assertTrue(self.contract["mandatory_restoration"]["attempt_exactly_once_after_any_post_first_effect_success_or_failure"])

    def test_failure_policy_is_explicit_and_no_retry(self) -> None:
        policy = self.contract["failure_policy"]
        self.assertEqual(set(policy), {
            "pre_first_effect_failure", "post_first_effect_failure", "sender_failure",
            "restoration_success_after_failure", "restoration_failure",
            "automatic_retry_forbidden", "second_sender_invocation_forbidden",
            "ssh_or_remote_fallback_forbidden",
        })
        self.assertTrue(policy["automatic_retry_forbidden"])
        self.assertTrue(policy["second_sender_invocation_forbidden"])
        self.assertTrue(policy["ssh_or_remote_fallback_forbidden"])
        self.assertEqual(self.seal["future_sender_invocation_count_exact"], 1)
        self.assertTrue(self.seal["future_single_restoration_attempt_only"])

    def test_contract_is_dormant_and_stops_before_ssh(self) -> None:
        current = self.contract["current_state"]
        for key in (
            "launcher_implemented", "transition_acknowledgement_set",
            "historical_reset_executed", "sender_preparation_executed",
            "restoration_executed", "ssh_invoked", "remote_acknowledgement_set",
            "object_delivery_executed", "source_odb_changed", "target_odb_changed",
            "import_executed", "detach_executed", "downstream_executed",
            "science_or_locked_test",
        ):
            self.assertFalse(current[key])
            self.assertFalse(self.seal[key])
        self.assertTrue(current["contract_only"])
        self.assertTrue(current["external_seal_created"])
        self.assertTrue(self.seal["future_ssh_execution_forbidden"])
        self.assertTrue(self.seal["future_transport_executed_false_required"])


if __name__ == "__main__":
    unittest.main()
