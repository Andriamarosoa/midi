from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_control_parent_creation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_creation_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27ControlParentCreationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_contract_seal_and_reviewed_admin_root_chain(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        entries = self.contract["reviewed_admin_root_creator_chain"]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (3, 3))
        for entry in entries:
            check(self, entry)
        self.assertEqual(entries[0]["reviewed_commit"], "042974fde833d1ec13132520f003fba0b60ae044")
        self.assertEqual(entries[0]["external_review_verdict"], "PASS")
        self.assertEqual(
            (self.contract["schema_version"], self.contract["contract_id"], self.contract["status"], self.contract["scope"]),
            (
                1,
                "H27_CONTROL_PARENT_ONE_SHOT_CREATION_CONTRACT_V1",
                "CONTRACT_ONLY_NO_RUNNER_NO_FILESYSTEM_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
                "define only the future one-shot bounded creation of the exact control parent below the terminally created H27 administrative root",
            ),
        )
        self.assertEqual(self.contract["completed_admin_root_creation"], {
            "status_exact": "H27_ADMIN_ROOT_CREATED_TERMINAL_SUCCESS",
            "authority_terminally_consumed": True,
            "verified_identity_count": 7,
            "target_path_exact": "/Users/amcarene/h27-admin",
            "target_device": 16777233,
            "target_inode": 1445438,
            "control_child_created": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "admin_root_creator_retry_forbidden": True,
        })

    def test_closed_future_parent_preflights_order_and_rules(self) -> None:
        self.assertEqual(self.contract["future_control_parent"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE",
            "acknowledgement_value_exact": "1",
            "arguments_forbidden": True,
            "parent_path_exact": "/Users/amcarene/h27-admin",
            "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1445438,
            "parent_must_preexist": True,
            "parent_must_be_real_directory_not_symlink": True,
            "parent_identity_must_remain_stable_by_open_verified_dirfd": True,
            "target_leaf_exact": "control",
            "target_path_exact": "/Users/amcarene/h27-admin/control",
            "target_must_be_absent_before_effect": True,
            "target_future_type_exact": "directory",
            "target_future_mode_exact_octal": "0700",
            "mkdir_parents_forbidden": True,
            "other_path_creation_or_modification_forbidden": True,
        })
        self.assertEqual(self.contract["future_static_preflight_before_target_observation"], [
            "rehash_three_reviewed_admin_root_creator_identities",
            "verify_exact_macos_platform_and_future_acknowledgement_without_arguments",
            "open_parent_exact_o_nofollow_and_require_fd_and_named_entry_match_terminal_device_16777233_inode_1445438",
            "retain_verified_exact_parent_dirfd_for_all_later_operations",
        ])
        self.assertEqual(self.contract["future_one_shot_creation_order"], [
            "probe_control_leaf_absence_once_relative_to_verified_parent_dirfd",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode",
            "mkdir_exact_control_leaf_mode_0700_relative_to_parent_dirfd_first_and_only_irreversible_effect",
            "fsync_parent_directory",
            "open_created_control_leaf_o_nofollow_as_directory_relative_to_parent_dirfd",
            "verify_created_control_leaf_real_directory_mode_0700_inode_and_device_against_named_entry",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode_then_return_success",
        ])
        self.assertEqual(self.contract["future_creation_rules"], {
            "exact_control_leaf_only": True,
            "future_target_mode_exact_octal_0700": True,
            "mkdir_p_forbidden": True,
            "target_probe_occurs_only_after_all_four_static_preflights": True,
            "mkdir_is_first_and_only_irreversible_effect": True,
            "target_creation_exclusive": True,
            "parent_and_target_symlink_forbidden": True,
            "all_operations_relative_to_stable_parent_dirfd": True,
            "parent_fsynced_after_creation": True,
            "created_target_real_directory_mode_inode_and_device_verified": True,
            "failure_after_mkdir_terminal": True,
            "retry_cleanup_repair_or_recreation_forbidden": True,
            "registry_observation_or_modification_forbidden": True,
            "authority_reservation_consumption_creator_bundle_or_science_forbidden": True,
            "target_checkout_detachment_forbidden_in_current_stage": True,
        })
        self.assertEqual(self.contract["future_runner_requirements"], {
            "must_be_created_in_distinct_later_commit": True,
            "external_review_pass_required_before_execution": True,
            "exact_identity_binding_required": True,
            "external_identity_binding_seal_required": True,
            "execution_from_exact_reviewed_git_blob_bytes_only": True,
            "current_checkout_or_worktree_file_fallback_forbidden": True,
            "runner_implementation_forbidden_in_current_stage": True,
        })
        self.assertEqual(
            (self.seal["future_acknowledgement_environment_exact"], self.seal["future_arguments_forbidden"], self.seal["reviewed_predecessor_identity_count"], self.seal["static_preflight_count"], self.seal["one_shot_creation_step_count"], self.seal["creation_rule_count"], self.seal["future_runner_requirement_count"]),
            ("H27_CONTROL_PARENT_CREATE_EXECUTE=1", True, 3, 4, 7, 15, 7),
        )
        terminal = self.contract["completed_admin_root_creation"]
        future = self.contract["future_control_parent"]
        self.assertEqual(
            (future["parent_path_exact"], future["parent_expected_device_exact"], future["parent_expected_inode_exact"]),
            (terminal["target_path_exact"], terminal["target_device"], terminal["target_inode"]),
        )

    def test_contract_only_state_and_no_back_reference(self) -> None:
        self.assertEqual(self.contract["dependency_graph"], {
            "acyclic": True,
            "self_hash_present": False,
            "historical_back_reference_present": False,
            "all_three_predecessor_identities_rehashed": True,
        })
        self.assertEqual(self.contract["current_state"], {
            "contract_exists": True,
            "admin_root_creation_authority_consumed": True,
            "admin_root_exists": True,
            "empty_registry_file_exists": True,
            "reviewed_creator_source_published": True,
            "runner_exists": False,
            "control_parent_observed": False,
            "control_parent_created": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
        })
        self.assertEqual(
            self.contract["next_action"],
            "External review of this declarative contract and its external seal only; do not implement a runner, create control, detach the target checkout, open the registry, or invoke the creator",
        )
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_CONTROL_PARENT_ONE_SHOT_CREATION_CONTRACT_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_CONTRACT_ONLY_NO_RUNNER_NO_FILESYSTEM_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "contract": {"path": "configs/harmonic_censoring_h27_control_parent_creation_contract.json", "git_blob_sha1": "a9b37b3081ad79b773f3a7291a508665d623307a", "size_bytes": 5537, "raw_sha256": "5d1d0474827e72708e4c1bcb5951e91425fcf95a00f3fc373266193c94653dc3"},
            "reviewed_admin_root_creator_commit": "042974fde833d1ec13132520f003fba0b60ae044",
            "admin_root_creation_authority_terminally_consumed": True,
            "empty_registry_file_exists": True,
            "reviewed_creator_source_published": True,
            "future_parent_path_exact": "/Users/amcarene/h27-admin",
            "future_parent_expected_device_exact": 16777233,
            "future_parent_expected_inode_exact": 1445438,
            "future_parent_fd_and_named_entry_must_match_terminal_identity": True,
            "future_target_leaf_exact": "control",
            "future_target_path_exact": "/Users/amcarene/h27-admin/control",
            "future_target_type_exact": "directory",
            "future_target_mode_exact_octal": "0700",
            "future_acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
            "future_arguments_forbidden": True,
            "reviewed_predecessor_identity_count": 3,
            "static_preflight_count": 4,
            "one_shot_creation_step_count": 7,
            "creation_rule_count": 15,
            "future_runner_requirement_count": 7,
            "contract_externally_reviewed": False,
            "contract_externally_sealed": False,
            "runner_exists": False,
            "control_parent_observed": False,
            "control_parent_created": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact control-parent contract and seal only",
        })
        for entry in self.contract["reviewed_admin_root_creator_chain"]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
