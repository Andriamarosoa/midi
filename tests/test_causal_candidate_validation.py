from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from src.polyphonic.causal_candidate_fit import FitStandardizer
from src.polyphonic.causal_candidate_validation import (
    CausalCandidateGate,
    configure_sealed_validation_cpu_tensorflow,
    evaluate_preregistered_ab_decision,
    infer_once_then_decode_ab,
    load_sealed_validation_contract,
)
from src.polyphonic.decoder import (
    CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
    CAUSAL_CANDIDATE_GATE_PRE_RANKING,
    CausalCandidateGateInput,
    PolyphonicDecoderConfig,
)
from src.polyphonic.evaluate_events import (
    NoteInterval,
    aggregate_strictly_causal_noteon_metrics,
    build_strictly_causal_noteon_clip,
)


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
            candidate_gate_placement=CAUSAL_CANDIDATE_GATE_PRE_RANKING,
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

    def test_v2_ab_path_requires_explicit_known_placement_before_inference(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=60, frame_on_threshold=0.5,
            strong_frame_threshold=0.8, frame_off_threshold=0.25,
            onset_threshold=0.5, activation_frames=1, release_frames=1,
            minimum_retrigger_frames=1, silence_release_frames=1,
            maximum_polyphony=1, harmonic_support_threshold=0.0,
        )
        for placement, message in ((None, "requires an explicit candidate gate placement"), ("after_noteon", "requires an explicit known gate placement")):
            with self.subTest(placement=placement):
                calls = 0

                def inference() -> dict[str, np.ndarray]:
                    nonlocal calls
                    calls += 1
                    return {
                        "frame": np.asarray([[0.9]], dtype=np.float32),
                        "onset": np.asarray([[0.9]], dtype=np.float32),
                        "harmonic_amplitude": np.zeros((1, 1, 1), dtype=np.float32),
                    }

                with self.assertRaisesRegex(ValueError, message):
                    infer_once_then_decode_ab(
                        transcription_inference=inference,
                        config=config,
                        audio_active=np.asarray([True]),
                        audio_onset=np.asarray([True]),
                        candidate_gate=self._gate(0.0),
                        candidate_gate_placement=placement,
                    )
                self.assertEqual(calls, 0)

    def test_v2_ab_path_gates_only_selected_candidates_after_shared_inference(
        self,
    ) -> None:
        calls = 0
        seen: list[CausalCandidateGateInput] = []

        def inference() -> dict[str, np.ndarray]:
            nonlocal calls
            calls += 1
            return {
                "frame": np.asarray([[0.99, 0.90, 0.80]], dtype=np.float32),
                "onset": np.asarray([[0.99, 0.90, 0.80]], dtype=np.float32),
                "harmonic_amplitude": np.zeros((1, 3, 1), dtype=np.float32),
            }

        def reject_top(values: CausalCandidateGateInput) -> bool:
            seen.append(values)
            return values.candidate_score > 1.9

        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=62, frame_on_threshold=0.5,
            strong_frame_threshold=0.8, frame_off_threshold=0.25,
            onset_threshold=0.5, activation_frames=1, release_frames=1,
            minimum_retrigger_frames=1, silence_release_frames=1,
            maximum_polyphony=2, harmonic_support_threshold=0.0,
        )
        result = infer_once_then_decode_ab(
            transcription_inference=inference,
            config=config,
            audio_active=np.asarray([True]),
            audio_onset=np.asarray([True]),
            candidate_gate=reject_top,
            candidate_gate_placement=(
                CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
            ),
        )

        self.assertEqual(calls, 1)
        self.assertEqual(
            [event.pitch for event in result.reference_events if event.kind == "note_on"],
            [60, 61],
        )
        self.assertEqual(
            [event.pitch for event in result.candidate_events if event.kind == "note_on"],
            [61],
        )
        self.assertEqual(
            [round(values.candidate_score, 2) for values in seen], [1.98, 1.8],
        )

    def test_preflight_rejects_artifact_mismatch_before_any_inference(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            bad_model = Path(directory) / "wrong.keras"
            bad_model.write_bytes(b"not the sealed model")
            with self.assertRaisesRegex(ValueError, "fit_report SHA-256 mismatch"):
                load_sealed_validation_contract(
                    repository_root=root,
                    policy_path=root / "configs" / "causal_candidate_fit_v1_validation_ab_policy.json",
                    selection_path=root / "configs" / "causal_candidate_fit_v1_validation_selection_12.json",
                    fit_report_path=bad_model,
                    model_path=bad_model,
                    standardizer_path=bad_model,
                    manifest_path=bad_model,
                    checkpoint_path=bad_model,
                    evaluation_config_path=bad_model,
                    decoder_config_path=bad_model,
                )

    def test_cpu_preflight_rejects_missing_worker_acknowledgement(self) -> None:
        # The environment guard is intentionally evaluated before TensorFlow
        # can be imported.  This keeps a manually invoked module fail-closed.
        with mock.patch.dict("os.environ", {"MIDI_FORCE_CPU": "0"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "MIDI_FORCE_CPU=1"):
                configure_sealed_validation_cpu_tensorflow()

    def test_decision_uses_real_causal_aggregate_schema(self) -> None:
        rules = {
            "candidate_false_positive_notes_delta_maximum": 0,
            "candidate_global_onset_recall_delta_minimum": 0,
            "candidate_global_onset_f1_delta_minimum": 0,
            "candidate_global_strictly_causal_recall_delta_minimum": 0,
            "candidate_strictly_causal_latency_p50_delta_hops_maximum": 1.0,
            "candidate_strictly_causal_latency_p90_delta_hops_maximum": 1.0,
            "causal_latency_hop_ms": 5.804988662131519,
            "candidate_retriggers_delta_maximum": 0,
            "candidate_excess_fragments_delta_maximum": 0,
            "candidate_per_corpus_onset_f1_delta_minimum": 0,
            "candidate_low_midi_40_51_onset_f1_delta_minimum": 0,
        }
        clip, _ = build_strictly_causal_noteon_clip(
            [NoteInterval(60, 0.0, 0.1)],
            [NoteInterval(60, 0.01, 0.11)],
            clip_id="synthetic", corpus_id="gaps_poly_mix", duration_s=0.2,
        )
        causal = aggregate_strictly_causal_noteon_metrics([clip])
        self.assertIn("recall_within_max_latency", causal["global"])
        self.assertNotIn("recall", causal["global"])
        base = {
            "onset": {"false_positive_notes": 2, "recall": 1.0, "f1": 1.0},
            "strictly_causal_noteon": causal,
            "retriggers": 0,
            "diagnostics": {"excess_fragments": 0},
            "dataset_metrics": {"per_dataset": {"gaps_poly_mix": {"onset": {"f1": 1.0}}}},
            "low_midi_40_51": {"onset": {"f1": 1.0}},
        }
        self.assertTrue(
            evaluate_preregistered_ab_decision(
                reference=base, candidate=base, rules=rules,
            )["all_rules_passed"]
        )
        candidate = {
            **base,
            "strictly_causal_noteon": {
                **causal,
                "global": {
                    **causal["global"],
                    "latency_p50_ms": float("nan"),
                },
            },
        }
        with self.assertRaisesRegex(ValueError, "non-finite metric"):
            evaluate_preregistered_ab_decision(reference=base, candidate=candidate, rules=rules)
