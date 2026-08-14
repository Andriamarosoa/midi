from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_identity_binding import hundred_twenty

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


def hundred_twenty_four(contract: dict[str, object]) -> list[dict[str, object]]:
    roots = contract["reviewed_and_sealed_bundle_creation_contract_chain"]
    bundle_creation_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
    return [*roots, *hundred_twenty(bundle_creation_contract)]


class TestAuthorityArtifactContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_126_identities(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        entries = [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_twenty_four(contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (126, 126))
        for entry in entries:
            check(self, entry)

    def test_exact_schema_guards_state_and_edges(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        schema = contract["future_artifact_schema"]
        preserved = self.binding["preserved_future_artifact_schema"]
        self.assertEqual(preserved, {
            "exact_top_level_field_count": 8,
            "artifact_type_exact": "h27_immutable_control_bundle_creation_authority",
            "creation_authority_artifact_id_lowercase_hex64": True,
            "canonical_payload_omits_only_creation_authority_artifact_id": True,
            "canonical_payload_exact_seven_field_order": True,
            "canonical_payload_compact_utf8_rfc8259_plus_one_lf": True,
            "full_artifact_compact_exact_eight_fields_plus_one_lf": True,
            "expected_execution_git_head_exact_native_lowercase_hex40": True,
            "expected_execution_git_head_distinct_later_reviewed_sealed_artifact_only": True,
            "automatic_current_head_derivation_forbidden": True,
            "authorization_chain_six_exact_ordered_values": True,
            "bundle_definition_three_exact_ordered_values": True,
            "single_use_exact_boolean": True,
            "consumed_initial_exact_boolean": False,
            "strict_rules_preserved": True,
        })
        self.assertEqual(len(contract["future_artifact_canonical_top_level_order"]), preserved["exact_top_level_field_count"])
        self.assertEqual(schema["artifact_type"]["exact_value"], preserved["artifact_type_exact"])
        self.assertEqual(self.binding["preserved_authorization_chain_identity"], schema["authorization_chain_identity"]["exact_values"])
        bundle = schema["bundle_definition_identity"]
        self.assertEqual(self.binding["preserved_bundle_definition_identity"], {
            "final_bundle_root": bundle["final_bundle_root_exact"],
            "closed_manifest_file_count": bundle["closed_manifest_file_count_exact"],
            "source_git_object_database": bundle["source_git_object_database_exact"],
        })
        self.assertEqual(list(self.binding["preserved_guards"]), ["artifact_id_unique_in_persistent_registry", "separate_real_artifact_commit_external_review_and_seal_required", "artifact_creation_does_not_create_or_observe_bundle", "consumption_only_by_future_reviewed_bundle_creator", "post_consumption_failure_terminal", "retry_after_consumption_forbidden"])
        self.assertTrue(all(self.binding["preserved_guards"].values()))
        allowed = {"authority_artifact_contract_exists", "authority_artifact_contract_externally_reviewed", "authority_artifact_contract_externally_sealed", "authority_artifact_contract_identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_twenty_six_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual((self.seal["bound_identity_count"], self.seal["future_artifact_top_level_field_count"], self.seal["authorization_chain_exact_value_count"], self.seal["bundle_definition_exact_value_count"], self.seal["public_edges_closed"]), (126, 8, 6, 3, 8))
        self.assertIs(self.seal["single_use"], True)
        for key in ("future_authority_artifact_exists", "administrative_control_bundle_exists", "bundle_path_observed", "filesystem_operation_authorized", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "constructor_invoked_really", "destination_observed", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_no_backrefs(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        for entry in [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_twenty_four(contract)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
