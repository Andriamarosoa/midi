from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_control_bundle_creation_authority_artifact_identity_binding import hundred_twenty_six

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


def hundred_twenty_six_predecessors(binding: dict[str, object]) -> list[dict[str, object]]:
    artifact_seal = json.loads((ROOT / binding["artifact_external_seal"]["path"]).read_bytes())
    contract_binding = json.loads((ROOT / artifact_seal["reviewed_contract_binding"]["path"]).read_bytes())
    return hundred_twenty_six(contract_binding)


class TestReviewedControlBundleCreatorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_130_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        roots = self.contract["reviewed_and_sealed_authority_chain"]
        binding = json.loads((ROOT / roots[2]["path"]).read_bytes())
        entries = [*roots, *hundred_twenty_six_predecessors(binding)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (130, 130))
        for entry in entries:
            check(self, entry)

    def test_exact_creator_orders_rules_and_state(self) -> None:
        definition = self.contract["future_creator_definition"]
        self.assertEqual(definition, {
            "implementation_must_be_distinct_later_commit_reviewed_pass_and_sealed": True,
            "implementation_or_entrypoint_does_not_exist_at_contract_stage": True,
            "target_checkout_root_exact": "/Users/amcarene/midi-worker/repository",
            "target_checkout_expected_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "source_git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "authority_artifact_id_exact": "4e1072559ff1ef5ec1e2fb0e4ec72b3baca2d98811fabfb568e9380951129c76",
            "authority_single_use_exact": True,
            "authority_initial_consumed_exact": False,
            "persistent_registry_parent_exact": "/Users/amcarene/h27-admin/registry",
            "persistent_registry_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "registry_record_key_exact": "creation_authority_artifact_id",
            "registry_terminal_states_exact": ["reserved", "consumed", "bundle_creation_succeeded", "terminal_failure"],
        })
        self.assertEqual(self.contract["future_static_preflight_before_registry_open"], ["rehash_all_one_hundred_thirty_predecessor_identities", "verify_target_checkout_realpath_head_and_cleanliness", "verify_authority_artifact_exact_eight_field_compact_lf_schema", "recompute_and_compare_authority_artifact_id_from_seven_canonical_fields", "verify_authorization_chain_six_exact_values", "verify_bundle_definition_three_exact_values", "verify_single_use_true_and_consumed_false", "verify_exact_source_git_object_database_realpath_and_no_symlink_escape", "verify_all_six_source_git_blobs_by_exact_identity_without_bundle_path_observation", "verify_registry_parent_realpath_policy_and_exact_registry_path_without_opening_registry"])
        self.assertEqual(self.contract["future_one_shot_effect_order"], ["open_and_exclusively_lock_exact_persistent_registry", "reject_if_exact_artifact_id_already_present_in_any_terminal_state", "append_and_fsync_exact_reserved_record_atomically_first_irreversible_effect", "append_and_fsync_exact_consumed_record_atomically", "execute_exact_thirteen_bundle_creation_steps_once_without_backfill_or_retry", "append_and_fsync_bundle_creation_succeeded_record", "release_registry_lock_and_return_terminal_success"])
        self.assertEqual(self.contract["exact_thirteen_bundle_creation_steps"], ["rehash_all_one_hundred_twenty_predecessor_identities", "verify_exact_git_object_database_path_and_no_symlink_escape", "extract_each_of_six_blobs_by_exact_git_blob_sha1", "verify_each_extracted_blob_size_and_sha256", "verify_control_parent_realpath_is_exact_and_not_symlinked", "probe_final_and_staging_bundle_absence_once", "create_staging_bundle_exclusively", "write_exact_six_files_with_preserved_relative_paths_and_no_overwrite", "fsync_files_and_directories", "rehash_staged_closed_manifest", "rename_staging_to_final_atomically_without_overwrite", "rehash_final_closed_manifest", "mark_success_terminal"])
        rules = ["all_static_checks_precede_registry_open", "registry_lock_is_exclusive", "artifact_id_reservation_is_unique_and_never_reusable", "reservation_is_first_irreversible_effect", "consumption_precedes_any_bundle_path_observation", "consumption_is_atomic_and_irreversible", "exact_thirteen_steps_executed_once", "post_reservation_failure_terminal", "post_consumption_failure_terminal", "post_first_filesystem_effect_failure_terminal", "retry_after_reservation_or_consumption_or_first_filesystem_effect_forbidden", "no_automatic_recovery_or_cleanup_that_enables_retry"]
        self.assertEqual(list(self.contract["future_creator_rules"]), rules)
        self.assertTrue(all(self.contract["future_creator_rules"].values()))
        allowed = {"reviewed_control_bundle_creator_contract_exists"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_thirty_predecessor_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual((self.seal["bound_predecessor_identity_count"], self.seal["static_preflight_step_count"], self.seal["one_shot_effect_step_count"], self.seal["bundle_creation_step_count"], self.seal["public_edges_closed"]), (130, 10, 7, 13, 8))
        for key in ("creator_implemented", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "bundle_path_observed", "administrative_control_bundle_exists", "filesystem_operation_authorized", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_no_backrefs(self) -> None:
        roots = self.contract["reviewed_and_sealed_authority_chain"]
        binding = json.loads((ROOT / roots[2]["path"]).read_bytes())
        for entry in [*roots, *hundred_twenty_six_predecessors(binding)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
