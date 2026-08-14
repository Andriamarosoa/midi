from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_identity_binding import (
    hundred_twenty,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract_external_seal.json"


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check_identity(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (git_blob_sha1(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestBundleCreationAuthorityArtifactContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_124_predecessors(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check_identity(self, self.seal["contract"])
        roots = self.contract["reviewed_and_sealed_bundle_creation_contract_chain"]
        bundle_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
        entries = [*roots, *hundred_twenty(bundle_contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (124, 124))
        for entry in entries:
            check_identity(self, entry)

    def test_closed_schema_exact_values_and_canonical_id(self) -> None:
        top_level = ["schema_version", "artifact_type", "creation_authority_artifact_id", "expected_execution_git_head", "authorization_chain_identity", "bundle_definition_identity", "single_use", "consumed"]
        self.assertEqual(self.contract["future_artifact_canonical_top_level_order"], top_level)
        schema = self.contract["future_artifact_schema"]
        self.assertEqual(list(schema), top_level)
        self.assertEqual(schema["artifact_type"]["exact_value"], "h27_immutable_control_bundle_creation_authority")

        chain_fields = ["contract_git_blob_sha1", "contract_size_bytes", "contract_raw_sha256", "binding_git_blob_sha1", "binding_size_bytes", "binding_raw_sha256"]
        chain_values = {
            "contract_git_blob_sha1": "0f9b4191a55e9942ebe739d378f40c4b01b23533",
            "contract_size_bytes": 7082,
            "contract_raw_sha256": "903f10596c8f81ad53ef37331d54c027b9e045b6d44ce2ede2513b0f3d7bf7c0",
            "binding_git_blob_sha1": "0385ba78d55f3c2e3af987132c985e60be612ddc",
            "binding_size_bytes": 3261,
            "binding_raw_sha256": "226cfc34329f9ef7545f95ae415c0b6f151bf4694c39bae3e80e18defec8f4d1",
        }
        chain_schema = schema["authorization_chain_identity"]
        self.assertEqual(chain_schema["exact_key_order"], chain_fields)
        self.assertEqual(list(chain_schema["exact_values"]), chain_fields)
        self.assertEqual(chain_schema["exact_values"], chain_values)

        id_schema = schema["creation_authority_artifact_id"]
        payload_order = [name for name in top_level if name != "creation_authority_artifact_id"]
        self.assertEqual(id_schema["canonical_payload_field_order_after_omitting_creation_authority_artifact_id"], payload_order)
        self.assertEqual(id_schema["derivation"], "lowercase_hex_sha256_of_canonical_payload_bytes")
        self.assertEqual(id_schema["canonical_payload_serialization"], "UTF-8 compact RFC8259 JSON using comma and colon separators, no insignificant whitespace, no BOM, exact prescribed object key orders, lowercase true and false literals, then exactly one terminal LF byte 0x0A")
        self.assertIs(id_schema["artifact_file_serialization_must_equal_canonical_eight_field_compact_json_plus_one_terminal_lf"], True)

        head_schema = schema["expected_execution_git_head"]
        self.assertEqual(head_schema["pattern"], "lowercase_hex40")
        for key in ("exact_native_string_required", "automatic_current_head_derivation_forbidden", "must_be_explicit_future_externally_reviewed_pass_commit", "value_supplied_only_in_distinct_later_reviewed_and_sealed_artifact_commit"):
            self.assertIs(head_schema[key], True, key)

        bundle_schema = schema["bundle_definition_identity"]
        self.assertEqual(bundle_schema, {
            "json_type": "object",
            "exact_key_order": ["final_bundle_root", "closed_manifest_file_count", "source_git_object_database"],
            "final_bundle_root_exact": "/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1",
            "closed_manifest_file_count_exact": 6,
            "source_git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
        })
        self.assertIs(schema["single_use"]["exact_value"], True)
        self.assertIs(schema["consumed"]["exact_value"], False)

        payload = {
            "schema_version": 1,
            "artifact_type": "h27_immutable_control_bundle_creation_authority",
            "expected_execution_git_head": "a" * 40,
            "authorization_chain_identity": chain_values,
            "bundle_definition_identity": {
                "final_bundle_root": bundle_schema["final_bundle_root_exact"],
                "closed_manifest_file_count": bundle_schema["closed_manifest_file_count_exact"],
                "source_git_object_database": bundle_schema["source_git_object_database_exact"],
            },
            "single_use": True,
            "consumed": False,
        }
        self.assertEqual(list(payload), payload_order)
        canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        self.assertNotIn(b" ", canonical)
        self.assertTrue(canonical.endswith(b"\n"))
        self.assertRegex(hashlib.sha256(canonical).hexdigest(), r"^[0-9a-f]{64}$")

    def test_rules_state_seal_and_no_backrefs(self) -> None:
        rules = ["strict_json_no_duplicate_keys_no_nan_no_infinity", "canonical_utf8_lf_no_bom", "exact_top_level_and_nested_key_order_required", "unknown_or_missing_field_rejected", "artifact_id_unique_in_persistent_registry", "separate_real_artifact_commit_external_review_and_seal_required", "artifact_creation_does_not_create_or_observe_bundle", "consumption_only_by_future_reviewed_bundle_creator", "post_consumption_failure_terminal", "retry_after_consumption_forbidden"]
        self.assertEqual(list(self.contract["future_artifact_rules"]), rules)
        self.assertTrue(all(self.contract["future_artifact_rules"].values()))
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key == "control_bundle_creation_authority_artifact_contract_exists", key)
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_twenty_four_predecessor_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        for key in ("authorization_chain_identity_exact", "creation_authority_artifact_id_canonical_bytes_fully_defined", "expected_execution_git_head_fail_closed", "bundle_definition_identity_exact", "single_use"):
            self.assertIs(self.seal[key], True, key)
        self.assertEqual((self.seal["bound_predecessor_identity_count"], self.seal["public_edges_closed"]), (124, 8))
        for key in ("future_artifact_exists", "administrative_control_bundle_exists", "bundle_path_observed", "filesystem_operation_authorized", "persistent_registry_opened", "authority_consumed", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)
        roots = self.contract["reviewed_and_sealed_bundle_creation_contract_chain"]
        bundle_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
        for entry in [*roots, *hundred_twenty(bundle_contract)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
