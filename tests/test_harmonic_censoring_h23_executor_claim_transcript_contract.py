from __future__ import annotations

import json
from pathlib import Path
import unittest


class HarmonicCensoringH23ExecutorClaimTranscriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = (
            cls.root
            / "configs/harmonic_censoring_h23_executor_claim_transcript_contract.json"
        )
        cls.raw = cls.path.read_bytes()
        cls.contract = json.loads(cls.raw)

    def test_contract_is_LF_contract_only_and_authorizes_nothing(self) -> None:
        self.assertNotIn(b"\r\n", self.raw)
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(
            self.contract["purpose"],
            "harmonic_censoring_h23_executor_claim_transcript_contract",
        )
        self.assertEqual(
            self.contract["status"], "contract_only_external_review_required"
        )
        scope = self.contract["scope"]
        self.assertTrue(scope["contract_only"])
        for name, value in scope.items():
            if name != "contract_only":
                self.assertFalse(value, name)

    def test_authorization_basis_and_approved_inputs_are_exact(self) -> None:
        basis = self.contract["authorization_basis"]
        self.assertEqual(
            basis["external_reviewed_head"],
            "84179a1d166e5719c0511040357e5b98025a5e4e",
        )
        self.assertEqual(
            basis["authorized_action"],
            "DEFINE_H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_ONLY",
        )
        self.assertFalse(basis["synthetic_population_consumed"])
        inputs = self.contract["approved_inputs"]
        self.assertEqual((inputs["fixture_count"], inputs["test_count"]), (175, 72))
        self.assertEqual(inputs["phase_counts"], {"P0": 27, "P1": 35, "P2": 10})
        self.assertFalse(inputs["administrative_seal_may_authorize_future_scientific_execution"])

    def test_future_implementation_requires_new_review_and_new_seal(self) -> None:
        implementation = self.contract["future_implementation_atomicity"]
        self.assertTrue(
            implementation["claim_and_scientific_executor_must_be_implemented_in_same_commit"]
        )
        self.assertTrue(
            implementation["transcript_writer_and_verifier_must_be_implemented_in_same_commit"]
        )
        self.assertFalse(implementation["current_administrative_activation_and_seal_reusable"])
        self.assertTrue(implementation["new_activation_and_seal_binding_new_source_blobs_required"])
        self.assertTrue(implementation["new_activation_and_seal_require_separate_external_review"])

    def test_future_capability_snapshots_activation_authority_before_claim(self) -> None:
        snapshot = self.contract["future_capability_authority_snapshot"]
        required = set(snapshot["required_immutable_fields"])
        self.assertTrue(
            {
                "authorization_activation_commit",
                "authorization_activation_sha256",
                "authorization_seal_sha256",
                "implementation_commit",
                "capability_source_blob",
                "runner_source_blob",
                "marker_path",
                "transcript_path",
            }.issubset(required)
        )
        self.assertTrue(snapshot["claim_marker_values_must_come_only_from_this_snapshot"])
        self.assertTrue(snapshot["claim_may_not_read_environment_for_authority_after_capability_issuance"])
        self.assertTrue(snapshot["optional_preclaim_file_revalidation_may_only_confirm_equality_to_snapshot"])
        self.assertTrue(snapshot["any_revalidation_difference_must_fail_before_O_EXCL"])

    def test_claim_is_durable_before_waveform_and_never_retryable(self) -> None:
        claim = self.contract["future_claim_contract"]
        self.assertEqual(
            claim["claim_method"], "os_open_O_CREAT_O_EXCL_O_WRONLY_mode_0600"
        )
        for name in (
            "claim_must_precede_first_waveform_allocation_or_synthesis",
            "fsync_marker_file_required",
            "close_marker_file_required",
            "fsync_parent_directory_required",
            "marker_existence_alone_means_consumed_even_if_partial_or_corrupt",
            "failure_after_O_EXCL_keeps_population_consumed",
            "second_process_claim_must_fail",
        ):
            self.assertTrue(claim[name], name)
        self.assertFalse(claim["automatic_retry_allowed"])
        self.assertFalse(claim["manual_same_population_retry_allowed"])
        self.assertEqual(
            claim["marker_fixed_values"]["claim_state"],
            "CLAIMED_BEFORE_FIRST_WAVEFORM",
        )
        self.assertTrue(claim["marker_exact_key_set_required"])
        self.assertFalse(claim["additional_marker_fields_allowed"])
        self.assertEqual(claim["marker_canonicalization"]["separators"], [",", ":"])
        self.assertFalse(claim["marker_canonicalization"]["allow_nan"])

    def test_executor_accepts_only_claimed_capability_and_plan_order(self) -> None:
        executor = self.contract["future_scientific_executor_contract"]
        self.assertEqual(
            executor["only_public_entry_inputs"],
            ["repository_root", "claimed_process_local_capability"],
        )
        for name in (
            "caller_supplied_test_results_allowed",
            "caller_supplied_pass_fail_booleans_allowed",
            "caller_supplied_fixture_or_test_selection_allowed",
            "caller_supplied_threshold_or_tolerance_override_allowed",
        ):
            self.assertFalse(executor[name], name)
        self.assertTrue(executor["test_order_must_be_derived_from_resolved_H23_plan"])
        self.assertTrue(executor["fixture_universe_must_equal_all_175_preregistered_IDs"])
        self.assertTrue(executor["test_universe_must_equal_all_72_preregistered_IDs_in_order"])
        self.assertEqual(executor["phase_order"], ["P0", "P1", "P2"])
        self.assertTrue(
            executor[
                "transcript_writer_session_must_be_private_identity_attested_and_created_only_after_claim"
            ]
        )
        self.assertFalse(executor["public_append_or_test_result_injection_API_allowed"])

    def test_transcript_is_persisted_canonical_hash_chain(self) -> None:
        transcript = self.contract["future_transcript_contract"]
        self.assertEqual(transcript["format"], "canonical_UTF8_LF_JSONL_hash_chain")
        for name in (
            "append_only_after_durable_marker",
            "one_event_per_line",
            "strict_duplicate_key_rejection",
            "event_index_starts_at_zero_and_is_contiguous",
            "each_event_contains_previous_event_sha256",
            "each_event_sha256_is_over_exact_canonical_line_bytes",
            "fsync_after_header",
            "fsync_after_each_test_result",
            "fsync_after_terminal_event",
        ):
            self.assertTrue(transcript[name], name)
        self.assertFalse(transcript["NaN_or_Infinity_allowed"])
        self.assertEqual(transcript["canonicalization"]["separators"], [",", ":"])
        self.assertTrue(transcript["canonicalization"]["each_hashed_record_includes_trailing_LF"])
        self.assertEqual(transcript["first_event_previous_event_sha256"], "0" * 64)
        self.assertEqual(
            transcript["previous_event_sha256_definition"],
            "SHA256_of_exact_canonical_bytes_of_immediately_preceding_line_including_trailing_LF",
        )
        self.assertEqual(
            transcript["common_event_exact_fields"],
            ["schema_version", "event_index", "event_type", "previous_event_sha256"],
        )
        self.assertEqual(
            transcript["event_type_exact_values"],
            ["HEADER", "FIXTURE_MATERIALIZED", "TEST_RESULT", "TERMINAL"],
        )
        self.assertFalse(transcript["additional_event_fields_allowed"])
        schemas = transcript["event_schemas"]
        self.assertEqual(set(schemas), set(transcript["event_type_exact_values"]))
        for event_type, schema in schemas.items():
            with self.subTest(event_type=event_type):
                self.assertEqual(schema["fixed_values"]["event_type"], event_type)
                self.assertEqual(schema["fixed_values"]["schema_version"], 1)
                self.assertEqual(len(schema["exact_fields"]), len(set(schema["exact_fields"])))
                self.assertTrue(set(transcript["common_event_exact_fields"]).issubset(schema["exact_fields"]))
        self.assertIn("marker_sha256", schemas["HEADER"]["exact_fields"])
        self.assertIn("waveform_sha256", schemas["FIXTURE_MATERIALIZED"]["exact_fields"])
        self.assertIn("evidence", schemas["TEST_RESULT"]["exact_fields"])
        self.assertIn("evidence_sha256", schemas["TEST_RESULT"]["exact_fields"])
        self.assertIn("resolved_test_contract_sha256", schemas["TEST_RESULT"]["exact_fields"])
        self.assertTrue(transcript["evidence_must_be_inline_canonical_and_match_evidence_sha256"])
        self.assertTrue(
            transcript[
                "evidence_schema_must_equal_preregistered_oracle_evidence_schema_for_test_id"
            ]
        )

    def test_finalizer_reopens_persisted_marker_and_transcript_only(self) -> None:
        finalizer = self.contract["future_authoritative_finalization"]
        self.assertEqual(
            finalizer["finalizer_inputs"],
            ["repository_root", "claimed_process_local_capability"],
        )
        self.assertFalse(finalizer["in_memory_H23AdministrativeTestResult_input_allowed"])
        self.assertFalse(finalizer["caller_supplied_transcript_path_allowed"])
        for name in (
            "must_reopen_marker_from_sealed_path",
            "must_reopen_transcript_from_sealed_path",
            "must_hash_exact_persisted_marker_bytes",
            "must_validate_complete_transcript_hash_chain",
            "must_recompute_all_bindings_counts_IDs_order_and_kill_rule",
            "must_recompute_each_pass_fail_from_persisted_evidence_and_preregistered_oracle",
        ):
            self.assertTrue(finalizer[name], name)
        success = finalizer["success_contract"]
        self.assertEqual((success["executed_tests_exactly"], success["passed_tests_exactly"]), (72, 72))
        self.assertTrue(success["materialized_fixture_ID_set_exactly_all_175"])
        self.assertEqual(success["global_go_status"], "AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL")
        self.assertFalse(success["training_authorized"])

    def test_kill_and_operational_outcomes_are_distinct(self) -> None:
        finalizer = self.contract["future_authoritative_finalization"]
        kill = finalizer["scientific_kill_contract"]
        self.assertTrue(kill["executed_tests_must_be_exact_prefix_ending_at_first_failure"])
        self.assertTrue(kill["remaining_tests_must_equal_exact_NOT_RUN_BY_KILL_RULE_suffix"])
        operational = finalizer["operational_failure_contract"]
        self.assertEqual(operational["status"], "H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED")
        self.assertIsNone(operational["scientific_verdict"])
        self.assertTrue(operational["marker_remains_authoritative_if_terminal_cannot_be_published"])

    def test_review_sequence_and_future_adversarial_tests_are_complete(self) -> None:
        sequence = self.contract["future_review_and_execution_sequence"]
        self.assertEqual(
            sequence["order"][:6],
            [
                "contract_only_commit",
                "external_review_of_contract",
                "single_claim_executor_transcript_implementation_commit",
                "external_review_of_implementation",
                "new_activation_and_seal_commit_binding_new_source_blobs",
                "external_review_of_new_activation_and_seal",
            ],
        )
        self.assertFalse(sequence["negative_inconclusive_or_crashed_population_retry_allowed"])
        tests = set(self.contract["required_future_tests_before_new_seal"])
        self.assertEqual(len(tests), 22)
        for required in (
            "claim_uses_O_EXCL_and_second_process_loses",
            "caller_fabricated_72_PASS_objects_cannot_finalize",
            "success_requires_72_PASS_and_all_175_fixture_IDs",
            "old_31b116_activation_and_seal_cannot_authorize_new_executor_blobs",
            "real_data_model_H17_and_locked_test_paths_fail_before_claim",
        ):
            self.assertIn(required, tests)

    def test_contract_definition_changes_no_scientific_or_execution_source(self) -> None:
        allowed = set(self.contract["contract_definition_allowed_files"])
        forbidden = set(self.contract["contract_definition_forbidden_files"])
        self.assertEqual(len(allowed), 5)
        self.assertFalse(any(path.startswith("src/") for path in allowed))
        self.assertIn("src/polyphonic/run_harmonic_censoring_h23_synthetic.py", forbidden)
        self.assertIn(
            "configs/harmonic_censoring_h23_synthetic_execution_authorization_seal.json",
            forbidden,
        )
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/harmonic_censoring_h23_executor_claim_transcript_contract.json text eol=lf",
            attributes.splitlines(),
        )


if __name__ == "__main__":
    unittest.main()
