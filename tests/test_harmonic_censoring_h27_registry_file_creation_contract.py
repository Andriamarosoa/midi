from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_registry_file_creation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_file_creation_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


class TestH27RegistryFileCreationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_bytes_seal_and_terminal_chain(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        entries = self.contract["reviewed_terminal_registry_leaf_chain"]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (4, 4))
        for entry in entries:
            check(self, entry)
        self.assertEqual(entries[-1]["reviewed_commit"], "0ea166702f7573d894e487cb7d7f2551af769317")
        self.assertEqual(entries[-1]["external_review_verdict"], "PASS")

    def test_exact_empty_file_boundary_order_and_rules(self) -> None:
        self.assertEqual(self.contract["completed_terminal_parent"], {
            "path_exact": "/Users/amcarene/h27-admin/registry", "device_exact": 16777233, "inode_exact": 1448669,
            "registry_leaf_creation_authority_terminally_consumed": True, "registry_leaf_runner_retry_forbidden": True,
            "registry_jsonl_observed": False, "registry_opened": False, "authority_reserved": False,
            "authority_consumed": False, "control_bundle_created": False, "science_or_locked_test": False,
        })
        self.assertEqual(self.contract["future_registry_file"], {
            "platform_exact": "darwin", "acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE",
            "acknowledgement_value_exact": "1", "arguments_forbidden": True,
            "parent_path_exact": "/Users/amcarene/h27-admin/registry", "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1448669, "parent_must_preexist": True,
            "parent_must_be_real_directory_not_symlink": True, "parent_identity_must_remain_stable_by_open_verified_dirfd": True,
            "target_leaf_exact": "h27-control-bundle-creation-authority-v1.jsonl",
            "target_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "target_must_be_absent_before_effect": True, "target_initial_size_bytes_exact": 0,
            "target_regular_file_only": True, "target_nlink_exact": 1, "target_mode_exact_octal": "0600",
            "mkdir_parents_forbidden": True, "other_path_creation_or_modification_forbidden": True,
        })
        self.assertEqual(len(self.contract["future_static_preflight_before_target_observation"]), 4)
        self.assertEqual(self.contract["future_one_shot_creation_order"], [
            "probe_registry_file_absence_once_relative_to_verified_parent_dirfd",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode",
            "open_exact_registry_file_o_creat_o_excl_o_nofollow_mode_0600_relative_to_parent_dirfd_first_and_only_irreversible_effect",
            "fsync_created_registry_file", "verify_created_fd_regular_nlink_one_and_size_zero", "fsync_parent_directory",
            "reopen_exact_registry_file_o_nofollow_relative_to_parent_dirfd",
            "verify_reopened_fd_and_named_entry_same_regular_inode_device_nlink_one_size_zero",
            "reverify_parent_fd_and_named_entry_match_terminal_device_and_inode_then_return_success",
        ])
        self.assertEqual(len(self.contract["future_creation_rules"]), 17)
        self.assertTrue(all(self.contract["future_creation_rules"].values()))
        self.assertEqual(len(self.contract["future_runner_requirements"]), 7)
        self.assertTrue(all(self.contract["future_runner_requirements"].values()))
        self.assertEqual(
            (self.seal["reviewed_predecessor_identity_count"], self.seal["static_preflight_count"], self.seal["one_shot_creation_step_count"], self.seal["creation_rule_count"], self.seal["future_runner_requirement_count"]),
            (4, 4, 9, 17, 7),
        )

    def test_contract_only_state_parent_link_and_no_back_reference(self) -> None:
        true_keys = {"contract_exists", "registry_leaf_exists", "registry_leaf_creation_authority_consumed"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in true_keys, key)
        seal_true = {"future_arguments_forbidden", "registry_leaf_creation_authority_terminally_consumed", "registry_leaf_runner_retry_forbidden"}
        for key, value in self.seal.items():
            if isinstance(value, bool):
                self.assertIs(value, key in seal_true, key)
        future = self.contract["future_registry_file"]
        terminal = self.contract["completed_terminal_parent"]
        self.assertEqual((future["parent_path_exact"], future["parent_expected_device_exact"], future["parent_expected_inode_exact"]), (terminal["path_exact"], terminal["device_exact"], terminal["inode_exact"]))
        self.assertEqual((self.seal["future_target_initial_size_bytes_exact"], self.seal["future_target_nlink_exact"], self.seal["future_target_mode_exact_octal"]), (0, 1, "0600"))
        self.assertEqual(self.contract["dependency_graph"], {"acyclic": True, "self_hash_present": False, "historical_back_reference_present": False, "all_four_predecessor_identities_rehashed": True})
        for entry in self.contract["reviewed_terminal_registry_leaf_chain"]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
