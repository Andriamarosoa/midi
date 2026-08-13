from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_future_bridge_dormant.py"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_dormant_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_dormant_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_dormant_identity_binding_external_seal.json"
COMPATIBILITY_BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding.json"
COMPATIBILITY_BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeDormantIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module_seal_raw = MODULE_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.compatibility_binding = json.loads(COMPATIBILITY_BINDING.read_bytes())
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
        reviewed = self.binding["reviewed_bridge_module"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, MODULE.read_bytes())
        self.assertEqual(reviewed["reviewed_parent_commit"], "19aec74d2e08f49830b1f9dc66e2ad2ec767f760")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, self.module_seal["implementation"], MODULE)
        _assert_binding(self, reviewed, MODULE)
        _assert_binding(self, self.binding["bridge_module_external_review_seal"], MODULE_SEAL)

    def test_compatibility_chain_and_twenty_predecessors_are_rebound_exactly(self) -> None:
        _assert_binding(self, self.binding["compatibility_identity_binding"], COMPATIBILITY_BINDING)
        _assert_binding(self, self.binding["compatibility_identity_binding_external_seal"], COMPATIBILITY_BINDING_SEAL)
        bound = self.binding["byte_identical_predecessor_chains"]
        expected = self.compatibility_binding["byte_identical_predecessor_chains"]
        self.assertEqual(len(bound), 20)
        self.assertEqual(bound, expected)
        for predecessor in bound.values():
            _assert_binding(self, predecessor, ROOT / predecessor["path"])

    def test_binding_seal_binds_exact_binding_module_and_compatibility_chain(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["reviewed_bridge_module"], MODULE)
        _assert_binding(self, self.binding_seal["bridge_module_external_review_seal"], MODULE_SEAL)
        _assert_binding(self, self.binding_seal["compatibility_identity_binding"], COMPATIBILITY_BINDING)
        _assert_binding(self, self.binding_seal["compatibility_identity_binding_external_seal"], COMPATIBILITY_BINDING_SEAL)

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        names = {MODULE_SEAL.name, BINDING.name, BINDING_SEAL.name}
        for predecessor in self.binding["byte_identical_predecessor_chains"].values():
            raw = (ROOT / predecessor["path"]).read_bytes()
            for name in names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_overlay_is_administrative_and_bridge_remains_disconnected(self) -> None:
        overlay = self.binding["normative_overlay"]
        self.assertTrue(overlay["bridge_module_exists"])
        self.assertTrue(overlay["bridge_module_externally_reviewed"])
        self.assertTrue(overlay["bridge_module_externally_sealed"])
        for field in (
            "bridge_operational",
            "composition_to_bridge_connected",
            "bridge_to_materializer_connected",
            "bridge_execution_path_open",
            "materializer_invocation_authorized",
        ):
            self.assertFalse(overlay[field])
        self.assertTrue(overlay["does_not_modify_module_contract_seal_binding_or_predecessor_bytes"])
        self.assertTrue(overlay["does_not_create_authority_claim_capability_activation_operation_or_science"])

    def test_only_reviewed_bridge_module_administrative_states_are_true(self) -> None:
        allowed = {
            "bridge_module_exists",
            "bridge_module_externally_reviewed",
            "bridge_module_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in (
            "bridge_operational",
            "composition_to_bridge_connected",
            "bridge_to_materializer_connected",
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

    def test_all_four_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            bridge.invoke_h27_future_bridge,
            composition.execute_h27_one_shot_composition,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
