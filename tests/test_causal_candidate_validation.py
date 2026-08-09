from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

import numpy as np

from src.polyphonic.causal_candidate_fit import FitStandardizer
from src.polyphonic.causal_candidate_validation import (
    CausalCandidateGate,
    evaluate_preregistered_ab_decision,
    infer_once_then_decode_ab,
    load_sealed_validation_contract,
)
from src.polyphonic.decoder import PolyphonicDecoderConfig


class CausalCandidateValidationTests(unittest.TestCase):
    def _gate(self, probability: float, seen: list[np.ndarray] | None = None) -> CausalCandidateGate:
        def scorer(batch: np.ndarray) -> np.ndarray:
            if seen is not None:
                seen.append(np.asarray(batch).copy())
            return np.full((len(batch), 1), probability, dtype=np.float32)
        return CausalCandidateGate(
            standardizer=FitStandardizer((0.0,) * 5, (1.0,) * 5),
            scorer=scorer,
            threshold=0.31,
        )

    def test_shared_inference_is_called_once_and_decoders_diverge_only_after_gate(self) -> None:
        calls = 0
        seen: list[np.ndarray] = []
        def inference() -> dict[str, np.ndarray]:
            nonlocal calls
            calls += 1
            return {
                "frame": np.asarray([[0.9, 0.0]], dtype=np.float32),
                "onset": np.asarray([[0.9, 0.0]], dtype=np.float32),
                "harmonic_amplitude": np.zeros((1, 2, 1), dtype=np.float32),
            }
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=61, frame_on_threshold=0.5,
            strong_frame_threshold=0.8, frame_off_threshold=0.25,
            onset_threshold=0.5, activation_frames=1, release_frames=1,
            minimum_retrigger_frames=1, silence_release_frames=1,
            maximum_polyphony=2, harmonic_support_threshold=0.0,
            audio_onset_lookback_frames=1,
        )
        result = infer_once_then_decode_ab(
            transcription_inference=inference,
            config=config,
            audio_active=np.asarray([True]),
            audio_onset=np.asarray([True]),
            candidate_gate=self._gate(0.0, seen),
        )
        self.assertEqual(calls, 1)
        self.assertIsNot(result.reference_decoder, result.candidate_decoder)
        self.assertEqual(
            [(event.kind, event.pitch) for event in result.reference_events],
            [("note_on", 60), ("note_off", 60)],
        )
        self.assertEqual(result.candidate_events, ())
        self.assertEqual(len(seen), 1)
        # score is pre-ranking, the reason is model_onset, and active polyphony is zero.
        self.assertEqual(seen[0].shape, (1, 12))
        self.assertAlmostEqual(float(seen[0][0, 2]), 1.8)
        self.assertEqual(float(seen[0][0, 4]), 0.0)
        self.assertEqual(float(seen[0][0, 7]), 1.0)

    def test_preflight_rejects_artifact_mismatch_before_any_inference(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            bad_model = Path(directory) / "wrong.keras"
            bad_model.write_bytes(b"not the sealed model")
            with self.assertRaisesRegex(ValueError, "manifest SHA-256 mismatch"):
                load_sealed_validation_contract(
                    repository_root=root,
                    policy_path=root / "configs" / "causal_candidate_fit_v1_validation_ab_policy.json",
                    selection_path=root / "configs" / "causal_candidate_fit_v1_validation_selection_12.json",
                    model_path=bad_model,
                    standardizer_path=bad_model,
                    manifest_path=bad_model,
                    checkpoint_path=bad_model,
                    evaluation_config_path=bad_model,
                    decoder_config_path=bad_model,
                )

    def test_decision_fails_closed_for_non_finite_causal_latency(self) -> None:
        rules = {
            "candidate_false_positive_notes_delta_maximum": -1,
            "candidate_global_onset_recall_delta_minimum": -0.005,
            "candidate_global_onset_f1_delta_minimum": -0.002,
            "candidate_global_strictly_causal_recall_delta_minimum": -0.005,
            "candidate_strictly_causal_latency_p50_delta_hops_maximum": 1.0,
            "candidate_strictly_causal_latency_p90_delta_hops_maximum": 1.0,
            "causal_latency_hop_ms": 5.804988662131519,
            "candidate_retriggers_delta_maximum": 0,
            "candidate_excess_fragments_delta_maximum": 0,
            "candidate_per_corpus_onset_f1_delta_minimum": -0.01,
            "candidate_low_midi_40_51_onset_f1_delta_minimum": -0.01,
        }
        base = {
            "onset": {"false_positive_notes": 2, "recall": 1.0, "f1": 1.0},
            "strictly_causal_noteon": {"global": {"recall": 1.0, "latency_p50_ms": 1.0, "latency_p90_ms": 2.0}},
            "retriggers": 0,
            "diagnostics": {"excess_fragments": 0},
            "dataset_metrics": {"per_dataset": {"gaps_poly_mix": {"onset": {"f1": 1.0}}}},
            "low_midi_40_51": {"onset": {"f1": 1.0}},
        }
        candidate = {**base, "strictly_causal_noteon": {"global": {"recall": 1.0, "latency_p50_ms": float("nan"), "latency_p90_ms": 2.0}}}
        with self.assertRaisesRegex(ValueError, "non-finite metric"):
            evaluate_preregistered_ab_decision(reference=base, candidate=candidate, rules=rules)
