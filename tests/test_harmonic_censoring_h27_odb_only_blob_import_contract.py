from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_import_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_import_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class TestH27OdbOnlyBlobImportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_contract_and_seal_bytes_are_canonical(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))

    def test_exact_eight_payloads_are_byte_bound(self) -> None:
        payloads = self.contract["payloads"]
        self.assertEqual((len(payloads), len({p["path"] for p in payloads}), len({p["git_blob_sha1"] for p in payloads})), (8, 8, 8))
        self.assertEqual([p["git_blob_sha1"] for p in payloads], [
            "d1cdf1562a814cef271d606da331e96565fcc79a",
            "d03385d842ca11631ba690d0a4bb70448c84480e",
            "e574ddbcccb8bac791d9719fbee3e7fd5db8a047",
            "a514aa0270926dca1d8402ac84078a50754d2f17",
            "0f6a64b7477bde24968200a81d389b03a4a6ced0",
            "11fff0962fc0951a0bb06605e233d34756a2f4d9",
            "24a8c14fddd52eca148f961a31c39abaa4de018f",
            "bda7e1fae7379996563e73d8bbcf1b2d7a871aa0",
        ])
        for identity in payloads:
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertEqual(
                (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
                (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
            )

    def test_fail_closed_order_and_effect_boundary(self) -> None:
        self.assertEqual(len(self.contract["future_fail_closed_order"]), 13)
        self.assertEqual(self.contract["future_fail_closed_order"][6], "prevalidate_all_eight_payload_triples_and_git_blob_ids_without_write")
        self.assertEqual(self.contract["future_fail_closed_order"][9], "write_each_exact_blob_once_in_declared_order_and_require_returned_id")
        self.assertEqual(self.contract["ref_snapshot"], {
            "regular_refs_operation_exact": "git --no-optional-locks --no-replace-objects --git-dir=/Users/amcarene/midi-worker/repository/.git for-each-ref --sort=refname --format=%(refname)%00%(objectname)%00%(objecttype)%00",
            "captures_all_regular_refs": True,
            "root_refs_directory_exact": "/Users/amcarene/midi-worker/repository/.git",
            "root_ref_name_regex_exact": "^[A-Z][A-Z0-9_]*$",
            "root_ref_scan_exact": "Python stdlib os.scandir on the exact ODB root; select every matching name; reject symlinks and non-regular entries; sort names by UTF-8 bytes; retain each name, presence and raw file bytes",
            "captures_all_present_uppercase_root_refs_and_pseudorefs": True,
            "regular_and_root_raw_bytes_retained_in_memory": True,
            "size_and_sha256_recorded_for_each_snapshot": True,
            "exact_regular_and_root_raw_bytes_equality_required_before_first_write_and_after_all_writes": True,
        })
        for index in (3, 7, 11):
            self.assertIn("regular_refs_root_refs", self.contract["future_fail_closed_order"][index])
        self.assertTrue(self.contract["prevalidation"]["all_payloads_before_any_write"])
        self.assertTrue(self.contract["prevalidation"]["write_flag_forbidden_during_prevalidation"])
        self.assertEqual(self.contract["future_write"]["operation_exact"], "git --no-replace-objects --git-dir=/Users/amcarene/midi-worker/repository/.git hash-object -w --stdin")
        for key in ("ref_update_forbidden", "head_change_forbidden", "index_change_forbidden", "worktree_change_forbidden", "unexpected_object_forbidden"):
            self.assertTrue(self.contract["future_write"][key])
        self.assertEqual(self.contract["failure_policy"], {
            "single_attempt_only": True, "no_retry": True, "no_cleanup": True,
            "no_repair": True, "no_rollback_claim": True,
            "partial_import_is_terminal_consumed_failure": True,
            "automatic_recovery_forbidden": True,
        })

    def test_current_state_is_fully_dormant(self) -> None:
        state = dict(self.contract["current_state"])
        self.assertTrue(state.pop("contract_only"))
        self.assertTrue(state.pop("external_seal_created"))
        self.assertFalse(any(state.values()))

    def test_exact_external_seal(self) -> None:
        expected_contract = {
            "path": "configs/harmonic_censoring_h27_odb_only_blob_import_contract.json",
            "git_blob_sha1": "52bfb9fe7e2e7b01c64da6fff5d7b4ed29860cf7",
            "size_bytes": 7010,
            "raw_sha256": "f51d7810fb261ab1e33d318d92c987432b9a245579e5607fffe8851e6a730ad2",
        }
        self.assertEqual(
            (expected_contract["git_blob_sha1"], expected_contract["size_bytes"], expected_contract["raw_sha256"]),
            (blob(self.contract_raw), len(self.contract_raw), hashlib.sha256(self.contract_raw).hexdigest()),
        )
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_ODB_ONLY_EXACT_BLOB_IMPORT_ONE_SHOT_CONTRACT_EXTERNAL_SEAL_V1",
            "status": "SEALED_DECLARATIVE_ONLY_PENDING_EXTERNAL_REVIEW_NO_IMPORT_NO_MAC_MUTATION_NO_DETACH_NO_DOWNSTREAM",
            "contract": expected_contract,
            "payloads": self.contract["payloads"],
            "future_regular_refs_snapshot_operation_exact": self.contract["ref_snapshot"]["regular_refs_operation_exact"],
            "future_root_refs_snapshot": {
                "directory_exact": self.contract["ref_snapshot"]["root_refs_directory_exact"],
                "name_regex_exact": self.contract["ref_snapshot"]["root_ref_name_regex_exact"],
                "scan_exact": self.contract["ref_snapshot"]["root_ref_scan_exact"],
            },
            "future_regular_and_root_refs_raw_bytes_equality_before_and_after_required": True,
            "future_fail_closed_order": self.contract["future_fail_closed_order"],
            "future_write_operation_exact": self.contract["future_write"]["operation_exact"],
            "future_all_payloads_prevalidated_before_any_write": True,
            "future_all_target_blobs_absent_before_execution": True,
            "future_ref_head_index_worktree_changes_forbidden": True,
            "future_single_attempt_only": True,
            "future_partial_import_terminal_consumed_failure": True,
            "future_retry_cleanup_repair_automatic_recovery_forbidden": True,
            "current_import_executed": False,
            "downstream_state": {
                "target_odb_changed": False, "head_changed": False,
                "index_changed": False, "worktree_changed": False,
                "runner_acknowledgement_set": False, "runner_invoked": False,
                "detach_executed": False, "registry_opened": False,
                "authority_reserved": False, "creator_invoked": False,
                "control_bundle_created": False, "materializer_executed": False,
                "science_or_locked_test": False,
            },
            "next_action": "External review of the exact declarative ODB-only import contract and this seal; no blob import",
        })


if __name__ == "__main__":
    unittest.main()
