from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


class HarmonicCensoringH23ExecutionCapabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = (
            cls.root
            / "configs/harmonic_censoring_h23_synthetic_execution_capability_contract.json"
        )
        cls.raw = cls.path.read_bytes()
        cls.contract = json.loads(cls.raw)

    def test_contract_is_lf_contract_only_and_authorizes_no_execution(self) -> None:
        self.assertNotIn(b"\r\n", self.raw)
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(
            self.contract["purpose"],
            "harmonic_censoring_h23_synthetic_execution_capability_contract",
        )
        self.assertEqual(
            self.contract["status"], "contract_only_external_review_required"
        )
        scope = self.contract["scope"]
        self.assertTrue(scope["contract_only"])
        for name, value in scope.items():
            if name != "contract_only":
                self.assertFalse(value, name)

    def test_authorization_basis_is_definition_only(self) -> None:
        basis = self.contract["authorization_basis"]
        self.assertEqual(
            basis["pilot_reviewed_head"],
            "2cc826b1b672d10ecd4d4ab23050cc7050cc91d8",
        )
        self.assertEqual(
            basis["authorized_action"],
            "define_future_synthetic_execution_capability_and_validation_conditions",
        )
        forbidden = set(basis["explicitly_not_authorized"])
        self.assertTrue(
            {
                "modify_current_unconditional_execution_guard",
                "implement_capability_factory",
                "issue_capability",
                "synthesize_any_fixture_waveform",
                "execute_any_P0_P1_or_P2_test",
                "reuse_H17",
                "access_locked_test",
            }.issubset(forbidden)
        )

    def test_approved_harness_contract_and_source_blobs_are_exact(self) -> None:
        binding = self.contract["approved_harness_binding"]
        self.assertEqual(
            binding["approved_commit"],
            "e97674cd1d1c3a12ff113f98789105941ab17030",
        )
        contract_raw = (self.root / binding["contract_path"]).read_bytes()
        self.assertEqual(
            hashlib.sha256(contract_raw).hexdigest(),
            binding["contract_raw_sha256"],
        )
        for path_key, blob_key in (
            ("contract_path", "contract_git_blob"),
            ("harness_path", "harness_git_blob"),
            ("harness_test_path", "harness_test_git_blob"),
        ):
            path = binding[path_key]
            actual = subprocess.check_output(
                ["git", "rev-parse", f"{binding['approved_commit']}:{path}"],
                cwd=self.root,
                text=True,
            ).strip()
            self.assertEqual(actual, binding[blob_key], path)
        source = (self.root / binding["harness_path"]).read_text(encoding="utf-8")
        self.assertIn("raise PermissionError(", source)
        self.assertTrue(binding["current_guard_must_remain_unchanged_during_contract_definition"])

    def test_resolved_fixture_and_test_universes_are_sealed(self) -> None:
        universe = self.contract["resolved_universe_binding"]
        self.assertEqual(
            (universe["fixture_count"], universe["base_fixture_count"], universe["variant_fixture_count"]),
            (175, 6, 169),
        )
        self.assertEqual(universe["variant_axis_count"], 17)
        self.assertEqual(universe["phase_counts"], {"P0": 27, "P1": 35, "P2": 10})
        self.assertEqual(
            universe["fixture_manifest_sha256"],
            "acfa37b987deb19884c9f60cf3410717b68788eb466396402aaf992b3224e19c",
        )
        self.assertEqual(
            universe["resolved_test_manifest_sha256"],
            "0d059d3f2540f2b08279bb8363e9036ae0f71b2bea11575bfebfce76b7fe7504",
        )
        self.assertFalse(universe["addition_omission_or_reordering_after_authorization_allowed"])

    def test_future_capability_is_nonconstructible_noncopyable_and_single_use(self) -> None:
        capability = self.contract["future_capability_design"]
        self.assertTrue(capability["public_dataclass_or_mapping_is_not_a_capability"])
        self.assertFalse(capability["constructor_publicly_callable"])
        self.assertTrue(capability["factory_required"])
        self.assertTrue(capability["factory_must_be_separately_reviewed"])
        self.assertTrue(capability["dataclasses_replace_copy_pickle_or_manual_construction_must_fail"])
        self.assertTrue(capability["capability_single_use"])
        self.assertFalse(capability["capability_cross_process_reuse_allowed"])
        self.assertFalse(capability["capability_serialization_allowed"])
        threat = capability["threat_model"]
        self.assertFalse(
            threat["arbitrary_CPython_closure_or_memory_introspection_is_claimed_secure"]
        )
        self.assertFalse(threat["hostile_code_inside_the_same_Python_process_is_in_scope"])
        self.assertFalse(
            threat["untrusted_plugins_exec_eval_debuggers_or_reflection_allowed_in_scientific_worker"]
        )
        self.assertTrue(threat["single_purpose_reviewed_worker_process_required"])
        self.assertTrue(
            threat[
                "OS_process_or_equivalent_authority_boundary_required_before_hostile_same_process_code_can_enter_scope"
            ]
        )
        self.assertTrue(
            threat[
                "current_dormant_commit_must_expose_no_effective_claim_or_authoritative_terminal_path"
            ]
        )
        self.assertIn(
            "this_capability_contract_raw_SHA256_matches_a_future_separate_authorization_seal",
            capability["factory_must_require_all"],
        )
        required = set(capability["factory_must_require_all"])
        for right in (
            "capability_issuance",
            "synthetic_execution",
            "scientific_execution",
            "P0_execution",
            "P1_execution",
            "P2_execution",
        ):
            self.assertIn(
                f"future_authorization_seal_{right}_authorized_is_true",
                required,
            )

    def test_future_authorization_seal_does_not_exist_and_authorizes_nothing(self) -> None:
        seal = self.contract["future_execution_authorization_seal"]
        self.assertTrue(seal["required_as_separate_reviewed_file"])
        self.assertFalse(seal["exists_now"])
        self.assertIsNone(seal["path"])
        self.assertIsNone(seal["raw_sha256"])
        self.assertIsNone(seal["reviewed_execution_commit"])
        self.assertFalse(seal["capability_issuance_authorized"])
        self.assertFalse(seal["synthetic_execution_authorized"])
        for right in (
            "scientific_execution_authorized",
            "P0_execution_authorized",
            "P1_execution_authorized",
            "P2_execution_authorized",
        ):
            self.assertFalse(seal[right], right)
        self.assertTrue(seal["must_bind_this_contract_raw_sha256"])
        self.assertTrue(
            seal["source_blob_may_be_bound_without_being_modified_in_reviewed_commit"]
        )
        self.assertTrue(
            seal["both_source_blobs_must_match_reviewed_commit_and_current_checkout"]
        )

    def test_future_activation_breaks_hash_cycle_and_is_OS_bound(self) -> None:
        activation = self.contract["future_seal_activation"]
        self.assertFalse(activation["exists_now"])
        self.assertFalse(activation["authorization_seal_exists_now"])
        self.assertIsNone(activation["raw_sha256"])
        self.assertEqual(
            activation["activation_commit_environment_variable"],
            "H23_AUTHORIZATION_ACTIVATION_COMMIT",
        )
        self.assertTrue(activation["checkout_HEAD_must_equal_OS_bound_activation_commit"])
        self.assertTrue(activation["activation_bytes_must_equal_blob_at_activation_commit"])
        self.assertTrue(activation["activation_and_seal_bindings_must_match_exactly"])
        self.assertFalse(
            activation["seal_or_activation_may_modify_attested_capability_or_runner_source"]
        )
        self.assertFalse(activation["activation_commit_may_be_inferred_from_unreviewed_HEAD"])
        self.assertTrue(activation["missing_OS_binding_fails_before_plan_resolution"])

    def test_one_shot_consumption_boundary_is_before_first_waveform(self) -> None:
        boundary = self.contract["one_shot_boundary"]
        self.assertIsNone(boundary["authorization_marker_path"])
        self.assertIsNone(boundary["success_result_destination"])
        self.assertIsNone(boundary["terminal_record_destination"])
        self.assertEqual(boundary["claim_method"], "atomic_create_exclusive")
        self.assertEqual(
            boundary["persist_before_first_fixture_waveform_synthesis"],
            {"synthetic_population_consumed": True},
        )
        self.assertTrue(boundary["manifest_resolution_or_hashing_is_not_consumption"])
        self.assertTrue(boundary["first_fixture_waveform_synthesis_is_consumption"])
        self.assertTrue(boundary["failure_after_consumption_keeps_population_consumed"])
        self.assertFalse(boundary["automatic_retry_allowed"])
        self.assertFalse(boundary["manual_same_population_retry_allowed"])
        self.assertFalse(boundary["partial_result_authoritative"])

    def test_phase_order_publication_and_verdict_are_fail_closed(self) -> None:
        phases = self.contract["future_phase_order"]
        self.assertEqual(
            phases["order"],
            [
                "zero_science_preflight",
                "capability_issue",
                "atomic_consumption_claim",
                "P0",
                "P1",
                "P2",
                "atomic_terminal_outcome_publication",
            ],
        )
        self.assertTrue(phases["P1_requires_all_P0_pass"])
        self.assertTrue(phases["P2_requires_all_P1_pass"])
        for name in (
            "execute_unlisted_test_allowed",
            "skip_list_allowed",
            "dynamic_test_selection_allowed",
            "post_observation_parameter_change_allowed",
        ):
            self.assertFalse(phases[name])
        publication = self.contract["future_atomic_publication"]
        self.assertTrue(publication["staging_then_verify_then_atomic_rename"])
        success = publication["success_publication"]
        self.assertTrue(success["requires_all_175_fixture_ids"])
        self.assertTrue(success["requires_all_72_test_ids"])
        scientific_failure = publication["scientific_failure_publication"]
        self.assertTrue(scientific_failure["atomic_terminal_negative_publication_required"])
        self.assertFalse(scientific_failure["all_175_fixture_ids_required"])
        self.assertFalse(scientific_failure["all_72_test_ids_required"])
        self.assertEqual(
            scientific_failure["unexecuted_test_ids_status"],
            "NOT_RUN_BY_KILL_RULE",
        )
        operational = publication["operational_failure_publication"]
        self.assertEqual(
            operational["outcome"], "H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED"
        )
        self.assertTrue(operational["must_never_be_reported_as_scientific_verdict"])
        verdict = self.contract["future_verdict_contract"]
        self.assertEqual(verdict["only_positive_status"], "AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL")
        self.assertEqual(verdict["explicitly_not"], "TRAIN_AUTHORIZED")
        self.assertFalse(verdict["negative_or_inconclusive_result_retry_allowed"])
        self.assertFalse(verdict["result_may_authorize_training"])
        self.assertFalse(verdict["result_may_access_real_data"])

    def test_preflight_is_zero_science_and_adversarial_suite_is_complete(self) -> None:
        preflight = self.contract["future_zero_science_preflight"]
        self.assertTrue(preflight["must_complete_before_consumption"])
        self.assertFalse(preflight["numpy_import_allowed_during_preflight"])
        self.assertFalse(preflight["waveform_allocation_allowed_during_preflight"])
        self.assertFalse(preflight["fixture_spec_or_test_set_mutation_allowed"])
        adversarial = set(self.contract["required_future_adversarial_tests_before_issuance"])
        self.assertEqual(len(adversarial), 29)
        self.assertIn("dataclasses_replace_on_plan_or_capability_is_rejected", adversarial)
        self.assertIn("second_capability_claim_fails_cross_process", adversarial)
        self.assertIn("partial_staging_never_becomes_success_destination", adversarial)
        self.assertIn(
            "P0_failure_atomically_publishes_terminal_negative_with_NOT_RUN_suffix",
            adversarial,
        )
        for right in (
            "capability_issuance",
            "synthetic_execution",
            "scientific_execution",
            "P0_execution",
            "P1_execution",
            "P2_execution",
        ):
            self.assertIn(
                f"seal_missing_{right}_right_refuses_capability",
                adversarial,
            )

    def test_review_sequence_prevents_self_authorization(self) -> None:
        sequence = self.contract["future_review_sequence"]
        self.assertEqual(
            sequence["order"][:4],
            [
                "capability_and_runner_implementation_commit",
                "external_review_of_implementation",
                "separate_authorization_seal_commit_binding_reviewed_implementation",
                "external_review_of_authorization_seal",
            ],
        )
        self.assertTrue(sequence["implementation_commit_may_not_self_authorize"])
        self.assertTrue(
            sequence["authorization_seal_must_bind_already_reviewed_implementation_commit"]
        )
        self.assertEqual(
            sequence["order"][4],
            "OS_bound_activation_commit_review_and_exact_HEAD_injection",
        )
        self.assertTrue(
            sequence[
                "authorization_seal_hash_must_not_be_embedded_in_attested_implementation_source"
            ]
        )
        self.assertTrue(sequence["activation_commit_must_not_modify_attested_implementation_blobs"])

    def test_allowed_files_exclude_both_scientific_contract_and_harness(self) -> None:
        allowed = set(self.contract["contract_definition_allowed_files"])
        forbidden = set(self.contract["contract_definition_forbidden_files"])
        self.assertEqual(len(allowed), 5)
        self.assertFalse(any(path.startswith("src/") for path in allowed))
        self.assertEqual(
            forbidden,
            {
                "src/polyphonic/harmonic_censoring_h23.py",
                "configs/harmonic_censoring_pretrain_h23_contract.json",
            },
        )
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/harmonic_censoring_h23_synthetic_execution_capability_contract.json text eol=lf",
            attributes.splitlines(),
        )


if __name__ == "__main__":
    unittest.main()
