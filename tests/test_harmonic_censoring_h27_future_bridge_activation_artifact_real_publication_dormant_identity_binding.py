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
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant_identity_binding_external_seal.json"
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant.py"

def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def _check(test: unittest.TestCase, item: dict, path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(item["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual((item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"]),
                     (_blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))

class H27DormantRealPublicationBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw, cls.seal_raw = BINDING.read_bytes(), SEAL.read_bytes()
        cls.binding, cls.seal = json.loads(cls.binding_raw), json.loads(cls.seal_raw)

    def test_canonical_and_exact_pass_module(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw); self.assertTrue(raw.endswith(b"\n"))
        reviewed = self.binding["reviewed_dormant_implementation"]
        old = subprocess.run(["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"], cwd=ROOT, check=True, capture_output=True).stdout
        self.assertEqual(old, MODULE.read_bytes()); _check(self, reviewed, MODULE)
        _check(self, self.binding["dormant_implementation_external_review_seal"], ROOT / self.binding["dormant_implementation_external_review_seal"]["path"])

    def test_fifty_six_upstream_identities_are_unique_and_exact(self) -> None:
        roots = self.binding["upstream_roots"]
        source = json.loads((ROOT / roots[0]["path"]).read_bytes())
        inherited = [source["reviewed_contract"], source["contract_external_seal"], *source["reviewed_and_sealed_dormant_publication_simulator"]]
        older = json.loads((ROOT / source["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
        entries = [*roots, *inherited, *older]
        self.assertEqual(len(entries), 56); self.assertEqual(len({x["path"] for x in entries}), 56)
        for item in entries: _check(self, item, ROOT / item["path"])

    def test_binding_seal_graph_states_and_eight_edges(self) -> None:
        _check(self, self.seal["identity_binding"], BINDING)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"]); self.assertFalse(graph["self_hash_present"]); self.assertFalse(graph["historical_back_reference_present"])
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in {"dormant_real_publication_module_exists", "dormant_real_publication_module_externally_reviewed", "dormant_real_publication_module_externally_sealed"}, key)
        for edge in (composition.execute_h27_one_shot_composition, bridge.invoke_h27_future_bridge, gate.activate_and_connect_h27_future_bridge, artifact.construct_h27_future_bridge_activation_artifact, publication.simulate_h27_future_bridge_activation_artifact_publication, real_publication.publish_h27_future_bridge_activation_artifact_real, boundary.issue_h27_materialization_authority_and_capability, materializer.materialize_h27_activation_capable_production_population):
            self.assertIs(type(edge), type(().__getitem__))

if __name__ == "__main__": unittest.main()
