from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeCompatibilityIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.contract_seal_raw = CONTRACT_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_new_binding_and_seal_are_canonical_without_self_hash(self) -> None:
        for raw in (self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_binding_binds_exact_pass_contract_bytes_from_git(self) -> None:
        reviewed = self.binding["reviewed_bridge_compatibility_contract"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, self.contract_raw)
        self.assertEqual(reviewed["reviewed_parent_commit"], "9828ddf2ef89dd6cddb88a482c88c0f1ef6abdd6")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["bridge_compatibility_contract_external_seal"], CONTRACT_SEAL)

    def test_all_twenty_predecessors_are_rebound_byte_identically(self) -> None:
        bound = self.binding["byte_identical_predecessor_chains"]
        original = self.contract["sealed_predecessors"]
        self.assertEqual(len(bound), 20)
        self.assertEqual(bound, original)
        for binding in bound.values():
            _assert_binding(self, binding, ROOT / binding["path"])

    def test_binding_seal_binds_exact_binding_contract_seal_and_chains(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["reviewed_bridge_compatibility_contract"], CONTRACT)
        _assert_binding(self, self.binding_seal["bridge_compatibility_contract_external_seal"], CONTRACT_SEAL)
        predecessors = self.binding["byte_identical_predecessor_chains"]
        for key in (
            "composition_module_identity_binding",
            "boundary_identity_binding",
            "materializer_identity_binding",
            "activation_contract",
            "authority_contract",
        ):
            self.assertEqual(self.binding_seal[key], predecessors[key])
            _assert_binding(self, self.binding_seal[key], ROOT / self.binding_seal[key]["path"])

    def test_dependency_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        names = {BINDING.name, BINDING_SEAL.name}
        for predecessor in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / predecessor["path"]).read_bytes()
            for name in names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_overlay_changes_only_contract_review_state(self) -> None:
        overlay = self.binding["normative_overlay"]
        self.assertTrue(overlay["bridge_contract_exists"])
        self.assertTrue(overlay["bridge_contract_externally_reviewed"])
        self.assertTrue(overlay["bridge_contract_externally_sealed"])
        self.assertFalse(overlay["bridge_exists"])
        self.assertFalse(overlay["bridge_implementation_authorized"])
        self.assertFalse(overlay["bridge_execution_path_open"])
        self.assertFalse(overlay["materializer_invocation_authorized"])
        self.assertTrue(overlay["does_not_modify_contract_seal_or_predecessor_bytes"])
        self.assertTrue(overlay["does_not_create_authority_claim_capability_activation_bridge_or_science"])

    def test_only_contract_review_administrative_states_are_true(self) -> None:
        allowed = {
            "bridge_contract_exists",
            "bridge_contract_externally_reviewed",
            "bridge_contract_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in (
            "bridge_exists",
            "bridge_implementation_authorized",
            "bridge_execution_path_open",
            "issuer_exists",
            "authority_exists",
            "claim_exists",
            "operational_capability_exists",
            "activation_exists",
            "materializer_invocation_authorized",
            "scientific_execution_authorized",
            "population_exists",
            "population_index_exists",
            "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(semantics[field], False, field)

    def test_all_public_operational_edges_remain_native_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
