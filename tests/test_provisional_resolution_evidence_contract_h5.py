from __future__ import annotations

import json
from pathlib import Path
import unittest


class ProvisionalResolutionEvidenceContractH5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "configs/provisional_resolution_evidence_contract_h5.json"
        cls.contract = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_contract_is_contract_only_and_terminal_status_is_exact(self) -> None:
        contract = self.contract
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(
            contract["status"],
            "provisional_resolution_evidence_contract_defined",
        )
        self.assertTrue(contract["scope"]["contract_only"])
        self.assertFalse(contract["scope"]["performance_hypothesis"])
        self.assertFalse(contract["scope"]["resolver_implemented"])
        self.assertFalse(contract["scope"]["resolver_validated"])
        self.assertFalse(contract["scope"]["policy_validated"])
        self.assertFalse(contract["scope"]["v3"])
        self.assertFalse(contract["scope"]["real_computation_authorized"])
        self.assertFalse(contract["locked_test_used"])

    def test_allowed_observation_schema_is_exact_and_causal(self) -> None:
        observations = self.contract["observations"]
        self.assertEqual(
            [item["name"] for item in observations],
            [
                "pitch",
                "note_on_frame",
                "current_frame",
                "age_frames",
                "candidate_reason_at_noteon",
                "candidate_score_at_noteon",
                "frame_probability_at_noteon",
                "onset_probability_at_noteon",
                "current_frame_probability",
                "current_onset_probability",
                "audio_onset_available",
                "audio_onset_recent",
                "harmonic_support",
                "emitted_polyphony",
                "contextual_polyphony",
            ],
        )
        for item in observations:
            self.assertEqual(item["status"], "allowed")
            self.assertTrue(item["provenance"])
            self.assertTrue(item["availability"])
            self.assertTrue(item["temporal_mode"])
            self.assertTrue(item["causal_argument"])
        self.assertFalse(self.contract["causal_clock"]["future_frame_access"])
        observation_type = self.contract["observation_type"]
        self.assertTrue(observation_type["immutable"])
        self.assertTrue(observation_type["constructed_only_by_decoder"])
        self.assertTrue(observation_type["complete_closed_schema"])
        self.assertFalse(observation_type["resolver_receives_decoder_object"])

    def test_forbidden_sources_and_compositions_are_fail_closed(self) -> None:
        rejected = set(self.contract["rejected_observations"])
        self.assertTrue({
            "ground_truth_labels",
            "reference_midi",
            "future_frames",
            "future_audio",
            "validation_results",
            "independent_v2_cohort_information",
            "arbitrary_decoder_object_access",
            "file_access",
            "network_access",
            "hidden_mutable_resolver_state",
        }.issubset(rejected))
        composition = self.contract["composition_contract"]
        self.assertEqual(
            composition["h4_with_causal_candidate_gate_v1_or_v2"],
            "unsupported_pending_separate_contract",
        )
        self.assertEqual(
            composition["h4_with_independent_note_threshold"],
            "unsupported_pending_separate_contract",
        )
        self.assertFalse(composition["silent_composition_allowed"])

    def test_resolution_and_error_rules_are_explicit_without_parameters(self) -> None:
        rules = self.contract["resolution_invariants"]
        self.assertEqual(rules["HOLD"]["midi_events"], [])
        self.assertFalse(rules["CONFIRM"]["new_noteon"])
        self.assertEqual(rules["REJECT"]["noteoff_count"], 1)
        self.assertTrue(rules["PREEMPT"]["distinct_from_reject"])
        self.assertTrue(rules["PREEMPT"]["noteoff_before_replacement_noteon"])
        errors = self.contract["resolver_error_contract"]
        self.assertTrue(errors["validation_is_atomic_across_all_provisional_notes_in_frame"])
        self.assertFalse(errors["partial_resolution_mutation_allowed"])
        self.assertFalse(errors["automatic_hold_fallback_allowed"])
        self.assertEqual(
            self.contract["unresolved_decision_parameters"],
            {
                "confirmation_threshold": None,
                "rejection_threshold": None,
                "maximum_provisional_age_frames": None,
                "eligible_noteon_population": None,
                "resolver_failure_runtime_policy": None,
            },
        )
        self.assertFalse(self.contract["population_contract"]["production_population_decided"])

    def test_contract_checkout_is_forced_to_lf(self) -> None:
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/provisional_resolution_evidence_contract_h5.json text eol=lf",
            attributes.splitlines(),
        )
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
