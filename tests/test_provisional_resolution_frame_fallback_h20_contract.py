from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


class ProvisionalResolutionFrameFallbackH20ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "configs/provisional_resolution_frame_fallback_h20_real_execution_contract.json"
        cls.contract = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.h18a_path = cls.root / "configs/provisional_resolution_frame_fallback_h18_metadata_audit.json"
        cls.h18a = json.loads(cls.h18a_path.read_text(encoding="utf-8"))

    def test_status_parent_and_zero_science_scope_are_exact(self):
        self.assertEqual(self.contract["parent_commit"], "9e6ffa9d9087f0b5ce386d7a177ef35bd7cd8708")
        self.assertEqual(
            self.contract["status"],
            "provisional_resolution_frame_fallback_h20_real_execution_contract_defined",
        )
        scope = self.contract["scope"]
        self.assertTrue(scope["contract_only"])
        for name, value in scope.items():
            if name != "contract_only":
                self.assertFalse(value, name)

    def test_all_scientific_bindings_are_exact_and_current(self):
        bindings = self.contract["scientific_bindings"]
        expected_files = {
            "h17_contract_git_blob": "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json",
            "h17a_amendment_contract_git_blob": "configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json",
            "h19a_contract_git_blob": "configs/provisional_resolution_frame_fallback_h19_synthetic_conformance.json",
            "h19a_implementation_git_blob": "src/polyphonic/provisional_resolution_frame_fallback_h19.py",
            "decoder_git_blob": "src/polyphonic/decoder.py",
            "exact_causal_target_extractor_git_blob": "src/polyphonic/provisional_resolution_age1.py",
            "canonical_group_universe_engine_git_blob": "src/polyphonic/provisional_resolution_age1_metrics.py",
            "grouping_implementation_git_blob": "src/polyphonic/decoder_candidate_provenance.py",
        }
        for field, relative_path in expected_files.items():
            actual = subprocess.check_output(
                ["git", "hash-object", relative_path], cwd=self.root, text=True
            ).strip()
            self.assertEqual(bindings[field], actual, field)
        self.assertEqual(bindings["checkpoint_sha256"], "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325")
        self.assertTrue(bindings["mismatch_must_fail_before_scientific_access"])

    def test_h18a_population_is_exact_unconsumed_and_not_reselected(self):
        population = self.contract["population_binding"]
        accepted = self.h18a["fresh_discovery_population"]
        self.assertEqual(accepted["recording_count"], 146)
        self.assertEqual(accepted["leakage_group_count"], 51)
        self.assertEqual(population["recording_count"], accepted["recording_count"])
        self.assertEqual(population["leakage_group_count"], accepted["leakage_group_count"])
        self.assertEqual(population["classification"], "fresh_discovery_only_not_independent_validation")
        self.assertTrue(population["selected_by_h18a"])
        self.assertFalse(population["scientifically_opened"])
        self.assertFalse(population["consumed"])
        for name in (
            "manual_reselection_allowed", "random_sampling_allowed", "corpus_balancing_allowed",
            "duration_filtering_allowed", "reason_frequency_filtering_allowed",
            "target_or_class_filtering_allowed", "post_hoc_removal_allowed",
        ):
            self.assertFalse(population[name])
        self.assertTrue(population["zero_eligible_row_groups_remain_in_universe"])

    def test_taxonomy_target_metric_and_bootstrap_are_frozen(self):
        taxonomy = self.contract["reason_taxonomy"]
        self.assertEqual(taxonomy["F_equals_1"], ["frame_fallback"])
        self.assertEqual(taxonomy["F_equals_0_comparator"], ["model_onset", "frame_attack", "chord_completion"])
        self.assertEqual(taxonomy["excluded_and_counted"], ["harmonic_strong_frame", "legacy", "retrigger"])
        self.assertFalse(taxonomy["harmonic_strong_frame_reason_reconstruction_allowed"])
        target = self.contract["target_contract"]
        self.assertFalse(target["new_matching_code_or_rule_allowed"])
        self.assertEqual(target["maximum_causal_latency_ms"], 250.0)
        metric = self.contract["primary_metric"]
        required = metric["positive_requires_all"]
        self.assertEqual(tuple(required.values()), (200, 50, 50, 0.1, 0.0))
        self.assertFalse(metric["secondary_output_may_alter_verdict"])
        bootstrap = self.contract["bootstrap"]
        self.assertEqual(bootstrap["replicate_count"], 10000)
        self.assertEqual(bootstrap["seed"], 721629268)
        self.assertEqual(bootstrap["sealed_group_count"], 51)
        self.assertEqual(bootstrap["minimum_valid_replicates"], 9500)
        self.assertEqual(bootstrap["percentiles"], [2.5, 97.5])
        self.assertEqual(bootstrap["interpolation"], "linear")
        self.assertFalse(bootstrap["invalid_replicate_retry_allowed"])

    def test_attrition_phases_one_shot_and_consumption_boundary_are_closed(self):
        counts = self.contract["mandatory_attrition"]["required_counts"]
        self.assertEqual(len(counts), 10)
        self.assertEqual(len(set(counts)), 10)
        self.assertIn("excluded_harmonic_strong_frame_count", counts)
        self.assertFalse(self.contract["mandatory_attrition"]["silent_deletion_allowed"])
        self.assertEqual(
            self.contract["future_execution_phases"],
            ["opening", "inference", "decoder", "target", "reconciliation", "metrics", "publication"],
        )
        one_shot = self.contract["future_one_shot_authorization"]
        self.assertTrue(one_shot["single_use"])
        self.assertFalse(one_shot["authorization_marker_created_by_h20"])
        self.assertTrue(one_shot["claim_must_be_atomic"])
        boundary = self.contract["consumption_boundary"]
        self.assertEqual(boundary["persist_atomically_before_boundary"], {"fresh_population_consumed": True})
        self.assertTrue(boundary["failure_after_boundary"]["population_remains_consumed"])
        self.assertFalse(boundary["failure_after_boundary"]["automatic_retry_allowed"])

    def test_publication_unresolved_values_and_restrictions_are_fail_closed(self):
        publication = self.contract["future_publication"]
        self.assertTrue(publication["atomic"])
        self.assertEqual(len(publication["required_logical_outputs"]), 4)
        unresolved = self.contract["unresolved_pre_execution_values"]
        for name, value in unresolved.items():
            if name != "require_later_zero_science_preparation_contract":
                self.assertIsNone(value, name)
        self.assertTrue(unresolved["require_later_zero_science_preparation_contract"])
        self.assertTrue(all(value is False for value in self.contract["post_result_restrictions"].values()))
        self.assertEqual(len(self.contract["inconclusive_or_failure_statuses"]), 5)
        self.assertFalse(self.contract["failure_policy"]["automatic_retry_from_any_status"])

    def test_allowed_files_lf_and_no_source_file_are_exact(self):
        allowed = self.contract["h20_allowed_files"]
        self.assertEqual(len(allowed), 5)
        self.assertFalse(any(path.startswith("src/") for path in allowed))
        self.assertIn("modify_src", self.contract["h20_forbidden_actions"])
        self.assertIn("create_runner", self.contract["h20_forbidden_actions"])
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "configs/provisional_resolution_frame_fallback_h20_real_execution_contract.json text eol=lf",
            attributes,
        )
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
