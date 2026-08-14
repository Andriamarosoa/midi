from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_control_parent_creation_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_creation_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27ControlParentCreationContractIdentityBinding(unittest.TestCase):
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
        paths = [self.binding["reviewed_contract"]["path"], self.binding["contract_external_seal"]["path"], *(entry["path"] for entry in predecessors)]
        self.assertEqual((len(paths), len(set(paths))), (5, 5))
        self.assertEqual(
            (self.binding["schema_version"], self.binding["binding_id"], self.binding["status"], self.binding["scope"]),
            (1, "H27_CONTROL_PARENT_CREATION_CONTRACT_IDENTITY_BINDING_V1", "IDENTITY_BOUND_PENDING_EXTERNAL_REVIEW_NO_RUNNER_NO_FILESYSTEM_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE", "bind the externally reviewed control-parent contract, its external seal, and all three terminal admin-root predecessor identities without authorizing execution"),
        )
        self.assertEqual(self.binding["reviewed_contract"]["reviewed_commit"], "a07522cbac45097acb53e24f06b61bb2a6060ce0")
        self.assertEqual(self.binding["reviewed_contract"]["external_review_verdict"], "PASS")

    def test_exact_future_boundary_authority_and_graph(self) -> None:
        self.assertEqual(self.binding["bound_future_control_parent"], {
            "parent_path_exact": "/Users/amcarene/h27-admin",
            "parent_device_exact": 16777233,
            "parent_inode_exact": 1445438,
            "target_path_exact": "/Users/amcarene/h27-admin/control",
            "target_type_exact": "directory",
            "target_mode_exact_octal": "0700",
            "acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
            "static_preflight_count": 4,
            "creation_step_count": 7,
            "creation_rule_count": 15,
            "runner_requirement_count": 7,
        })
        self.assertEqual(self.binding["bound_authority_state"], {
            "admin_root_creation_authority_terminally_consumed": True,
            "admin_root_creator_retry_forbidden": True,
            "admin_root_exists": True,
            "empty_registry_file_exists": True,
            "reviewed_creator_source_published": True,
            "control_parent_creation_authority_reserved": False,
            "control_parent_creation_authority_consumed": False,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "unique_path_count": 5,
            "reviewed_contract_and_seal_bound": True,
            "all_three_contract_predecessors_rebound": True,
            "acyclic": True,
            "self_hash_present": False,
            "historical_back_reference_present": False,
        })
        self.assertEqual(self.binding["current_state"], {
            "identity_binding_exists": True,
            "identity_binding_externally_reviewed": False,
            "identity_binding_externally_sealed": False,
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
        self.assertEqual(self.binding["next_action"], "External review of this identity binding and its external seal only")

    def test_complete_seal_dormancy_and_acyclicity(self) -> None:
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_CONTROL_PARENT_CREATION_CONTRACT_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_IDENTITY_BINDING_ONLY_NO_RUNNER_NO_FILESYSTEM_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {"path": "configs/harmonic_censoring_h27_control_parent_creation_contract_identity_binding.json", "git_blob_sha1": "4c84d7d62b177b23feef55a4cb4b2521212fc0ff", "size_bytes": 3531, "raw_sha256": "f9e15642e6747bc4e2073c09c243c6999065fc5085a5e850d31b10e39dd86a36"},
            "reviewed_contract_commit": "a07522cbac45097acb53e24f06b61bb2a6060ce0",
            "contract_git_blob_sha1": "a9b37b3081ad79b773f3a7291a508665d623307a",
            "contract_external_seal_git_blob_sha1": "9edefaa15313be5d3a618b4b3ada012e14ef039b",
            "bound_predecessor_identity_count": 3,
            "bound_unique_path_count": 5,
            "terminal_parent_path_exact": "/Users/amcarene/h27-admin",
            "terminal_parent_device_exact": 16777233,
            "terminal_parent_inode_exact": 1445438,
            "future_target_path_exact": "/Users/amcarene/h27-admin/control",
            "future_target_type_exact": "directory",
            "future_target_mode_exact_octal": "0700",
            "future_acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
            "static_preflight_count": 4,
            "one_shot_creation_step_count": 7,
            "creation_rule_count": 15,
            "future_runner_requirement_count": 7,
            "admin_root_creation_authority_terminally_consumed": True,
            "admin_root_creator_retry_forbidden": True,
            "admin_root_exists": True,
            "empty_registry_file_exists": True,
            "reviewed_creator_source_published": True,
            "control_parent_creation_authority_reserved": False,
            "control_parent_creation_authority_consumed": False,
            "identity_binding_externally_reviewed": False,
            "identity_binding_externally_sealed": False,
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
            "next_action": "External review of the exact control-parent contract identity binding and seal only",
        })
        for identity in (self.binding["reviewed_contract"], self.binding["contract_external_seal"], *self.binding["bound_predecessor_identities"]):
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
