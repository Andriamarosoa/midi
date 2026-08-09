from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic.causal_candidate_fit import ENCODED_FEATURES


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "configs" / "causal_candidate_fit_v1_validation_selection_12.json"
POLICY_PATH = ROOT / "configs" / "causal_candidate_fit_v1_validation_ab_policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CausalCandidateValidationPreregistrationTests(unittest.TestCase):
    def test_selection_is_exactly_the_sealed_twelve_recording_validation_cohort(self) -> None:
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

        self.assertEqual(selection["schema_version"], 1)
        self.assertFalse(selection["locked_test_used"])
        self.assertEqual(
            selection["manifest_sha256"],
            "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7",
        )
        recordings = selection["recording_keys"]
        self.assertEqual(len(recordings), 12)
        self.assertEqual(len(set(recordings)), 12)
        self.assertEqual(
            {recording.split("|", 1)[0] for recording in recordings},
            {
                "gaps_poly_mix",
                "guitar_techs_poly_directinput",
                "guitar_techs_poly_micamp",
                "guitarset_poly_mix",
            },
        )
    def test_ab_policy_freezes_the_fitted_head_and_prohibits_new_scientific_work(self) -> None:
        selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(policy["schema_version"], 1)
        self.assertEqual(policy["status"], "preregistered_not_executed")
        self.assertFalse(policy["locked_test_used"])
        self.assertTrue(policy["historical_validation_used"])
        self.assertEqual(
            policy["validation_cohort"]["selection_sha256"],
            _sha256(SELECTION_PATH),
        )
        self.assertEqual(
            policy["validation_cohort"]["recording_count"],
            len(selection["recording_keys"]),
        )
        self.assertEqual(
            policy["fit_artifacts"]["model_sha256"],
            "b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e",
        )
        self.assertEqual(
            policy["fit_artifacts"]["standardizer_sha256"],
            "0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b",
        )
        self.assertEqual(policy["fit_artifacts"]["threshold"], 0.31)
        self.assertEqual(
            tuple(policy["fit_artifacts"]["feature_names"]),
            ENCODED_FEATURES,
        )

        contract = policy["ab_contract"]
        self.assertIsNone(contract["reference"]["causal_candidate_gate"])
        gate = contract["candidate"]["causal_candidate_gate"]
        self.assertEqual(gate["model_sha256"], policy["fit_artifacts"]["model_sha256"])
        self.assertEqual(
            gate["standardizer_sha256"],
            policy["fit_artifacts"]["standardizer_sha256"],
        )
        self.assertEqual(gate["threshold"], 0.31)
        self.assertTrue(contract["single_transcription_inference_per_recording"])
        self.assertTrue(contract["same_base_transcription_predictions"])
        self.assertTrue(contract["same_base_decoder_configuration"])
        self.assertTrue(
            contract["only_branch_specific_decoder_difference_is_causal_candidate_gate"]
        )
        self.assertTrue(contract["audio_evidence_override_forbidden"])
        self.assertTrue(contract["audio_evidence_computed_once_per_recording"])
        self.assertTrue(contract["same_audio_evidence_masks_reused_across_ab"])
        self.assertTrue(contract["independent_decoder_state_after_gate_decisions"])
        self.assertTrue(
            contract["candidate_features_computed_immediately_pre_gate_from_candidate_state"]
        )
        self.assertTrue(
            contract["candidate_head_must_not_change_reference_branch_or_base_inference"]
        )
        self.assertNotIn("candidate_head_must_reuse_the_same_pre_gate_candidates", contract)
        self.assertEqual(
            policy["decision_rules"][
                "candidate_strictly_causal_latency_p50_delta_hops_maximum"
            ],
            1.0,
        )
        self.assertEqual(
            policy["decision_rules"][
                "candidate_strictly_causal_latency_p90_delta_hops_maximum"
            ],
            1.0,
        )
        self.assertEqual(
            policy["decision_rules"]["causal_latency_hop_ms"],
            5.804988662131519,
        )
        self.assertTrue(
            policy["decision_rules"]["all_rules_must_pass_for_a_positive_ab_result"]
        )
        self.assertFalse(policy["decision_rules"]["automatic_promotion"])
        self.assertEqual(
            set(policy["forbidden_actions"]),
            {
                "fit",
                "recalibration",
                "threshold_search",
                "export",
                "live",
                "locked_test",
            },
        )
