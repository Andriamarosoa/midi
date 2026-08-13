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
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as authority
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_identity_binding_external_seal.json"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_external_review_seal.json"
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_real_publication_one_shot_authority_issuer.py"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _check(test: unittest.TestCase, item: dict) -> None:
    path = ROOT / item["path"]
    raw = path.read_bytes()
    test.assertEqual(
        (item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"]),
        (_blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )


def _sixty_four(execution_roots: list[dict]) -> list[dict]:
    execution_contract = json.loads((ROOT / execution_roots[0]["path"]).read_bytes())
    destination_roots = execution_contract["reviewed_and_sealed_destination_contract_chain"]
    destination_binding = json.loads((ROOT / destination_roots[2]["path"]).read_bytes())
    destination_contract = json.loads((ROOT / destination_binding["reviewed_contract"]["path"]).read_bytes())
    dormant_roots = destination_contract["reviewed_and_sealed_dormant_boundary"]
    old_binding = json.loads((ROOT / destination_contract["transitive_identity_source"]["path"]).read_bytes())
    activation_roots = old_binding["upstream_roots"]
    execution_binding = json.loads((ROOT / activation_roots[0]["path"]).read_bytes())
    inherited = [
        execution_binding["reviewed_contract"],
        execution_binding["contract_external_seal"],
        *execution_binding["reviewed_and_sealed_dormant_publication_simulator"],
    ]
    older = json.loads((ROOT / execution_binding["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
    return [*destination_roots, *dormant_roots, *activation_roots, *inherited, *older]


class H27EffectFreeIssuerIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.module_seal_raw = MODULE_SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_pass_module_and_three_canonical_administrative_files(self) -> None:
        for raw in (self.module_seal_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        reviewed = self.binding["reviewed_effect_free_implementation"]
        committed = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(committed, MODULE.read_bytes())
        _check(self, reviewed)
        _check(self, self.binding["implementation_external_review_seal"])
        _check(self, self.seal["identity_binding"])

    def test_eighty_predecessors_and_eighty_two_bound_paths_are_unique_and_exact(self) -> None:
        roots = self.binding["upstream_roots"]
        implementation_binding = json.loads((ROOT / roots[0]["path"]).read_bytes())
        implementation_contract = json.loads((ROOT / implementation_binding["reviewed_contract"]["path"]).read_bytes())
        issuance_roots = implementation_contract["reviewed_and_sealed_issuance_artifact_contract_chain"]
        issuance_contract = json.loads((ROOT / issuance_roots[0]["path"]).read_bytes())
        authority_roots = issuance_contract["reviewed_and_sealed_one_shot_authority_chain"]
        authority_contract = json.loads((ROOT / authority_roots[0]["path"]).read_bytes())
        execution_roots = authority_contract["reviewed_and_sealed_execution_authorization_chain"]
        expanded = [
            implementation_binding["reviewed_contract"],
            implementation_binding["contract_external_seal"],
            *issuance_roots,
            *authority_roots,
            *execution_roots,
            *_sixty_four(execution_roots),
        ]
        predecessors = [*roots, *expanded]
        bound = [
            self.binding["reviewed_effect_free_implementation"],
            self.binding["implementation_external_review_seal"],
            *predecessors,
        ]
        self.assertEqual((len(expanded), len(predecessors), len(bound)), (78, 80, 82))
        self.assertEqual(len({item["path"] for item in bound}), 82)
        for item in bound:
            _check(self, item)

    def test_graph_state_and_eight_historical_edges_remain_closed(self) -> None:
        allowed = {
            "effect_free_issuer_module_exists",
            "effect_free_issuer_module_externally_reviewed",
            "effect_free_issuer_module_externally_sealed",
            "effect_free_issuer_identity_binding_exists",
        }
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
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


if __name__ == "__main__":
    unittest.main()
