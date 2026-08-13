from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeOperationalActivationConnectionIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = BINDING_SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
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

    def test_binding_references_exact_pass_contract_bytes_and_commit(self) -> None:
        reviewed = self.binding["reviewed_operational_activation_connection_contract"]
        self.assertEqual(reviewed["reviewed_commit"], "4327484ec20e4331277112ec7b4606f0cba923b5")
        self.assertEqual(reviewed["reviewed_parent_commit"], "afae63f00c71e5629f5aae9767e83e854ec3dfc1")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, self.contract_raw)
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["operational_activation_connection_contract_external_seal"], CONTRACT_SEAL)

    def test_binding_seal_binds_exact_binding_contract_and_contract_seal(self) -> None:
        _assert_binding(self, self.seal["identity_binding"], BINDING)
        self.assertEqual(
            self.seal["reviewed_operational_activation_connection_contract"],
            self.binding["reviewed_operational_activation_connection_contract"],
        )
        self.assertEqual(
            self.seal["operational_activation_connection_contract_external_seal"],
            self.binding["operational_activation_connection_contract_external_seal"],
        )
        _assert_binding(self, self.seal["reviewed_operational_activation_connection_contract"], CONTRACT)
        _assert_binding(self, self.seal["operational_activation_connection_contract_external_seal"], CONTRACT_SEAL)

    def test_exact_bridge_and_compatibility_chains_are_rebound(self) -> None:
        self.assertEqual(self.binding["reviewed_bridge_chain"], self.contract["reviewed_bridge_chain"])
        self.assertEqual(self.binding["compatibility_chain"], self.contract["compatibility_chain"])
        seal_mapping = {
            "reviewed_bridge_module": self.contract["reviewed_bridge_chain"]["bridge_module"],
            "bridge_module_external_review_seal": self.contract["reviewed_bridge_chain"]["bridge_module_external_review_seal"],
            "bridge_identity_binding": self.contract["reviewed_bridge_chain"]["bridge_identity_binding"],
            "bridge_identity_binding_external_seal": self.contract["reviewed_bridge_chain"]["bridge_identity_binding_external_seal"],
            "compatibility_contract": self.contract["compatibility_chain"]["contract"],
            "compatibility_contract_external_seal": self.contract["compatibility_chain"]["contract_external_seal"],
            "compatibility_identity_binding": self.contract["compatibility_chain"]["identity_binding"],
            "compatibility_identity_binding_external_seal": self.contract["compatibility_chain"]["identity_binding_external_seal"],
        }
        for key, expected in seal_mapping.items():
            self.assertEqual(self.seal[key], expected)
            _assert_binding(self, self.seal[key], ROOT / self.seal[key]["path"])

    def test_twenty_predecessors_remain_exact_and_byte_identical(self) -> None:
        predecessors = self.binding["byte_identical_predecessor_chains"]
        self.assertEqual(predecessors, self.contract["sealed_predecessors"])
        self.assertEqual(len(predecessors), 20)
        for predecessor in predecessors.values():
            _assert_binding(self, predecessor, ROOT / predecessor["path"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        new_names = {BINDING.name, BINDING_SEAL.name}
        for predecessor in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / predecessor["path"]).read_bytes()
            for name in new_names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_only_administrative_contract_review_states_are_true(self) -> None:
        allowed = {
            "activation_connection_contract_exists",
            "activation_connection_contract_externally_reviewed",
            "activation_connection_contract_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        for field in (
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
            self.assertIs(self.seal["seal_semantics"][field], False, field)

    def test_all_four_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
