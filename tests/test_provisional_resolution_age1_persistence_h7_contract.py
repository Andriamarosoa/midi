from __future__ import annotations

import json
from pathlib import Path
import unittest


class ProvisionalResolutionAge1PersistenceH7ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = (
            cls.root
            / "configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json"
        )
        cls.contract = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_status_and_scope_are_contract_only(self) -> None:
        contract = self.contract
        self.assertEqual(
            contract["status"],
            "provisional_resolution_age1_persistence_hypothesis_defined",
        )
        self.assertFalse(contract["real_computation_authorized"])
        self.assertFalse(contract["locked_test_used"])
        self.assertTrue(contract["scope"]["contract_only"])
        for name in (
            "signal_demonstrated",
            "target_extracted",
            "cohort_selected",
            "execution_authorized",
            "resolver_implemented",
            "threshold_selected",
            "policy_validated",
            "v3_authorized",
        ):
            self.assertFalse(contract["scope"][name])

    def test_single_signal_age_and_comparators_are_exact(self) -> None:
        signals = self.contract["signals"]
        self.assertEqual(signals["primary"]["name"], "S1")
        self.assertEqual(
            signals["primary"]["definition"], "current_frame_probability"
        )
        self.assertEqual(signals["primary"]["required_age_frames"], 1)
        self.assertFalse(signals["primary"]["may_be_combined_with_other_fields"])
        self.assertEqual(
            signals["baseline"],
            {
                "name": "S0",
                "definition": "frame_probability_at_noteon",
                "role": "descriptive_comparator_only",
                "gating": False,
            },
        )
        self.assertEqual(signals["secondary"]["name"], "D1")
        self.assertFalse(signals["secondary"]["may_rescue_negative_primary"])
        age = self.contract["age_contract"]
        self.assertEqual(age["required_age_frames"], 1)
        self.assertFalse(age["interpolation_allowed"])
        self.assertFalse(age["later_age_substitution_allowed"])
        self.assertFalse(age["other_age_search_authorized"])
        forbidden = set(self.contract["forbidden_signal_inputs"])
        self.assertTrue({
            "audio_onset_available",
            "audio_onset_recent",
            "harmonic_support",
            "current_onset_probability",
            "candidate_score_at_noteon",
            "candidate_reason_at_noteon",
            "any_other_h5_field",
        }.issubset(forbidden))

    def test_target_reuses_frozen_strict_causal_matcher(self) -> None:
        target = self.contract["target_contract"]
        self.assertFalse(target["resolver_access"])
        self.assertTrue(target["offline_diagnostic_only"])
        self.assertEqual(target["maximum_latency_ms"], 250.0)
        self.assertEqual(
            target["label_mapping"],
            {
                "prediction_index_in_matches": 1,
                "prediction_index_in_false_prediction_indices": 0,
            },
        )
        sources = {item["path"]: item for item in target["source_code"]}
        self.assertEqual(
            sources["src/polyphonic/causal_event_metrics.py"]["git_blob"],
            "42f7954b75b0994f43d7f59c62c1ff1b04c0a81d",
        )
        self.assertEqual(
            sources["src/polyphonic/decoder_candidate_labels.py"]["git_blob"],
            "98c3f2e87b89df599e71068ab4ae874f69172c5a",
        )
        self.assertIn(
            "reference_is_eligible_only_if_same_pitch_and_reference_start_not_after_prediction_time",
            target["matching_semantics"],
        )
        self.assertFalse(target["new_truth_rule_allowed"])

    def test_metric_bootstrap_and_verdicts_are_preregistered(self) -> None:
        metric = self.contract["primary_metric"]
        self.assertEqual(metric["metric"], "ROC_AUC")
        self.assertEqual(metric["score"], "S1")
        self.assertEqual(metric["target"], "true_noteon")
        self.assertEqual(
            metric["positive_requires_all"],
            {
                "global_roc_auc_minimum_inclusive": 0.60,
                "group_resampled_95pct_ci_lower_bound_strictly_greater_than": 0.50,
            },
        )
        self.assertEqual(
            metric["positive_verdict"], "age1_persistence_signal_demonstrated"
        )
        self.assertEqual(
            metric["negative_verdict"], "age1_persistence_signal_not_demonstrated"
        )
        bootstrap = self.contract["bootstrap_contract"]
        self.assertEqual(bootstrap["method"], "group_resampled_percentile_bootstrap")
        self.assertEqual(bootstrap["confidence_interval_percentiles"], [2.5, 97.5])
        self.assertEqual(
            bootstrap["single_class_replicate"],
            "invalid_excluded_from_percentiles",
        )
        self.assertFalse(
            bootstrap["row_frame_noteon_or_recording_bootstrap_substitution_allowed"]
        )
        self.assertFalse(bootstrap["retry_after_observation_allowed"])

    def test_grouping_attrition_and_execution_parameters_remain_unresolved(self) -> None:
        grouping = self.contract["grouping_contract"]
        self.assertEqual(grouping["grouping_function"], "leakage_group_key")
        self.assertTrue(grouping["row_or_noteon_level_grouping_forbidden"])
        data = self.contract["data_contract"]
        self.assertIsNone(data["future_cohort_selection"])
        self.assertTrue(data["consumed_independent_v2_cohort_forbidden"])
        self.assertTrue(data["locked_test_forbidden"])
        self.assertFalse(data["data_access_authorized_now"])
        self.assertEqual(
            self.contract["unresolved_execution_parameters"],
            {
                "future_cohort_selection": None,
                "bootstrap_replicate_count": None,
                "bootstrap_random_seed": None,
                "minimum_valid_age1_observation_count": None,
                "minimum_valid_bootstrap_replicate_count": None,
            },
        )
        self.assertIsNone(
            self.contract["attrition_contract"]["minimum_valid_age1_observations"]
        )

    def test_inconclusive_and_post_result_rules_are_fail_closed(self) -> None:
        statuses = set(self.contract["inconclusive_statuses"])
        self.assertEqual(statuses, {
            "target_definition_requires_separate_contract",
            "grouping_identity_not_established",
            "group_resampling_inconclusive",
            "age1_signal_insufficient_valid_observations",
            "age1_signal_single_class",
            "age1_signal_execution_invalid",
        })
        rules = self.contract["post_result_rules"]
        self.assertTrue(rules["negative_is_terminal_for_h7"])
        for name, value in rules.items():
            if name != "negative_is_terminal_for_h7":
                self.assertFalse(value)

    def test_contract_checkout_is_forced_to_lf(self) -> None:
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json text eol=lf",
            attributes.splitlines(),
        )
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
