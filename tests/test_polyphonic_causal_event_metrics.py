from __future__ import annotations

import json
import unittest

from src.polyphonic.causal_event_metrics import (
    CausalMetricGate,
    ClipNoteOnData,
    NoteOnPrediction,
    ReferenceNote,
    causal_metrics_summary,
    evaluate_causal_event_metrics,
    match_causal_note_ons,
    reference_context_masks,
)


def _reference(
    pitch: int,
    start_s: float,
    end_s: float | None = None,
) -> ReferenceNote:
    return ReferenceNote(
        pitch=pitch,
        start_s=start_s,
        end_s=start_s + 0.25 if end_s is None else end_s,
    )


def _prediction(pitch: int, time_s: float) -> NoteOnPrediction:
    return NoteOnPrediction(pitch=pitch, time_s=time_s)


class CausalNoteOnMatcherTests(unittest.TestCase):
    def test_prediction_before_reference_is_never_matched(self) -> None:
        result = match_causal_note_ons(
            [_reference(60, 0.100)],
            [_prediction(60, 0.099)],
        )

        self.assertEqual(result.matches, ())
        self.assertEqual(result.missed_reference_indices, (0,))
        self.assertEqual(result.false_prediction_indices, (0,))

    def test_latest_causal_same_pitch_reference_wins(self) -> None:
        reference = [
            _reference(60, 0.000, 0.080),
            _reference(60, 0.100, 0.300),
        ]
        result = match_causal_note_ons(
            reference,
            [_prediction(60, 0.110), _prediction(60, 0.120)],
        )

        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.matches[0].reference_index, 1)
        self.assertAlmostEqual(result.matches[0].latency_ms, 10.0)
        self.assertEqual(result.missed_reference_indices, (0,))
        self.assertEqual(result.false_prediction_indices, (1,))

    def test_matching_is_one_to_one_and_maximum_latency_is_inclusive(self) -> None:
        result = match_causal_note_ons(
            [_reference(60, 0.0)],
            [_prediction(60, 0.250), _prediction(60, 0.251)],
            max_latency_ms=250.0,
        )

        self.assertEqual(len(result.matches), 1)
        self.assertAlmostEqual(result.matches[0].latency_ms, 250.0)
        self.assertEqual(result.false_prediction_indices, (1,))


class CausalNoteOnMetricTests(unittest.TestCase):
    def test_all_deadline_boundaries_and_latency_percentiles(self) -> None:
        delays_ms = (12.0, 18.0, 24.0, 35.0, 46.0)
        reference = [
            _reference(60 + index, 0.0) for index in range(len(delays_ms))
        ]
        predictions = [
            _prediction(60 + index, delay / 1000.0)
            for index, delay in enumerate(delays_ms)
        ]

        summary, result = causal_metrics_summary(
            reference, predictions, duration_s=1.0
        )

        self.assertEqual(len(result.matches), 5)
        self.assertEqual(
            summary["recall_at_ms"],
            {"12": 0.2, "18": 0.4, "24": 0.6, "35": 0.8, "46": 1.0},
        )
        self.assertAlmostEqual(summary["latency_p50_ms"], 24.0)
        self.assertAlmostEqual(summary["latency_p90_ms"], 41.6)

    def test_context_false_rate_same_pitch_and_octave_metrics(self) -> None:
        reference = [
            _reference(60, 0.000, 0.300),
            _reference(64, 0.000, 0.300),
            _reference(60, 0.350, 0.600),
        ]
        predictions = [
            _prediction(60, 0.010),
            _prediction(72, 0.020),  # octave-up false NoteOn
            _prediction(60, 0.370),
        ]

        masks = reference_context_masks(reference)
        summary, _ = causal_metrics_summary(
            reference, predictions, duration_s=120.0
        )

        self.assertEqual(masks["polyphonic"], (True, True, False))
        self.assertEqual(masks["monophonic"], (False, False, True))
        self.assertEqual(masks["same_pitch_close"], (False, False, True))
        self.assertEqual(summary["false_noteons"], 1)
        self.assertAlmostEqual(summary["false_noteons_per_min"], 0.5)
        self.assertEqual(summary["octave_error_false_noteons"], 1)
        self.assertEqual(summary["octave_up_false_noteons"], 1)
        self.assertEqual(summary["octave_down_false_noteons"], 0)
        self.assertAlmostEqual(
            summary["contexts"]["polyphonic"]["recall_at_ms"]["24"], 0.5
        )
        self.assertAlmostEqual(
            summary["contexts"]["monophonic"]["recall_at_ms"]["24"], 1.0
        )
        self.assertAlmostEqual(
            summary["contexts"]["same_pitch_close"]["recall_at_ms"]["24"],
            1.0,
        )

    def test_empty_context_is_reported_as_unsupported(self) -> None:
        summary, _ = causal_metrics_summary(
            [_reference(60, 0.0)],
            [_prediction(60, 0.01)],
            duration_s=1.0,
        )

        self.assertEqual(
            summary["contexts"]["polyphonic"]["reference_noteons"], 0
        )
        self.assertIsNone(
            summary["contexts"]["polyphonic"]["recall_at_ms"]["24"]
        )


class CausalNoteOnAggregationAndGateTests(unittest.TestCase):
    @staticmethod
    def _clips() -> list[ClipNoteOnData]:
        return [
            ClipNoteOnData(
                clip_id="a1",
                corpus_id="A",
                duration_s=60.0,
                reference=[_reference(60, 0.0)],
                predictions=[_prediction(60, 0.010)],
            ),
            ClipNoteOnData(
                clip_id="a2",
                corpus_id="A",
                duration_s=60.0,
                reference=[_reference(61, 0.0)],
                predictions=[],
            ),
            ClipNoteOnData(
                clip_id="b1",
                corpus_id="B",
                duration_s=120.0,
                reference=[_reference(62, 0.0)],
                predictions=[
                    _prediction(62, 0.035),
                    _prediction(70, 0.500),
                ],
            ),
        ]

    def test_micro_aggregation_is_clip_local_and_duration_weighted(self) -> None:
        report = evaluate_causal_event_metrics(
            list(reversed(self._clips()))
        )

        self.assertEqual(
            [row["clip_id"] for row in report["per_clip"]],
            ["a1", "a2", "b1"],
        )
        self.assertEqual(report["aggregate"]["reference_noteons"], 3)
        self.assertEqual(report["aggregate"]["matched_noteons"], 2)
        self.assertEqual(report["aggregate"]["false_noteons"], 1)
        self.assertAlmostEqual(
            report["aggregate"]["false_noteons_per_min"], 0.25
        )
        self.assertAlmostEqual(
            report["aggregate"]["recall_at_ms"]["24"], 1.0 / 3.0
        )
        self.assertAlmostEqual(
            report["by_corpus"]["A"]["recall_at_ms"]["24"], 0.5
        )
        self.assertAlmostEqual(
            report["by_corpus"]["B"]["recall_at_ms"]["24"], 0.0
        )
        self.assertEqual(
            report["worst"]["clip"]["recall_at_ms"]["24"]["clip_id"],
            "a2",
        )
        self.assertEqual(
            report["worst"]["corpus"]["recall_at_ms"]["24"]["corpus_id"],
            "B",
        )
        # The complete report must be directly serializable for automation.
        json.dumps(report, sort_keys=True)

    def test_gate_passes_all_configured_aggregate_and_tail_checks(self) -> None:
        gate = CausalMetricGate(
            minimum_recall_at_ms={24.0: 0.30, 35.0: 0.60},
            maximum_latency_p90_ms=40.0,
            maximum_false_noteons_per_min=0.25,
            minimum_context_recall_at_ms={"monophonic": {24.0: 0.0}},
            maximum_octave_error_rate=0.0,
            minimum_worst_clip_recall_at_ms={24.0: 0.0},
            minimum_worst_corpus_recall_at_ms={24.0: 0.0},
            maximum_worst_clip_false_noteons_per_min=0.5,
            maximum_worst_corpus_false_noteons_per_min=0.5,
        )

        report = evaluate_causal_event_metrics(self._clips(), gate=gate)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["gate"]["failed_checks"], [])
        self.assertEqual(report["gate"]["configured_checks"], 10)

    def test_gate_exposes_worst_clip_and_corpus_failures(self) -> None:
        gate = CausalMetricGate(
            minimum_worst_clip_recall_at_ms={24.0: 0.10},
            minimum_worst_corpus_recall_at_ms={24.0: 0.10},
            maximum_worst_clip_false_noteons_per_min=0.49,
        )

        report = evaluate_causal_event_metrics(self._clips(), gate=gate)
        gate_report = report["gate"]

        self.assertFalse(gate_report["passed"])
        self.assertEqual(
            gate_report["failed_checks"],
            [
                "worst_clip.recall_at_24ms",
                "worst_corpus.recall_at_24ms",
                "worst_clip.false_noteons_per_min",
            ],
        )
        self.assertEqual(
            gate_report["checks"][0]["scope"],
            {"corpus_id": "A", "clip_id": "a2"},
        )

    def test_gate_fails_when_a_configured_context_has_no_support(self) -> None:
        clips = [
            ClipNoteOnData(
                clip_id="mono",
                corpus_id="A",
                duration_s=1.0,
                reference=[_reference(60, 0.0)],
                predictions=[_prediction(60, 0.010)],
            )
        ]
        gate = CausalMetricGate(
            minimum_context_recall_at_ms={"polyphonic": {24.0: 0.0}}
        )

        report = evaluate_causal_event_metrics(clips, gate=gate)

        self.assertFalse(report["gate"]["passed"])
        self.assertIsNone(report["gate"]["checks"][0]["value"])

    def test_invalid_scope_and_gate_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duration_s must be positive"):
            ClipNoteOnData("clip", "corpus", 0.0, [], [])
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            CausalMetricGate(minimum_recall_at_ms={24.0: 1.1})
        with self.assertRaisesRegex(ValueError, "no greater"):
            evaluate_causal_event_metrics(
                self._clips(), max_latency_ms=35.0
            )

    def test_gate_reports_its_effective_check_count(self) -> None:
        self.assertEqual(CausalMetricGate().configured_check_count(), 0)
        self.assertEqual(
            CausalMetricGate(
                minimum_recall_at_ms={24.0: 0.5},
                minimum_context_recall_at_ms={
                    "polyphonic": {12.0: 0.1, 24.0: 0.2},
                },
                maximum_latency_p90_ms=50.0,
            ).configured_check_count(),
            4,
        )


if __name__ == "__main__":
    unittest.main()
