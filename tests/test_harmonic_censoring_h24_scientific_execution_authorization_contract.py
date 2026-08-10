from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json"
)


class H24ScientificExecutionAuthorizationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT_PATH.read_bytes()
        cls.contract = json.loads(cls.raw)

    def test_contract_is_lf_contract_only_and_authorizes_no_science(self) -> None:
        self.assertNotIn(b"\r", self.raw)
        self.assertEqual(self.contract["schema_version"], 4)
        self.assertEqual(
            self.contract["purpose"],
            "harmonic_censoring_h24_scientific_execution_authorization_contract",
        )
        self.assertEqual(
            self.contract["authorization_basis"][
                "path_topology_correction_authorized_action"
            ],
            "AUTHORIZED_TO_CORRECT_H24_DORMANT_SCIENTIFIC_PATH_TOPOLOGY_GUARDS_ONLY",
        )
        self.assertEqual(
            self.contract["status"],
            "dormant_scientific_capability_and_runner_implemented_external_review_required",
        )
        scope = self.contract["scope"]
        self.assertFalse(scope["contract_only"])
        for name in (
            "dormant_implementation_only",
            "scientific_capability_implementation_authorized",
            "scientific_runner_implementation_authorized",
            "evidence_transcript_and_finalizer_implementation_authorized",
        ):
            self.assertTrue(scope[name], name)
        for name in (
            "scientific_capability_issuance_authorized",
            "scientific_claim_authorized",
            "evaluator_or_oracle_execution_authorized",
            "P0_execution_authorized",
            "P1_execution_authorized",
            "P2_execution_authorized",
            "population_modification_or_retry_authorized",
            "real_data_access_authorized",
            "H17_population_use_authorized",
            "model_or_checkpoint_access_authorized",
            "training_or_calibration_authorized",
            "locked_test_used",
        ):
            self.assertFalse(scope[name], name)

    def test_population_publication_is_bound_exactly_and_remains_immutable(self) -> None:
        population = self.contract["published_population_binding"]
        self.assertEqual(population["population_id"], "H24_SYNTHETIC_V1")
        self.assertTrue(population["population_consumed"])
        self.assertTrue(population["population_materialized"])
        self.assertEqual(
            population["activation_commit"],
            "e7c2eecf49ede43b3334266c74b1fe438f9e793d",
        )
        self.assertEqual(
            population["reviewed_materializer_commit"],
            "c51d8eaf7dbb8370456d92f9a76ec3f336d98016",
        )
        self.assertEqual(
            population["materializer_source_blob"],
            "1f76391592ab0f4725147504bcb059f0c3d89e50",
        )
        self.assertEqual(
            population["claim_marker"]["raw_sha256"],
            "3185adfdba7615900062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d",
        )
        self.assertEqual(
            population["terminal"]["raw_sha256"],
            "50ec58c81d1a0ae533599676536d141c7f98ac337686c1baf66517bc3e39c54eb",
        )
        self.assertEqual(
            population["receipt"]["raw_sha256"],
            "8a8128dc97c61f4203a89e116787f9eae319e7c146fbcd06b4432c4108f92cd5",
        )
        self.assertEqual(
            population["index"]["raw_sha256"],
            "b45b63c477a3db13d161779bb28067c0b2b6fa5c4cc80c985199e9347e1eff15",
        )
        self.assertEqual(
            population["index"]["ordered_fixture_ids_sha256"],
            "d4b23a898d8775f772e91933ace7c90c2e7b5a808e32bf9955088287bbe9670f",
        )
        self.assertEqual(
            (
                population["fixture_count"],
                population["fixture_file_count"],
                population["published_file_count"],
                population["waveform_file_count"],
                population["waveform_byte_count_each"],
            ),
            (175, 525, 527, 175, 100352),
        )
        self.assertIsNone(population["first_failed_fixture_id"])
        self.assertEqual(population["scientific_tests_executed"], 0)
        self.assertFalse(population["locked_test_used"])
        self.assertTrue(population["population_bytes_are_immutable"])
        self.assertFalse(population["repair_regeneration_or_materialization_retry_allowed"])

    def test_all_sealed_config_bytes_match_the_contract(self) -> None:
        sealed = self.contract["sealed_scientific_inputs"]
        for name in (
            "successor_contract",
            "population_manifest",
            "test_manifest",
            "manifest_binding",
            "dormant_harness_contract",
            "materialization_contract",
        ):
            item = sealed[name]
            digest = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, item["raw_sha256"], name)
        population = self.contract["published_population_binding"]
        self.assertEqual(
            population["materialization_activation_contract_raw_sha256"],
            hashlib.sha256(
                (
                    ROOT
                    / "configs/harmonic_censoring_h24_population_materialization_activation_contract.json"
                ).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            population["authorization_seal_raw_sha256"],
            hashlib.sha256(
                (
                    ROOT
                    / "configs/harmonic_censoring_h24_population_materialization_authorization_seal.json"
                ).read_bytes()
            ).hexdigest(),
        )

    def test_source_blobs_match_the_reviewed_harness_and_materializer(self) -> None:
        sealed = self.contract["sealed_scientific_inputs"]
        for name in ("approved_harness_source", "approved_operator_source"):
            item = sealed[name]
            blob = subprocess.check_output(
                ["git", "rev-parse", f"{item['commit']}:{item['path']}"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
            ).strip()
            self.assertEqual(blob, item["git_blob"], name)
        population = self.contract["published_population_binding"]
        blob = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"{population['reviewed_materializer_commit']}:src/polyphonic/harmonic_censoring_h24_population_materializer.py",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).strip()
        self.assertEqual(blob, population["materializer_source_blob"])

    def test_fixture_and_test_universes_are_exactly_the_sealed_manifests(self) -> None:
        sealed = self.contract["sealed_scientific_inputs"]
        population = json.loads((ROOT / sealed["population_manifest"]["path"]).read_bytes())
        tests = json.loads((ROOT / sealed["test_manifest"]["path"]).read_bytes())
        self.assertEqual(len(population["fixture_ids"]), 175)
        self.assertEqual(len(population["fixture_ids"]), len(set(population["fixture_ids"])))
        phase_counts = {name: len(values) for name, values in tests["phase_test_ids"].items()}
        self.assertEqual(phase_counts, sealed["phase_counts"])
        self.assertEqual(sum(phase_counts.values()), sealed["test_count"])
        all_tests = [item for phase in ("P0", "P1", "P2") for item in tests["phase_test_ids"][phase]]
        self.assertEqual(len(all_tests), len(set(all_tests)))
        self.assertFalse(
            sealed["fixture_or_test_addition_omission_duplicate_or_reordering_allowed"]
        )

    def test_future_capability_is_separate_nonconstructible_and_fail_closed(self) -> None:
        capability = self.contract["future_scientific_capability"]
        self.assertTrue(capability["implementation_exists_now"])
        self.assertTrue(capability["factory_exists_now"])
        self.assertFalse(capability["constructor_publicly_callable"])
        self.assertFalse(capability["factory_must_be_separately_implemented_and_reviewed"])
        self.assertTrue(capability["identity_only_process_local_attestation_required"])
        self.assertTrue(capability["copy_pickle_replace_or_manual_construction_must_fail"])
        self.assertFalse(capability["serialization_allowed"])
        self.assertFalse(capability["cross_process_reuse_allowed"])
        self.assertTrue(capability["single_use"])
        required = set(capability["preissue_fail_closed_requirements"])
        self.assertIn("all_525_fixture_file_hashes_and_175_waveform_sizes_match_without_decoding", required)
        self.assertIn("H17_real_data_locked_test_model_checkpoint_and_training_inputs_absent", required)
        self.assertIn(
            "scientific_claim_staging_success_and_terminal_neither_descend_from_nor_are_ancestors_of_the_immutable_population_control_namespace",
            required,
        )
        self.assertIn(
            "one_shot_paths_have_only_the_three_explicitly_authorized_ancestor_descendant_relations",
            required,
        )
        self.assertTrue(
            (ROOT / capability["implemented_source_path"]).is_file()
        )
        self.assertTrue(
            (ROOT / capability["implemented_runner_path"]).is_file()
        )
        self.assertTrue(
            capability[
                "public_issuer_fails_before_population_access_without_reviewed_activation"
            ]
        )
        self.assertTrue(
            capability[
                "runner_fails_before_scientific_claim_while_evidence_producer_registry_is_dormant"
            ]
        )

    def test_future_seal_activation_and_all_scientific_rights_are_absent(self) -> None:
        seal = self.contract["future_scientific_authorization_seal"]
        self.assertTrue(seal["required_as_separate_reviewed_file"])
        self.assertFalse(seal["exists_now"])
        self.assertIsNone(seal["raw_sha256"])
        self.assertIsNone(seal["reviewed_scientific_implementation_commit"])
        for name in (
            "capability_issuance_authorized",
            "scientific_claim_authorized",
            "scientific_execution_authorized",
            "P0_execution_authorized",
            "P1_execution_authorized",
            "P2_execution_authorized",
        ):
            self.assertFalse(seal[name], name)
        activation = self.contract["future_scientific_activation"]
        self.assertFalse(activation["exists_now"])
        self.assertEqual(
            activation["OS_environment_variable"],
            "H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT",
        )
        self.assertTrue(activation["checkout_HEAD_must_equal_OS_bound_commit"])
        self.assertFalse(activation["unreviewed_HEAD_may_be_inferred_as_authority"])

    def test_scientific_claim_is_distinct_irreversible_and_precedes_waveform_decode(self) -> None:
        boundary = self.contract["future_scientific_one_shot_boundary"]
        self.assertTrue(boundary["population_consumption_marker_is_not_the_scientific_execution_claim"])
        self.assertTrue(boundary["separate_scientific_claim_required"])
        self.assertEqual(
            boundary["claim_method"],
            "atomic_create_exclusive_before_first_waveform_decode_or_evaluator",
        )
        self.assertTrue(boundary["scientific_execution_consumed_after_successful_claim"])
        self.assertFalse(boundary["automatic_retry_allowed"])
        self.assertFalse(boundary["manual_retry_allowed"])
        self.assertTrue(boundary["failure_after_claim_remains_consumed"])
        self.assertFalse(boundary["partial_output_authoritative"])
        self.assertFalse(
            boundary["population_control_namespace_may_contain_scientific_outputs"]
        )
        self.assertEqual(
            boundary["authorized_ancestor_descendant_relations"],
            [
                "success_directory->scientific_transcript.jsonl",
                "success_directory->evidence_directory",
                "staging_directory->scientific_transcript.jsonl.part",
            ],
        )
        self.assertFalse(
            boundary[
                "all_other_ancestor_descendant_relations_between_one_shot_paths_allowed"
            ]
        )
        self.assertFalse(boundary["claim_parent_creation_may_create_staging_or_success"])

    def test_transcript_is_a_closed_ordered_hash_chain_over_persisted_evidence(self) -> None:
        transcript = self.contract["future_scientific_transcript_contract"]
        self.assertTrue(transcript["normative"])
        self.assertTrue(transcript["implementation_exists_now"])
        self.assertEqual(transcript["finalized_transcript_format"], "CANONICAL_JSONL_UTF8_LF")
        serialization = transcript["canonical_line_serialization"]
        self.assertEqual(serialization["encoding"], "UTF-8")
        self.assertFalse(serialization["BOM_allowed"])
        self.assertEqual(serialization["line_terminator"], "LF")
        self.assertTrue(serialization["one_JSON_object_per_line"])
        self.assertEqual(serialization["object_keys"], "lexicographic_order")
        self.assertFalse(serialization["allow_NaN_or_infinity"])
        self.assertFalse(serialization["duplicate_object_keys_allowed"])
        self.assertEqual(transcript["record_count"], 72)
        tests = json.loads(
            (ROOT / self.contract["sealed_scientific_inputs"]["test_manifest"]["path"]).read_bytes()
        )
        ordered_test_ids = json.dumps(
            tests["test_ids"],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(ordered_test_ids).hexdigest(),
            transcript["ordered_test_ids_canonical_json_sha256"],
        )
        self.assertEqual(
            transcript["ordered_test_ids_canonical_json_sha256"],
            self.contract["sealed_scientific_inputs"][
                "ordered_test_ids_canonical_json_sha256"
            ],
        )
        self.assertEqual(
            set(transcript["record_states"]),
            {
                "EVIDENCE_PERSISTED",
                "NOT_RUN_BY_KILL_RULE",
                "OPERATIONAL_ERROR",
                "NOT_RUN_BY_OPERATIONAL_FAILURE",
            },
        )
        evidence = transcript["record_states"]["EVIDENCE_PERSISTED"]
        self.assertFalse(evidence["producer_PASS_or_FAIL_field_allowed"])
        chain = transcript["hash_chain"]
        self.assertEqual(chain["first_previous_record_sha256"], "0" * 64)
        self.assertTrue(chain["next_previous_record_sha256_must_equal_prior_record_sha256"])
        self.assertTrue(chain["terminal_must_bind_final_record_sha256"])
        self.assertTrue(chain["terminal_must_bind_raw_transcript_sha256"])
        self.assertTrue(chain["suppression_insertion_duplication_or_reordering_must_fail"])
        binding = transcript["evidence_binding"]
        self.assertEqual(
            binding["evidence_path_rule"],
            "evidence/{sequence_index_zero_padded_2}_{test_id}.json",
        )
        self.assertTrue(
            binding["exactly_one_unique_evidence_file_per_EVIDENCE_PERSISTED_record"]
        )
        self.assertFalse(binding["extra_unbound_evidence_files_allowed"])
        self.assertTrue(binding["raw_operands_required"])
        self.assertTrue(binding["producer_verdict_field_forbidden"])
        self.assertTrue(binding["rehash_each_evidence_file_from_disk_before_finalization"])
        self.assertTrue(
            binding["missing_extra_nonfinite_or_hash_mismatched_evidence_fails_closed"]
        )

    def test_terminal_is_recomputed_from_persisted_transcript_and_closes_failures(self) -> None:
        terminal = self.contract["future_terminal_contract"]
        required_keys = {
            "transcript_raw_sha256",
            "transcript_byte_count",
            "transcript_record_count",
            "final_record_sha256",
            "ordered_evidence_bindings_sha256",
            "ordered_test_ids_sha256",
            "scientific_execution_claim_sha256",
            "population_marker_sha256",
            "population_terminal_sha256",
            "population_receipt_sha256",
            "population_index_sha256",
            "scientific_status",
            "first_failed_test_id",
        }
        self.assertTrue(required_keys.issubset(set(terminal["terminal_exact_keys"])))
        self.assertTrue(
            terminal[
                "terminal_must_bind_raw_transcript_sha256_byte_count_record_count_and_final_record_sha256"
            ]
        )
        self.assertTrue(terminal["terminal_must_bind_ordered_evidence_bindings_sha256"])
        self.assertTrue(terminal["finalizer_is_a_separate_pure_recomputation_from_persisted_bytes"])
        self.assertTrue(terminal["finalizer_must_reopen_transcript_and_all_bound_evidence_from_disk"])
        self.assertTrue(terminal["finalizer_must_not_accept_in_memory_producer_outcomes"])
        self.assertTrue(terminal["finalizer_recomputes_each_PASS_or_FAIL_with_the_independent_oracle"])
        self.assertTrue(terminal["finalizer_recomputes_first_failure_and_all_counts"])
        self.assertEqual(
            terminal["scientific_status_derivation"],
            {
                "all_72_independent_oracles_PASS": "AUTHORIZED_TO_PREPARE_H24_TRAIN_PROTOCOL",
                "first_independent_FAIL_in_P0": "H24_SYNTHETIC_HYPOTHESIS_KILLED",
                "first_independent_FAIL_in_P1_or_P2": "H24_PRETRAIN_READINESS_NOT_DEMONSTRATED",
                "any_ordinary_operational_error": "H24_EXECUTION_INCONCLUSIVE_CONSUMED",
            },
        )
        self.assertTrue(
            terminal["AUTHORIZED_TO_PREPARE_H24_TRAIN_PROTOCOL_is_not_training_authority"]
        )
        self.assertEqual(
            terminal["transcript_validation_status_values"],
            ["VALIDATED", "FINALIZER_ERROR"],
        )
        self.assertIn("NOT_RUN_BY_KILL_RULE", terminal["scientific_failure_suffix_rule"])
        self.assertIn("OPERATIONAL_ERROR", terminal["operational_failure_suffix_rule"])
        self.assertIn(
            "H24_EXECUTION_INCONCLUSIVE_CONSUMED",
            terminal["ordinary_post_claim_error_before_or_during_a_test"],
        )
        self.assertIn("terminal_absent", terminal["brutal_crash_timeout_SIGKILL_or_power_loss"])
        self.assertIn("no_retry", terminal["brutal_crash_timeout_SIGKILL_or_power_loss"])

    def test_future_phase_order_and_terminal_are_closed_without_authorizing_execution(self) -> None:
        execution = self.contract["future_execution_order"]
        self.assertEqual(
            execution["steps"][3:7],
            [
                "decode_exact_175_published_waveforms",
                "P0_exact_27_tests",
                "P1_exact_35_tests_if_all_P0_pass",
                "P2_exact_10_tests_if_all_P1_pass",
            ],
        )
        self.assertTrue(execution["P1_requires_all_P0_pass"])
        self.assertTrue(execution["P2_requires_all_P1_pass"])
        self.assertTrue(execution["stop_on_first_failed_test"])
        self.assertFalse(execution["execute_unlisted_test_allowed"])
        self.assertFalse(execution["skip_or_dynamic_selection_allowed"])
        self.assertFalse(execution["producer_verdict_is_authoritative"])
        self.assertTrue(execution["independent_oracle_recomputation_required"])
        terminal = self.contract["future_terminal_contract"]
        self.assertTrue(terminal["success_requires_all_72_tests_in_exact_order"])
        self.assertEqual(
            terminal["operational_failure_status"],
            "H24_EXECUTION_INCONCLUSIVE_CONSUMED",
        )
        self.assertTrue(terminal["operational_failure_is_not_scientific_verdict"])
        self.assertFalse(terminal["result_may_authorize_training"])
        self.assertFalse(terminal["result_may_access_real_data_or_locked_test"])

    def test_contract_topology_and_current_dormancy_are_exact(self) -> None:
        expected = [
            "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json",
            "readme/README.md",
            "readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md",
            "src/polyphonic/harmonic_censoring_h24_scientific_capability.py",
            "tests/test_harmonic_censoring_h24_scientific_execution_authorization_contract.py",
        ]
        self.assertEqual(self.contract["contract_definition_exact_changed_files"], expected)
        dormancy = self.contract["current_dormancy"]
        self.assertFalse(dormancy["this_contract_grants_scientific_authority"])
        self.assertTrue(dormancy["scientific_capability_or_runner_implemented_now"])
        self.assertFalse(dormancy["evidence_producer_registry_implemented_now"])
        self.assertFalse(dormancy["scientific_seal_or_activation_exists_now"])
        self.assertFalse(dormancy["scientific_claim_or_terminal_created_now"])
        self.assertFalse(dormancy["waveforms_decoded_now"])
        self.assertFalse(dormancy["P0_P1_P2_executed_now"])
        self.assertEqual(dormancy["scientific_tests_executed_now"], 0)
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for path in expected:
            if path.endswith((".json", ".py", ".md")) and path != "readme/README.md":
                self.assertIn(f"{path} text eol=lf", attributes)


if __name__ == "__main__":
    unittest.main()
