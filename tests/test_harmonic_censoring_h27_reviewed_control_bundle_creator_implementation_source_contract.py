from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_reviewed_control_bundle_creator_contract_identity_binding import hundred_thirty

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


class TestReviewedCreatorImplementationSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_134_predecessor_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["contract"])
        creator_contract = json.loads((ROOT / self.contract["reviewed_creator_chain"][0]["path"]).read_bytes())
        entries = [*self.contract["reviewed_creator_chain"], *hundred_thirty(creator_contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (134, 134))
        for entry in entries:
            check(self, entry)

    def test_closed_source_schema_publication_and_state(self) -> None:
        source = self.contract["future_implementation_source"]
        manifest = self.contract["future_manifest_schema"]
        self.assertEqual(source, {
            "source_id_exact": "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_IMPLEMENTATION_SOURCE_V1",
            "final_root_exact": "/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1",
            "staging_root_exact": "/Users/amcarene/h27-admin/creator/.h27-reviewed-control-bundle-creator-v1.staging",
            "entrypoint_relative_path_exact": "h27_reviewed_control_bundle_creator.py",
            "entrypoint_path_exact": "/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1/h27_reviewed_control_bundle_creator.py",
            "manifest_relative_path_exact": "manifest.json",
            "manifest_path_exact": "/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1/manifest.json",
            "closed_relative_path_order_exact": ["h27_reviewed_control_bundle_creator.py", "manifest.json"],
            "exact_file_count": 2,
            "implementation_bytes_do_not_exist_at_contract_stage": True,
            "implementation_identity_must_be_supplied_by_distinct_later_reviewed_pass_commit_and_external_seal": True,
            "implementation_identity_required_fields_exact": ["path", "git_blob_sha1", "size_bytes", "raw_sha256"],
            "implementation_identity_placeholders_forbidden": True,
            "implicit_current_checkout_path_or_head_selection_forbidden": True,
            "target_checkout_source_fallback_forbidden": True,
            "source_root_must_be_distinct_from_target_checkout": True,
        })
        self.assertEqual(manifest, {
            "encoding_exact": "UTF-8",
            "bom_forbidden": True,
            "compact_rfc8259_json_exact": True,
            "terminal_lf_count_exact": 1,
            "top_level_order_exact": ["schema_version", "source_id", "reviewed_creator_contract_identity", "reviewed_creator_binding_identity", "root", "entrypoint"],
            "schema_version_exact_integer": 1,
            "source_id_exact": "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_IMPLEMENTATION_SOURCE_V1",
            "reviewed_creator_contract_identity_exact": {"git_blob_sha1": "cee37fbececa8387266ba693ae915aeb8ce3ac4e", "size_bytes": 9920, "raw_sha256": "8decca47ec6947951fddfb8becdaa550609fa50e2c12e310d7a4476210f583da"},
            "reviewed_creator_binding_identity_exact": {"git_blob_sha1": "b5ec9c1c65e1f15a8eff65fec7749d808c1193ae", "size_bytes": 3248, "raw_sha256": "54a31600aa1898d946b57bcda5330993e6740a642aec5f1a7ca35d5bb96b380c"},
            "root_exact": "/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1",
            "entrypoint_field_order_exact": ["path", "git_blob_sha1", "size_bytes", "raw_sha256"],
            "entrypoint_path_exact": "h27_reviewed_control_bundle_creator.py",
            "unknown_missing_reordered_or_extra_field_forbidden": True,
            "manifest_does_not_self_hash": True,
        })
        self.assertEqual(self.contract["future_source_static_preflight_before_root_observation"], ["rehash_all_one_hundred_thirty_four_predecessor_identities", "verify_later_implementation_identity_binding_and_external_seal_reviewed_pass", "verify_exact_implementation_git_object_database_is_explicit_and_sealed", "extract_entrypoint_bytes_only_by_exact_later_reviewed_git_blob_sha1", "verify_entrypoint_size_and_raw_sha256_before_any_root_observation", "construct_expected_manifest_bytes_from_closed_schema_and_exact_entrypoint_identity", "verify_creator_parent_realpath_exact_and_not_symlinked_without_observing_final_or_staging_roots"])
        self.assertEqual(self.contract["future_immutable_source_publication_order"], ["probe_final_and_staging_absence_once", "create_exact_staging_root_exclusively_first_irreversible_effect", "write_entrypoint_bytes_exclusively_without_overwrite", "write_exact_canonical_manifest_bytes_exclusively_without_overwrite", "fsync_both_files_and_staging_directory", "rehash_closed_staging_source_and_reject_extra_missing_or_changed_paths", "rename_staging_to_final_atomically_without_overwrite", "fsync_creator_parent_directory", "rehash_closed_final_source_and_return_terminal_success"])
        rules = self.contract["future_publication_rules"]
        self.assertEqual(set(rules), {"all_seven_static_checks_precede_root_observation", "final_and_staging_roots_must_both_be_absent", "symlink_or_realpath_escape_forbidden", "entrypoint_bytes_obtained_only_from_exact_sealed_git_blob", "manifest_bytes_constructed_canonically_and_not_read_from_checkout", "exactly_two_closed_paths_and_no_extras", "no_overwrite_or_backfill", "staging_creation_is_first_irreversible_effect", "single_atomic_publication_attempt", "post_first_filesystem_effect_failure_terminal", "retry_cleanup_repair_or_republication_forbidden", "published_source_is_read_only_immutable_input_for_later_creator_execution"})
        self.assertEqual(len(rules), 12)
        self.assertTrue(all(value is True for value in rules.values()))
        allowed = {"implementation_source_contract_exists"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in allowed, key)
        self.assertEqual((self.seal["bound_predecessor_identity_count"], self.seal["closed_source_file_count"], self.seal["manifest_top_level_field_count"], self.seal["manifest_entrypoint_field_count"], self.seal["static_preflight_step_count"], self.seal["publication_step_count"], self.seal["publication_rule_count"], self.seal["public_edges_closed"]), (134, 2, 6, 4, 7, 9, 12, 8))
        for key in ("implementation_source_created", "implementation_root_observed", "filesystem_operation_authorized", "creator_implemented", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "bundle_path_observed", "administrative_control_bundle_exists", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_dependency_graph_and_no_backrefs(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_thirty_four_predecessor_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        creator_contract = json.loads((ROOT / self.contract["reviewed_creator_chain"][0]["path"]).read_bytes())
        for entry in [*self.contract["reviewed_creator_chain"], *hundred_thirty(creator_contract)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
