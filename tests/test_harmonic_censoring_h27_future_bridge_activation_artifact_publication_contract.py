from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27FutureBridgeActivationArtifactPublicationContractTests(unittest.TestCase):
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

    def test_external_seal_binds_contract_and_four_dormant_module_artifacts(self) -> None:
        _assert_binding(self, self.seal["contract"], CONTRACT)
        for key in (
            "reviewed_dormant_activation_artifact_module",
            "dormant_activation_artifact_module_external_review_seal",
            "dormant_activation_artifact_module_identity_binding",
            "dormant_activation_artifact_module_identity_binding_external_seal",
        ):
            self.assertEqual(self.seal[key], self.contract[key])
            _assert_binding(self, self.seal[key], ROOT / self.seal[key]["path"])

    def test_all_forty_existing_dependencies_are_rebound_exactly(self) -> None:
        count = 0
        for key in (
            "reviewed_activation_artifact_contract",
            "activation_artifact_contract_external_seal",
            "activation_artifact_identity_binding",
            "activation_artifact_identity_binding_external_seal",
        ):
            item = self.contract[key]
            _assert_binding(self, item, ROOT / item["path"])
            count += 1
        for chain_name in (
            "reviewed_dormant_gate_chain", "activation_connection_chain",
            "reviewed_bridge_chain", "compatibility_chain",
        ):
            chain = self.contract[chain_name]
            self.assertEqual(len(chain), 4)
            for item in chain.values():
                _assert_binding(self, item, ROOT / item["path"])
                count += 1
        predecessors = self.contract["byte_identical_predecessor_chains"]
        self.assertEqual(len(predecessors), 20)
        for item in predecessors.values():
            _assert_binding(self, item, ROOT / item["path"])
            count += 1
        self.assertEqual(count, 40)

    def test_future_publication_schema_is_closed_absent_and_unauthorized(self) -> None:
        publication = self.contract["future_publication"]
        self.assertEqual(len(publication["required_fields_in_order"]), 14)
        self.assertEqual(publication["required_fields_in_order"][0], "schema_version")
        self.assertEqual(publication["required_fields_in_order"][-1], "terminal")
        self.assertIsNone(publication["destination_path"])
        self.assertIsNone(publication["artifact_sha256"])
        self.assertFalse(publication["artifact_exists"])
        self.assertFalse(publication["write_authorized"])
        self.assertFalse(publication["publication_implementation_exists"])
        self.assertFalse(publication["publication_implementation_authorized"])
        self.assertTrue(publication["separate_implementation_commit_review_and_seal_required"])

    def test_all_fail_closed_publication_preconditions_are_exact_and_true(self) -> None:
        expected = {
            "exact_git_head_and_clean_worktree",
            "exact_dormant_module_seal_binding_and_binding_seal_bytes",
            "exact_four_activation_artifact_and_thirty_six_dependency_bytes",
            "all_six_public_edges_native_and_closed",
            "exact_in_memory_payload_schema_and_order",
            "created_at_utc_parseable_rfc3339_utc",
            "activation_id_unique_nonempty_and_explicitly_attested",
            "exact_terminal_step11_binding_identity",
            "authority_and_claim_current_durable_and_byte_exact",
            "invocation_nonce_process_id_and_code_identity_match",
            "exact_materializer_blob_and_native_closed_barrier",
            "both_future_connections_closed_and_unauthorized",
            "destination_absent_before_publication",
            "one_shot_right_consumed_immediately_before_first_write",
            "create_exclusive_without_overwrite_required",
            "canonical_bytes_fully_written_flushed_and_fsynced",
            "atomic_same_filesystem_visibility_without_replace",
            "published_bytes_reopened_and_rehashed",
            "parent_directory_fsync_after_visibility",
            "partial_or_failed_publication_terminal_without_retry",
            "every_check_before_any_artifact_write_or_scientific_access",
        }
        self.assertEqual(set(self.contract["mandatory_fail_closed_preconditions"]), expected)
        self.assertTrue(all(self.contract["mandatory_fail_closed_preconditions"].values()))

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.contract["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_predecessors_remain_byte_identical"])
        for item in self.contract["byte_identical_predecessor_chains"].values():
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(CONTRACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)

    def test_only_contract_and_reviewed_dormant_chain_states_are_true(self) -> None:
        allowed = {
            "activation_artifact_contract_exists",
            "activation_artifact_contract_externally_reviewed",
            "activation_artifact_contract_externally_sealed",
            "dormant_activation_artifact_module_exists",
            "dormant_activation_artifact_module_externally_reviewed",
            "dormant_activation_artifact_module_externally_sealed",
            "activation_artifact_publication_contract_exists",
        }
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, field in allowed, field)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["contract_and_external_seal_creation_authorized"])
        self.assertTrue(all(value is False for key, value in authorization.items() if key != "contract_and_external_seal_creation_authorized"))

    def test_seal_keeps_all_operational_states_false(self) -> None:
        semantics = self.seal["seal_semantics"]
        for field in (
            "activation_artifact_publication_contract_externally_reviewed",
            "activation_artifact_publication_contract_externally_sealed",
            "publication_implementation_exists", "publication_implementation_authorized",
            "activation_artifact_exists", "activation_artifact_write_authorized",
            "composition_to_bridge_connected", "bridge_to_materializer_connected",
            "execution_path_open", "materializer_invocation_authorized",
            "scientific_execution_authorized", "authority_exists", "claim_exists",
            "operational_capability_exists", "population_exists", "population_index_exists",
            "locked_test_used", "training_or_calibration_authorized",
        ):
            self.assertIs(semantics[field], False, field)

    def test_all_six_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
