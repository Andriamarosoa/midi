from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_identity_binding_external_seal.json"

def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())

class H27ActivationArtifactPublicationIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = BINDING_SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_artifacts_are_canonical_without_self_hash(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.seal)

    def test_reviewed_contract_and_seal_are_exact(self) -> None:
        reviewed = self.binding["reviewed_publication_contract"]
        raw = subprocess.run(["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"], cwd=ROOT, check=True, capture_output=True).stdout
        self.assertEqual(raw, CONTRACT.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "ab19acf97bd919dd17d9a8daf98925e0937c22f0")
        self.assertEqual(reviewed["reviewed_parent_commit"], "309b93153ee4df7a17ae13a85b70532c0a426a69")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["publication_contract_external_seal"], CONTRACT_SEAL)

    def test_four_module_artifacts_and_forty_dependencies_are_exact(self) -> None:
        for key in (
            "reviewed_dormant_activation_artifact_module",
            "dormant_activation_artifact_module_external_review_seal",
            "dormant_activation_artifact_module_identity_binding",
            "dormant_activation_artifact_module_identity_binding_external_seal",
        ):
            _assert_binding(self, self.binding[key], ROOT / self.binding[key]["path"])
        count = 0
        for key in ("reviewed_activation_artifact_contract", "activation_artifact_contract_external_seal", "activation_artifact_identity_binding", "activation_artifact_identity_binding_external_seal"):
            _assert_binding(self, self.binding[key], ROOT / self.binding[key]["path"]); count += 1
        for chain_name in ("reviewed_dormant_gate_chain", "activation_connection_chain", "reviewed_bridge_chain", "compatibility_chain"):
            for item in self.binding[chain_name].values():
                _assert_binding(self, item, ROOT / item["path"]); count += 1
        for item in self.binding["byte_identical_predecessor_chains"].values():
            _assert_binding(self, item, ROOT / item["path"]); count += 1
        self.assertEqual(count, 40)

    def test_binding_seal_binds_exact_binding_contract_and_module(self) -> None:
        _assert_binding(self, self.seal["identity_binding"], BINDING)
        for key in ("reviewed_publication_contract", "publication_contract_external_seal", "reviewed_dormant_activation_artifact_module"):
            self.assertEqual(self.seal[key], self.binding[key])
            _assert_binding(self, self.seal[key], ROOT / self.seal[key]["path"])

    def test_graph_is_acyclic_and_predecessors_have_no_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        for item in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode(), raw)
            self.assertNotIn(BINDING_SEAL.name.encode(), raw)

    def test_publication_and_science_remain_false(self) -> None:
        for field in ("publication_implementation_exists", "publication_implementation_authorized", "activation_artifact_exists", "activation_artifact_write_authorized", "composition_to_bridge_connected", "bridge_to_materializer_connected", "execution_path_open", "materializer_invocation_authorized", "scientific_execution_authorized", "authority_exists", "claim_exists", "operational_capability_exists", "population_exists", "population_index_exists", "locked_test_used", "training_or_calibration_authorized"):
            self.assertIs(self.seal["seal_semantics"][field], False, field)

    def test_all_six_public_edges_remain_closed(self) -> None:
        for edge in (composition.execute_h27_one_shot_composition, bridge.invoke_h27_future_bridge, gate.activate_and_connect_h27_future_bridge, artifact.construct_h27_future_bridge_activation_artifact, boundary.issue_h27_materialization_authority_and_capability, materializer.materialize_h27_activation_capable_production_population):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")

if __name__ == "__main__":
    unittest.main()
