from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract_external_seal.json"
BRIDGE_BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_dormant_identity_binding.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeOperationalActivationConnectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.bridge_binding = json.loads(BRIDGE_BINDING.read_bytes())

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

    def test_external_seal_binds_exact_contract_and_reviewed_bridge_chain(self) -> None:
        _assert_binding(self, self.seal["contract"], CONTRACT)
        mapping = {
            "reviewed_bridge_module": "bridge_module",
            "bridge_module_external_review_seal": "bridge_module_external_review_seal",
            "bridge_identity_binding": "bridge_identity_binding",
            "bridge_identity_binding_external_seal": "bridge_identity_binding_external_seal",
        }
        for seal_key, contract_key in mapping.items():
            self.assertEqual(self.seal[seal_key], self.contract["reviewed_bridge_chain"][contract_key])
            _assert_binding(self, self.seal[seal_key], ROOT / self.seal[seal_key]["path"])

    def test_external_seal_binds_exact_compatibility_chain(self) -> None:
        mapping = {
            "compatibility_contract": "contract",
            "compatibility_contract_external_seal": "contract_external_seal",
            "compatibility_identity_binding": "identity_binding",
            "compatibility_identity_binding_external_seal": "identity_binding_external_seal",
        }
        for seal_key, contract_key in mapping.items():
            self.assertEqual(self.seal[seal_key], self.contract["compatibility_chain"][contract_key])
            _assert_binding(self, self.seal[seal_key], ROOT / self.seal[seal_key]["path"])

    def test_twenty_predecessors_are_exact_and_byte_identical(self) -> None:
        predecessors = self.contract["sealed_predecessors"]
        self.assertEqual(len(predecessors), 20)
        self.assertEqual(predecessors, self.bridge_binding["byte_identical_predecessor_chains"])
        for binding in predecessors.values():
            _assert_binding(self, binding, ROOT / binding["path"])

    def test_both_future_connections_remain_disconnected_and_unauthorized(self) -> None:
        connections = self.contract["future_connections"]
        composition_bridge = connections["composition_to_bridge"]
        bridge_materializer = connections["bridge_to_materializer"]
        self.assertFalse(composition_bridge["connected"])
        self.assertFalse(composition_bridge["connection_authorized"])
        self.assertTrue(composition_bridge["requires_exact_successful_step11_binding_identity"])
        self.assertTrue(composition_bridge["requires_terminal_step11_consumption"])
        self.assertFalse(bridge_materializer["connected"])
        self.assertFalse(bridge_materializer["connection_authorized"])
        self.assertTrue(bridge_materializer["requires_terminal_bridge_one_shot_right"])
        self.assertTrue(bridge_materializer["requires_exact_materializer_blob_and_closed_barrier"])

    def test_future_fail_closed_preconditions_are_complete_and_true(self) -> None:
        expected = {
            "exact_git_head_and_clean_worktree",
            "exact_composition_boundary_bridge_and_materializer_code_identities",
            "exact_contract_seal_and_binding_bytes",
            "exact_step11_binding_object_identity",
            "step11_capability_terminally_consumed",
            "authority_and_claim_sha256_match_binding",
            "claim_current_durable_and_not_rewritten",
            "invocation_nonce_matches_authority_claim_and_binding",
            "process_id_matches_binding",
            "code_identity_sha256_matches_binding",
            "bridge_binding_owned_one_shot_terminal_state",
            "exact_materializer_blob_and_native_closed_barrier",
            "second_invocation_and_retry_forbidden",
            "direct_helper_bridge_or_materializer_call_forbidden",
            "all_checks_before_any_connection_or_scientific_access",
        }
        self.assertEqual(set(self.contract["future_fail_closed_preconditions"]), expected)
        self.assertTrue(all(self.contract["future_fail_closed_preconditions"].values()))

    def test_activation_is_distinct_absent_and_requires_separate_review(self) -> None:
        activation = self.contract["future_activation_artifact"]
        self.assertFalse(activation["exists"])
        self.assertFalse(activation["implementation_authorized"])
        for field in ("path", "reviewed_commit", "git_blob_sha1", "raw_sha256", "external_seal_path", "external_seal_sha256"):
            self.assertIsNone(activation[field])
        self.assertTrue(activation["must_be_distinct"])
        self.assertTrue(activation["must_be_separately_implemented_reviewed_and_sealed"])

    def test_graph_is_acyclic_and_all_operational_states_remain_false(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        allowed = {"activation_connection_contract_exists"}
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, field in allowed, field)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["contract_and_external_seal_creation_authorized"])
        self.assertTrue(all(value is False for key, value in authorization.items() if key != "contract_and_external_seal_creation_authorized"))
        for field in (
            "composition_to_bridge_connected",
            "bridge_to_materializer_connected",
            "activation_exists",
            "activation_authorized",
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
