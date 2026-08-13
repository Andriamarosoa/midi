from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant as real_publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as authority
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition
from tests.test_harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_contract_identity_binding import _eighty_eight

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_instance_artifact_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_instance_artifact_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _check(test: unittest.TestCase, item: dict) -> None:
    raw = (ROOT / item["path"]).read_bytes()
    test.assertEqual(
        (item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"]),
        (_blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )


class H27OneShotAuthorityInstanceArtifactContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_canonical_seal_and_ninety_two_exact_predecessors(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        _check(self, self.seal["contract"])
        roots = self.contract["reviewed_and_sealed_one_shot_authority_contract_chain"]
        authority_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
        entries = [*roots, *_eighty_eight(authority_contract)]
        self.assertEqual(len(entries), 92)
        self.assertEqual(len({item["path"] for item in entries}), 92)
        for item in entries:
            _check(self, item)

    def test_exact_future_schema_order_and_closed_state(self) -> None:
        schema = self.contract["future_artifact_schema"]
        self.assertEqual(
            schema["exact_top_level_field_order"],
            [
                "schema_version", "artifact_type", "authority_instance_id", "issuer_id",
                "issued_at_utc", "invocation_nonce", "canonical_destination_path",
                "sealed_chain_identity", "single_use", "consumed",
            ],
        )
        self.assertIs(type(schema["schema_version_exact_integer"]), int)
        self.assertEqual(schema["schema_version_exact_integer"], 1)
        self.assertEqual(schema["issuer_id_exact"], "h27-execution-codex-mac-primary")
        self.assertEqual(schema["canonical_destination_path_exact"], "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json")
        self.assertTrue(schema["single_use_exact_boolean"])
        self.assertFalse(schema["consumed_initial_exact_boolean"])
        self.assertTrue(schema["object_key_order_must_equal_exact_top_level_field_order"])
        self.assertTrue(schema["sealed_chain_identity_key_order_must_equal_exact_fields"])
        self.assertTrue(schema["nested_object_key_order_must_equal_sealed_chain_identity_exact_fields"])
        self.assertEqual(
            list(schema["sealed_chain_identity_exact_values"]),
            schema["sealed_chain_identity_exact_fields"],
        )
        self.assertNotIn("sorted_keys", " ".join(schema))
        self.assertIn("sha256(", schema["authority_instance_id_derivation"])
        self.assertTrue(schema["authority_instance_id_unique_in_namespace_and_never_reusable"])
        self.assertTrue(schema["invocation_nonce_unique_in_h27_namespace_and_never_reusable"])
        self.assertTrue(schema["persistent_used_identity_and_nonce_registry_required_before_creation"])
        self.assertTrue(schema["identity_or_nonce_reserved_terminally_before_artifact_publication"])
        values = {
            "schema_version": 1,
            "artifact_type": schema["artifact_type_exact"],
            "authority_instance_id": "a" * 64,
            "issuer_id": schema["issuer_id_exact"],
            "issued_at_utc": "2026-08-13T00:00:00Z",
            "invocation_nonce": "b" * 64,
            "canonical_destination_path": schema["canonical_destination_path_exact"],
            "sealed_chain_identity": schema["sealed_chain_identity_exact_values"],
            "single_use": True,
            "consumed": False,
        }
        ordered = {key: values[key] for key in schema["exact_top_level_field_order"]}
        canonical = (json.dumps(ordered, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        self.assertEqual(list(json.loads(canonical).keys()), schema["exact_top_level_field_order"])
        parsed = json.loads(canonical)
        self.assertEqual(
            list(parsed["sealed_chain_identity"]),
            schema["sealed_chain_identity_exact_fields"],
        )
        permuted_nested = dict(reversed(list(schema["sealed_chain_identity_exact_values"].items())))
        self.assertNotEqual(list(permuted_nested), schema["sealed_chain_identity_exact_fields"])
        self.assertNotEqual(
            json.dumps(permuted_nested, separators=(",", ":")),
            json.dumps(schema["sealed_chain_identity_exact_values"], separators=(",", ":")),
        )
        self.assertNotIn(b"\r", canonical)
        self.assertFalse(canonical.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(canonical.endswith(b"\n"))
        def derive(nonce: str) -> str:
            preimage = "\0".join((
                schema["authority_instance_id_namespace"], schema["issuer_id_exact"],
                values["issued_at_utc"], nonce, schema["canonical_destination_path_exact"],
                schema["sealed_chain_identity_exact_values"]["contract_raw_sha256"],
                schema["sealed_chain_identity_exact_values"]["binding_raw_sha256"],
            )).encode("ascii")
            return hashlib.sha256(preimage).hexdigest()
        self.assertNotEqual(derive("b" * 64), derive("c" * 64))
        used_ids: set[str] = set()
        used_nonces: set[str] = set()
        instance_id = derive("b" * 64)
        used_ids.add(instance_id); used_nonces.add("b" * 64)
        self.assertIn(instance_id, used_ids)
        self.assertIn("b" * 64, used_nonces)
        self.assertEqual(
            self.contract["future_normative_order"],
            [
                "rehash_all_ninety_two_predecessor_identities",
                "consume_one_shot_authority",
                "first_destination_observation_probes_absence",
                "create_exclusive_without_overwrite",
            ],
        )
        rules = self.contract["future_instance_rules"]
        self.assertTrue(rules["instance_strictly_single_use_and_non_reusable"])
        self.assertTrue(rules["success_terminal"] and rules["post_consumption_failure_terminal"])
        self.assertTrue(rules["retry_after_consumption_forbidden"])
        allowed = {"authority_instance_artifact_contract_exists"}
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual(self.contract["public_edges_closed"], 8)
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            real_publication.publish_h27_future_bridge_activation_artifact_real,
            authority.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))

    def test_no_predecessor_references_new_contract_or_seal(self) -> None:
        roots = self.contract["reviewed_and_sealed_one_shot_authority_contract_chain"]
        authority_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
        for item in [*roots, *_eighty_eight(authority_contract)]:
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
