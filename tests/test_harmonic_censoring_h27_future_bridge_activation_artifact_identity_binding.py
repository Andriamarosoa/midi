from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeActivationArtifactIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = BINDING_SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_binding_and_seal_are_canonical_without_self_hash(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.seal)

    def test_binding_references_exact_pass_contract_commit_and_seal(self) -> None:
        reviewed = self.binding["reviewed_activation_artifact_contract"]
        self.assertEqual(reviewed["reviewed_commit"], "b22e7e5f8f8c2d1032c719ed19ec5e956613ed8d")
        self.assertEqual(reviewed["reviewed_parent_commit"], "da5acf7026e89afec4155880d8e0cf7b1bf73f21")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        self.assertEqual(raw, CONTRACT.read_bytes())
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["activation_artifact_contract_external_seal"], CONTRACT_SEAL)

    def test_binding_seal_binds_exact_binding_contract_and_contract_seal(self) -> None:
        _assert_binding(self, self.seal["identity_binding"], BINDING)
        self.assertEqual(self.seal["reviewed_activation_artifact_contract"], self.binding["reviewed_activation_artifact_contract"])
        self.assertEqual(self.seal["activation_artifact_contract_external_seal"], self.binding["activation_artifact_contract_external_seal"])
        _assert_binding(self, self.seal["reviewed_activation_artifact_contract"], CONTRACT)
        _assert_binding(self, self.seal["activation_artifact_contract_external_seal"], CONTRACT_SEAL)

    def test_all_thirty_six_dependencies_are_rebound_exactly(self) -> None:
        count = 0
        for chain_name in (
            "reviewed_dormant_gate_chain", "activation_connection_chain",
            "reviewed_bridge_chain", "compatibility_chain",
        ):
            chain = self.binding[chain_name]
            self.assertEqual(len(chain), 4)
            for item in chain.values():
                _assert_binding(self, item, ROOT / item["path"])
                count += 1
        predecessors = self.binding["byte_identical_predecessor_chains"]
        self.assertEqual(len(predecessors), 20)
        for item in predecessors.values():
            _assert_binding(self, item, ROOT / item["path"])
            count += 1
        self.assertEqual(count, 36)

    def test_binding_seal_key_dependencies_match_binding(self) -> None:
        expected = {
            "gate_module": self.binding["reviewed_dormant_gate_chain"]["gate_module"],
            "gate_identity_binding": self.binding["reviewed_dormant_gate_chain"]["gate_identity_binding"],
            "activation_connection_identity_binding": self.binding["activation_connection_chain"]["identity_binding"],
            "bridge_identity_binding": self.binding["reviewed_bridge_chain"]["bridge_identity_binding"],
            "compatibility_identity_binding": self.binding["compatibility_chain"]["identity_binding"],
        }
        for key, item in expected.items():
            self.assertEqual(self.seal[key], item)
            _assert_binding(self, item, ROOT / item["path"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        for item in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(BINDING_SEAL.name.encode("ascii"), raw)

    def test_only_contract_review_states_are_true(self) -> None:
        allowed = {
            "activation_artifact_contract_exists",
            "activation_artifact_contract_externally_reviewed",
            "activation_artifact_contract_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        for field, value in self.seal["seal_semantics"].items():
            if field in {"administrative_identity_binding_only", "dependency_graph_acyclic", "all_thirty_six_dependencies_remain_byte_identical"} or field in allowed:
                self.assertTrue(value, field)
            elif field not in {"self_hash_present", "historical_back_reference_present"}:
                self.assertFalse(value, field)

    def test_all_five_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
