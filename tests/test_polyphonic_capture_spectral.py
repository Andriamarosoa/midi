from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import soundfile as sf

from src.polyphonic.diagnose_capture_spectral import (
    _maximum_polyphony,
    diagnose,
    find_likely_missing_candidates,
)
from src.polyphonic.evaluate_events import NoteInterval
from src.product.midi_file import write_midi


SAMPLE_RATE = 16_000


def _tone(
    pitch: int,
    amplitude: float = 0.7,
    start_s: float = 0.20,
    end_s: float = 0.80,
    duration_s: float = 1.0,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    waveform = np.zeros(round(duration_s * sample_rate), np.float32)
    start = round(start_s * sample_rate)
    end = round(end_s * sample_rate)
    time_s = np.arange(end - start, dtype=np.float64) / sample_rate
    frequency = 440.0 * 2.0 ** ((pitch - 69) / 12.0)
    envelope = np.ones(len(time_s), np.float64)
    attack = min(round(0.01 * sample_rate), len(envelope))
    release = min(round(0.02 * sample_rate), len(envelope))
    envelope[:attack] = np.linspace(0.0, 1.0, attack, endpoint=False)
    envelope[-release:] *= np.linspace(1.0, 0.0, release, endpoint=False)
    waveform[start:end] = (
        amplitude * envelope * np.sin(2.0 * np.pi * frequency * time_s)
    ).astype(np.float32)
    return waveform


class CaptureSpectralDiagnosticsTests(unittest.TestCase):
    def test_maximum_polyphony_treats_offset_before_same_time_onset(self) -> None:
        notes = [
            NoteInterval(60, 0.0, 1.0),
            NoteInterval(64, 0.2, 0.8),
            NoteInterval(67, 1.0, 2.0),
        ]

        self.assertEqual(_maximum_polyphony(notes), 2)

    def test_finds_durable_missing_note_hypothesis(self) -> None:
        report = find_likely_missing_candidates(
            _tone(60), SAMPLE_RATE, [],
        )

        self.assertIn(60, {row["pitch"] for row in report["examples"]})
        self.assertFalse(report["ground_truth_claimed"])
        self.assertFalse(report["recall_claimed"])
        self.assertIn("Offline diagnostic", report["latency_impact"])
        self.assertEqual(report["count"], len(report["review_candidates"]))
        self.assertEqual(
            report["raw_candidate_detections"],
            len(report["raw_candidates"]),
        )

    def test_does_not_report_note_already_active_in_midi(self) -> None:
        report = find_likely_missing_candidates(
            _tone(60),
            SAMPLE_RATE,
            [NoteInterval(60, 0.20, 0.80)],
        )

        self.assertNotIn(60, {row["pitch"] for row in report["examples"]})
        self.assertGreaterEqual(report["covered_by_active_midi"], 1)

    def test_filters_probable_harmonic_of_lower_active_note(self) -> None:
        waveform = _tone(48, amplitude=0.35) + _tone(60, amplitude=0.80)
        report = find_likely_missing_candidates(
            waveform,
            SAMPLE_RATE,
            [NoteInterval(48, 0.20, 0.80)],
        )

        self.assertNotIn(60, {row["pitch"] for row in report["examples"]})
        self.assertGreaterEqual(report["probable_harmonics_filtered"], 1)
        self.assertTrue(any(
            row["pitch"] == 60
            and row["probable_fundamental_pitch"] == 48
            for row in report["probable_harmonic_examples"]
        ))

    def test_review_respects_polyphony_budget_including_active_midi(self) -> None:
        pitches = (41, 50, 55)
        waveform = sum(
            (_tone(pitch, amplitude=0.28) for pitch in pitches),
            np.zeros(round(SAMPLE_RATE), np.float32),
        )
        report = find_likely_missing_candidates(
            waveform,
            SAMPLE_RATE,
            [
                NoteInterval(41, 0.20, 0.80),
            ],
            maximum_polyphony=2,
        )

        selected = [
            row for row in report["raw_candidates"]
            if row["disposition"] == "review_selected"
        ]
        self.assertTrue(selected)
        for attack_hop in {row["attack_hop"] for row in selected}:
            rows = [
                row for row in selected
                if row["attack_hop"] == attack_hop
            ]
            self.assertLessEqual(
                len(rows) + rows[0]["active_midi_polyphony"],
                rows[0]["maximum_polyphony"],
            )
        self.assertGreaterEqual(
            report["counts_by_level"][
                "review_rejected_by_polyphony_budget"
            ],
            1,
        )
        self.assertEqual(
            len(report["raw_candidates"]),
            report["counts_by_level"][
                "raw_spectral_pitch_detections"
            ],
        )
        self.assertTrue(all(
            row["candidate_id"]
            and row["disposition"] != "pending"
            and "review_score" in row
            and "stability_ratio" in row
            for row in report["raw_candidates"]
        ))

    def test_harmonic_stack_stays_traceable_but_out_of_review(self) -> None:
        waveform = (
            _tone(48, amplitude=0.60)
            + _tone(60, amplitude=0.80)
            + _tone(67, amplitude=0.55)
        )
        report = find_likely_missing_candidates(
            waveform,
            SAMPLE_RATE,
            [],
        )

        harmonic_rows = {
            row["pitch"]: row
            for row in report["raw_candidates"]
            if row["disposition"] == "probable_harmonic"
        }
        review_pitches = {
            row["pitch"] for row in report["review_candidates"]
        }
        self.assertIn(60, harmonic_rows)
        self.assertIn(67, harmonic_rows)
        self.assertEqual(
            harmonic_rows[60]["probable_fundamental_pitch"], 48,
        )
        self.assertNotIn(60, review_pitches)
        self.assertNotIn(67, review_pitches)
        self.assertGreater(
            report["raw_candidate_detections"], report["count"],
        )

    def test_product_policy_resamples_and_reports_exact_cadence(self) -> None:
        metadata = {
            "sample_rate": 44_100,
            "hop_samples": 256,
            "min_pitch": 40,
            "max_pitch": 76,
            "maximum_polyphony": 6,
            "audio_evidence": {
                "fft_size": 512,
                "onset_cooldown_ms": 80.0,
                "onset_rearm_ratio": 1.35,
                "onset_rearm_stable_hops": 3,
                "onset_rearm_attack_ratio": 3.0,
                "onset_rearm_flux_ratio": 2.0,
                "onset_rearm_growth_ratio": 8.0,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            (artifacts / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8",
            )
            wav = root / "input.wav"
            midi = root / "output.mid"
            sf.write(wav, _tone(60), SAMPLE_RATE, subtype="FLOAT")
            write_midi(midi, [])

            report = diagnose(wav, midi, artifacts)
            json.dumps(report)

        self.assertEqual(report["contract"]["source_sample_rate"], SAMPLE_RATE)
        self.assertEqual(report["contract"]["sample_rate"], 44_100)
        self.assertEqual(report["contract"]["hop_samples"], 256)
        self.assertTrue(report["contract"]["resampled_to_product_rate"])
        self.assertEqual(
            report["contract"]["attack_source"],
            "product_polyphonic_audio_evidence_from_bundle_metadata",
        )
        self.assertGreaterEqual(report["contract"]["attack_count"], 1)
        self.assertEqual(
            report["likely_missing_notes"]["sample_rate"], 44_100,
        )
        self.assertIn(
            60,
            {
                row["pitch"]
                for row in report["likely_missing_notes"]["examples"]
            },
        )

    def test_direct_helper_keeps_explicit_synthetic_fallback(self) -> None:
        report = find_likely_missing_candidates(
            _tone(60), SAMPLE_RATE, [],
        )

        self.assertEqual(
            report["attack_source"],
            "synthetic_test_fallback_adaptive_rms_flux",
        )
        self.assertIn("synthetic tests", (
            report["attack_diagnostics"]["purpose"]
        ))


if __name__ == "__main__":
    unittest.main()
