from dataclasses import fields
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from src.polyphonic.decoder_candidate_mining import (
    CANDIDATE_REASON_ENCODING,
    CANDIDATE_REASON_VOCABULARY,
    CAUSAL_FEATURES,
    POST_GATE_METADATA_FIELDS,
    PROVENANCE_FIELDS,
    DecoderCandidateAttempt,
    DecoderCandidateBatch,
    DecoderCandidateCollector,
    select_trainable_emitted_events,
)
from src.polyphonic.decoder_candidate_provenance import (
    build_decoder_candidate_partition_plan_from_snapshot,
    validate_decoder_candidate_partition_plan_against_snapshot,
)
from src.polyphonic.data import load_manifest_snapshot
from src.polyphonic.decoder_reason_codes import NOTE_ON_REASON_CODES


class CandidateMiningContractTests(unittest.TestCase):
    @staticmethod
    def manifest_item(**overrides) -> SimpleNamespace:
        values = dict(
            source_id="source",
            dataset_id="corpus",
            player_id="player",
            group_id="group",
            capture_id="capture",
            split="train",
        )
        values.update(overrides)
        return SimpleNamespace(**values)

    @classmethod
    def collector(
        cls,
        *,
        maximum_attempts: int = 4096,
        seed: int = 47,
        **overrides,
    ) -> DecoderCandidateCollector:
        item = cls.manifest_item(**overrides)
        items = [
            item,
            cls.manifest_item(
                source_id="second-source",
                dataset_id=item.dataset_id,
                group_id="second-group",
                capture_id="second-capture",
            ),
            cls.manifest_item(
                source_id="third-source",
                dataset_id=item.dataset_id,
                group_id="third-group",
                capture_id="third-capture",
            ),
        ]
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.csv"
            fields = (
                "source_id", "dataset_id", "player_id", "group_id",
                "capture_id", "split", "audio_path", "audio_member",
                "labels_path", "license_id",
            )
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for candidate in items:
                    row = {
                        field: getattr(candidate, field) for field in fields
                        if hasattr(candidate, field)
                    }
                    row.update({
                        "audio_path": str(Path(temporary) / f"{candidate.source_id}.wav"),
                        "audio_member": "",
                        "labels_path": str(Path(temporary) / f"{candidate.source_id}.npz"),
                        "license_id": "unit-test",
                    })
                    writer.writerow(row)
            snapshot = load_manifest_snapshot(path)
            plan = build_decoder_candidate_partition_plan_from_snapshot(
                snapshot, seed=seed
            )
            validated = validate_decoder_candidate_partition_plan_against_snapshot(
                plan, snapshot
            )
        return DecoderCandidateCollector(
            validated_snapshot=validated,
            manifest_item=snapshot.items[0],
            maximum_attempts=maximum_attempts,
        )

    @staticmethod
    def row(**overrides) -> DecoderCandidateAttempt:
        values = dict(
            source_id="source",
            dataset_id="corpus",
            group_id="group",
            capture_id="capture",
            leakage_group_key="corpus:group:group",
            partition="fit",
            frame_index=2,
            pitch=60,
            candidate_reason="model_onset",
            candidate_score=0.6,
            frame_probability=0.7,
            onset_probability=0.8,
            harmonic_support=0.8,
            audio_onset_available=True,
            audio_onset_recent=True,
            active_polyphony=2,
            gate_eligible=True,
            post_gate_rank=0,
            post_gate_selected=True,
            emitted_noteon=True,
            event_id="decoder-noteon-v2:e2",
        )
        values.update(overrides)
        return DecoderCandidateAttempt(**values)

    def test_selects_real_emitted_events_without_temporal_collapse(self) -> None:
        rows = [
            self.row(frame_index=2, event_id="decoder-noteon-v2:e2"),
            self.row(frame_index=3, event_id="decoder-noteon-v2:e3"),
            self.row(
                frame_index=4,
                event_id=None,
                post_gate_rank=None,
                post_gate_selected=False,
                emitted_noteon=False,
            ),
            self.row(
                frame_index=5,
                event_id="decoder-noteon-v2:not-eligible",
                gate_eligible=False,
            ),
        ]

        result = select_trainable_emitted_events(rows)

        self.assertEqual([row.frame_index for row in result], [2, 3])
        self.assertEqual(
            [row.event_id for row in result],
            ["decoder-noteon-v2:e2", "decoder-noteon-v2:e3"],
        )

    def test_duplicate_trainable_event_id_fails_closed(self) -> None:
        duplicate = self.row(event_id="decoder-noteon-v2:duplicate")
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            select_trainable_emitted_events([duplicate, duplicate])

    def test_causal_features_exclude_provenance_and_post_gate_metadata(self) -> None:
        declared = {field.name for field in fields(DecoderCandidateAttempt)}
        self.assertTrue(set(CAUSAL_FEATURES) <= declared)
        self.assertTrue(set(POST_GATE_METADATA_FIELDS) <= declared)
        self.assertTrue(set(PROVENANCE_FIELDS) <= declared)
        self.assertFalse(set(CAUSAL_FEATURES) & set(POST_GATE_METADATA_FIELDS))
        self.assertFalse(set(CAUSAL_FEATURES) & set(PROVENANCE_FIELDS))

    def test_candidate_reason_encoding_is_fixed_and_immutable(self) -> None:
        expected = (
            "model_onset",
            "frame_attack",
            "frame_fallback",
            "legacy",
            "chord_completion",
        )
        self.assertEqual(CANDIDATE_REASON_VOCABULARY, expected)
        self.assertEqual(
            dict(CANDIDATE_REASON_ENCODING),
            {
                "model_onset": 1,
                "frame_attack": 2,
                "frame_fallback": 3,
                "legacy": 6,
                "chord_completion": 7,
            },
        )
        self.assertEqual(NOTE_ON_REASON_CODES["harmonic_strong_frame"], 4)
        self.assertEqual(NOTE_ON_REASON_CODES["retrigger"], 5)
        with self.assertRaises(TypeError):
            CANDIDATE_REASON_ENCODING["new_reason"] = len(expected)

    def test_collector_is_bounded_drainable_and_uses_complete_event_identity(self) -> None:
        collector = self.collector(maximum_attempts=2)
        for name, value in (
            ("source_id", "other"),
            ("dataset_id", "other"),
            ("group_id", "other"),
            ("capture_id", "other"),
            ("leakage_group_key", "other"),
            ("partition", "dev"),
            ("maximum_attempts", 3),
        ):
            with self.assertRaises(AttributeError):
                setattr(collector, name, value)
        recorded = []
        for frame_index in range(3):
            recorded.append(collector.record_candidate(
                frame_index=frame_index,
                pitch=60,
                candidate_reason="legacy",
                candidate_score=0.6,
                frame_probability=0.7,
                onset_probability=0.8,
                harmonic_support=0.0,
                audio_onset_available=False,
                audio_onset_recent=False,
                active_polyphony=0,
                gate_eligible=False,
                post_gate_rank=0,
                post_gate_selected=True,
                emitted_noteon=True,
            ))

        self.assertEqual(collector.total_attempts, 3)
        self.assertEqual(collector.dropped_attempts, 1)
        self.assertEqual(
            [row.frame_index for row in collector.attempts], [1, 2]
        )
        self.assertEqual(recorded[0].capture_id, "capture")
        self.assertEqual(recorded[0].partition, collector.partition)
        batch = collector.drain()
        self.assertEqual(len(batch.attempts), 2)
        self.assertEqual(batch.total_attempts, 3)
        self.assertEqual(batch.dropped_attempts, 1)
        self.assertFalse(batch.complete)
        with self.assertRaisesRegex(RuntimeError, "overflowed"):
            batch.require_complete()
        self.assertEqual(collector.attempts, ())
        self.assertEqual(collector.total_attempts, 3)

        repeated = self.collector().record_candidate(
            frame_index=0,
            pitch=60,
            candidate_reason="legacy",
            candidate_score=0.6,
            frame_probability=0.7,
            onset_probability=0.8,
            harmonic_support=0.0,
            audio_onset_available=False,
            audio_onset_recent=False,
            active_polyphony=0,
            gate_eligible=False,
            post_gate_rank=0,
            post_gate_selected=True,
            emitted_noteon=True,
        )
        other_capture = self.collector(
            capture_id="other-capture"
        ).record_candidate(
            frame_index=0,
            pitch=60,
            candidate_reason="legacy",
            candidate_score=0.6,
            frame_probability=0.7,
            onset_probability=0.8,
            harmonic_support=0.0,
            audio_onset_available=False,
            audio_onset_recent=False,
            active_polyphony=0,
            gate_eligible=False,
            post_gate_rank=0,
            post_gate_selected=True,
            emitted_noteon=True,
        )
        self.assertEqual(repeated.event_id, recorded[0].event_id)
        self.assertNotEqual(other_capture.event_id, recorded[0].event_id)
        self.assertTrue(repeated.event_id.startswith("decoder-noteon-v2:"))

        with self.assertRaisesRegex(ValueError, "retained plus dropped"):
            DecoderCandidateBatch(
                attempts=(),
                total_attempts=1,
                dropped_attempts=0,
                manifest_sha256="a" * 64,
                partition_plan_sha256="b" * 64,
                recording_identity=("corpus", "source", "capture"),
                partition="fit",
            )

    def test_event_id_changes_with_each_physical_identity_component(self) -> None:
        def emitted_id(**overrides) -> str:
            row = self.collector(**overrides).record_candidate(
                frame_index=7,
                pitch=60,
                candidate_reason="legacy",
                candidate_score=0.6,
                frame_probability=0.7,
                onset_probability=0.8,
                harmonic_support=0.0,
                audio_onset_available=False,
                audio_onset_recent=False,
                active_polyphony=0,
                gate_eligible=False,
                post_gate_rank=0,
                post_gate_selected=True,
                emitted_noteon=True,
            )
            self.assertIsNotNone(row.event_id)
            return str(row.event_id)

        baseline = emitted_id()
        for override in (
            {"source_id": "other-source"},
            {"dataset_id": "other-dataset"},
            {"group_id": "other-group"},
            {"capture_id": "other-capture"},
        ):
            with self.subTest(override=override):
                self.assertNotEqual(baseline, emitted_id(**override))

    def test_row_invariants_fail_closed(self) -> None:
        invalid_rows = (
            {"frame_probability": 1.1},
            {"candidate_score": float("nan")},
            {"active_polyphony": 1.5},
            {"gate_eligible": 1},
            {"audio_onset_available": False, "audio_onset_recent": True},
            {"candidate_reason": "runtime_order_dependent_reason"},
            {"capture_id": ""},
            {"partition": "validation"},
            {"post_gate_rank": -1},
            {"post_gate_selected": False, "emitted_noteon": True},
            {"emitted_noteon": False, "event_id": "e"},
        )
        for overrides in invalid_rows:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.row(**overrides)


if __name__ == "__main__":
    unittest.main()
