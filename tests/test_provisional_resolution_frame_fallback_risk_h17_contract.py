from __future__ import annotations

import json
from pathlib import Path
import unittest


class ProvisionalResolutionFrameFallbackRiskH17ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = (
            cls.root
            / "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json"
        )
        cls.contract = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_scope_is_contract_only_and_zero_science(self) -> None:
        self.assertEqual(
            self.contract["status"],
            "provisional_resolution_frame_fallback_risk_hypothesis_defined",
        )
        self.assertEqual(
            self.contract["scope"],
            {
                "contract_only": True,
                "cohort_selected": False,
                "data_access_authorized": False,
                "scientific_execution_authorized": False,
                "signals_extracted": False,
                "targets_extracted": False,
                "metrics_computed": False,
                "model_loaded": False,
                "h8_reused": False,
                "consumed_v2_reused": False,
                "locked_test_used": False,
            },
        )

    def test_population_exposure_and_comparator_are_exact(self) -> None:
        population = self.contract["population_contract"]
        self.assertEqual(
            population["eligible_reason_taxonomy"],
            ["model_onset", "frame_attack", "chord_completion", "frame_fallback"],
        )
        self.assertEqual(population["primary_exposure"]["name"], "F")
        self.assertIn("frame_fallback", population["primary_exposure"]["definition"])
        self.assertEqual(
            population["comparator"]["reasons"],
            ["model_onset", "frame_attack", "chord_completion"],
        )
        self.assertEqual(
            population["preregistered_pathway_exclusions"],
            ["retrigger", "legacy"],
        )
        self.assertFalse(population["silent_pooling_or_deletion_allowed"])

    def test_signal_is_single_categorical_indicator(self) -> None:
        signal = self.contract["primary_signal"]
        self.assertEqual(signal["source_field"], "candidate_reason_at_noteon")
        self.assertEqual(signal["symbol"], "F")
        self.assertFalse(signal["may_be_combined_with_other_fields"])
        self.assertFalse(signal["model_fitting_allowed"])
        forbidden = set(self.contract["forbidden_primary_inputs"])
        self.assertTrue(
            {
                "candidate_score_at_noteon",
                "frame_probability_at_noteon",
                "current_frame_probability",
                "audio_onset_recent",
                "S0",
                "S1",
                "D1",
                "age_search",
                "learned_classifiers",
            }.issubset(forbidden)
        )

    def test_target_reuses_exact_frozen_causal_semantics(self) -> None:
        target = self.contract["target_contract"]
        self.assertEqual(target["base_target"], "true_noteon")
        self.assertEqual(target["derived_target"], "false_noteon")
        self.assertEqual(target["true_noteon_to_false_noteon"], {"1": 0, "0": 1})
        self.assertTrue(target["excluded_or_unmatchable_rows_remain_excluded"])
        self.assertFalse(target["new_matching_rule_allowed"])
        self.assertEqual(target["maximum_causal_latency_ms"], 250.0)
        self.assertEqual(
            {item["path"]: item["git_blob"] for item in target["source_code"]},
            {
                "src/polyphonic/evaluate_events.py": "c63b9751e5acef49fb51b5e2a8264b00d6e60893",
                "src/polyphonic/decoder_candidate_labels.py": "98c3f2e87b89df599e71068ab4ae874f69172c5a",
                "src/polyphonic/causal_event_metrics.py": "42f7954b75b0994f43d7f59c62c1ff1b04c0a81d",
            },
        )

    def test_primary_metric_and_decision_gate_are_frozen(self) -> None:
        metric = self.contract["primary_metric"]
        self.assertEqual(metric["name"], "RD_false")
        self.assertEqual(
            metric["definition"],
            "P(false_noteon=1 | F=1) - P(false_noteon=1 | F=0)",
        )
        self.assertFalse(metric["roc_auc_is_primary"])
        self.assertEqual(
            metric["positive_requires_all"],
            {
                "total_eligible_noteons_minimum": 200,
                "eligible_frame_fallback_noteons_minimum": 50,
                "eligible_comparator_noteons_minimum": 50,
                "global_rd_false_minimum_inclusive": 0.10,
                "group_resampled_95pct_ci_lower_bound_strictly_greater_than": 0.0,
            },
        )
        self.assertEqual(
            metric["positive_verdict"],
            "frame_fallback_false_risk_enrichment_demonstrated",
        )
        self.assertEqual(
            metric["negative_verdict"],
            "frame_fallback_false_risk_enrichment_not_demonstrated",
        )
        self.assertFalse(metric["secondary_can_change_verdict"])

    def test_bootstrap_is_group_safe_and_exact(self) -> None:
        bootstrap = self.contract["bootstrap_contract"]
        self.assertEqual(bootstrap["replicate_count"], 10000)
        self.assertEqual(bootstrap["random_seed"], 721629268)
        self.assertEqual(bootstrap["sampling_unit"], "leakage_group_key")
        self.assertEqual(bootstrap["minimum_valid_replicates"], 9500)
        self.assertEqual(bootstrap["confidence_interval_percentiles"], [2.5, 97.5])
        self.assertEqual(bootstrap["quantile_method"], "linear")
        self.assertFalse(bootstrap["row_noteon_frame_or_recording_bootstrap_allowed"])
        self.assertFalse(bootstrap["alternate_seed_allowed"])
        self.assertFalse(bootstrap["retry_allowed"])

    def test_future_cohort_is_unselected_and_requires_fresh_groups(self) -> None:
        cohort = self.contract["future_cohort_contract"]
        self.assertIsNone(cohort["future_cohort_selection"])
        self.assertIsNone(cohort["recording_identities"])
        self.assertIsNone(cohort["asset_hashes"])
        self.assertFalse(cohort["data_access_authorized"])
        self.assertEqual(cohort["class"], "fresh_discovery_only")
        self.assertFalse(cohort["may_be_called_independent_validation_now"])
        self.assertEqual(cohort["minimum_independent_leakage_groups"], 20)
        preparation = cohort["metadata_only_preparation_after_h17_review"]
        self.assertTrue(preparation["select_all_admissible_fresh_unseen_groups"])
        self.assertFalse(preparation["open_audio"])
        self.assertFalse(preparation["parse_scientific_labels"])
        self.assertFalse(preparation["outcome_based_sampling_allowed"])
        self.assertEqual(
            preparation["failure_status_if_minimum_not_established"],
            "fresh_discovery_population_not_established",
        )

    def test_provenance_closes_historical_runners_and_consumed_cohorts(self) -> None:
        bindings = self.contract["provenance_bindings"]
        self.assertEqual(
            bindings["accepted_h16_commit"],
            "31d36165e65399750342159fef591fe65d4f7ce5",
        )
        self.assertEqual(
            bindings["h16_future_orchestrator_blob"],
            "80d7d17361a69203526dc40f79a9b2659dfc916d",
        )
        self.assertFalse(bindings["update_h12_or_h13_bindings"])
        self.assertFalse(bindings["historical_runner_made_executable"])
        rules = self.contract["post_result_rules"]
        self.assertFalse(rules["h8_reuse_allowed"])
        self.assertFalse(rules["locked_test_access_allowed"])

    def test_inconclusive_attrition_and_stop_rules_are_fail_closed(self) -> None:
        self.assertEqual(
            set(self.contract["inconclusive_statuses"]),
            {
                "fresh_discovery_population_not_established",
                "target_definition_requires_separate_contract",
                "grouping_identity_not_established",
                "frame_fallback_signal_insufficient_valid_observations",
                "frame_fallback_exposed_population_insufficient",
                "frame_fallback_comparator_population_insufficient",
                "group_resampling_inconclusive",
                "frame_fallback_execution_invalid",
            },
        )
        self.assertFalse(self.contract["inconclusive_triggers_automatic_retry"])
        required = set(self.contract["future_attrition_contract"]["required_counts"])
        self.assertIn("malformed_reason_count", required)
        self.assertIn("target_unmatchable_or_excluded_count", required)
        stops = set(self.contract["stop_conditions"])
        self.assertIn("opening_audio", stops)
        self.assertIn("computing_rd_auc_or_bootstrap", stops)
        self.assertIn("accessing_locked_test_assets", stops)

    def test_contract_checkout_is_forced_to_lf(self) -> None:
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json text eol=lf",
            attributes.splitlines(),
        )
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
