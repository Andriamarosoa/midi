from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
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
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _check(test: unittest.TestCase, item: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(item["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(item["git_blob_sha1"], _blob(raw))
    test.assertEqual(item["size_bytes"], len(raw))
    test.assertEqual(item["raw_sha256"], hashlib.sha256(raw).hexdigest())


def _sixty_transitive(contract: dict[str, object]) -> list[dict[str, object]]:
    dormant_roots = contract["reviewed_and_sealed_dormant_boundary"]
    dormant_binding = json.loads((ROOT / contract["transitive_identity_source"]["path"]).read_bytes())
    administrative_roots = dormant_binding["upstream_roots"]
    earlier = json.loads((ROOT / administrative_roots[0]["path"]).read_bytes())
    fifty_four = [
        earlier["reviewed_contract"],
        earlier["contract_external_seal"],
        *earlier["reviewed_and_sealed_dormant_publication_simulator"],
    ]
    oldest = json.loads((ROOT / earlier["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
    return [*dormant_roots, *administrative_roots, *fifty_four, *oldest]


class H27DestinationContractIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = BINDING_SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.contract = json.loads(CONTRACT.read_bytes())

    def test_canonical_without_self_hash_and_exact_pass_contract(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        reviewed = self.binding["reviewed_contract"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, CONTRACT.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "85fc9d33f58a20575727be76fa6bc3678f145956")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _check(self, reviewed, CONTRACT)
        _check(self, self.binding["contract_external_seal"], CONTRACT_SEAL)

    def test_sixty_two_bound_identities_are_unique_and_exact(self) -> None:
        entries = [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *_sixty_transitive(self.contract)]
        self.assertEqual(len(entries), 62)
        self.assertEqual(len({item["path"] for item in entries}), 62)
        for item in entries:
            _check(self, item, ROOT / item["path"])
        self.assertEqual(self.binding["bound_identity_counts"]["combined_unique_identity_count"], 62)

    def test_seal_graph_destination_states_and_eight_edges(self) -> None:
        _check(self, self.seal["identity_binding"], BINDING)
        self.assertEqual(self.seal["reviewed_contract"], self.binding["reviewed_contract"])
        self.assertEqual(self.seal["contract_external_seal"], self.binding["contract_external_seal"])
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertTrue(graph["all_sixty_two_bound_identities_rehashed"])
        destination = self.binding["canonical_destination"]
        self.assertEqual(destination["destination_path"], "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json")
        for key, value in destination.items():
            if key != "destination_path":
                self.assertIs(value, False, key)
        allowed = {
            "destination_contract_exists",
            "destination_contract_externally_reviewed",
            "destination_contract_externally_sealed",
            "destination_contract_identity_binding_exists",
        }
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        self.assertEqual(self.binding["public_edges_closed"], 8)
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
