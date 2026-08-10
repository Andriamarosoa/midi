from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest


class ProvisionalResolutionFrameFallbackH17aAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json"
        cls.contract = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.h17_path = cls.root / "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json"
        cls.h17 = json.loads(cls.h17_path.read_text(encoding="utf-8"))

    def test_historical_h17_remains_immutable_and_review_chain_is_exact(self):
        historical = self.contract["historical_contract_immutability"]
        self.assertFalse(historical["original_h17_file_modified"])
        self.assertEqual(historical["original_h17_commit"], "3a3e65ab532a4983fadae89c842b544228c3b028")
        actual_blob = subprocess.check_output(
            ["git", "hash-object", str(self.h17_path)], cwd=self.root, text=True
        ).strip()
        self.assertEqual(actual_blob, "f8d8e71f8d2b98955c2e19fedf2f4019ab4cca2f")
        self.assertEqual(historical["original_h17_contract_git_blob"], actual_blob)
        self.assertEqual(
            self.h17["population_contract"]["preregistered_pathway_exclusions"],
            ["retrigger", "legacy"],
        )
        chain = self.contract["review_chain"]
        self.assertEqual(chain["h19_rejected_commit"], "2361486241f6f58662ab483eb526d3b9bdeb68db")
        self.assertEqual(chain["corrected_h19a_commit"], "a28068a55d711ad4dd24e31736974bdf30533c00")

    def test_amended_taxonomy_is_exact_and_unknown_reasons_fail_closed(self):
        taxonomy = self.contract["amended_population_taxonomy"]
        self.assertEqual(taxonomy["F_equals_1"], ["frame_fallback"])
        self.assertEqual(
            taxonomy["F_equals_0_comparator"],
            ["model_onset", "frame_attack", "chord_completion"],
        )
        self.assertEqual(
            taxonomy["excluded_and_counted_only"],
            ["harmonic_strong_frame", "legacy", "retrigger"],
        )
        self.assertEqual(taxonomy["all_other_reasons_status"], "frame_fallback_execution_invalid")
        self.assertFalse(taxonomy["harmonic_strong_frame_reason_reconstruction_allowed"])

    def test_change_declarations_are_honest_and_narrow(self):
        declarations = self.contract["amendment_declarations"]
        unchanged = (
            "scientific_question_changed", "primary_signal_changed",
            "comparator_changed", "target_changed", "RD_threshold_changed",
            "bootstrap_changed",
        )
        self.assertTrue(all(declarations[name] is False for name in unchanged))
        self.assertTrue(declarations["population_taxonomy_amended"])
        self.assertTrue(declarations["attrition_schema_amended"])
        self.assertTrue(declarations["amendment_occurred_before_real_data_access"])

    def test_attrition_and_primary_thresholds_are_complete_and_unchanged(self):
        counts = self.contract["amended_attrition_schema"]["required_counts"]
        self.assertIn("excluded_harmonic_strong_frame_count", counts)
        self.assertEqual(len(counts), len(set(counts)))
        self.assertFalse(self.contract["amended_attrition_schema"]["silent_deletion_allowed"])
        primary = self.contract["unchanged_primary_contract"]
        self.assertEqual(primary["minimum_eligible_noteons"], 200)
        self.assertEqual(primary["minimum_frame_fallback_noteons"], 50)
        self.assertEqual(primary["minimum_comparator_noteons"], 50)
        self.assertEqual(primary["minimum_RD_false_inclusive"], 0.1)
        self.assertEqual(primary["bootstrap_lower_95_strictly_greater_than"], 0.0)
        self.assertEqual(primary["bootstrap_replicates"], 10000)
        self.assertEqual(primary["bootstrap_seed"], 721629268)
        self.assertEqual(primary["minimum_valid_bootstrap_replicates"], 9500)
        self.assertFalse(primary["secondary_can_change_verdict"])

    def test_scope_is_zero_science_and_lf_is_forced(self):
        scope = self.contract["scope"]
        self.assertTrue(scope["contract_only"])
        for name, value in scope.items():
            if name != "contract_only":
                self.assertFalse(value, name)
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json text eol=lf",
            attributes,
        )
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
