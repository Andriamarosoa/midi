from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestControlParentIdentityDriftCorrectionContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_nine_identity_graph_and_no_back_reference(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        identities = [
            self.binding["reviewed_correction_contract"],
            self.binding["correction_contract_external_seal"],
            *self.binding["bound_historical_identities"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (9, 9))
        self.assertEqual(
            [item["git_blob_sha1"] for item in identities],
            [
                "f4c45904c72a8f2e12a3ea7d8d79bea276fefd3e",
                "527bb2d0b7cd5da384fcb4efb1ac5fee186b355c",
                "a9b37b3081ad79b773f3a7291a508665d623307a",
                "9edefaa15313be5d3a618b4b3ada012e14ef039b",
                "4c84d7d62b177b23feef55a4cb4b2521212fc0ff",
                "297ff5953c0fed3db0c4dca2b984dcc822244dcb",
                "96df05111a5e40a418e12fb2b3db4bd9516bcab3",
                "4a1b1ac62395d9880e747dc24395c2e2a0edce85",
                "449537a22bf1979273fd90e8bac7650170248f62",
            ],
        )
        for identity in identities:
            raw = check(self, identity)
            self.assertNotIn(b"correction_contract_identity_binding.json", raw)

    def test_exact_parent_stale_runner_and_future_boundary(self) -> None:
        self.assertEqual(
            self.binding["bound_parent_states"],
            {
                "historical": {"path_exact": "/Users/amcarene/h27-admin", "device_exact": 16777233, "inode_exact": 1445438},
                "reported_read_only": {"path_exact": "/Users/amcarene/h27-admin", "device_reported": 16777234, "inode_reported": 1445438, "real_directory_reported": True, "symlink_reported": False, "target_control_absent_reported": True},
                "future_corrected": {"path_exact": "/Users/amcarene/h27-admin", "device_exact": 16777234, "inode_exact": 1445438},
            },
        )
        self.assertEqual(
            self.binding["bound_stale_runner_state"],
            {
                "runner_git_blob_sha1": "96df05111a5e40a418e12fb2b3db4bd9516bcab3",
                "execution_authorization_revoked": True,
                "executable": False,
                "executed": False,
                "consumed": False,
                "acknowledgement_set": False,
                "mkdir_attempted": False,
            },
        )
        self.assertEqual(
            self.binding["bound_future_control_parent"],
            {
                "target_path_exact": "/Users/amcarene/h27-admin/control",
                "target_type_exact": "directory",
                "target_mode_exact_octal": "0700",
                "acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
                "arguments_forbidden": True,
                "single_absence_probe_required": True,
                "mkdir_first_and_only_irreversible_effect": True,
                "parent_fsync_required": True,
                "reopen_and_mode_device_inode_verification_required": True,
                "cleanup_retry_repair_or_recreation_forbidden": True,
            },
        )

    def test_exact_graph_and_dormant_state(self) -> None:
        self.assertEqual(
            self.binding["identity_graph"],
            {
                "unique_path_count": 9,
                "correction_contract_and_seal_bound": True,
                "all_seven_historical_identities_rebound": True,
                "duplicates_forbidden": True,
                "path_or_identity_drift_forbidden": True,
                "acyclic": True,
                "self_hash_present": False,
                "historical_back_reference_present": False,
            },
        )
        self.assertEqual(
            self.binding["current_state"],
            {
                "identity_binding_exists": True,
                "identity_binding_externally_reviewed": False,
                "identity_binding_externally_sealed": False,
                "corrected_runner_exists": False,
                "mac_action_after_read_only_preflight": False,
                "control_parent_created": False,
                "registry_opened": False,
                "authority_reserved": False,
                "authority_consumed": False,
                "creator_entrypoint_executed": False,
                "control_bundle_created": False,
                "constructor_or_materializer_executed": False,
                "science_or_locked_test": False,
            },
        )

    def test_exact_external_seal(self) -> None:
        self.assertEqual(
            self.seal,
            {
                "schema_version": 1,
                "seal_id": "H27_CONTROL_PARENT_IDENTITY_DRIFT_CORRECTION_CONTRACT_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
                "status": "SEALED_PENDING_EXTERNAL_REVIEW_NO_RUNNER_NO_MAC_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
                "identity_binding": {"path": "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_identity_binding.json", "git_blob_sha1": "6a7fb83658d07a9c553e9bb66852652894f46b14", "size_bytes": 5067, "raw_sha256": "5c35433aea01fc8ca2772289d4a2bd3ca291161e16625abaeff4e8d73dc7d5f3"},
                "reviewed_correction_contract_commit": "90fe6eec1a3c6eeb0e174c24b497280a39ee4668",
                "reviewed_correction_contract_git_blob_sha1": "f4c45904c72a8f2e12a3ea7d8d79bea276fefd3e",
                "correction_contract_seal_git_blob_sha1": "527bb2d0b7cd5da384fcb4efb1ac5fee186b355c",
                "bound_unique_identity_count": 9,
                "historical_parent_device_exact": 16777233,
                "historical_parent_inode_exact": 1445438,
                "reported_parent_device": 16777234,
                "reported_parent_inode": 1445438,
                "reported_real_directory": True,
                "reported_symlink": False,
                "reported_target_control_absent": True,
                "stale_runner_git_blob_sha1": "96df05111a5e40a418e12fb2b3db4bd9516bcab3",
                "stale_runner_execution_authorization_revoked": True,
                "stale_runner_executable": False,
                "stale_runner_executed": False,
                "stale_runner_consumed": False,
                "future_parent_device_exact": 16777234,
                "future_parent_inode_exact": 1445438,
                "future_target_path_exact": "/Users/amcarene/h27-admin/control",
                "future_target_type_exact": "directory",
                "future_target_mode_exact_octal": "0700",
                "future_acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
                "future_arguments_forbidden": True,
                "identity_binding_externally_reviewed": False,
                "identity_binding_externally_sealed": False,
                "corrected_runner_exists": False,
                "mac_action_after_read_only_preflight": False,
                "control_parent_created": False,
                "registry_opened": False,
                "authority_reserved": False,
                "authority_consumed": False,
                "creator_entrypoint_executed": False,
                "control_bundle_created": False,
                "constructor_or_materializer_executed": False,
                "science_or_locked_test": False,
                "next_action": "External review of the correction-contract identity binding and this seal only",
            },
        )


if __name__ == "__main__":
    unittest.main()
