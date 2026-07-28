from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PolyphonicDesktopContractTests(unittest.TestCase):
    def test_live_and_transcribe_default_to_the_validated_v22_bundle(self) -> None:
        for relative in (
            "src/polyphonic/live.py",
            "src/polyphonic/transcribe.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("artifacts/guitar_midi_polyphonic_v2_2_0", source)
            self.assertNotIn("artifacts/guitar_midi_polyphonic_v2_0_0", source)

    def test_live_accepts_the_benchmarked_three_thread_runtime(self) -> None:
        source = (ROOT / "src/polyphonic/live.py").read_text(encoding="utf-8")
        self.assertIn("choices=(1, 2, 3, 4)", source)

    def test_live_exposes_explicit_synthetic_calibration_candidate(self) -> None:
        source = (ROOT / "src/polyphonic/live.py").read_text(encoding="utf-8")

        self.assertIn('"--synthetic-calibration"', source)
        self.assertIn("audio_evidence_policy.prime_silence()", source)
        self.assertIn('"synthetic_calibration": bool(', source)

    def test_batch_launcher_targets_the_polyphonic_live_module(self) -> None:
        launcher = (ROOT / "START_LIVE_POLYPHONIC.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn("-m src.polyphonic.live", launcher)

    def test_unvalidated_auto_level_is_opt_in_and_amplification_only(self) -> None:
        metadata = json.loads((
            ROOT
            / "artifacts"
            / "guitar_midi_polyphonic_v2_2_0"
            / "metadata.json"
        ).read_text(encoding="utf-8"))
        policy = metadata["automatic_model_input_level"]

        self.assertFalse(policy["enabled_by_default"])
        self.assertEqual(policy["minimum_gain_db"], 0.0)
        self.assertEqual(policy["session_policy"], "amplification_only_opt_in")
        self.assertTrue(policy["safety_attenuation_enabled"])

    def test_unattacked_frame_threshold_is_an_accepted_runtime_policy(self) -> None:
        artifact = (
            ROOT
            / "artifacts"
            / "guitar_midi_polyphonic_v2_2_0"
        )
        metadata = json.loads(
            (artifact / "metadata.json").read_text(encoding="utf-8")
        )
        policy = metadata["decoder_runtime_policy"]
        acceptance = json.loads(
            (artifact / policy["acceptance_report"]).read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(policy["unattacked_frame_threshold_enforced"])
        self.assertFalse(policy["locked_test_used"])
        self.assertEqual(acceptance["decision"], "accepted_for_desktop")
        self.assertLess(
            acceptance["twelve_recording_coverage_confirmation"][
                "false_positive_notes_delta"
            ],
            0,
        )

    def test_recoverable_overload_preserves_active_polyphonic_notes(self) -> None:
        source = (ROOT / "src/polyphonic/live.py").read_text(encoding="utf-8")

        self.assertEqual(source.count("decoder.reset_observation_continuity()"), 3)
        self.assertIn('"preserved_active_notes": list(preserved_notes)', source)
        self.assertIn("decoder.panic()", source)

    def test_stable_bundle_declares_bounded_release_graces(self) -> None:
        metadata = json.loads((
            ROOT
            / "artifacts"
            / "guitar_midi_polyphonic_v2_2_0"
            / "metadata.json"
        ).read_text(encoding="utf-8"))
        decoder = metadata["decoder"]
        policy = metadata["live_continuity_policy"]

        self.assertEqual(decoder["recovery_release_grace_frames"], 4)
        self.assertEqual(decoder["chord_release_grace_frames"], 6)
        self.assertEqual(decoder["chord_formation_frames"], 21)
        self.assertTrue(policy["recoverable_overload_preserves_active_notes"])
        self.assertTrue(
            policy["independent_chord_onsets_receive_release_grace"]
        )
        self.assertTrue(policy["causal_chord_formation_memory"])
        self.assertEqual(policy["decision"], "candidate_pending_live_validation")
        self.assertFalse(policy["locked_test_used"])


if __name__ == "__main__":
    unittest.main()
