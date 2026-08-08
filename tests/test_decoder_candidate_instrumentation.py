from __future__ import annotations

from dataclasses import fields
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import numpy as np

from src.polyphonic.decoder import (
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    PolyphonicMidiEvent,
)
from src.polyphonic.decoder_candidate_mining import DecoderCandidateCollector
from src.polyphonic.decoder_candidate_labels import (
    label_emitted_decoder_candidates,
)
from src.polyphonic.decoder_candidate_provenance import (
    build_decoder_candidate_partition_plan_from_snapshot,
    load_decoder_candidate_partition_plan,
    validate_decoder_candidate_partition_plan_against_snapshot,
    write_decoder_candidate_partition_plan,
)
from src.polyphonic.data import load_manifest_snapshot


class DecoderCandidateInstrumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._collector_temporaries: list[TemporaryDirectory] = []

    def tearDown(self) -> None:
        for temporary in self._collector_temporaries:
            temporary.cleanup()

    @staticmethod
    def decoder_state(decoder: PolyphonicDecoder) -> dict[str, object]:
        state: dict[str, object] = {}
        for name, value in vars(decoder).items():
            if name in {"_candidate_collector", "_candidate_collection_error"}:
                continue
            if isinstance(value, np.ndarray):
                state[name] = (value.dtype.str, value.shape, value.tobytes())
            elif isinstance(value, list):
                state[name] = tuple(value)
            else:
                state[name] = value
        return state

    def collector(
        self,
        maximum_attempts: int = 4096,
        collector_type: type[DecoderCandidateCollector] = DecoderCandidateCollector,
    ) -> DecoderCandidateCollector:
        item = SimpleNamespace(
            source_id="source",
            dataset_id="corpus",
            player_id="player",
            group_id="group",
            capture_id="capture",
            split="train",
        )
        items = [
            item,
            SimpleNamespace(
                source_id="source-2", dataset_id="corpus", player_id="player-2",
                group_id="group-2", capture_id="capture-2", split="train",
            ),
            SimpleNamespace(
                source_id="source-3", dataset_id="corpus", player_id="player-3",
                group_id="group-3", capture_id="capture-3", split="train",
            ),
        ]
        temporary = TemporaryDirectory()
        try:
            path = Path(temporary.name) / "manifest.csv"
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
                        "audio_path": str(Path(temporary.name) / f"{candidate.source_id}.wav"),
                        "audio_member": "",
                        "labels_path": str(Path(temporary.name) / f"{candidate.source_id}.npz"),
                        "license_id": "unit-test",
                    })
                    writer.writerow(row)
            snapshot = load_manifest_snapshot(path)
            plan = build_decoder_candidate_partition_plan_from_snapshot(
                snapshot, seed=47
            )
            persisted = write_decoder_candidate_partition_plan(
                Path(temporary.name) / "partition-plan.json", plan
            )
            persisted = load_decoder_candidate_partition_plan(persisted.path)
            validated = validate_decoder_candidate_partition_plan_against_snapshot(
                persisted, snapshot
            )
            collector = collector_type(
                validated_snapshot=validated,
                manifest_item=snapshot.items[0],
                maximum_attempts=maximum_attempts,
            )
        except Exception:
            temporary.cleanup()
            raise
        # The collector re-verifies the persisted plan at drain time, so keep
        # the synthetic plan alive for the complete test lifecycle.
        self._collector_temporaries.append(temporary)
        return collector

    def test_instrumentation_is_disabled_by_default(self) -> None:
        decoder = PolyphonicDecoder(PolyphonicDecoderConfig())

        self.assertIsNone(decoder._candidate_collector)
        self.assertEqual(
            tuple(field.name for field in fields(PolyphonicMidiEvent)),
            ("kind", "pitch", "velocity", "frame_index", "reason"),
        )

    def test_trace_freezes_pre_gate_features_then_adds_post_decision_metadata(
        self,
    ) -> None:
        collector = self.collector()
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=2,
            minimum_retrigger_frames=3,
            silence_release_frames=2,
            maximum_polyphony=2,
        )
        decoder = PolyphonicDecoder(config, candidate_collector=collector)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        harmonic = np.zeros((13, 4), np.float32)
        frame[[0, 12]] = 0.95
        onset[0] = 0.90
        harmonic[0, 1] = 0.80

        events = decoder.step(
            frame,
            onset,
            harmonic,
            audio_onset=True,
        )

        self.assertEqual(
            [(event.pitch, event.reason) for event in events],
            [(60, "model_onset"), (72, "harmonic_strong_frame")],
        )
        attempts = {row.pitch: row for row in collector.attempts}
        self.assertEqual(set(attempts), {60, 72})
        harmonic_attempt = attempts[72]
        self.assertEqual(harmonic_attempt.candidate_reason, "frame_attack")
        self.assertAlmostEqual(harmonic_attempt.candidate_score, 0.95, places=6)
        self.assertAlmostEqual(harmonic_attempt.harmonic_support, 0.80, places=6)
        self.assertTrue(harmonic_attempt.gate_eligible)
        self.assertEqual(harmonic_attempt.active_polyphony, 0)
        self.assertEqual(harmonic_attempt.post_gate_rank, 1)
        self.assertTrue(harmonic_attempt.post_gate_selected)
        self.assertTrue(harmonic_attempt.emitted_noteon)
        self.assertIsNotNone(harmonic_attempt.event_id)

    def test_gate_rejection_is_observed_without_a_rank_or_event(self) -> None:
        collector = self.collector()
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            maximum_polyphony=2,
            independent_note_threshold=0.5,
        )
        decoder = PolyphonicDecoder(config, candidate_collector=collector)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        harmonic = np.zeros((13, 4), np.float32)
        independent = np.ones(13, np.float32)
        frame[[0, 12]] = 0.95
        onset[0] = 0.90
        harmonic[0, 1] = 0.80
        independent[12] = 0.10

        events = decoder.step(
            frame,
            onset,
            harmonic,
            audio_onset=True,
            independent_note_probability=independent,
        )

        self.assertEqual([event.pitch for event in events], [60])
        rejected = next(row for row in collector.attempts if row.pitch == 72)
        self.assertTrue(rejected.gate_eligible)
        self.assertIsNone(rejected.post_gate_rank)
        self.assertFalse(rejected.post_gate_selected)
        self.assertFalse(rejected.emitted_noteon)
        self.assertIsNone(rejected.event_id)

    def test_polyphony_ranking_is_recorded_after_selection(self) -> None:
        class CountingCollector(DecoderCandidateCollector):
            batch_calls = 0

            def record_candidates(self, rows):
                self.batch_calls += 1
                return super().record_candidates(rows)

        collector = self.collector(collector_type=CountingCollector)
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=72,
                activation_frames=1,
                maximum_polyphony=1,
            ),
            candidate_collector=collector,
        )
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[[0, 12]] = 0.90
        onset[[0, 12]] = 0.90

        events = decoder.step(frame, onset, audio_onset=True)

        self.assertEqual([event.pitch for event in events], [60])
        attempts = {row.pitch: row for row in collector.attempts}
        self.assertEqual(attempts[60].post_gate_rank, 0)
        self.assertTrue(attempts[60].post_gate_selected)
        self.assertTrue(attempts[60].emitted_noteon)
        self.assertEqual(attempts[72].post_gate_rank, 1)
        self.assertFalse(attempts[72].post_gate_selected)
        self.assertFalse(attempts[72].emitted_noteon)
        self.assertEqual(collector.batch_calls, 1)

    def test_retrigger_is_an_explicit_nonlearning_exclusion_in_decoder_to_label_flow(
        self,
    ) -> None:
        """A real retrigger must not masquerade as a missing model-onset trace."""
        collector = self.collector()
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=60,
                activation_frames=1,
                release_frames=4,
                minimum_retrigger_frames=1,
                maximum_polyphony=1,
                harmonic_support_threshold=0.0,
            ),
            candidate_collector=collector,
        )
        probability = np.asarray([0.9], np.float32)
        harmonic = np.zeros((1, 4), np.float32)
        events = []
        events.extend(
            decoder.step(
                probability,
                probability,
                harmonic,
                audio_onset=True,
            )
        )
        events.extend(
            decoder.step(
                probability,
                probability,
                harmonic,
                audio_onset=True,
            )
        )
        self.assertEqual(
            [event.reason for event in events if event.kind == "note_on"],
            ["model_onset", "retrigger"],
        )

        labeled = label_emitted_decoder_candidates(
            collector.drain(),
            [],
            frame_valid=[True, True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=events,
            candidate_collection_error=decoder.candidate_collection_error,
        )
        labeled.require_complete()
        self.assertEqual(labeled.negative_targets, 1)
        self.assertEqual(labeled.uninstrumented_decoder_noteons, 1)
        self.assertEqual(
            labeled.uninstrumented_decoder_noteons_by_reason,
            (("retrigger", 1),),
        )

    def test_instrumented_and_plain_decoders_have_strict_frame_state_parity(
        self,
    ) -> None:
        for gate_enabled in (False, True):
            for audio_onset_available in (False, True):
                with self.subTest(
                    gate_enabled=gate_enabled,
                    audio_onset_available=audio_onset_available,
                ):
                    self.assert_strict_parity(
                        gate_enabled=gate_enabled,
                        audio_onset_available=audio_onset_available,
                    )

    def assert_strict_parity(
        self,
        *,
        gate_enabled: bool,
        audio_onset_available: bool,
    ) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=2,
            release_frames=2,
            minimum_retrigger_frames=3,
            silence_release_frames=3,
            maximum_polyphony=3,
            independent_note_threshold=0.5 if gate_enabled else None,
        )
        plain = PolyphonicDecoder(
            config,
            independent_note_diagnostic_thresholds=(0.25, 0.75),
        )
        collector = self.collector()
        instrumented = PolyphonicDecoder(
            config,
            independent_note_diagnostic_thresholds=(0.25, 0.75),
            candidate_collector=collector,
        )
        generator = np.random.default_rng(20260808)
        observed_reasons: set[str] = set()

        for frame_index in range(64):
            frame = generator.random(13, dtype=np.float32)
            onset = generator.random(13, dtype=np.float32)
            harmonic = generator.random((13, 4), dtype=np.float32)
            independent = generator.random(13, dtype=np.float32)
            arguments: dict[str, object] = {
                "harmonic_amplitude": harmonic,
                "audio_active": frame_index % 17 != 16,
                "audio_hop_index": (
                    frame_index if frame_index < 40 else frame_index + 2
                ),
                "independent_note_probability": independent,
            }
            if audio_onset_available:
                arguments["audio_onset"] = frame_index % 7 == 0
            plain_events = plain.step(frame, onset, **arguments)
            instrumented_events = instrumented.step(frame, onset, **arguments)
            self.assertEqual(plain_events, instrumented_events)
            observed_reasons.update(
                event.reason for event in instrumented_events
            )
            self.assertEqual(
                self.decoder_state(plain),
                self.decoder_state(instrumented),
            )
            self.assertIsNone(instrumented.candidate_collection_error)
            if frame_index == 31:
                batch = collector.drain()
                batch.require_complete()
                self.assertEqual(
                    self.decoder_state(plain),
                    self.decoder_state(instrumented),
                )

        self.assertEqual(
            plain.reset_observation_continuity(),
            instrumented.reset_observation_continuity(),
        )
        self.assertEqual(
            self.decoder_state(plain),
            self.decoder_state(instrumented),
        )
        self.assertEqual(plain.panic(), instrumented.panic())
        self.assertEqual(
            self.decoder_state(plain),
            self.decoder_state(instrumented),
        )
        self.assertGreater(collector.total_attempts, 0)
        self.assertIn("retrigger", observed_reasons)
        self.assertIn("release", observed_reasons)

    def test_collector_failure_is_latched_without_blocking_midi(self) -> None:
        class RaisingCollector:
            @staticmethod
            def record_candidates(_: object) -> None:
                raise RuntimeError("collector unavailable")

        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=1,
            maximum_polyphony=1,
        )
        plain = PolyphonicDecoder(config)
        instrumented = PolyphonicDecoder(
            config,
            candidate_collector=RaisingCollector(),
        )
        probability = np.asarray([0.9], np.float32)

        self.assertEqual(
            plain.step(probability, probability, audio_onset=True),
            instrumented.step(probability, probability, audio_onset=True),
        )
        self.assertEqual(
            self.decoder_state(plain), self.decoder_state(instrumented)
        )
        self.assertEqual(
            instrumented.candidate_collection_error,
            "RuntimeError: collector unavailable",
        )

    def test_collector_lock_contention_never_waits_in_decoder_step(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=1,
            maximum_polyphony=1,
        )
        plain = PolyphonicDecoder(config)
        collector = self.collector()
        instrumented = PolyphonicDecoder(
            config,
            candidate_collector=collector,
        )
        probability = np.asarray([0.9], np.float32)

        collector._lock.acquire()
        try:
            self.assertEqual(
                plain.step(probability, probability, audio_onset=True),
                instrumented.step(
                    probability, probability, audio_onset=True
                ),
            )
        finally:
            collector._lock.release()
        self.assertEqual(
            self.decoder_state(plain), self.decoder_state(instrumented)
        )
        self.assertIn(
            "collector is busy", instrumented.candidate_collection_error
        )


if __name__ == "__main__":
    unittest.main()
