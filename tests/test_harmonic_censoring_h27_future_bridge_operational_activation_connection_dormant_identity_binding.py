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
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant.py"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeOperationalActivationConnectionDormantIdentityBindingTests(unittest.TestCase):
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
        reviewed = self.binding["reviewed_dormant_gate_module"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, MODULE.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "339e79d6e7f49606c0bfd05b269e7b4cb34faeb3")
        self.assertEqual(reviewed["reviewed_parent_commit"], "e0c51e9f2006aabfcc104f3bf63caa8885aac607")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, self.module_seal["implementation"], MODULE)
        _assert_binding(self, reviewed, MODULE)
        _assert_binding(self, self.binding["dormant_gate_module_external_review_seal"], MODULE_SEAL)

    def test_four_activation_connection_artifacts_are_rebound_exactly(self) -> None:
        chain = self.binding["activation_connection_chain"]
        self.assertEqual(len(chain), 4)
        for item in chain.values():
            _assert_binding(self, item, ROOT / item["path"])

    def test_bridge_compatibility_and_twenty_predecessors_are_exact(self) -> None:
        for chain_name in ("reviewed_bridge_chain", "compatibility_chain"):
            chain = self.binding[chain_name]
            self.assertEqual(len(chain), 4)
            for item in chain.values():
                _assert_binding(self, item, ROOT / item["path"])
        predecessors = self.binding["byte_identical_predecessor_chains"]
        self.assertEqual(len(predecessors), 20)
        for item in predecessors.values():
            _assert_binding(self, item, ROOT / item["path"])

    def test_binding_seal_binds_exact_binding_module_seal_and_key_chains(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        self.assertEqual(self.binding_seal["reviewed_dormant_gate_module"], self.binding["reviewed_dormant_gate_module"])
        self.assertEqual(self.binding_seal["dormant_gate_module_external_review_seal"], self.binding["dormant_gate_module_external_review_seal"])
        _assert_binding(self, self.binding_seal["reviewed_dormant_gate_module"], MODULE)
        _assert_binding(self, self.binding_seal["dormant_gate_module_external_review_seal"], MODULE_SEAL)
        expected = {
            "activation_connection_contract": self.binding["activation_connection_chain"]["contract"],
            "activation_connection_contract_external_seal": self.binding["activation_connection_chain"]["contract_external_seal"],
            "activation_connection_identity_binding": self.binding["activation_connection_chain"]["identity_binding"],
            "activation_connection_identity_binding_external_seal": self.binding["activation_connection_chain"]["identity_binding_external_seal"],
            "bridge_module": self.binding["reviewed_bridge_chain"]["bridge_module"],
            "bridge_identity_binding": self.binding["reviewed_bridge_chain"]["bridge_identity_binding"],
            "compatibility_contract": self.binding["compatibility_chain"]["contract"],
            "compatibility_identity_binding": self.binding["compatibility_chain"]["identity_binding"],
        }
        for key, item in expected.items():
            self.assertEqual(self.binding_seal[key], item)
            _assert_binding(self, self.binding_seal[key], ROOT / item["path"])

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

    def test_only_dormant_gate_administrative_states_are_true(self) -> None:
        allowed = {
            "dormant_gate_module_exists",
            "dormant_gate_module_externally_reviewed",
            "dormant_gate_module_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in (
            "gate_operational",
            "activation_exists",
            "activation_authorized",
            "composition_to_bridge_connected",
            "bridge_to_materializer_connected",
            "execution_path_open",
            "materializer_invocation_authorized",
            "scientific_execution_authorized",
            "authority_exists",
            "claim_exists",
            "operational_capability_exists",
            "population_exists",
            "population_index_exists",
            "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(semantics[field], False, field)

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
