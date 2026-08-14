from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creation_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creation_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27RegistryLeafCreationContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_bytes_and_five_bound_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        check(self, self.binding["reviewed_contract"])
        check(self, self.binding["contract_external_seal"])
        predecessors = self.binding["bound_predecessor_identities"]
        self.assertEqual((len(predecessors), len({entry["path"] for entry in predecessors})), (3, 3))
        for entry in predecessors:
            check(self, entry)
        all_paths = [self.binding["reviewed_contract"]["path"], self.binding["contract_external_seal"]["path"], *(entry["path"] for entry in predecessors)]
        self.assertEqual((len(all_paths), len(set(all_paths))), (5, 5))
        self.assertEqual(self.binding["reviewed_contract"]["reviewed_commit"], "e07e26111bbcf0343a7b57f30c154ab667154fcf")
        self.assertEqual(self.binding["reviewed_contract"]["external_review_verdict"], "PASS")

    def test_exact_bound_future_boundary_and_authority(self) -> None:
        self.assertEqual(self.binding["bound_future_registry_leaf"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_REGISTRY_LEAF_CREATE_EXECUTE=1",
            "arguments_forbidden": True,
            "parent_path_exact": "/Users/amcarene/h27-admin",
            "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1445438,
            "parent_fd_and_named_entry_must_match_terminal_identity": True,
            "target_leaf_exact": "registry",
            "target_path_exact": "/Users/amcarene/h27-admin/registry",
            "static_preflight_count": 4,
            "one_shot_creation_step_count": 7,
            "creation_rule_count": 14,
            "future_runner_requirement_count": 7,
        })
        self.assertEqual(self.binding["bound_authority_state"], {
            "admin_root_creation_authority_terminally_consumed": True,
            "admin_root_creator_retry_forbidden": True,
            "publisher_authority_terminally_consumed": True,
            "publisher_retry_forbidden": True,
            "reviewed_creator_source_published": True,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "unique_path_count": 5,
            "reviewed_contract_and_seal_bound": True,
            "all_three_contract_predecessors_rebound": True,
            "acyclic": True,
            "self_hash_present": False,
            "historical_back_reference_present": False,
        })
        self.assertEqual(
            (
                self.seal["terminal_parent_path_exact"], self.seal["terminal_parent_device_exact"], self.seal["terminal_parent_inode_exact"],
                self.seal["future_target_path_exact"], self.seal["future_acknowledgement_environment_exact"],
                self.seal["bound_predecessor_identity_count"], self.seal["bound_unique_path_count"],
                self.seal["static_preflight_count"], self.seal["one_shot_creation_step_count"], self.seal["creation_rule_count"], self.seal["future_runner_requirement_count"],
            ),
            ("/Users/amcarene/h27-admin", 16777233, 1445438, "/Users/amcarene/h27-admin/registry", "H27_REGISTRY_LEAF_CREATE_EXECUTE=1", 3, 5, 4, 7, 14, 7),
        )

    def test_dormant_state_and_acyclicity(self) -> None:
        true_keys = {"identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in true_keys, key)
        seal_true = {
            "future_arguments_forbidden",
            "admin_root_creation_authority_terminally_consumed",
            "admin_root_creator_retry_forbidden",
            "publisher_authority_terminally_consumed",
            "publisher_retry_forbidden",
            "reviewed_creator_source_published",
        }
        for key, value in self.seal.items():
            if isinstance(value, bool):
                self.assertIs(value, key in seal_true, key)
        self.assertEqual(self.seal["contract_git_blob_sha1"], self.binding["reviewed_contract"]["git_blob_sha1"])
        self.assertEqual(self.seal["contract_external_seal_git_blob_sha1"], self.binding["contract_external_seal"]["git_blob_sha1"])
        for identity in (self.binding["reviewed_contract"], self.binding["contract_external_seal"], *self.binding["bound_predecessor_identities"]):
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
