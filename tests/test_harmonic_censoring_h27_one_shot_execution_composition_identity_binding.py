from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding_external_seal.json"
BOUNDARY_BINDING = ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json"
BOUNDARY_BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json"
MATERIALIZER_BINDING = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json"
MATERIALIZER_BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json"
ACTIVATION = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json"
ACTIVATION_SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json"
AUTHORITY = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json"
AUTHORITY_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27OneShotExecutionCompositionIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.contract_seal_raw = CONTRACT_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.contract_seal = json.loads(cls.contract_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_new_artifacts_are_canonical_without_self_hash(self) -> None:
        for raw in (self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)
        self.assertFalse(self.binding["dependency_graph"]["self_hash_present"])
        self.assertFalse(self.binding_seal["seal_semantics"]["self_hash_present"])

    def test_binding_binds_exact_passed_contract_and_external_seal(self) -> None:
        reviewed = self.binding["reviewed_composition_contract"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, self.contract_raw)
        self.assertEqual(reviewed["reviewed_parent_commit"], "8f6b6a3be74dbbaa56a059da981196d8a83d7049")
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["composition_contract_external_seal"], CONTRACT_SEAL)
        self.assertEqual(reviewed["external_review_verdict"], "PASS")

    def test_binding_rebinds_exact_predecessor_chains_without_modification(self) -> None:
        for key, path in (
            ("issuer_boundary_identity_binding", BOUNDARY_BINDING),
            ("issuer_boundary_identity_binding_external_seal", BOUNDARY_BINDING_SEAL),
            ("materializer_identity_binding", MATERIALIZER_BINDING),
            ("materializer_identity_binding_external_seal", MATERIALIZER_BINDING_SEAL),
            ("historical_activation_contract", ACTIVATION),
            ("historical_activation_contract_external_seal", ACTIVATION_SEAL),
            ("historical_authority_contract", AUTHORITY),
            ("historical_authority_contract_external_seal", AUTHORITY_SEAL),
        ):
            _assert_binding(self, self.binding[key], path)
            self.assertTrue(self.binding[key]["remains_byte_identical"])

    def test_overlay_changes_only_administrative_review_state(self) -> None:
        overlay = self.binding["normative_overlay"]
        self.assertTrue(overlay["composition_contract_exists"])
        self.assertTrue(overlay["composition_contract_externally_reviewed"])
        self.assertTrue(overlay["composition_contract_externally_sealed"])
        self.assertFalse(overlay["future_operational_composition_module_exists"])
        self.assertFalse(overlay["future_operational_composition_module_implementation_authorized"])
        self.assertFalse(overlay["future_operational_composition_execution_path_open"])
        self.assertTrue(overlay["does_not_modify_contract_or_seal_bytes"])
        self.assertTrue(overlay["does_not_modify_boundary_or_materializer"])
        self.assertTrue(overlay["does_not_create_issuer_authority_claim_capability_activation_or_bridge"])

    def test_binding_seal_binds_exact_binding_contract_and_chains(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["reviewed_composition_contract"], CONTRACT)
        _assert_binding(self, self.binding_seal["composition_contract_external_seal"], CONTRACT_SEAL)
        _assert_binding(self, self.binding_seal["issuer_boundary_identity_binding"], BOUNDARY_BINDING)
        _assert_binding(self, self.binding_seal["materializer_identity_binding"], MATERIALIZER_BINDING)
        self.assertEqual(self.binding_seal["reviewed_composition_contract"]["reviewed_commit"], "40eb4a3eb4a10fa6218f0a6e4fa6e3cc45b85307")
        self.assertEqual(self.binding_seal["reviewed_composition_contract"]["external_review_verdict"], "PASS")

    def test_dependency_graph_is_acyclic_and_predecessors_are_byte_identical(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["composition_contract_and_seal_remain_byte_identical"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        _assert_binding(self, self.contract_seal["composition_contract"], CONTRACT)

    def test_both_public_operational_edges_remain_closed(self) -> None:
        for edge in (
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")

    def test_only_administrative_exists_reviewed_sealed_states_are_true(self) -> None:
        state = self.binding["current_state"]
        for field, value in state.items():
            if field in {
                "composition_contract_exists",
                "composition_contract_externally_reviewed",
                "composition_contract_externally_sealed",
            }:
                self.assertIs(value, True, field)
            else:
                self.assertIs(value, False, field)
        semantics = self.binding_seal["seal_semantics"]
        for field, value in semantics.items():
            if field in {
                "administrative_identity_binding_only",
                "composition_contract_exists",
                "composition_contract_externally_reviewed",
                "composition_contract_externally_sealed",
                "dependency_graph_acyclic",
                "composition_contract_and_seal_remain_byte_identical",
                "boundary_and_materializer_remain_byte_identical",
            }:
                self.assertIs(value, True, field)
            else:
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
