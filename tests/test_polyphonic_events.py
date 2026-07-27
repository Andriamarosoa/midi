from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from src.polyphonic.causal_event_metrics import CausalMetricGate
from src.polyphonic.data import ManifestItem
from src.polyphonic.decoder import PolyphonicDecoderConfig, PolyphonicMidiEvent
from src.polyphonic.evaluate_events import (
    NoteInterval,
    _audio_duration_s,
    aggregate_dataset_note_metrics,
    aggregate_strictly_causal_noteon_metrics,
    build_strictly_causal_noteon_clip,
    decode_probabilities,
    events_to_notes,
    match_notes,
    note_metrics,
    select_evaluation_recordings,
)


class PolyphonicEventEvaluationTests(unittest.TestCase):
    def test_strictly_causal_metrics_do_not_replace_historical_matching(self) -> None:
        reference = [NoteInterval(60, 0.100, 0.500)]
        early_prediction = [NoteInterval(60, 0.099, 0.400)]

        historical = match_notes(reference, early_prediction)
        _clip, causal = build_strictly_causal_noteon_clip(
            reference,
            early_prediction,
            clip_id="early",
            corpus_id="synthetic",
            duration_s=1.0,
        )

        self.assertEqual(historical, [(0, 0)])
        self.assertEqual(causal["matched_noteons"], 0)
        self.assertEqual(causal["missed_noteons"], 1)
        self.assertEqual(causal["false_noteons"], 1)
        self.assertEqual(causal["recall_at_24ms"], 0.0)

    def test_strict_causal_aggregation_is_global_and_per_corpus(self) -> None:
        first, first_metrics = build_strictly_causal_noteon_clip(
            [NoteInterval(60, 0.0, 0.5)],
            [NoteInterval(60, 0.010, 0.5)],
            clip_id="a",
            corpus_id="corpus_a",
            duration_s=60.0,
        )
        second, second_metrics = build_strictly_causal_noteon_clip(
            [],
            [NoteInterval(72, 0.5, 0.8)],
            clip_id="b",
            corpus_id="corpus_b",
            duration_s=120.0,
        )

        report = aggregate_strictly_causal_noteon_metrics([second, first])

        self.assertTrue(report["available"])
        self.assertEqual(first_metrics["matched_noteons"], 1)
        self.assertEqual(second_metrics["false_noteons"], 1)
        self.assertEqual(report["global"]["duration_s"], 180.0)
        self.assertEqual(report["global"]["matched_noteons"], 1)
        self.assertEqual(report["global"]["false_noteons"], 1)
        self.assertAlmostEqual(
            report["global"]["false_noteons_per_min"], 1.0 / 3.0,
        )
        self.assertEqual(
            sorted(report["by_corpus"]), ["corpus_a", "corpus_b"]
        )
        self.assertAlmostEqual(
            report["by_corpus"]["corpus_b"]["false_noteons_per_min"],
            0.5,
        )

    def test_strict_causal_aggregation_exposes_configured_gate(self) -> None:
        clip, _metrics = build_strictly_causal_noteon_clip(
            [NoteInterval(60, 0.0, 0.5)],
            [NoteInterval(60, 0.010, 0.5)],
            clip_id="gate",
            corpus_id="synthetic",
            duration_s=60.0,
        )

        report = aggregate_strictly_causal_noteon_metrics(
            [clip],
            gate=CausalMetricGate(
                minimum_recall_at_ms={24.0: 1.0},
                maximum_false_noteons_per_min=0.0,
            ),
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["gate"]["configured_checks"], 2)

    def test_custom_causal_deadline_is_available_per_recording(self) -> None:
        _clip, metrics = build_strictly_causal_noteon_clip(
            [NoteInterval(60, 0.0, 0.5)],
            [NoteInterval(60, 0.030, 0.5)],
            clip_id="custom",
            corpus_id="synthetic",
            duration_s=1.0,
            recall_deadlines_ms=(30.0,),
        )

        self.assertEqual(metrics["recall_at_30ms"], 1.0)

    def test_audio_duration_uses_real_sample_count(self) -> None:
        self.assertEqual(
            _audio_duration_s(np.zeros(44_100, np.float32), 44_100),
            1.0,
        )

    def test_decoder_replay_uses_audio_activity_without_label_leakage(self) -> None:
        frame = np.full((2, 1), 0.95, np.float32)
        onset = np.full((2, 1), 0.95, np.float32)
        harmonic = np.zeros((2, 1, 1), np.float32)
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=60, maximum_polyphony=1,
        )

        muted, _ = decode_probabilities(
            frame, onset, harmonic, config, sample_rate=100, hop_size=10,
            audio_active=np.zeros(2, np.bool_),
        )
        audible, _ = decode_probabilities(
            frame, onset, harmonic, config, sample_rate=100, hop_size=10,
            audio_active=np.ones(2, np.bool_),
        )

        self.assertEqual(muted, [])
        self.assertEqual([note.pitch for note in audible], [60])

    @staticmethod
    def _item(
        dataset: str,
        group: str,
        source: str,
        split: str = "validation",
    ) -> ManifestItem:
        return ManifestItem(
            source_id=source,
            dataset_id=dataset,
            player_id="player",
            group_id=group,
            split=split,
            audio_path=Path(f"{source}.wav"),
            audio_member="",
            labels_path=Path(f"{source}.npz"),
            capture_id="capture",
            license_id="test",
        )

    @staticmethod
    def _counts(true_positive: int, false_positive: int, missing: int) -> dict:
        estimated = true_positive + false_positive
        reference = true_positive + missing
        precision = true_positive / max(estimated, 1)
        recall = true_positive / max(reference, 1)
        return {
            "reference_notes": reference,
            "estimated_notes": estimated,
            "matched_notes": true_positive,
            "false_positive_notes": false_positive,
            "missing_notes": missing,
            "precision": precision,
            "recall": recall,
            "f1": 2.0 * precision * recall / max(precision + recall, 1e-12),
        }

    def test_events_are_paired_globally_by_pitch(self) -> None:
        notes = events_to_notes([
            PolyphonicMidiEvent("note_on", 60, 100, 0),
            PolyphonicMidiEvent("note_on", 64, 100, 0),
            PolyphonicMidiEvent("note_off", 60, 0, 4),
            PolyphonicMidiEvent("note_off", 64, 0, 5),
        ], sample_rate=100, hop_size=10, final_frame=5)
        self.assertEqual([note.pitch for note in notes], [60, 64])
        self.assertAlmostEqual(notes[0].start_s, 0.1)
        self.assertAlmostEqual(notes[0].end_s, 0.5)

    def test_inverse_matching_reports_ghosts_and_missing_notes(self) -> None:
        reference = [
            NoteInterval(60, 0.0, 1.0),
            NoteInterval(64, 0.0, 1.0),
        ]
        estimated = [
            NoteInterval(60, 0.02, 1.01),
            NoteInterval(67, 0.0, 1.0),
        ]
        matches = match_notes(reference, estimated)
        metrics = note_metrics(reference, estimated, matches)
        self.assertEqual(metrics["matched_notes"], 1)
        self.assertEqual(metrics["false_positive_notes"], 1)
        self.assertEqual(metrics["missing_notes"], 1)
        self.assertAlmostEqual(metrics["f1"], 0.5)

    def test_limited_selection_balances_datasets(self) -> None:
        items = [
            self._item(dataset, f"{dataset}-g{index}", f"{dataset}-s{index}")
            for dataset in ("a", "b", "c")
            for index in range(4)
        ]
        selected = select_evaluation_recordings(
            items, "validation", maximum_recordings=7,
        )
        counts = {
            dataset: sum(item.dataset_id == dataset for item in selected)
            for dataset in ("a", "b", "c")
        }
        self.assertEqual(counts, {"a": 3, "b": 2, "c": 2})

    def test_selection_is_independent_of_manifest_order(self) -> None:
        items = [
            self._item(dataset, group, f"{dataset}-{group}")
            for dataset in ("gaps", "guitarset", "techs")
            for group in ("g3", "g1", "g2")
        ]
        forward = select_evaluation_recordings(items, "validation", 5)
        reverse = select_evaluation_recordings(
            list(reversed(items)), "validation", 5,
        )
        self.assertEqual(
            [(item.dataset_id, item.group_id, item.source_id) for item in forward],
            [(item.dataset_id, item.group_id, item.source_id) for item in reverse],
        )

    def test_shared_capture_groups_are_diversified_globally(self) -> None:
        items = [
            self._item(dataset, group, f"{dataset}-{group}")
            for dataset in ("techs_direct", "techs_mic")
            for group in (
                "performance_1", "performance_2",
                "performance_3", "performance_4",
            )
        ]
        selected = select_evaluation_recordings(items, "validation", 4)
        self.assertEqual(len({item.group_id for item in selected}), 4)
        self.assertEqual(
            {
                dataset: sum(item.dataset_id == dataset for item in selected)
                for dataset in ("techs_direct", "techs_mic")
            },
            {"techs_direct": 2, "techs_mic": 2},
        )

    def test_split_and_dataset_filters_are_applied_before_selection(self) -> None:
        items = [
            self._item("wanted", "validation_group", "validation_source"),
            self._item("other", "other_group", "other_source"),
            self._item("wanted", "train_group", "train_source", split="train"),
            self._item("wanted", "test_group", "test_source", split="test"),
        ]
        selected = select_evaluation_recordings(
            items, "validation", maximum_recordings=3, dataset_id="wanted",
        )
        self.assertEqual(
            [(item.split, item.dataset_id, item.source_id) for item in selected],
            [("validation", "wanted", "validation_source")],
        )

    def test_maximum_recordings_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            select_evaluation_recordings([], "validation", 0)

    def test_dataset_aggregation_prevents_long_source_domination(self) -> None:
        strong = self._counts(45, 5, 5)
        weak = self._counts(1, 9, 9)
        reports = [
            {
                "dataset_id": "long",
                "onset": strong,
                "onset_offset": strong,
                "retriggers": 2,
            },
            {
                "dataset_id": "long",
                "onset": strong,
                "onset_offset": strong,
                "retriggers": 3,
            },
            {
                "dataset_id": "short",
                "onset": weak,
                "onset_offset": weak,
                "retriggers": 1,
            },
        ]
        result = aggregate_dataset_note_metrics(
            reports, {"long": 0.25, "short": 0.75},
        )
        self.assertEqual(
            result["per_dataset"]["long"]["onset"]["matched_notes"], 90,
        )
        self.assertEqual(result["per_dataset"]["long"]["retriggers"], 5)
        self.assertAlmostEqual(result["per_dataset"]["long"]["onset"]["f1"], 0.9)
        self.assertAlmostEqual(result["per_dataset"]["short"]["onset"]["f1"], 0.1)
        self.assertAlmostEqual(result["macro"]["onset"]["f1"], 0.5)
        self.assertAlmostEqual(result["weighted"]["onset"]["f1"], 0.3)
        self.assertEqual(
            result["weighted"]["effective_weights"],
            {"long": 0.25, "short": 0.75},
        )

    def test_weighted_dataset_score_requires_complete_configured_coverage(self) -> None:
        reports = [{
            "dataset_id": "present",
            "onset": self._counts(8, 2, 2),
            "onset_offset": self._counts(7, 3, 3),
            "retriggers": 0,
        }]

        result = aggregate_dataset_note_metrics(
            reports,
            {"present": 0.55, "missing": 0.45},
        )

        self.assertFalse(result["weighted"]["available"])
        self.assertEqual(
            result["weighted"]["missing_configured_datasets"],
            ["missing"],
        )
        self.assertAlmostEqual(
            result["weighted"]["configured_weight_coverage"],
            0.55,
        )

    def test_weighted_dataset_score_rejects_unconfigured_selected_dataset(self) -> None:
        reports = [
            {
                "dataset_id": dataset,
                "onset": self._counts(8, 2, 2),
                "onset_offset": self._counts(7, 3, 3),
                "retriggers": 0,
            }
            for dataset in ("configured", "unexpected")
        ]

        result = aggregate_dataset_note_metrics(
            reports,
            {"configured": 1.0},
        )

        self.assertFalse(result["weighted"]["available"])
        self.assertEqual(
            result["weighted"]["missing_selected_datasets"],
            ["unexpected"],
        )

    def test_zero_weight_dataset_does_not_require_validation_presence(self) -> None:
        reports = [{
            "dataset_id": "present",
            "onset": self._counts(8, 2, 2),
            "onset_offset": self._counts(7, 3, 3),
            "retriggers": 0,
        }]

        result = aggregate_dataset_note_metrics(
            reports,
            {"present": 1.0, "unused": 0.0},
        )

        self.assertTrue(result["weighted"]["available"])
        self.assertEqual(
            result["weighted"]["missing_configured_datasets"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
