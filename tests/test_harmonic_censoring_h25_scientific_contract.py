from __future__ import annotations

import json
import unittest
from pathlib import Path


class H25ScientificHypothesisExecutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = Path(__file__).resolve().parents[1]
        cls.path = (
            cls.repository
            / "configs/harmonic_censoring_h25_scientific_hypothesis_execution_contract.json"
        )
        cls.raw = cls.path.read_bytes()
        cls.contract = json.loads(cls.raw.decode("utf-8"))

    def test_contract_is_canonical_contract_only_and_binds_admin_result(self) -> None:
        self.assertNotIn(b"\r", self.raw)
        self.assertFalse(self.raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(
            self.contract["status"], "contract_only_pending_external_review"
        )
        self.assertTrue(self.contract["scope"]["contract_only"])
        for key, value in self.contract["scope"].items():
            if key != "contract_only":
                self.assertFalse(value, key)
        self.assertEqual(
            self.contract["authority"][
                "administrative_qualification_record_sha256"
            ],
            "54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1",
        )

    def test_transform_only_collision_and_geometry_cannot_be_claimed(self) -> None:
        hypotheses = self.contract["hypotheses"]
        operator = self.contract["pitch_dilution_operator_contract"]
        self.assertIn("no source attribution", hypotheses["null_transform_only"])
        self.assertTrue(operator["raw_disappearance_index_forbidden"])
        self.assertTrue(
            operator[
                "aligned_whole_mixture_transform_is_equivariant_control_not_positive_evidence"
            ]
        )
        self.assertTrue(
            operator["exact_collision_must_remain_identical_under_every_transform"]
        )
        self.assertEqual(operator["transform_grid_semitones"], list(range(89)))
        self.assertEqual(operator["transform_grid_step_semitones"], 1)
        self.assertEqual(operator["transform_grid_count"], 89)
        self.assertTrue(operator["transform_grid_change_after_contract_review_forbidden"])
        self.assertIn("AMBIGUOUS", hypotheses["non_identifiability"])

    def test_windows_are_strictly_causal_and_have_separate_roles(self) -> None:
        signal = self.contract["signal_and_coordinate_contract"]
        causal = self.contract["causal_evidence_contract"]
        self.assertEqual(signal["short_causal_window_samples"], 4096)
        self.assertEqual(signal["long_causal_window_samples"], 8192)
        self.assertTrue(signal["both_windows_end_at_same_current_hop"])
        self.assertEqual(signal["future_lookahead_samples"], 0)
        self.assertEqual(signal["decision_delay_hops_for_new_source"], 1)
        self.assertEqual(causal["state_machine"], ["INACTIVE", "PENDING_NEW", "ACTIVE"])
        self.assertIn("future_audio", causal["forbidden_inputs"])
        self.assertIn("raw_transform_disappearance_index", causal["forbidden_inputs"])

    def test_phases_and_kill_rules_are_complete_and_ordered(self) -> None:
        phases = self.contract["phase_contract"]
        decision = self.contract["decision_contract"]
        self.assertEqual(phases["fixed_order"], ["P0", "P1", "P2"])
        self.assertTrue(phases["P1_requires_all_P0_pass"])
        self.assertTrue(phases["P2_requires_all_P1_pass"])
        self.assertIn("H25_SYNTHETIC_HYPOTHESIS_KILLED", phases["P0"]["kill_rule"])
        self.assertIn("H25_IDENTIFIABILITY_NOT_DEMONSTRATED", phases["P1"]["kill_rule"])
        self.assertIn("H25_PRETRAIN_READINESS_NOT_DEMONSTRATED", phases["P2"]["kill_rule"])
        self.assertTrue(
            decision["all_P0_P1_P2_pass_is_not_training_or_real_validation_authority"]
        )
        self.assertTrue(decision["posthoc_threshold_grid_population_bootstrap_or_taxonomy_change_forbidden"])
        self.assertTrue(decision["retry_after_claim_forbidden"])
        numeric = self.contract["analytic_graph_and_numeric_contract"]
        self.assertEqual(numeric["same_runtime_rtol"], 1e-10)
        self.assertEqual(numeric["same_runtime_atol"], 1e-12)
        self.assertEqual(numeric["integer_boolean_category_mask_tolerance"], 0)
        self.assertTrue(numeric["posthoc_tolerance_change_forbidden"])

    def test_new_population_is_required_but_absent(self) -> None:
        population = self.contract["future_population_requirements"]
        self.assertEqual(population["population_namespace"], "H25_SYNTHETIC_V1")
        self.assertEqual(population["test_namespace"], "H25_TEST_V1")
        self.assertFalse(population["population_manifest_currently_exists"])
        self.assertFalse(population["test_manifest_currently_exists"])
        self.assertTrue(population["all_fixture_and_test_IDs_must_be_new"])
        self.assertTrue(population["deterministic_synthetic_only"])
        self.assertTrue(population["real_recordings_forbidden"])
        self.assertGreaterEqual(len(population["required_fixture_families"]), 12)

    def test_lifecycle_and_one_shot_topology_are_predeclared(self) -> None:
        lifecycle = self.contract["scientific_lifecycle_contract"]
        topology = self.contract["future_one_shot_topology"]
        self.assertTrue(
            lifecycle[
                "single_reviewed_entrypoint_owns_preflight_capability_claim_P0_P1_P2_and_closure"
            ]
        )
        self.assertTrue(lifecycle["claim_is_last_irreversible_action_before_automatic_P0"])
        self.assertTrue(
            lifecycle[
                "stdin_EOF_parent_disconnect_signal_and_timeout_have_predeclared_closures"
            ]
        )
        self.assertEqual(
            topology["claim_path"],
            "tmp/local/harmonic_censoring_h25_scientific_v1.consumed.json",
        )
        self.assertTrue(topology["all_paths_must_be_absent_before_claim"])
        self.assertTrue(topology["claim_created_with_O_EXCL_and_fsync"])
        self.assertTrue(topology["claim_never_deleted_recreated_or_reused"])

    def test_no_predecessor_or_scientific_artifact_is_created_by_contract(self) -> None:
        self.assertTrue(
            self.contract["predecessor_firewall"][
                "H17_population_or_rows_must_not_be_opened_or_reused"
            ]
        )
        self.assertTrue(
            self.contract["predecessor_firewall"][
                "H24_population_claim_or_test_ID_reuse_forbidden"
            ]
        )
        forbidden = set(self.contract["forbidden_now"])
        self.assertIn("create_H25_population_or_test_manifest", forbidden)
        self.assertIn("synthesize_or_decode_any_waveform", forbidden)
        self.assertIn("execute_P0_P1_or_P2", forbidden)
        self.assertIn("open_real_data_H17_or_locked_test", forbidden)
        self.assertIn("train_fit_calibrate_export_or_live", forbidden)
        self.assertTrue(
            self.contract["future_provenance_runtime_and_authority_requirements"][
                "seal_activation_and_OS_binding_do_not_exist_now"
            ]
        )


if __name__ == "__main__":
    unittest.main()
