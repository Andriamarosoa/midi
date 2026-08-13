from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / "src/polyphonic/harmonic_censoring_h27_one_shot_execution_composition_dormant.py"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_dormant_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_dormant_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_dormant_identity_binding_external_seal.json"
PREDECESSORS = {
    "composition_contract": ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json",
    "composition_contract_external_seal": ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json",
    "composition_contract_identity_binding": ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding.json",
    "composition_contract_identity_binding_external_seal": ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding_external_seal.json",
    "issuer_boundary_identity_binding": ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json",
    "issuer_boundary_identity_binding_external_seal": ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json",
    "materializer_identity_binding": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json",
    "materializer_identity_binding_external_seal": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json",
    "historical_activation_contract": ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json",
    "historical_activation_contract_external_seal": ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json",
    "historical_authority_contract": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json",
    "historical_authority_contract_external_seal": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json",
}


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27OneShotCompositionDormantIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module_seal_raw = MODULE_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.module_seal = json.loads(cls.module_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_new_artifacts_are_canonical_and_have_no_self_hash(self) -> None:
        for raw in (self.module_seal_raw, self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("seal_sha256", self.module_seal)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_module_seal_binds_exact_pass_commit_bytes(self) -> None:
        implementation = self.module_seal["implementation"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{self.module_seal['reviewed_commit']}:{implementation['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, IMPLEMENTATION.read_bytes())
        _assert_binding(self, implementation, IMPLEMENTATION)
        self.assertEqual(self.module_seal["reviewed_parent_commit"], "b17e827bba31330000069baf89f99f36923b246e")
        self.assertEqual(self.module_seal["external_review_verdict"], "PASS")

    def test_module_seal_and_binding_rebind_exact_predecessors(self) -> None:
        for key in (
            "composition_contract",
            "composition_contract_external_seal",
            "composition_contract_identity_binding",
            "composition_contract_identity_binding_external_seal",
            "issuer_boundary_identity_binding",
            "materializer_identity_binding",
        ):
            _assert_binding(self, self.module_seal[key if key != "composition_contract" else "reviewed_composition_contract"], PREDECESSORS[key])
        for key, path in PREDECESSORS.items():
            _assert_binding(self, self.binding[key], path)
            self.assertTrue(self.binding[key]["remains_byte_identical"])

    def test_binding_binds_exact_module_and_external_seal(self) -> None:
        _assert_binding(self, self.binding["reviewed_composition_module"], IMPLEMENTATION)
        _assert_binding(self, self.binding["composition_module_external_review_seal"], MODULE_SEAL)
        self.assertEqual(self.binding["reviewed_composition_module"]["reviewed_commit"], "b2e6a06ebe236eb9f192d85497753ee878617ec6")

    def test_binding_seal_binds_binding_module_and_seal(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["reviewed_composition_module"], IMPLEMENTATION)
        _assert_binding(self, self.binding_seal["composition_module_external_review_seal"], MODULE_SEAL)
        _assert_binding(self, self.binding_seal["composition_contract"], PREDECESSORS["composition_contract"])
        _assert_binding(self, self.binding_seal["composition_contract_identity_binding"], PREDECESSORS["composition_contract_identity_binding"])
        _assert_binding(self, self.binding_seal["issuer_boundary_identity_binding"], PREDECESSORS["issuer_boundary_identity_binding"])
        _assert_binding(self, self.binding_seal["materializer_identity_binding"], PREDECESSORS["materializer_identity_binding"])

    def test_dependency_graph_is_acyclic_and_has_no_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        seal_semantics = self.binding_seal["seal_semantics"]
        self.assertTrue(seal_semantics["dependency_graph_acyclic"])
        self.assertFalse(seal_semantics["self_hash_present"])
        self.assertFalse(seal_semantics["historical_back_reference_present"])

    def test_public_edge_remains_exact_native_empty_tuple_barrier(self) -> None:
        edge = composition.execute_h27_one_shot_composition
        self.assertIs(type(edge), type(().__getitem__))
        self.assertEqual(edge.__self__, ())
        self.assertEqual(edge.__name__, "__getitem__")

    def test_only_reviewed_administrative_states_are_true(self) -> None:
        allowed = {
            "reviewed_composition_module_exists",
            "reviewed_composition_module_externally_reviewed",
            "reviewed_composition_module_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in (
            "reviewed_composition_module_operational",
            "issuer_exists",
            "authority_exists",
            "claim_exists",
            "operational_capability_exists",
            "activation_exists",
            "bridge_exists",
            "materializer_invocation_authorized",
            "scientific_execution_authorized",
            "population_exists",
            "population_index_exists",
            "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(semantics[field], False, field)


if __name__ == "__main__":
    unittest.main()
