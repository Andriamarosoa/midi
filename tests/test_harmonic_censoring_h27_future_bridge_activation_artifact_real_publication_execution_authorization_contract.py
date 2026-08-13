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
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_execution_authorization_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_execution_authorization_contract_external_seal.json"
DESTINATION_BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract_identity_binding.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _check(test: unittest.TestCase, item: dict[str, object]) -> None:
    path = ROOT / item["path"]
    raw = path.read_bytes()
    test.assertEqual(item["git_blob_sha1"], _blob(raw))
    test.assertEqual(item["size_bytes"], len(raw))
    test.assertEqual(item["raw_sha256"], hashlib.sha256(raw).hexdigest())


def _sixty_from_destination_binding(binding: dict[str, object]) -> list[dict[str, object]]:
    destination_contract = json.loads((ROOT / binding["reviewed_contract"]["path"]).read_bytes())
    dormant_roots = destination_contract["reviewed_and_sealed_dormant_boundary"]
    dormant_binding = json.loads((ROOT / destination_contract["transitive_identity_source"]["path"]).read_bytes())
    administrative_roots = dormant_binding["upstream_roots"]
    earlier = json.loads((ROOT / administrative_roots[0]["path"]).read_bytes())
    fifty_four = [earlier["reviewed_contract"], earlier["contract_external_seal"], *earlier["reviewed_and_sealed_dormant_publication_simulator"]]
    oldest = json.loads((ROOT / earlier["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
    return [*dormant_roots, *administrative_roots, *fifty_four, *oldest]


class H27RealPublicationExecutionAuthorizationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.binding = json.loads(DESTINATION_BINDING.read_bytes())

    def test_canonical_contract_seal_and_sixty_four_exact_identities(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        _check(self, self.seal["contract"])
        roots = self.contract["reviewed_and_sealed_destination_contract_chain"]
        entries = [*roots, *_sixty_from_destination_binding(self.binding)]
        self.assertEqual(len(entries), 64)
        self.assertEqual(len({item["path"] for item in entries}), 64)
        for item in entries:
            _check(self, item)

    def test_graph_is_acyclic_and_predecessors_do_not_reference_new_artifacts(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        entries = [*self.contract["reviewed_and_sealed_destination_contract_chain"], *_sixty_from_destination_binding(self.binding)]
        for item in entries:
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)

    def test_no_destination_operation_or_real_authorization_is_open(self) -> None:
        destination = self.contract["canonical_destination"]
        self.assertEqual(destination["destination_path"], "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json")
        for key, value in destination.items():
            if key != "destination_path":
                self.assertIs(value, False, key)
        for key, value in self.contract["current_state"].items():
            self.assertIs(value, key == "execution_authorization_contract_exists", key)
        self.assertEqual(self.contract["public_edges_closed"], 8)
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            real_publication.publish_h27_future_bridge_activation_artifact_real,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))


if __name__ == "__main__":
    unittest.main()
