from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class TestTargetCheckoutDetachTransitionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_bytes_and_sealed_contract_identity(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        identity = self.seal["contract_identity"]
        self.assertEqual(
            (identity["path"], identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
            (
                "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json",
                blob(self.contract_raw),
                len(self.contract_raw),
                hashlib.sha256(self.contract_raw).hexdigest(),
            ),
        )

    def test_exact_contract_boundary_order_and_dormant_state(self) -> None:
        self.assertEqual(tuple(self.contract), (
            "schema_version", "contract_id", "status", "scope", "reviewed_preflight",
            "future_transition", "future_fail_closed_order", "forbidden_operations",
            "preserved_state", "current_state", "next_action",
        ))
        self.assertEqual((self.contract["schema_version"], self.contract["contract_id"], self.contract["status"]), (
            1,
            "H27_TARGET_CHECKOUT_EXACT_DETACH_TRANSITION_ONE_SHOT_CONTRACT_V1",
            "DECLARATIVE_CONTRACT_ONLY_NO_RUNNER_NO_MAC_CHECKOUT_CHANGE_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
        ))
        self.assertEqual(self.contract["reviewed_preflight"], {
            "evidence_commit": "b832f8797b557256dda85e40e8f952c59402fa3d",
            "external_review_verdict": "PASS",
            "checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "observed_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "observed_checkout_real": True,
            "observed_checkout_clean": True,
            "target_commit_verified_present_as_commit": True,
            "creator_preflight_blocked_only_by_head_mismatch": True,
        })
        self.assertEqual(self.contract["future_transition"], {
            "platform_exact": "darwin",
            "checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "initial_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "initial_checkout_real_required": True,
            "initial_checkout_clean_required": True,
            "target_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "target_object_type_exact": "commit",
            "explicit_detach_to_exact_sha_only": True,
            "branch_or_current_head_selection_forbidden": True,
            "fetch_pull_merge_reset_rebase_forbidden": True,
            "branch_modification_forbidden": True,
            "head_and_worktree_transition_only_mutation": True,
            "post_transition_head_exact_required": True,
            "post_transition_detached_required": True,
            "post_transition_clean_required": True,
            "single_attempt_only": True,
            "failure_terminal_stop": True,
            "retry_reset_cleanup_or_automatic_repair_forbidden": True,
        })
        self.assertEqual(self.contract["future_fail_closed_order"], [
            "verify_platform_and_zero_arguments", "verify_checkout_and_odb_realpaths",
            "verify_initial_head_exact", "verify_initial_worktree_clean",
            "verify_target_object_exists_and_type_is_commit", "reverify_initial_head_and_cleanliness",
            "perform_single_explicit_detach_to_exact_target_sha_as_first_and_only_mutation",
            "verify_target_head_exact", "verify_detached_state", "verify_worktree_clean",
            "terminal_success_then_stop",
        ])
        self.assertEqual(self.contract["forbidden_operations"], {
            "fetch": True, "pull": True, "merge": True, "reset": True, "rebase": True,
            "branch_create_delete_or_move": True, "implicit_branch_checkout": True,
            "creator_acknowledgement": True, "creator_invocation": True,
            "registry_lock_or_open": True, "registry_write": True,
            "authority_reservation_or_consumption": True,
            "staging_or_final_bundle_creation": True, "constructor_or_materializer": True,
            "science_or_locked_test": True,
        })
        self.assertEqual(self.contract["preserved_state"], {
            "control_parent_exists": True,
            "control_parent_runner_terminally_consumed": True,
            "control_parent_runner_retry_forbidden": True,
            "registry_regular_mode_0600_and_empty_reported": True,
            "registry_opened": False, "authority_reserved": False, "authority_consumed": False,
            "creator_acknowledgement_set": False, "creator_invoked": False,
            "final_bundle_exists": False, "staging_bundle_exists": False,
            "constructor_or_materializer_executed": False, "science_or_locked_test": False,
        })
        self.assertEqual(self.contract["current_state"], {
            "contract_exists": True, "contract_externally_reviewed": False,
            "contract_externally_sealed": False, "transition_runner_exists": False,
            "mac_checkout_transition_executed": False, "registry_opened": False,
            "authority_reserved": False, "authority_consumed": False,
            "creator_invoked": False, "control_bundle_created": False,
            "constructor_or_materializer_executed": False, "science_or_locked_test": False,
        })
        self.assertEqual(self.contract["next_action"], "External review of this declarative checkout-transition contract and its external seal only; do not implement or execute a transition runner")

    def test_exact_external_seal(self) -> None:
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_TARGET_CHECKOUT_EXACT_DETACH_TRANSITION_ONE_SHOT_CONTRACT_EXTERNAL_SEAL_V1",
            "status": "SEALED_DECLARATIVE_CONTRACT_PENDING_EXTERNAL_REVIEW_NO_RUNNER_NO_MAC_CHECKOUT_CHANGE_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "contract_identity": {"path": "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json", "git_blob_sha1": "11fff0962fc0951a0bb06605e233d34756a2f4d9", "size_bytes": 3643, "raw_sha256": "f1c7bf1b94b0a35e3f0bd1771e93addd594053cb155ed1c3a9e09670e57de1e5"},
            "reviewed_preflight_evidence_commit": "b832f8797b557256dda85e40e8f952c59402fa3d",
            "future_checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "future_git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "future_initial_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "future_target_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "future_target_object_type_exact": "commit",
            "future_explicit_detach_only": True, "future_single_attempt_only": True,
            "future_fetch_pull_merge_reset_rebase_forbidden": True,
            "future_branch_modification_forbidden": True,
            "future_post_transition_head_detached_and_clean_required": True,
            "future_retry_cleanup_or_automatic_repair_forbidden": True,
            "transition_runner_exists": False, "mac_checkout_transition_executed": False,
            "registry_opened": False, "authority_reserved": False, "authority_consumed": False,
            "creator_acknowledgement_set": False, "creator_invoked": False,
            "final_bundle_exists": False, "staging_bundle_exists": False,
            "constructor_or_materializer_executed": False, "science_or_locked_test": False,
            "next_action": "External review of the exact declarative checkout-transition contract and this seal only; no runner or Mac checkout transition",
        })


if __name__ == "__main__":
    unittest.main()
