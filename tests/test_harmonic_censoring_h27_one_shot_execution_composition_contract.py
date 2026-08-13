from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json"
ACTIVATION = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json"

PATHS = {
    "issuer_boundary_identity_binding": ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json",
    "issuer_boundary_identity_binding_external_seal": ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json",
    "issuer_boundary_external_review_seal": ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_boundary_external_review_seal.json",
    "issuer_boundary_module": ROOT / "src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py",
    "materializer_identity_binding": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json",
    "materializer_identity_binding_external_seal": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json",
    "materializer_external_review_seal": ROOT / "configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json",
    "materializer_module": ROOT / "src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py",
    "activation_contract": ACTIVATION,
    "activation_contract_external_seal": ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json",
    "authority_contract": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json",
    "authority_contract_external_seal": ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json",
}


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27OneShotExecutionCompositionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.activation = json.loads(ACTIVATION.read_bytes())

    def test_contract_and_seal_are_canonical_without_self_hash(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("contract_sha256", self.contract)
        self.assertNotIn("seal_sha256", self.seal)
        self.assertFalse(self.contract["dependency_graph"]["self_hash_present"])
        self.assertFalse(self.seal["seal_semantics"]["self_hash_present"])

    def test_every_composed_identity_is_byte_exact(self) -> None:
        issuer = self.contract["issuer_boundary_chain"]
        materializer_chain = self.contract["materializer_chain"]
        historical = self.contract["historical_contract_chain"]
        _assert_binding(self, issuer["identity_binding"], PATHS["issuer_boundary_identity_binding"])
        _assert_binding(self, issuer["identity_binding_external_seal"], PATHS["issuer_boundary_identity_binding_external_seal"])
        _assert_binding(self, issuer["boundary_external_review_seal"], PATHS["issuer_boundary_external_review_seal"])
        _assert_binding(self, issuer["reviewed_boundary"], PATHS["issuer_boundary_module"])
        _assert_binding(self, materializer_chain["identity_binding"], PATHS["materializer_identity_binding"])
        _assert_binding(self, materializer_chain["identity_binding_external_seal"], PATHS["materializer_identity_binding_external_seal"])
        _assert_binding(self, materializer_chain["materializer_external_review_seal"], PATHS["materializer_external_review_seal"])
        _assert_binding(self, materializer_chain["reviewed_materializer"], PATHS["materializer_module"])
        for key in ("activation_contract", "activation_contract_external_seal", "authority_contract", "authority_contract_external_seal"):
            _assert_binding(self, historical[key], PATHS[key])

    def test_runtime_environment_paths_and_counts_are_derived_exactly(self) -> None:
        self.assertEqual(self.contract["runtime_exact"], self.activation["runtime_exact"])
        self.assertEqual(self.contract["process_environment_exact"], self.activation["process_environment_exact"])
        fixed = self.contract["fixed_paths_and_counts"]
        self.assertEqual(fixed["issuer_identity"], self.activation["future_activation"]["issuer_identity"])
        self.assertEqual(fixed["administrative_root"], self.activation["future_activation"]["administrative_root"])
        self.assertEqual(fixed["activation_path"], self.activation["future_activation"]["activation_path"])
        self.assertEqual(fixed["authority_path"], self.activation["future_materialization_authority"]["authority_path"])
        self.assertEqual(fixed["claim_path"], self.activation["future_materialization_authority"]["claim_path"])
        self.assertEqual(fixed["staging_destination"], self.activation["atomic_publication"]["staging_destination"])
        self.assertEqual(fixed["final_destination"], self.activation["atomic_publication"]["final_destination"])
        self.assertEqual(
            (fixed["expected_record_count"], fixed["expected_baseline_record_count"], fixed["expected_p2_record_count"]),
            (124, 17, 107),
        )

    def test_fail_closed_order_is_complete_and_science_is_last(self) -> None:
        order = self.contract["future_fail_closed_order"]
        self.assertEqual(len(order), 12)
        self.assertIn("fixed paths", order[0])
        self.assertIn("composition contract", order[1])
        self.assertIn("Git HEAD", order[4])
        self.assertIn("runtime", order[5])
        self.assertIn("durable claim", order[8])
        self.assertIn("capability", order[9])
        self.assertIn("consume", order[10])
        self.assertIn("only then", order[-1])
        self.assertIn("science", order[-1])

    def test_future_module_is_explicitly_absent_and_unauthorized(self) -> None:
        future = self.contract["future_operational_composition_module"]
        self.assertFalse(future["exists"])
        self.assertFalse(future["implementation_authorized"])
        self.assertFalse(future["execution_path_open"])
        for field in ("path", "reviewed_commit", "git_blob_sha1", "raw_sha256", "external_seal_path", "external_seal_sha256"):
            self.assertIsNone(future[field], field)
        self.assertTrue(future["must_be_a_distinct_module"])
        self.assertTrue(future["must_be_separately_implemented_reviewed_and_sealed"])

    def test_required_future_properties_are_fail_closed(self) -> None:
        required = self.contract["required_future_implementation_properties"]
        for field, value in required.items():
            if field == "authority_and_claim_file_mode_octal":
                self.assertEqual(value, "0600")
            elif field == "retry_allowed":
                self.assertIs(value, False)
            else:
                self.assertIs(value, True, field)

    def test_dependency_graph_is_acyclic_and_historical_files_are_predecessors(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        for path in PATHS.values():
            self.assertTrue(path.is_file())

    def test_external_seal_binds_exact_contract_and_both_identity_chains(self) -> None:
        _assert_binding(self, self.seal["composition_contract"], CONTRACT)
        _assert_binding(self, self.seal["issuer_boundary_identity_binding"], PATHS["issuer_boundary_identity_binding"])
        _assert_binding(self, self.seal["issuer_boundary_identity_binding_external_seal"], PATHS["issuer_boundary_identity_binding_external_seal"])
        _assert_binding(self, self.seal["materializer_identity_binding"], PATHS["materializer_identity_binding"])
        _assert_binding(self, self.seal["materializer_identity_binding_external_seal"], PATHS["materializer_identity_binding_external_seal"])

    def test_operational_edges_and_every_current_authorization_remain_closed(self) -> None:
        self.assertIs(type(boundary.issue_h27_materialization_authority_and_capability), type(().__getitem__))
        self.assertEqual(boundary.issue_h27_materialization_authority_and_capability.__self__, ())
        self.assertIs(type(materializer.materialize_h27_activation_capable_production_population), type(().__getitem__))
        self.assertEqual(materializer.materialize_h27_activation_capable_production_population.__self__, ())
        for section in (self.contract["current_state"], self.contract["authorization"], self.seal["seal_semantics"]):
            for field, value in section.items():
                if field in {
                    "composition_contract_exists",
                    "composition_contract_and_external_seal_creation_authorized",
                    "composition_contract_only",
                    "dependency_graph_acyclic",
                    "boundary_and_materializer_remain_byte_identical",
                }:
                    self.assertIs(value, True, field)
                else:
                    self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
