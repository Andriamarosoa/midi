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
        true_keys = {"contract_exists", "admin_root_creation_authority_consumed", "admin_root_exists", "empty_registry_file_exists", "reviewed_creator_source_published"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in true_keys, key)
        for key in (
            "contract_externally_reviewed", "contract_externally_sealed", "runner_exists",
            "control_parent_observed", "control_parent_created", "registry_opened",
            "authority_reserved", "authority_consumed", "creator_entrypoint_executed",
            "control_bundle_created", "constructor_or_materializer_executed", "science_or_locked_test",
        ):
            self.assertIs(self.seal[key], False, key)
        self.assertIs(self.seal["admin_root_creation_authority_terminally_consumed"], True)
        self.assertIs(self.seal["empty_registry_file_exists"], True)
        self.assertIs(self.seal["reviewed_creator_source_published"], True)
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_three_predecessor_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        for entry in self.contract["reviewed_admin_root_creator_chain"]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
