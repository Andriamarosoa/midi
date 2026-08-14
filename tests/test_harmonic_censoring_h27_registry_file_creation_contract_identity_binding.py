from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_registry_file_creation_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_file_creation_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27RegistryFileCreationContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_bytes_and_six_bound_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        check(self, self.binding["reviewed_contract"])
        check(self, self.binding["contract_external_seal"])
        predecessors = self.binding["bound_predecessor_identities"]
        self.assertEqual((len(predecessors), len({entry["path"] for entry in predecessors})), (4, 4))
        for entry in predecessors:
            check(self, entry)
        paths = [self.binding["reviewed_contract"]["path"], self.binding["contract_external_seal"]["path"], *(entry["path"] for entry in predecessors)]
        self.assertEqual((len(paths), len(set(paths))), (6, 6))
        self.assertEqual(self.binding["reviewed_contract"]["reviewed_commit"], "ef866d365b79455508f5d2d866bbf1dc043f0f70")
        self.assertEqual(self.binding["reviewed_contract"]["external_review_verdict"], "PASS")

    def test_exact_future_boundary_authority_and_graph(self) -> None:
        self.assertEqual(self.binding["bound_future_registry_file"], {
            "parent_path_exact": "/Users/amcarene/h27-admin/registry",
            "parent_device_exact": 16777233,
            "parent_inode_exact": 1448669,
            "target_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "initial_size_bytes_exact": 0,
            "nlink_exact": 1,
            "mode_exact_octal": "0600",
            "acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE=1",
            "static_preflight_count": 4,
            "creation_step_count": 9,
            "creation_rule_count": 18,
            "runner_requirement_count": 7,
        })
        self.assertEqual(self.binding["bound_authority_state"], {
            "registry_leaf_creation_authority_terminally_consumed": True,
            "registry_leaf_runner_retry_forbidden": True,
            "registry_leaf_exists": True,
            "registry_file_creation_authority_reserved": False,
            "registry_file_creation_authority_consumed": False,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "unique_path_count": 6,
            "reviewed_contract_and_seal_bound": True,
            "all_four_contract_predecessors_rebound": True,
            "acyclic": True,
            "self_hash_present": False,
            "historical_back_reference_present": False,
        })

    def test_complete_seal_dormancy_and_acyclicity(self) -> None:
        expected_seal = {
            "schema_version": 1,
            "seal_id": "H27_EMPTY_AUTHORITY_REGISTRY_FILE_CREATION_CONTRACT_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_IDENTITY_BINDING_ONLY_NO_RUNNER_NO_FILESYSTEM_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {"path": "configs/harmonic_censoring_h27_registry_file_creation_contract_identity_binding.json", "git_blob_sha1": "30e013f3dec986b031eed5a08c1b2f537742b5fb", "size_bytes": 3930, "raw_sha256": "8d7131482ee43c7ac19cbdf1a3e9c24ac3700b784712ec07870f68581c7929db"},
            "reviewed_contract_commit": "ef866d365b79455508f5d2d866bbf1dc043f0f70",
            "contract_git_blob_sha1": "943034b75504eefc6986e5eb5b7237b63cd36155",
            "contract_external_seal_git_blob_sha1": "e697b7fe342583d7d153a9fcd717b43e28f7c581",
            "bound_predecessor_identity_count": 4,
            "bound_unique_path_count": 6,
            "terminal_parent_path_exact": "/Users/amcarene/h27-admin/registry",
            "terminal_parent_device_exact": 16777233,
            "terminal_parent_inode_exact": 1448669,
            "future_target_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "future_target_initial_size_bytes_exact": 0,
            "future_target_nlink_exact": 1,
            "future_target_mode_exact_octal": "0600",
            "future_acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE=1",
            "static_preflight_count": 4,
            "one_shot_creation_step_count": 9,
            "creation_rule_count": 18,
            "future_runner_requirement_count": 7,
            "registry_leaf_creation_authority_terminally_consumed": True,
            "registry_leaf_runner_retry_forbidden": True,
            "registry_leaf_exists": True,
            "registry_file_creation_authority_reserved": False,
            "registry_file_creation_authority_consumed": False,
            "identity_binding_externally_reviewed": False,
            "identity_binding_externally_sealed": False,
            "runner_exists": False,
            "registry_file_observed": False,
            "registry_file_created": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact empty-registry-file contract identity binding and seal only",
        }
        self.assertEqual(self.seal, expected_seal)
        true_keys = {"identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in true_keys, key)
        for identity in (self.binding["reviewed_contract"], self.binding["contract_external_seal"], *self.binding["bound_predecessor_identities"]):
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
