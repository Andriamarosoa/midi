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
BINDING = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_instance_artifact_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_instance_artifact_contract_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _check(test: unittest.TestCase, item: dict) -> None:
    raw = (ROOT / item["path"]).read_bytes()
    test.assertEqual(
        (item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"]),
        (_blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )


def _ninety_two(contract: dict) -> list[dict]:
    roots = contract["reviewed_and_sealed_one_shot_authority_contract_chain"]
    authority_contract = json.loads((ROOT / roots[0]["path"]).read_bytes())
    return [*roots, *_eighty_eight(authority_contract)]


class H27AuthorityInstanceArtifactContractBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_canonical_binding_seal_and_ninety_four_exact_identities(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        _check(self, self.seal["identity_binding"])
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        entries = [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *_ninety_two(contract)]
        self.assertEqual(len(entries), 94)
        self.assertEqual(len({item["path"] for item in entries}), 94)
        for item in entries:
            _check(self, item)

    def test_preserved_schema_order_identity_rules_and_closed_state(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        schema = contract["future_artifact_schema"]
        preserved = self.binding["preserved_canonical_schema"]
        self.assertTrue(preserved["top_level_field_order_exact"])
        self.assertTrue(preserved["sealed_chain_identity_field_order_exact"])
        self.assertTrue(schema["object_key_order_must_equal_exact_top_level_field_order"])
        self.assertTrue(schema["sealed_chain_identity_key_order_must_equal_exact_fields"])
        self.assertEqual(list(schema["sealed_chain_identity_exact_values"]), schema["sealed_chain_identity_exact_fields"])
        self.assertTrue(schema["authority_instance_id_unique_in_namespace_and_never_reusable"])
        self.assertTrue(schema["invocation_nonce_unique_in_h27_namespace_and_never_reusable"])
        self.assertTrue(schema["persistent_used_identity_and_nonce_registry_required_before_creation"])
        self.assertTrue(schema["identity_or_nonce_reserved_terminally_before_artifact_publication"])
        self.assertEqual(self.binding["preserved_normative_order"], contract["future_normative_order"])
        allowed = {
            "authority_instance_artifact_contract_exists",
            "authority_instance_artifact_contract_externally_reviewed",
            "authority_instance_artifact_contract_externally_sealed",
            "authority_instance_artifact_contract_identity_binding_exists",
        }
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual(self.binding["public_edges_closed"], 8)
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

    def test_no_predecessor_references_new_binding_or_seal(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        for item in [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *_ninety_two(contract)]:
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
