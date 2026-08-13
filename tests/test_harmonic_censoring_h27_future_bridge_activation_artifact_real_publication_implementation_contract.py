from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_external_seal.json"
UPSTREAM_BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_identity_binding.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27RealPublicationImplementationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.upstream_raw = UPSTREAM_BINDING.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.upstream = json.loads(cls.upstream_raw)

    def test_contract_and_seal_are_canonical_without_self_hash(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("contract_sha256", self.contract)
        self.assertNotIn("seal_sha256", self.seal)

    def test_seal_binds_exact_contract_bytes(self) -> None:
        _assert_binding(self, self.seal["contract"], CONTRACT)
        self.assertEqual(
            self.seal["reviewed_and_sealed_dormant_publication_simulator"]["combined_unique_identity_count"],
            52,
        )

    def test_four_simulator_artifacts_and_forty_eight_upstream_are_exact_and_unique(self) -> None:
        simulator = self.contract["reviewed_and_sealed_dormant_publication_simulator"]
        upstream = self.upstream["upstream_entries"]
        self.assertEqual(len(simulator), 4)
        self.assertEqual(len(upstream), 48)
        entries = simulator + upstream
        self.assertEqual(len(entries), 52)
        self.assertEqual(len({item["path"] for item in entries}), 52)
        self.assertEqual(len({item["name"] for item in entries}), 52)
        for item in entries:
            _assert_binding(self, item, ROOT / item["path"])
        transitive = self.contract["transitive_upstream_binding"]
        self.assertEqual(transitive["expected_unique_entries"], 48)
        self.assertEqual(transitive["combined_unique_identity_count"], 52)
        self.assertTrue(transitive["all_entries_rehashed_by_administrative_test"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_fifty_two_bound_identities_remain_byte_identical"])
        for item in self.contract["reviewed_and_sealed_dormant_publication_simulator"] + self.upstream["upstream_entries"]:
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)

    def test_future_implementation_destination_and_write_remain_absent(self) -> None:
        future = self.contract["future_real_publication_implementation"]
        self.assertIsNone(future["implementation_path"])
        self.assertIsNone(future["destination_path"])
        self.assertIsNone(future["artifact_path"])
        for field in (
            "implementation_exists", "implementation_authorized", "destination_exists",
            "artifact_exists", "write_authorized",
        ):
            self.assertIs(future[field], False, field)
        self.assertTrue(future["separate_implementation_commit_review_identity_binding_and_external_seal_required"])

    def test_only_contract_creation_is_authorized(self) -> None:
        allowed_state = {"real_publication_contract_exists"}
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, field in allowed_state, field)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["contract_and_external_seal_creation_authorized"])
        self.assertTrue(all(value is False for key, value in authorization.items() if key != "contract_and_external_seal_creation_authorized"))

    def test_seal_keeps_every_operational_state_false(self) -> None:
        semantics = self.seal["seal_semantics"]
        permitted_true = {
            "contract_only", "dependency_graph_acyclic",
            "all_four_dormant_simulator_artifacts_bound_exactly",
            "all_forty_eight_transitive_upstream_entries_rehashed",
            "all_fifty_two_bound_identities_remain_byte_identical",
            "real_publication_contract_exists",
        }
        for field, value in semantics.items():
            if field in {"self_hash_present", "historical_back_reference_present"}:
                self.assertIs(value, False, field)
            else:
                self.assertIs(value, field in permitted_true, field)

    def test_all_seven_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
