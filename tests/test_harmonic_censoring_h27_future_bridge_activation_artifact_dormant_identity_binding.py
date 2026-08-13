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
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_future_bridge_activation_artifact_dormant.py"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_dormant_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_dormant_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_dormant_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeActivationArtifactDormantIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module_seal_raw = MODULE_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.module_seal = json.loads(cls.module_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_new_artifacts_are_canonical_without_self_hash(self) -> None:
        for raw in (self.module_seal_raw, self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("seal_sha256", self.module_seal)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_module_seal_and_binding_use_exact_pass_module_bytes(self) -> None:
        reviewed = self.binding["reviewed_dormant_activation_artifact_module"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, MODULE.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "19af83ea7127e16c1abccc05315e5651f6074241")
        self.assertEqual(reviewed["reviewed_parent_commit"], "d18ed0ffb9a815ec349fb43c844fa25360e02449")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, self.module_seal["implementation"], MODULE)
        _assert_binding(self, reviewed, MODULE)
        _assert_binding(self, self.binding["dormant_activation_artifact_module_external_review_seal"], MODULE_SEAL)

    def test_four_activation_artifact_artifacts_are_rebound_exactly(self) -> None:
        entries = (
            self.binding["reviewed_activation_artifact_contract"],
            self.binding["activation_artifact_contract_external_seal"],
            self.binding["activation_artifact_identity_binding"],
            self.binding["activation_artifact_identity_binding_external_seal"],
        )
        for item in entries:
            _assert_binding(self, item, ROOT / item["path"])

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

    def test_binding_seal_binds_exact_binding_module_and_artifact_chain(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        for key in (
            "reviewed_dormant_activation_artifact_module",
            "dormant_activation_artifact_module_external_review_seal",
            "reviewed_activation_artifact_contract",
            "activation_artifact_contract_external_seal",
            "activation_artifact_identity_binding",
            "activation_artifact_identity_binding_external_seal",
        ):
            self.assertEqual(self.binding_seal[key], self.binding[key])
            _assert_binding(self, self.binding_seal[key], ROOT / self.binding_seal[key]["path"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        new_names = {MODULE_SEAL.name, BINDING.name, BINDING_SEAL.name}
        for item in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / item["path"]).read_bytes()
            for name in new_names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_only_reviewed_module_and_contract_administrative_states_are_true(self) -> None:
        allowed = {
            "activation_artifact_contract_exists",
            "activation_artifact_contract_externally_reviewed",
            "activation_artifact_contract_externally_sealed",
            "dormant_activation_artifact_module_exists",
            "dormant_activation_artifact_module_externally_reviewed",
            "dormant_activation_artifact_module_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in allowed:
            self.assertIs(semantics[field], True, field)
        for field in (
            "activation_implementation_exists", "activation_implementation_authorized", "activation_artifact_exists",
            "activation_artifact_creation_authorized", "composition_to_bridge_connected",
            "bridge_to_materializer_connected", "execution_path_open",
            "materializer_invocation_authorized", "scientific_execution_authorized",
            "authority_exists", "claim_exists", "operational_capability_exists",
            "population_exists", "population_index_exists", "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(semantics[field], False, field)

    def test_all_six_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
