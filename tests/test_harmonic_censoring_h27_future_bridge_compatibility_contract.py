from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_compatibility_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeCompatibilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

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

    def test_every_predecessor_identity_is_recomputed_from_exact_bytes(self) -> None:
        predecessors = self.contract["sealed_predecessors"]
        self.assertEqual(len(predecessors), 20)
        for binding in predecessors.values():
            _assert_binding(self, binding, ROOT / binding["path"])

    def test_external_seal_binds_exact_contract_and_key_chains(self) -> None:
        _assert_binding(self, self.seal["contract"], CONTRACT)
        predecessors = self.contract["sealed_predecessors"]
        for key in (
            "composition_module_identity_binding",
            "composition_module_identity_binding_external_seal",
            "boundary_identity_binding",
            "materializer_identity_binding",
            "composition_contract_identity_binding",
            "activation_contract",
            "authority_contract",
        ):
            self.assertEqual(self.seal[key], predecessors[key])
            _assert_binding(self, self.seal[key], ROOT / self.seal[key]["path"])

    def test_step_11_handoff_is_exact_binding_only_and_pre_science(self) -> None:
        handoff = self.contract["step_11_consumption_output"]
        expected = [
            "authority_sha256",
            "claim_sha256",
            "materializer_blob",
            "invocation_nonce",
            "process_id",
            "code_identity_sha256",
        ]
        self.assertEqual(handoff["required_binding_fields_in_order"], expected)
        self.assertEqual(handoff["successful_return"], "the exact same binding object by identity")
        self.assertEqual(handoff["capability_state_after_return"], "terminally consumed and unusable")
        self.assertFalse(handoff["science_may_begin_before_return"])
        self.assertFalse(handoff["science_may_use_the_consumed_capability_object"])

    def test_future_bridge_input_and_materializer_handoff_are_closed_and_exact(self) -> None:
        bridge_input = self.contract["future_bridge_input_contract"]
        handoff = self.contract["future_materializer_handoff_contract"]
        self.assertTrue(bridge_input["accepts_only_successful_step_11_return"])
        self.assertFalse(bridge_input["accepts_capability_object"])
        self.assertFalse(bridge_input["accepts_caller_constructed_mapping_or_tuple"])
        self.assertTrue(bridge_input["requires_exact_binding_object_identity"])
        self.assertEqual(bridge_input["requires_materializer_blob"], self.contract["sealed_predecessors"]["materializer_module"]["git_blob_sha1"])
        self.assertEqual(handoff["target_module_blob"], bridge_input["requires_materializer_blob"])
        self.assertEqual(handoff["expected_binding_fields_in_order"], self.contract["step_11_consumption_output"]["required_binding_fields_in_order"])
        self.assertTrue(handoff["binding_forwarded_without_field_rewrite"])
        self.assertTrue(handoff["direct_materializer_or_helper_call_forbidden"])
        self.assertTrue(handoff["bridge_may_invoke_materializer_at_most_once"])

    def test_all_required_rejections_are_fail_closed(self) -> None:
        required = {
            "wrong_capability_or_binding",
            "caller_constructed_or_equal_but_nonidentical_binding",
            "stale_missing_replaced_or_rewritten_claim",
            "wrong_authority_sha256",
            "wrong_claim_sha256",
            "wrong_materializer_blob",
            "wrong_invocation_nonce",
            "wrong_process_id",
            "wrong_code_identity_sha256",
            "post_consume_code_or_file_drift",
            "second_bridge_or_materializer_invocation",
            "direct_bridge_helper_or_materializer_call",
            "retry_after_any_consumption_success_failure_interrupt_or_timeout",
        }
        self.assertEqual(set(self.contract["mandatory_rejections"]), required)
        self.assertTrue(all(self.contract["mandatory_rejections"].values()))

    def test_dependency_graph_is_acyclic_and_predecessors_have_no_back_reference(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        new_names = {CONTRACT.name, SEAL.name}
        for binding in self.contract["sealed_predecessors"].values():
            raw = (ROOT / binding["path"]).read_bytes()
            for name in new_names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_all_operational_and_scientific_states_remain_false(self) -> None:
        bridge = self.contract["future_bridge"]
        self.assertTrue(all(value is False for key, value in bridge.items() if key.endswith("authorized") or key in {"exists", "execution_path_open"}))
        allowed = {"bridge_contract_exists"}
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.seal["seal_semantics"]
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
