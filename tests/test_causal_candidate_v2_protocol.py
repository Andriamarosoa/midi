from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic import (
    V2_DIAGNOSTIC_PROTOCOL_SHA256,
)


class CausalCandidateV2ProtocolTests(unittest.TestCase):
    def test_train_only_dev_diagnostic_is_frozen_and_non_promotional(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol_path = (
            root / "configs" / "causal_candidate_fit_v2_train_dev_diagnostic_protocol.json"
        )
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

        self.assertEqual(
            protocol["status"], "sealed_runner_implemented_pending_external_review"
        )
        self.assertIs(protocol["locked_test_used"], False)
        self.assertEqual(protocol["cohort"]["manifest_split"], "train")
        self.assertEqual(protocol["cohort"]["partition"], "dev")
        self.assertEqual(protocol["cohort"]["historical_validation_recordings_used"], 0)
        self.assertEqual(
            protocol["cohort"]["classification"],
            "train_only_exploratory_non_promotional",
        )
        selection = protocol["cohort"]["selection_source"]
        self.assertEqual(selection["recording_count"], 30)
        self.assertEqual(sum(selection["recordings_per_dataset"].values()), 30)
        self.assertEqual(
            selection["recordings_per_dataset"],
            {
                "gaps_poly_mix": 6,
                "guitar_techs_poly_directinput": 6,
                "guitar_techs_poly_micamp": 6,
                "guitarset_poly_mix": 12,
            },
        )
        v3_path = root / selection["sealed_v3_policy_relative_path"]
        self.assertEqual(
            hashlib.sha256(v3_path.read_bytes()).hexdigest(),
            selection["sealed_v3_policy_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
            V2_DIAGNOSTIC_PROTOCOL_SHA256,
        )

    def test_v2_diagnostic_freezes_the_only_experimental_change(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads((
            root / "configs" / "causal_candidate_fit_v2_train_dev_diagnostic_protocol.json"
        ).read_text(encoding="utf-8"))

        candidate = protocol["decoder_ab_contract"]["candidate"]
        self.assertEqual(
            candidate["causal_candidate_gate_placement"],
            "post_ranking_pre_noteon",
        )
        self.assertEqual(candidate["threshold"], 0.31)
        self.assertEqual(
            candidate["head_and_standardizer"], "exactly_frozen_v1_artifacts"
        )
        self.assertTrue(candidate["selected_population_only"])
        self.assertFalse(candidate["same_hop_backfill_after_rejection"])
        self.assertFalse(protocol["decision_policy"]["automatic_promotion"])
        self.assertFalse(protocol["decision_policy"]["threshold_or_model_selection"])
        self.assertFalse(protocol["decision_policy"]["historical_validation_reuse"])


if __name__ == "__main__":
    unittest.main()
