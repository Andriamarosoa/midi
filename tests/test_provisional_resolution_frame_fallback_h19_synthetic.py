from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import numpy as np

from src.polyphonic.causal_event_metrics import ReferenceNote
from src.polyphonic.decoder import PolyphonicDecoder, PolyphonicDecoderConfig, PolyphonicMidiEvent
from src.polyphonic.provisional_resolution_age1 import TARGET_MATCHABLE
from src.polyphonic.provisional_resolution_frame_fallback_h19 import (
    BOOTSTRAP_REPLICATE_COUNT,
    BOOTSTRAP_SEED,
    FRAME_FALLBACK_RISK_DEMONSTRATED,
    FRAME_FALLBACK_RISK_NOT_DEMONSTRATED,
    FRAME_FALLBACK_COMPARATOR_INSUFFICIENT,
    FRAME_FALLBACK_EXPOSED_INSUFFICIENT,
    FRAME_FALLBACK_SIGNAL_INSUFFICIENT,
    GROUP_RESAMPLING_INCONCLUSIVE,
    GroupedFrameFallbackRow,
    PassiveFrameFallbackExposureCollector,
    evaluate_h19_synthetic_metrics,
    extract_synthetic_h19_rows,
    grouped_rd_false_bootstrap,
    MINIMUM_COMPARATOR_NOTEONS,
    MINIMUM_ELIGIBLE_NOTEONS,
    MINIMUM_FRAME_FALLBACK_NOTEONS,
    MINIMUM_RD_FALSE,
    risk_difference_false,
)


def _event_tuple(events):
    return tuple(
        (event.kind, event.pitch, event.velocity, event.frame_index, event.reason)
        for event in events
    )


def _state(decoder):
    encoded = []
    for name, value in sorted(vars(decoder).items()):
        if isinstance(value, np.ndarray):
            value = (value.dtype.str, value.shape, value.tobytes())
        encoded.append((name, value))
    return tuple(encoded)


def _row(index, *, exposed, false, group):
    return GroupedFrameFallbackRow(
        recording_key=f"recording-{group}",
        corpus_category="synthetic",
        leakage_group_key=group,
        frame_index=index,
        pitch=40 + index % 40,
        candidate_reason_at_noteon=("frame_fallback" if exposed else "model_onset"),
        frame_fallback_indicator=int(exposed),
        false_noteon=int(false),
        target_status=TARGET_MATCHABLE,
    )


class ProvisionalResolutionFrameFallbackH19SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.contract_path = cls.root / "configs/provisional_resolution_frame_fallback_h19_synthetic_conformance.json"
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))

    def test_contract_is_synthetic_only_and_bound_to_h17_h18a_decoder(self):
        self.assertEqual(
            self.contract["status"],
            "provisional_resolution_frame_fallback_h19_synthetic_conformance_demonstrated",
        )
        scope = self.contract["scope"]
        self.assertTrue(scope["synthetic_conformance_only"])
        for name in (
            "real_data_accessed", "checkpoint_loaded", "model_inference",
            "real_reason_counts_computed", "real_targets_extracted",
            "real_rd_or_bootstrap_computed", "locked_test_used",
        ):
            self.assertFalse(scope[name])
        bindings = self.contract["provenance_bindings"]
        self.assertEqual(bindings["accepted_h17_commit"], "3a3e65ab532a4983fadae89c842b544228c3b028")
        self.assertEqual(bindings["accepted_h18a_commit"], "3f9a15540d783c32486a9e0d50446efdb637ba60")
        self.assertEqual(bindings["h18a_audit_git_blob"], "c06459b5877526a515930561b15a5e9a08c3af31")
        self.assertEqual(bindings["h18a_audit_raw_sha256"], "580ea2a77cd68798946c324d190082d5b960e5d1280fd93527b8ac47116fcff9")
        decoder_blob = subprocess.check_output(
            ["git", "hash-object", "src/polyphonic/decoder.py"], cwd=self.root, text=True
        ).strip()
        self.assertEqual(decoder_blob, "27026d368081fadc4fa282954428f0377020e723")
        self.assertEqual(bindings["reviewed_decoder_reason_taxonomy_blob"], decoder_blob)
        self.assertEqual(bindings["exact_causal_target_extractor_blob"], "22b93d2b5a6e2a3826eddc4aee0057d68fe34141")
        self.assertEqual(bindings["canonical_group_universe_engine_blob"], "5e40574dab4a53e0ce5b2288536d337f0da66fa9")
        self.assertEqual(
            self.contract["passive_exposure_contract"]["excluded_but_counted_reasons"],
            ["harmonic_strong_frame", "legacy", "retrigger"],
        )
        self.assertTrue(
            self.contract["synthetic_proofs"]["all_seven_reviewed_decoder_reason_taxonomy_values"]
        )
        self.assertEqual(
            self.contract["h19a_review_resolution"]["previous_reason"],
            "reviewed_decoder_reason_taxonomy_incomplete_harmonic_strong_frame",
        )
        self.assertNotIn(b"\r\n", self.contract_path.read_bytes())

    def test_passive_observer_returns_exact_events_and_freezes_all_reasons(self):
        events = tuple(
            PolyphonicMidiEvent("note_on", 60 + index, 100, index, reason)
            for index, reason in enumerate((
                "model_onset", "frame_attack", "chord_completion",
                "frame_fallback", "harmonic_strong_frame", "retrigger", "legacy",
            ))
        )
        collector = PassiveFrameFallbackExposureCollector()
        returned = collector.observe_emitted_noteons(events)
        self.assertIs(returned[0], events[0])
        self.assertEqual(returned, events)
        self.assertEqual(
            [row.candidate_reason_at_noteon for row in collector.records],
            [event.reason for event in events],
        )
        self.assertEqual(
            tuple(field.name for field in fields(type(collector.records[0]))),
            ("frame_index", "pitch", "candidate_reason_at_noteon"),
        )

    def test_real_synthetic_decoder_path_emits_and_excludes_harmonic_strong_frame(self):
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            frame_off_threshold=0.25,
            onset_threshold=0.5,
            activation_frames=1,
            release_frames=2,
            minimum_retrigger_frames=3,
            silence_release_frames=2,
            maximum_polyphony=2,
            harmonic_support_threshold=0.6,
            harmonic_suppression_strength=0.25,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.zeros(13, dtype=np.float32)
        onset = np.zeros(13, dtype=np.float32)
        harmonic = np.zeros((13, 2), dtype=np.float32)
        frame[0], onset[0] = 0.90, 0.90
        frame[12], onset[12] = 0.86, 0.10
        harmonic[0, 1] = 0.80
        events = decoder.step(frame, onset, harmonic, audio_onset=True)
        emitted = {event.pitch: event for event in events if event.kind == "note_on"}
        self.assertEqual(emitted[72].reason, "harmonic_strong_frame")

        rows = extract_synthetic_h19_rows(
            events,
            [],
            recording_key="r", corpus_category="c", leakage_group_key="g",
            frame_valid=[1], sample_rate=1000, hop_size=10, audio_frames=1000,
        )
        harmonic_row = next(row for row in rows if row.pitch == 72)
        self.assertEqual(harmonic_row.candidate_reason_at_noteon, "harmonic_strong_frame")
        self.assertIsNone(harmonic_row.frame_fallback_indicator)
        self.assertIsNone(harmonic_row.false_noteon)
        report = evaluate_h19_synthetic_metrics(rows, cohort_group_universe=("g",))
        self.assertEqual(report.excluded_harmonic_strong_frame_count, 1)
        self.assertEqual(report.counts_per_frozen_reason["harmonic_strong_frame"], 1)

    def test_unexpected_reason_and_duplicate_identity_fail_closed(self):
        collector = PassiveFrameFallbackExposureCollector()
        with self.assertRaisesRegex(RuntimeError, "frame_fallback_execution_invalid"):
            collector.observe_emitted_noteons([
                PolyphonicMidiEvent("note_on", 60, 100, 0, "future_reason")
            ])
        self.assertEqual(collector.records, ())
        valid = PolyphonicMidiEvent("note_on", 60, 100, 0, "frame_fallback")
        collector.observe_emitted_noteons([valid])
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            collector.observe_emitted_noteons([valid])

    def test_observing_decoder_outputs_changes_neither_events_nor_state(self):
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=72, activation_frames=1, release_frames=2,
            minimum_retrigger_frames=2, maximum_polyphony=3,
        )
        baseline = PolyphonicDecoder(config)
        observed = PolyphonicDecoder(config)
        collector = PassiveFrameFallbackExposureCollector()
        rng = np.random.default_rng(721629268)
        observed_noteons = 0
        for frame_index in range(64):
            frame = rng.random(13, dtype=np.float32)
            onset = rng.random(13, dtype=np.float32)
            kwargs = dict(audio_hop_index=frame_index, audio_onset=bool(frame_index % 4 == 0))
            events_a = baseline.step(frame.copy(), onset.copy(), **kwargs)
            events_b = observed.step(frame.copy(), onset.copy(), **kwargs)
            before = _state(observed)
            returned = collector.observe_emitted_noteons(events_b)
            after = _state(observed)
            self.assertEqual(_event_tuple(events_a), _event_tuple(returned))
            self.assertEqual(_state(baseline), after)
            self.assertEqual(before, after)
            observed_noteons += sum(event.kind == "note_on" for event in events_b)
        self.assertEqual(len(collector.records), observed_noteons)
        self.assertGreater(observed_noteons, 0)

    def test_exact_existing_causal_target_is_reused_and_exclusions_are_counted(self):
        events = (
            PolyphonicMidiEvent("note_on", 60, 100, 0, "frame_fallback"),
            PolyphonicMidiEvent("note_on", 61, 100, 1, "model_onset"),
            PolyphonicMidiEvent("note_on", 62, 100, 2, "retrigger"),
            PolyphonicMidiEvent("note_on", 63, 100, 3, "legacy"),
        )
        rows = extract_synthetic_h19_rows(
            events,
            [ReferenceNote(pitch=60, start_s=0.0, end_s=1.0)],
            recording_key="r", corpus_category="c", leakage_group_key="g",
            frame_valid=[1, 1, 1, 1], sample_rate=1000, hop_size=10,
            audio_frames=1000,
        )
        self.assertEqual([row.false_noteon for row in rows], [0, 1, None, None])
        report = evaluate_h19_synthetic_metrics(rows, cohort_group_universe=("g",))
        self.assertEqual(report.excluded_retrigger_count, 1)
        self.assertEqual(report.excluded_legacy_count, 1)
        self.assertEqual(report.excluded_harmonic_strong_frame_count, 0)
        self.assertEqual(report.counts_per_frozen_reason["frame_fallback"], 1)

    def test_rd_formula_thresholds_and_group_bootstrap_are_exact(self):
        rows = []
        for group_index in range(10):
            group = f"g-{group_index:02d}"
            for index in range(12):
                rows.append(_row(group_index * 24 + index, exposed=True, false=index < 10, group=group))
                rows.append(_row(group_index * 24 + 12 + index, exposed=False, false=index < 2, group=group))
        universe = tuple(f"g-{index:02d}" for index in range(10)) + ("empty",)
        self.assertAlmostEqual(risk_difference_false(rows), 2.0 / 3.0)
        report = evaluate_h19_synthetic_metrics(rows, cohort_group_universe=universe)
        self.assertEqual(report.status, FRAME_FALLBACK_RISK_DEMONSTRATED)
        self.assertEqual(report.eligible_noteons, 240)
        self.assertEqual(report.frame_fallback_noteons, 120)
        self.assertEqual(report.comparator_noteons, 120)
        self.assertEqual(report.bootstrap.requested_replicates, BOOTSTRAP_REPLICATE_COUNT)
        self.assertEqual(report.bootstrap.seed, BOOTSTRAP_SEED)
        self.assertEqual(report.bootstrap.valid_replicates, 10_000)
        self.assertGreater(report.bootstrap.lower_95, 0.0)
        reverse = evaluate_h19_synthetic_metrics(tuple(reversed(rows)), cohort_group_universe=tuple(reversed(universe)))
        self.assertEqual(report, reverse)

    def test_all_preregistered_primary_thresholds_gate_mechanically(self):
        self.assertEqual(MINIMUM_ELIGIBLE_NOTEONS, 200)
        self.assertEqual(MINIMUM_FRAME_FALLBACK_NOTEONS, 50)
        self.assertEqual(MINIMUM_COMPARATOR_NOTEONS, 50)
        self.assertEqual(MINIMUM_RD_FALSE, 0.10)

        too_few = tuple(
            _row(index, exposed=index < 100, false=index < 80, group=f"g-{index % 10}")
            for index in range(199)
        )
        self.assertEqual(
            evaluate_h19_synthetic_metrics(
                too_few, cohort_group_universe=tuple(f"g-{index}" for index in range(10))
            ).status,
            FRAME_FALLBACK_SIGNAL_INSUFFICIENT,
        )
        exposed_few = tuple(
            _row(index, exposed=index < 49, false=index < 40, group=f"g-{index % 10}")
            for index in range(200)
        )
        self.assertEqual(
            evaluate_h19_synthetic_metrics(
                exposed_few, cohort_group_universe=tuple(f"g-{index}" for index in range(10))
            ).status,
            FRAME_FALLBACK_EXPOSED_INSUFFICIENT,
        )
        comparator_few = tuple(
            _row(index, exposed=index >= 49, false=index >= 80, group=f"g-{index % 10}")
            for index in range(200)
        )
        self.assertEqual(
            evaluate_h19_synthetic_metrics(
                comparator_few, cohort_group_universe=tuple(f"g-{index}" for index in range(10))
            ).status,
            FRAME_FALLBACK_COMPARATOR_INSUFFICIENT,
        )

        no_enrichment = tuple(
            _row(
                group_index * 20 + index,
                exposed=index < 5,
                false=(index % 5 == 0),
                group=f"g-{group_index}",
            )
            for group_index in range(10)
            for index in range(20)
        )
        report = evaluate_h19_synthetic_metrics(
            no_enrichment, cohort_group_universe=tuple(f"g-{index}" for index in range(10))
        )
        self.assertEqual(report.status, FRAME_FALLBACK_RISK_NOT_DEMONSTRATED)
        self.assertAlmostEqual(report.rd_false, 0.0)

    def test_empty_groups_are_retained_and_can_make_bootstrap_inconclusive(self):
        rows = tuple(
            [_row(index, exposed=True, false=True, group="observed") for index in range(100)]
            + [_row(100 + index, exposed=False, false=False, group="observed") for index in range(100)]
        )
        universe = ("observed",) + tuple(f"empty-{index}" for index in range(9))
        result = grouped_rd_false_bootstrap(rows, cohort_group_universe=universe)
        self.assertEqual(result.cohort_group_count, 10)
        self.assertEqual(result.status, GROUP_RESAMPLING_INCONCLUSIVE)
        self.assertLess(result.valid_replicates, 9_500)


if __name__ == "__main__":
    unittest.main()
