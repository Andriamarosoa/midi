from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeActivationArtifactContractTests(unittest.TestCase):
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

    def test_external_seal_binds_exact_contract_and_gate_chain(self) -> None:
        _assert_binding(self, self.seal["contract"], CONTRACT)
        mapping = {
            "reviewed_gate_module": "gate_module",
            "gate_module_external_review_seal": "gate_module_external_review_seal",
            "gate_identity_binding": "gate_identity_binding",
            "gate_identity_binding_external_seal": "gate_identity_binding_external_seal",
        }
        for seal_key, contract_key in mapping.items():
            self.assertEqual(self.seal[seal_key], self.contract["reviewed_dormant_gate_chain"][contract_key])
            _assert_binding(self, self.seal[seal_key], ROOT / self.seal[seal_key]["path"])

    def test_all_thirty_two_sealed_dependencies_are_exact(self) -> None:
        count = 0
        for chain_name in ("activation_connection_chain", "reviewed_bridge_chain", "compatibility_chain"):
            chain = self.contract[chain_name]
            self.assertEqual(len(chain), 4)
            for item in chain.values():
                _assert_binding(self, item, ROOT / item["path"])
                count += 1
        predecessors = self.contract["sealed_predecessors"]
        self.assertEqual(len(predecessors), 20)
        for item in predecessors.values():
            _assert_binding(self, item, ROOT / item["path"])
            count += 1
        self.assertEqual(count, 32)

    def test_future_artifact_schema_is_closed_exact_and_absent(self) -> None:
        schema = self.contract["future_activation_artifact_schema"]
        self.assertEqual(
            schema["required_fields_in_order"],
            [
                "schema_version", "activation_id", "population_namespace",
                "gate_module_blob", "gate_identity_binding_sha256",
                "authority_sha256", "claim_sha256", "invocation_nonce",
                "process_id", "code_identity_sha256", "materializer_blob",
                "terminal_step11_binding_sha256", "created_at_utc", "terminal",
            ],
        )
        self.assertEqual(schema["schema_version_exact"], 1)
        self.assertEqual(schema["population_namespace_exact"], "H27_SYNTHETIC_V1")
        self.assertEqual(schema["gate_module_blob_exact"], "d60470373ab261d585ab8f8ad40e3c94b3a03d23")
        self.assertEqual(schema["gate_identity_binding_sha256_exact"], "a44d05b2e447f0f84167575354e7b54c0003651087d4b6660fc11d5540876504")
        self.assertTrue(schema["terminal_exact"])
        self.assertTrue(schema["additional_fields_forbidden"])
        self.assertIsNone(schema["artifact_path"])
        self.assertIsNone(schema["artifact_sha256"])
        self.assertFalse(schema["artifact_exists"])

    def test_all_fail_closed_preconditions_are_exact_and_true(self) -> None:
        expected = {
            "exact_git_head_and_clean_worktree",
            "exact_gate_module_seal_binding_and_binding_seal_bytes",
            "exact_activation_connection_bridge_compatibility_and_predecessor_bytes",
            "all_five_public_edges_native_and_closed",
            "exact_terminal_step11_binding_identity",
            "authority_and_claim_current_durable_and_byte_exact",
            "invocation_nonce_matches_authority_claim_and_binding",
            "process_id_matches_binding",
            "code_identity_sha256_matches_binding",
            "dormant_gate_owned_one_shot_right_unconsumed_before_creation",
            "exact_materializer_blob_and_native_closed_barrier",
            "both_future_connections_closed_and_unauthorized",
            "activation_destination_absent",
            "atomic_create_exclusive_publication_required",
            "second_creation_and_retry_after_consumption_forbidden",
            "every_check_before_any_artifact_write_or_scientific_access",
        }
        self.assertEqual(set(self.contract["mandatory_fail_closed_preconditions"]), expected)
        self.assertTrue(all(self.contract["mandatory_fail_closed_preconditions"].values()))

    def test_future_implementation_is_distinct_absent_and_requires_separate_review(self) -> None:
        lifecycle = self.contract["future_lifecycle"]
        self.assertFalse(lifecycle["implementation_exists"])
        self.assertFalse(lifecycle["implementation_authorized"])
        for field in (
            "implementation_path", "implementation_reviewed_commit",
            "implementation_git_blob_sha1", "implementation_raw_sha256",
            "external_review_seal_path", "external_review_seal_sha256",
        ):
            self.assertIsNone(lifecycle[field])
        self.assertTrue(lifecycle["must_be_distinct_from_contract_and_dormant_gate"])
        self.assertTrue(lifecycle["separate_implementation_review_and_seal_required"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        for item in self.contract["sealed_predecessors"].values():
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)

    def test_only_contract_exists_and_every_operational_state_is_false(self) -> None:
        allowed = {"activation_artifact_contract_exists"}
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, field in allowed, field)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["contract_and_external_seal_creation_authorized"])
        self.assertTrue(all(value is False for key, value in authorization.items() if key != "contract_and_external_seal_creation_authorized"))
        for field in (
            "activation_artifact_exists", "activation_artifact_creation_authorized",
            "activation_implementation_exists", "activation_implementation_authorized",
            "composition_to_bridge_connected", "bridge_to_materializer_connected",
            "execution_path_open", "materializer_invocation_authorized",
            "scientific_execution_authorized", "authority_exists", "claim_exists",
            "operational_capability_exists", "population_exists",
            "population_index_exists", "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(self.seal["seal_semantics"][field], False, field)

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
