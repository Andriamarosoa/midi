from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestTargetCheckoutDetachTransitionContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_three_identity_graph_and_no_back_reference(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        identities = [
            self.binding["reviewed_transition_contract"],
            self.binding["transition_contract_external_seal"],
            self.binding["reviewed_preflight_evidence"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (3, 3))
        self.assertEqual(
            [item["git_blob_sha1"] for item in identities],
            [
                "11fff0962fc0951a0bb06605e233d34756a2f4d9",
                "24a8c14fddd52eca148f961a31c39abaa4de018f",
                "bda7e1fae7379996563e73d8bbcf1b2d7a871aa0",
            ],
        )
        for identity in identities:
            raw = check(self, identity)
            self.assertNotIn(b"target_checkout_detach_transition_contract_identity_binding.json", raw)

    def test_exact_review_roots_and_transition_boundary(self) -> None:
        self.assertEqual(tuple(self.binding), (
            "schema_version", "binding_id", "status", "reviewed_transition_contract",
            "transition_contract_external_seal", "reviewed_preflight_evidence",
            "bound_checkout_transition", "bound_one_shot_fail_closed",
            "bound_forbidden_operations", "bound_preserved_state", "identity_graph",
            "current_state", "next_action",
        ))
        self.assertEqual(self.binding["reviewed_transition_contract"], {
            "path": "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json",
            "reviewed_commit": "36d9ee11fc800a7e57edff1a73858c47ccbdb947",
            "external_review_verdict": "PASS",
            "git_blob_sha1": "11fff0962fc0951a0bb06605e233d34756a2f4d9",
            "size_bytes": 3643,
            "raw_sha256": "f1c7bf1b94b0a35e3f0bd1771e93addd594053cb155ed1c3a9e09670e57de1e5",
        })
        self.assertEqual(self.binding["transition_contract_external_seal"], {
            "path": "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_external_seal.json",
            "git_blob_sha1": "24a8c14fddd52eca148f961a31c39abaa4de018f",
            "size_bytes": 1796,
            "raw_sha256": "b62eff68cbca0c84c7483cbd9f3ea5049b1156129398e571b88adcbf553f0aba",
        })
        self.assertEqual(self.binding["reviewed_preflight_evidence"], {
            "path": "readme/results/2026-08-15_harmonic-censoring-h27-creator-read-only-preflight.md",
            "evidence_commit": "b832f8797b557256dda85e40e8f952c59402fa3d",
            "external_review_verdict": "PASS",
            "git_blob_sha1": "bda7e1fae7379996563e73d8bbcf1b2d7a871aa0",
            "size_bytes": 1987,
            "raw_sha256": "a28a73389a338c8d493b7c75ca82656fb01ce75eddf3aa0f277d4a928b5dbc95",
        })
        self.assertEqual(self.binding["bound_checkout_transition"], {
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
            "head_and_worktree_transition_only_mutation": True,
            "post_transition_head_exact_required": True,
            "post_transition_detached_required": True,
            "post_transition_clean_required": True,
        })

    def test_exact_fail_closed_graph_and_dormant_state(self) -> None:
        self.assertEqual(self.binding["bound_one_shot_fail_closed"], {
            "zero_arguments_required": True,
            "target_object_preverified_present_as_commit": True,
            "initial_head_and_cleanliness_revalidation_before_first_effect_required": True,
            "single_attempt_only": True,
            "failure_terminal_stop": True,
            "retry_reset_cleanup_or_automatic_repair_forbidden": True,
        })
        self.assertEqual(self.binding["bound_forbidden_operations"], {
            "fetch": True, "pull": True, "merge": True, "reset": True, "rebase": True,
            "branch_create_delete_or_move": True, "implicit_branch_checkout": True,
            "creator_acknowledgement": True, "creator_invocation": True,
            "registry_lock_or_open": True, "registry_write": True,
            "authority_reservation_or_consumption": True,
            "staging_or_final_bundle_creation": True,
            "constructor_or_materializer": True, "science_or_locked_test": True,
        })
        self.assertEqual(self.binding["bound_preserved_state"], {
            "control_parent_exists": True,
            "control_parent_runner_terminally_consumed": True,
            "control_parent_runner_retry_forbidden": True,
            "registry_regular_mode_0600_and_empty_reported": True,
            "registry_opened": False, "authority_reserved": False, "authority_consumed": False,
            "creator_acknowledgement_set": False, "creator_invoked": False,
            "final_bundle_exists": False, "staging_bundle_exists": False,
            "constructor_or_materializer_executed": False, "science_or_locked_test": False,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "unique_path_count": 3,
            "contract_seal_and_preflight_evidence_bound": True,
            "duplicates_forbidden": True, "path_or_identity_drift_forbidden": True,
            "acyclic": True, "self_hash_present": False,
            "historical_back_reference_present": False,
        })
        self.assertEqual(self.binding["current_state"], {
            "identity_binding_exists": True,
            "identity_binding_externally_reviewed": False,
            "identity_binding_externally_sealed": False,
            "transition_runner_exists": False,
            "mac_checkout_transition_executed": False,
            "registry_opened": False, "authority_reserved": False, "authority_consumed": False,
            "creator_acknowledgement_set": False, "creator_invoked": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
        })
        self.assertEqual(
            self.binding["next_action"],
            "External review of this identity binding and its external seal only; do not implement or execute a checkout transition runner",
        )

    def test_exact_external_seal(self) -> None:
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_TARGET_CHECKOUT_EXACT_DETACH_TRANSITION_CONTRACT_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_IDENTITY_BINDING_PENDING_EXTERNAL_REVIEW_NO_RUNNER_NO_MAC_CHECKOUT_CHANGE_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {"path": "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding.json", "git_blob_sha1": "538020022099b186d381d9243076d6f5f5222f7b", "size_bytes": 4052, "raw_sha256": "96b000024e96a3badffc4f6d7ff038b091cf3d79619c8dd0489e33b2cddf78da"},
            "reviewed_transition_contract_commit": "36d9ee11fc800a7e57edff1a73858c47ccbdb947",
            "reviewed_transition_contract_git_blob_sha1": "11fff0962fc0951a0bb06605e233d34756a2f4d9",
            "transition_contract_seal_git_blob_sha1": "24a8c14fddd52eca148f961a31c39abaa4de018f",
            "reviewed_preflight_evidence_commit": "b832f8797b557256dda85e40e8f952c59402fa3d",
            "reviewed_preflight_evidence_git_blob_sha1": "bda7e1fae7379996563e73d8bbcf1b2d7a871aa0",
            "bound_unique_identity_count": 3,
            "future_checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "future_git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "future_initial_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "future_target_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "future_target_object_type_exact": "commit",
            "future_explicit_detach_only": True,
            "future_head_and_worktree_transition_only_mutation": True,
            "future_post_transition_head_detached_and_clean_required": True,
            "future_single_attempt_only": True,
            "future_fetch_pull_merge_reset_rebase_forbidden": True,
            "future_branch_modification_forbidden": True,
            "future_retry_cleanup_or_automatic_repair_forbidden": True,
            "identity_binding_externally_reviewed": False,
            "identity_binding_externally_sealed": False,
            "transition_runner_exists": False,
            "mac_checkout_transition_executed": False,
            "registry_opened": False, "authority_reserved": False, "authority_consumed": False,
            "creator_acknowledgement_set": False, "creator_invoked": False,
            "final_bundle_exists": False, "staging_bundle_exists": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact transition-contract identity binding and this seal only; no runner or Mac checkout transition",
        })


if __name__ == "__main__":
    unittest.main()
