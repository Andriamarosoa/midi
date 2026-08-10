from __future__ import annotations

from dataclasses import fields
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from src.polyphonic.causal_event_metrics import ReferenceNote
from src.polyphonic.decoder import (
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    PolyphonicMidiEvent,
)
from src.polyphonic.provisional_resolution_age1 import (
    AGE1_OBSERVATION_AVAILABLE,
    AGE1_OBSERVATION_UNAVAILABLE,
    TARGET_EXCLUDED_INVALID_FRAME,
    TARGET_EXCLUDED_OUTSIDE_AUDIO,
    TARGET_MATCHABLE,
    Age1ScientificRow,
    Age1SignalRecord,
    Age1TargetRecord,
    PassiveAge1SignalCollector,
    count_age1_attrition,
    extract_exact_causal_age1_targets,
    join_age1_signals_and_targets,
)


def _event_tuple(events):
    return tuple(
        (event.kind, event.pitch, event.velocity, event.frame_index, event.reason)
        for event in events
    )


def _state(decoder):
    encoded = []
    for name, value in sorted(vars(decoder).items()):
        if name == "_passive_age1_collector":
            continue
        if isinstance(value, np.ndarray):
            value = (value.dtype.str, value.shape, value.tobytes())
        encoded.append((name, value))
    return tuple(encoded)


class ProvisionalResolutionAge1H9SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.contract_path = cls.root / "configs/provisional_resolution_age1_persistence_h9_synthetic_conformance.json"
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))

    def test_h9_contract_status_scope_and_lf_are_exact(self) -> None:
        self.assertEqual(
            self.contract["status"],
            "provisional_resolution_age1_persistence_h9_synthetic_extractor_ready",
        )
        self.assertEqual(
            self.contract["verdict"],
            "age1_persistence_h9_synthetic_extractor_conformance_demonstrated",
        )
        state = self.contract["implementation_state"]
        for name in (
            "passive_signal_collector_implemented",
            "exact_causal_target_extractor_implemented",
            "exact_signal_target_joiner_implemented",
            "synthetic_conformance_demonstrated",
        ):
            self.assertTrue(state[name])
        for name in (
            "scientific_execution_authorized", "real_targets_extracted",
            "real_signals_extracted", "metrics_computed", "h8_cohort_consumed",
            "locked_test_used", "consumed_v2_cohort_used",
        ):
            self.assertFalse(state[name])
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "configs/provisional_resolution_age1_persistence_h9_synthetic_conformance.json text eol=lf",
            attributes,
        )
        self.assertNotIn(b"\r\n", self.contract_path.read_bytes())

    def test_signal_schema_exact_age1_frozen_s0_and_clock_jump(self) -> None:
        collector = PassiveAge1SignalCollector()
        collector.observe_emitted_noteons(
            [PolyphonicMidiEvent("note_on", 60, 100, 4, "legacy")],
            frame_probability=np.asarray([0.8], np.float32),
            midi_min=60,
        )
        collector.observe_frame(
            frame_index=5,
            frame_probability=np.asarray([0.3], np.float32),
            midi_min=60,
        )
        row = collector.records[0]
        self.assertEqual(row.frame_index, 4)
        self.assertAlmostEqual(row.S0, 0.8)
        self.assertAlmostEqual(row.S1, 0.3)
        self.assertAlmostEqual(row.D1, row.S1 - row.S0)
        self.assertEqual(row.age1_status, AGE1_OBSERVATION_AVAILABLE)
        self.assertEqual(
            tuple(field.name for field in fields(Age1SignalRecord)),
            ("frame_index", "pitch", "S0", "age1_status", "S1", "D1"),
        )

        skipped = PassiveAge1SignalCollector()
        skipped.observe_emitted_noteons(
            [PolyphonicMidiEvent("note_on", 60, 100, 4, "legacy")],
            frame_probability=[0.8],
            midi_min=60,
        )
        skipped.observe_frame(frame_index=6, frame_probability=[0.99], midi_min=60)
        self.assertEqual(skipped.records[0].age1_status, AGE1_OBSERVATION_UNAVAILABLE)
        self.assertIsNone(skipped.records[0].S1)
        skipped.observe_frame(frame_index=7, frame_probability=[0.1], midi_min=60)
        self.assertEqual(len(skipped.records), 1)

    def test_retrigger_resolves_old_event_before_creating_new_pending_event(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=1,
            minimum_retrigger_frames=1,
            release_frames=3,
        )
        collector = PassiveAge1SignalCollector()
        decoder = PolyphonicDecoder(config, passive_age1_collector=collector)
        first = np.asarray([0.9], np.float32)
        decoder.step(first, first, audio_hop_index=0)
        second = np.asarray([0.7], np.float32)
        events = decoder.step(second, second, audio_hop_index=1)
        self.assertEqual([event.kind for event in events], ["note_off", "note_on"])
        self.assertEqual([(row.frame_index, row.pitch) for row in collector.records], [(0, 60)])
        self.assertAlmostEqual(collector.records[0].S1, 0.7)
        self.assertEqual(collector.pending_count, 1)
        decoder.step(np.asarray([0.4], np.float32), np.zeros(1, np.float32), audio_hop_index=2)
        self.assertEqual([(row.frame_index, row.pitch) for row in collector.records], [(0, 60), (1, 60)])
        self.assertAlmostEqual(collector.records[1].S1, 0.4)

    def test_passive_collector_is_behaviorally_neutral_across_decoder_paths(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=1,
            minimum_retrigger_frames=2,
            silence_release_frames=2,
            maximum_polyphony=2,
        )
        baseline = PolyphonicDecoder(config)
        collector = PassiveAge1SignalCollector()
        observed = PolyphonicDecoder(config, passive_age1_collector=collector)
        zero = np.zeros(13, np.float32)
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0
        onset60 = zero.copy(); onset60[0] = 0.95
        partial = zero.copy(); partial[[0, 12]] = [0.9, 0.7]
        onset72 = zero.copy(); onset72[12] = 0.95
        poly = zero.copy(); poly[[4, 7, 9]] = 0.95
        sequence = (
            (onset60, onset60, {}, None),
            (partial, zero, {}, harmonic),
            (partial, onset72, {"audio_hop_index": 2, "audio_onset": True}, harmonic),
            (poly, poly, {"audio_hop_index": 4, "audio_onset": False}, None),
            (zero, zero, {"audio_hop_index": 5, "audio_onset": False}, None),
            (zero, zero, {"audio_active": False, "audio_hop_index": 6}, None),
            (zero, zero, {"audio_active": False, "audio_hop_index": 7}, None),
        )
        for frame, onset, kwargs, amplitude in sequence:
            events_a = baseline.step(frame.copy(), onset.copy(), amplitude, **kwargs)
            events_b = observed.step(frame.copy(), onset.copy(), None if amplitude is None else amplitude.copy(), **kwargs)
            self.assertEqual(_event_tuple(events_a), _event_tuple(events_b))
            self.assertEqual(_state(baseline), _state(observed))

        # Separate audio-aware retrigger path.
        retrigger_config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=60, activation_frames=1,
            release_frames=2, minimum_retrigger_frames=1, maximum_polyphony=1,
        )
        a = PolyphonicDecoder(retrigger_config)
        c = PassiveAge1SignalCollector()
        b = PolyphonicDecoder(retrigger_config, passive_age1_collector=c)
        note = np.asarray([0.95], np.float32)
        for hop in (0, 1):
            ea = a.step(note, note, audio_hop_index=hop, audio_onset=True)
            eb = b.step(note.copy(), note.copy(), audio_hop_index=hop, audio_onset=True)
            self.assertEqual(_event_tuple(ea), _event_tuple(eb))
            self.assertEqual(_state(a), _state(b))

    def test_passive_collection_rejects_every_population_changing_gate(self) -> None:
        collector = PassiveAge1SignalCollector()
        base = PolyphonicDecoderConfig(midi_min=60, midi_max=60)
        with self.assertRaisesRegex(ValueError, "historical baseline"):
            PolyphonicDecoder(base, passive_age1_collector=collector, provisional_state_resolver=lambda _: "HOLD")
        with self.assertRaisesRegex(ValueError, "historical baseline"):
            PolyphonicDecoder(base, passive_age1_collector=collector, causal_candidate_gate=lambda _: False)
        with self.assertRaisesRegex(ValueError, "historical baseline"):
            PolyphonicDecoder(
                PolyphonicDecoderConfig(midi_min=60, midi_max=60, independent_note_threshold=0.5),
                passive_age1_collector=collector,
            )

    def test_randomized_paired_neutrality_covers_future_state_fields(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=72, activation_frames=2, release_frames=2,
            minimum_retrigger_frames=3, silence_release_frames=3,
            maximum_polyphony=3,
        )
        baseline = PolyphonicDecoder(config)
        collector = PassiveAge1SignalCollector()
        observed = PolyphonicDecoder(config, passive_age1_collector=collector)
        rng = np.random.default_rng(721629268)
        hop = -1
        for index in range(64):
            hop += 2 if index in (17, 41) else 1
            frame = rng.random(13, dtype=np.float32)
            onset = rng.random(13, dtype=np.float32)
            amplitude = rng.random((13, 4), dtype=np.float32)
            kwargs = {
                "audio_hop_index": hop,
                "audio_active": index % 13 != 12,
            }
            if index >= 4:
                kwargs["audio_onset"] = index % 5 == 0
            events_a = baseline.step(frame, onset, amplitude, **kwargs)
            events_b = observed.step(frame.copy(), onset.copy(), amplitude.copy(), **kwargs)
            self.assertEqual(_event_tuple(events_a), _event_tuple(events_b))
            self.assertEqual(_state(baseline), _state(observed))

    def test_target_extractor_preserves_causality_pitch_and_250ms_boundary(self) -> None:
        # hop=10 at 1000 Hz => frame 0 occurs at 10 ms.
        events = (
            PolyphonicMidiEvent("note_on", 60, 100, 0, "legacy"),
            PolyphonicMidiEvent("note_on", 61, 100, 1, "legacy"),
            PolyphonicMidiEvent("note_on", 62, 100, 25, "legacy"),
            PolyphonicMidiEvent("note_on", 63, 100, 26, "legacy"),
            PolyphonicMidiEvent("note_on", 64, 100, 3, "legacy"),
        )
        reference = (
            ReferenceNote(60, 0.010, 0.2),              # exact causal match
            ReferenceNote(61, 0.021, 0.2),              # future by 1 ms: false
            ReferenceNote(62, 0.010, 0.4),              # exactly +250 ms: match
            ReferenceNote(63, 0.010, 0.4),              # +260 ms: false
            ReferenceNote(65, 0.040, 0.2),              # same time, wrong pitch
        )
        targets = extract_exact_causal_age1_targets(
            events,
            reference,
            frame_valid=[1] * 27,
            sample_rate=1000,
            hop_size=10,
            audio_frames=1000,
        )
        self.assertEqual([row.true_noteon for row in targets], [1, 0, 0, 1, 0])
        self.assertEqual({row.target_status for row in targets}, {TARGET_MATCHABLE})

    def test_target_latest_pending_invalid_outside_and_duplicate_fail_closed(self) -> None:
        rapid = (
            ReferenceNote(60, 0.010, 0.4),
            ReferenceNote(60, 0.015, 0.4),
        )
        targets = extract_exact_causal_age1_targets(
            (
                PolyphonicMidiEvent("note_on", 60, 100, 1, "retrigger"),
                PolyphonicMidiEvent("note_on", 60, 100, 2, "retrigger"),
            ),
            rapid,
            frame_valid=[1, 1, 1],
            sample_rate=1000,
            hop_size=10,
            audio_frames=100,
        )
        # The first prediction consumes the latest pending reference and makes
        # the older one unrecoverable; the second prediction is therefore false.
        self.assertEqual([row.true_noteon for row in targets], [1, 0])

        excluded = extract_exact_causal_age1_targets(
            (
                PolyphonicMidiEvent("note_on", 60, 100, 1, "legacy"),
                PolyphonicMidiEvent("note_on", 61, 100, 2, "legacy"),
            ),
            (),
            frame_valid=[1, 0, 1],
            sample_rate=1000,
            hop_size=10,
            audio_frames=25,
        )
        self.assertEqual(
            [row.target_status for row in excluded],
            [TARGET_EXCLUDED_INVALID_FRAME, TARGET_EXCLUDED_OUTSIDE_AUDIO],
        )
        self.assertEqual([row.true_noteon for row in excluded], [None, None])

        duplicate = (
            PolyphonicMidiEvent("note_on", 60, 100, 0, "legacy"),
            PolyphonicMidiEvent("note_on", 60, 100, 0, "retrigger"),
        )
        with self.assertRaisesRegex(RuntimeError, "duplicate NoteOn"):
            extract_exact_causal_age1_targets(
                duplicate, (), frame_valid=[1], sample_rate=1000, hop_size=10, audio_frames=100
            )

    def test_exact_join_schema_and_attrition_without_metrics(self) -> None:
        signals = (
            Age1SignalRecord(0, 60, 0.8, AGE1_OBSERVATION_AVAILABLE, 0.4, -0.4),
            Age1SignalRecord(1, 61, 0.7, AGE1_OBSERVATION_UNAVAILABLE, None, None),
        )
        targets = (
            Age1TargetRecord(0, 60, 1, TARGET_MATCHABLE),
            Age1TargetRecord(1, 61, None, TARGET_EXCLUDED_INVALID_FRAME),
        )
        rows = join_age1_signals_and_targets(signals, targets)
        self.assertEqual(
            tuple(field.name for field in fields(Age1ScientificRow)),
            ("frame_index", "pitch", "S0", "S1", "D1", "age1_status", "true_noteon", "target_status"),
        )
        counts = count_age1_attrition(rows)
        self.assertEqual(counts.emitted_noteons_initially_considered, 2)
        self.assertEqual(counts.noteons_with_exact_age1_observation, 1)
        self.assertEqual(counts.noteons_unavailable_due_to_decoder_clock_skip, 0)
        self.assertEqual(counts.noteons_excluded_as_ambiguous_or_unmatchable, 1)
        self.assertFalse(any("auc" in field.name.lower() for field in fields(type(counts))))
        with self.assertRaisesRegex(RuntimeError, "identities differ"):
            join_age1_signals_and_targets(signals[:1], targets)

    def test_target_information_and_runtime_dependencies_are_absent_from_collector(self) -> None:
        constructor = set(inspect.signature(PassiveAge1SignalCollector).parameters)
        observe_frame = set(inspect.signature(PassiveAge1SignalCollector.observe_frame).parameters)
        observe_noteons = set(inspect.signature(PassiveAge1SignalCollector.observe_emitted_noteons).parameters)
        forbidden = {"true_noteon", "reference", "labels", "matching_result", "target"}
        self.assertFalse((constructor | observe_frame | observe_noteons) & forbidden)
        module_text = (
            self.root / "src/polyphonic/provisional_resolution_age1.py"
        ).read_text(encoding="utf-8").lower()
        for forbidden_import in (
            "import tensorflow", "from tensorflow", "import keras", "from keras",
            "import librosa", "from librosa", "import soundfile", "from soundfile",
        ):
            self.assertNotIn(forbidden_import, module_text)


if __name__ == "__main__":
    unittest.main()
