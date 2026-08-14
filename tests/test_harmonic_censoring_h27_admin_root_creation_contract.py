from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_admin_root_creation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_admin_root_creation_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27AdminRootCreationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_contract_seal_and_reviewed_predecessors(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        entries = self.contract["reviewed_blocked_publication_chain"]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (3, 3))
        for entry in entries:
            check(self, entry)
        self.assertEqual(entries[0]["reviewed_commit"], "ddba2178028b385cb33f9a68455d724015e22814")
        self.assertEqual(entries[0]["external_review_verdict"], "PASS")

    def test_closed_future_root_preflight_order_and_rules(self) -> None:
        self.assertEqual(self.contract["future_root"], {
            "platform_exact": "darwin",
            "parent_path_exact": "/Users/amcarene",
            "parent_must_preexist": True,
            "parent_must_be_real_directory_not_symlink": True,
            "parent_identity_must_remain_stable_by_open_verified_dirfd": True,
            "target_leaf_exact": "h27-admin",
            "target_path_exact": "/Users/amcarene/h27-admin",
            "target_must_be_absent_before_effect": True,
            "mkdir_parents_forbidden": True,
            "other_path_creation_or_modification_forbidden": True,
        })
        self.assertEqual(self.contract["future_static_preflight_before_target_observation"], [
            "rehash_three_reviewed_blocked_publication_identities",
            "verify_exact_macos_platform_and_future_acknowledgement_without_arguments",
            "open_parent_exact_with_o_nofollow_and_verify_directory_realpath_inode_and_device",
            "retain_verified_parent_dirfd_for_all_later_operations",
        ])
        self.assertEqual(self.contract["future_one_shot_creation_order"], [
            "probe_target_absence_once_relative_to_verified_parent_dirfd",
            "reverify_parent_named_identity",
            "mkdir_exact_leaf_relative_to_parent_dirfd_first_and_only_irreversible_effect",
            "fsync_parent_directory",
            "open_created_leaf_o_nofollow_relative_to_parent_dirfd",
            "verify_created_leaf_real_directory_inode_and_device_against_named_entry",
            "reverify_parent_named_identity_and_return_terminal_success",
        ])
        rules = self.contract["future_creation_rules"]
        self.assertEqual(len(rules), 14)
        self.assertTrue(all(value is True for value in rules.values()))
        self.assertEqual(
            (self.seal["reviewed_predecessor_identity_count"], self.seal["static_preflight_step_count"], self.seal["one_shot_creation_step_count"], self.seal["creation_rule_count"]),
            (3, 4, 7, 14),
        )

    def test_dormant_state_and_no_back_reference(self) -> None:
        allowed = {"contract_exists"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in allowed, key)
        for key in (
            "contract_externally_reviewed",
            "identity_binding_exists",
            "runner_exists",
            "parent_observed",
            "target_observed",
            "target_created",
            "publisher_authorization_consumed",
            "creator_child_created",
            "source_published",
            "registry_opened",
            "control_bundle_created",
            "science_or_locked_test",
        ):
            self.assertIs(self.seal[key], False, key)
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_three_predecessor_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        for entry in self.contract["reviewed_blocked_publication_chain"]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
