from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_reviewed_control_bundle_creator_contract_identity_binding import hundred_thirty

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


def hundred_thirty_four(contract: dict[str, object]) -> list[dict[str, object]]:
    creator_contract = json.loads((ROOT / contract["reviewed_creator_chain"][0]["path"]).read_bytes())
    return [*contract["reviewed_creator_chain"], *hundred_thirty(creator_contract)]


class TestReviewedCreatorImplementationSourceContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_136_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        entries = [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_thirty_four(contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (136, 136))
        for entry in entries:
            check(self, entry)

    def test_preserved_contract_state_and_edges(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        source = contract["future_implementation_source"]
        manifest = contract["future_manifest_schema"]
        rules = contract["future_publication_rules"]
        self.assertEqual(self.binding["preserved_contract"], {
            "final_root_exact": source["final_root_exact"],
            "staging_root_exact": source["staging_root_exact"],
            "entrypoint_path_exact": source["entrypoint_path_exact"],
            "manifest_path_exact": source["manifest_path_exact"],
            "closed_relative_path_order_exact": source["closed_relative_path_order_exact"],
            "exact_file_count": source["exact_file_count"],
            "manifest_top_level_field_count": len(manifest["top_level_order_exact"]),
            "manifest_entrypoint_field_count": len(manifest["entrypoint_field_order_exact"]),
            "static_preflight_step_count": len(contract["future_source_static_preflight_before_root_observation"]),
            "publication_step_count": len(contract["future_immutable_source_publication_order"]),
            "publication_rule_count": len(rules),
            "identity_future_distinct_reviewed_pass_and_sealed": source["implementation_identity_must_be_supplied_by_distinct_later_reviewed_pass_commit_and_external_seal"],
            "identity_placeholders_forbidden": source["implementation_identity_placeholders_forbidden"],
            "implicit_current_checkout_path_or_head_selection_forbidden": source["implicit_current_checkout_path_or_head_selection_forbidden"],
            "target_checkout_source_fallback_forbidden": source["target_checkout_source_fallback_forbidden"],
            "source_root_distinct_from_target_checkout": source["source_root_must_be_distinct_from_target_checkout"],
            "manifest_unknown_missing_reordered_or_extra_field_forbidden": manifest["unknown_missing_reordered_or_extra_field_forbidden"],
            "manifest_does_not_self_hash": manifest["manifest_does_not_self_hash"],
            "staging_first_irreversible_effect": rules["staging_creation_is_first_irreversible_effect"],
            "atomic_no_overwrite_publication": rules["single_atomic_publication_attempt"] and rules["no_overwrite_or_backfill"],
            "terminal_no_retry": rules["post_first_filesystem_effect_failure_terminal"] and rules["retry_cleanup_repair_or_republication_forbidden"],
        })
        allowed = {"implementation_source_contract_exists", "implementation_source_contract_externally_reviewed", "implementation_source_contract_externally_sealed", "implementation_source_contract_identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        self.assertEqual((self.seal["bound_identity_count"], self.seal["closed_source_file_count"], self.seal["manifest_top_level_field_count"], self.seal["manifest_entrypoint_field_count"], self.seal["static_preflight_step_count"], self.seal["publication_step_count"], self.seal["publication_rule_count"], self.seal["public_edges_closed"]), (136, 2, 6, 4, 7, 9, 12, 8))
        for key in ("implementation_source_created", "implementation_root_observed", "filesystem_operation_authorized", "creator_implemented", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "bundle_path_observed", "administrative_control_bundle_exists", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_no_backrefs(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_thirty_six_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        for entry in [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_thirty_four(contract)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
