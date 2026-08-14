from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creation_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27RegistryLeafCreationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_bytes_seal_and_reviewed_chain(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        entries = self.contract["reviewed_terminal_parent_chain"]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (3, 3))
        for entry in entries:
            check(self, entry)
        self.assertEqual(entries[0]["reviewed_commit"], "e22296126b8119fd2422d79f85597536e02f6bb8")
        self.assertEqual(entries[2]["reviewed_commit"], "9d8106135144c449e9d06a71269f61adf64457e8")
        self.assertTrue(all(entry.get("external_review_verdict", "PASS") == "PASS" for entry in entries))

    def test_closed_parent_leaf_order_and_rules(self) -> None:
        self.assertEqual(self.contract["completed_terminal_parent"], {
            "path_exact": "/Users/amcarene/h27-admin",
            "device_exact": 16777233,
            "inode_exact": 1445438,
            "admin_root_creation_authority_terminally_consumed": True,
            "admin_root_creator_retry_forbidden": True,
            "reviewed_creator_source_published": True,
            "publisher_authority_terminally_consumed": True,
            "publisher_retry_forbidden": True,
            "registry_observed": False,
            "registry_created": False,
            "registry_opened": False,
            "control_bundle_created": False,
            "science_or_locked_test": False,
        })
        self.assertEqual(self.contract["future_registry_leaf"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_REGISTRY_LEAF_CREATE_EXECUTE",
            "acknowledgement_value_exact": "1",
            "arguments_forbidden": True,
            "parent_path_exact": "/Users/amcarene/h27-admin",
            "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1445438,
            "parent_must_preexist": True,
            "parent_must_be_real_directory_not_symlink": True,
            "parent_identity_must_remain_stable_by_open_verified_dirfd": True,
            "target_leaf_exact": "registry",
            "target_path_exact": "/Users/amcarene/h27-admin/registry",
            "target_must_be_absent_before_effect": True,
            "mkdir_parents_forbidden": True,
            "other_path_creation_or_modification_forbidden": True,
        })
        self.assertEqual(self.contract["future_static_preflight_before_target_observation"], [
            "rehash_three_reviewed_terminal_parent_identities",
            "verify_exact_macos_platform_and_future_acknowledgement_without_arguments",
            "open_parent_exact_o_nofollow_and_require_fd_and_named_entry_match_terminal_device_16777233_inode_1445438",
            "retain_verified_exact_parent_dirfd_for_all_later_operations",
        ])
        self.assertEqual(self.contract["future_one_shot_creation_order"], [
            "probe_registry_leaf_absence_once_relative_to_verified_parent_dirfd",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode",
            "mkdir_exact_registry_leaf_relative_to_parent_dirfd_first_and_only_irreversible_effect",
            "fsync_parent_directory",
            "open_created_registry_leaf_o_nofollow_relative_to_parent_dirfd",
            "verify_created_registry_leaf_real_directory_inode_and_device_against_named_entry",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode_then_return_success",
        ])
        self.assertEqual(self.contract["future_creation_rules"], {
            "exact_registry_leaf_only": True,
            "mkdir_p_forbidden": True,
            "target_probe_occurs_only_after_all_four_static_preflights": True,
            "mkdir_is_first_and_only_irreversible_effect": True,
            "target_creation_exclusive": True,
            "parent_and_target_symlink_forbidden": True,
            "all_operations_relative_to_stable_parent_dirfd": True,
            "parent_fsynced_after_creation": True,
            "created_target_inode_and_device_verified": True,
            "failure_after_mkdir_terminal": True,
            "retry_cleanup_repair_or_recreation_forbidden": True,
            "registry_file_observation_open_or_creation_forbidden": True,
            "authority_reservation_consumption_bundle_or_science_forbidden": True,
            "consumed_admin_root_and_publisher_authorities_remain_non_replayable": True,
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
            (self.seal["reviewed_predecessor_identity_count"], self.seal["static_preflight_count"], self.seal["one_shot_creation_step_count"], self.seal["creation_rule_count"], self.seal["future_runner_requirement_count"]),
            (3, 4, 7, 14, 7),
        )

    def test_contract_only_state_and_no_back_reference(self) -> None:
        true_keys = {"contract_exists", "admin_root_exists", "admin_root_creation_authority_consumed", "creator_source_published", "publisher_authority_consumed"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in true_keys, key)
        seal_true = {
            "parent_fd_and_named_entry_must_match_terminal_identity",
            "future_arguments_forbidden",
            "admin_root_creation_authority_terminally_consumed",
            "publisher_authority_terminally_consumed",
            "admin_root_creator_retry_forbidden",
            "publisher_retry_forbidden",
            "reviewed_creator_source_published",
        }
        for key, value in self.seal.items():
            if isinstance(value, bool):
                self.assertIs(value, key in seal_true, key)
        future = self.contract["future_registry_leaf"]
        terminal = self.contract["completed_terminal_parent"]
        self.assertEqual(
            (future["parent_path_exact"], future["parent_expected_device_exact"], future["parent_expected_inode_exact"]),
            (terminal["path_exact"], terminal["device_exact"], terminal["inode_exact"]),
        )
        self.assertEqual(
            (self.seal["future_target_leaf_exact"], self.seal["future_target_path_exact"], self.seal["future_acknowledgement_environment_exact"]),
            ("registry", "/Users/amcarene/h27-admin/registry", "H27_REGISTRY_LEAF_CREATE_EXECUTE=1"),
        )
        graph = self.contract["dependency_graph"]
        self.assertEqual(graph, {"acyclic": True, "self_hash_present": False, "historical_back_reference_present": False, "all_three_predecessor_identities_rehashed": True})
        for entry in self.contract["reviewed_terminal_parent_chain"]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
