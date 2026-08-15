from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestControlParentIdentityDriftCorrectionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seven_historical_identities_and_no_back_reference(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["correction_contract"])
        identities = self.contract["historical_exact_identities"]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (7, 7))
        for identity in identities:
            raw = check(self, identity)
            self.assertNotIn(b"harmonic_censoring_h27_control_parent_identity_drift_correction_contract", raw)
        self.assertEqual(
            [item["git_blob_sha1"] for item in identities],
            [
                "a9b37b3081ad79b773f3a7291a508665d623307a",
                "9edefaa15313be5d3a618b4b3ada012e14ef039b",
                "4c84d7d62b177b23feef55a4cb4b2521212fc0ff",
                "297ff5953c0fed3db0c4dca2b984dcc822244dcb",
                "96df05111a5e40a418e12fb2b3db4bd9516bcab3",
                "4a1b1ac62395d9880e747dc24395c2e2a0edce85",
                "449537a22bf1979273fd90e8bac7650170248f62",
            ],
        )

    def test_exact_historical_observed_and_superseded_states(self) -> None:
        self.assertEqual(
            self.contract["historical_terminal_parent"],
            {
                "path_exact": "/Users/amcarene/h27-admin",
                "device_exact": 16777233,
                "inode_exact": 1445438,
                "source": "H27_ADMIN_ROOT_CREATED_TERMINAL_SUCCESS",
                "preserved_as_historical_fact": True,
            },
        )
        self.assertEqual(
            self.contract["reported_current_read_only_observation"],
            {
                "observed_at_utc": "2026-08-15T07:10:00Z",
                "path_exact": "/Users/amcarene/h27-admin",
                "device_reported": 16777234,
                "inode_reported": 1445438,
                "real_directory_reported": True,
                "symlink_reported": False,
                "target_control_absent_reported": True,
                "git_object_database_realpath_reported": "/Users/amcarene/midi-worker/repository/.git",
                "repository_worktree_clean_reported": True,
                "remote_commit_reported": "6cfc210f2f96217b713baf1a84b5d09558023a73",
                "observation_read_only": True,
                "mac_fact_not_reproducible_from_git_alone": True,
            },
        )
        self.assertEqual(
            self.contract["superseded_execution"],
            {
                "runner_git_blob_sha1": "96df05111a5e40a418e12fb2b3db4bd9516bcab3",
                "execution_authorization_revoked": True,
                "executable_under_current_observation": False,
                "executed": False,
                "consumed": False,
                "acknowledgement_set": False,
                "target_observed_by_runner": False,
                "mkdir_attempted": False,
                "cleanup_or_retry_performed": False,
            },
        )

    def test_exact_future_boundary_graph_and_dormant_state(self) -> None:
        self.assertEqual(
            self.contract["future_corrected_boundary"],
            {
                "platform_exact": "darwin",
                "acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
                "arguments_forbidden": True,
                "parent_path_exact": "/Users/amcarene/h27-admin",
                "parent_device_exact": 16777234,
                "parent_inode_exact": 1445438,
                "target_path_exact": "/Users/amcarene/h27-admin/control",
                "target_type_exact": "directory",
                "target_mode_exact_octal": "0700",
                "seven_historical_identities_must_be_rehashed_before_parent_observation": True,
                "single_absence_probe_required": True,
                "parent_revalidation_before_first_effect_and_before_success_required": True,
                "mkdir_exact_leaf_first_and_only_irreversible_effect": True,
                "parent_fsync_required": True,
                "reopen_o_nofollow_o_directory_required": True,
                "target_mode_device_inode_verification_required": True,
                "cleanup_retry_repair_or_recreation_forbidden": True,
            },
        )
        self.assertEqual(
            self.contract["identity_graph"],
            {
                "historical_unique_path_count": 7,
                "all_seven_historical_identities_must_be_rehashed": True,
                "duplicates_forbidden": True,
                "path_or_identity_drift_forbidden": True,
                "acyclic": True,
                "self_hash_present": False,
                "historical_back_reference_present": False,
            },
        )
        self.assertEqual(
            self.contract["current_state"],
            {
                "correction_contract_exists": True,
                "correction_contract_externally_reviewed": False,
                "correction_contract_externally_sealed": False,
                "corrected_contract_binding_exists": False,
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
                "seal_id": "H27_CONTROL_PARENT_IDENTITY_DRIFT_CORRECTION_CONTRACT_EXTERNAL_SEAL_V1",
                "status": "SEALED_PENDING_EXTERNAL_REVIEW_STALE_RUNNER_NOT_EXECUTED_NOT_CONSUMED_NO_RUNNER_NO_MAC_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
                "correction_contract": {"path": "configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract.json", "git_blob_sha1": "f4c45904c72a8f2e12a3ea7d8d79bea276fefd3e", "size_bytes": 5475, "raw_sha256": "9c7cae98c0590c88c0af17ae03102a617498ab4e3b98531905a59f95da228fe2"},
                "historical_identity_count": 7,
                "historical_parent_path_exact": "/Users/amcarene/h27-admin",
                "historical_parent_device_exact": 16777233,
                "historical_parent_inode_exact": 1445438,
                "reported_parent_device": 16777234,
                "reported_parent_inode": 1445438,
                "reported_real_directory": True,
                "reported_symlink": False,
                "reported_target_control_absent": True,
                "reported_observation_read_only": True,
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
                "corrected_contract_binding_exists": False,
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
                "next_action": "External review of the correction contract and this seal only",
            },
        )


if __name__ == "__main__":
    unittest.main()
