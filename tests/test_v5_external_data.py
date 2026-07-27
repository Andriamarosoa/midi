from __future__ import annotations

import csv
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from src.v5.external_data import (
    SourceRecording,
    build_recording_arrays,
    parse_midi_notes,
)
from src.v5.manifest import load_manifest, split_manifest


def _write_test_midi(path: Path) -> None:
    track = bytes([
        0x00, 0x90, 60, 100,
        0x83, 0x60, 0x80, 60, 0,
        0x00, 0xFF, 0x2F, 0x00,
    ])
    content = (
        b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        + b"MTrk" + struct.pack(">I", len(track)) + track
    )
    path.write_bytes(content)


def _write_silent_wav(
    path: Path,
    duration_s: float = 1.0,
    sample_rate: int = 44_100,
) -> None:
    frames = int(round(sample_rate * duration_s))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(np.zeros(frames, dtype="<i2").tobytes())


def _write_sine_wav(
    path: Path,
    frequency_hz: float,
    duration_s: float = 1.0,
    sample_rate: int = 44_100,
) -> None:
    time = np.arange(int(round(sample_rate * duration_s))) / sample_rate
    samples = np.asarray(
        np.clip(0.5 * np.sin(2.0 * np.pi * frequency_hz * time), -1.0, 1.0)
        * 32767.0,
        dtype="<i2",
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


class ExternalDataTests(unittest.TestCase):
    def test_standard_midi_parser_converts_ticks_to_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one_note.mid"
            _write_test_midi(path)

            notes = parse_midi_notes(path)

        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].pitch_midi, 60)
        self.assertAlmostEqual(notes[0].start_s, 0.0)
        self.assertAlmostEqual(notes[0].end_s, 0.5)

    def test_builder_keeps_only_solo_active_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio.wav"
            annotation = root / "notes.xml"
            _write_silent_wav(audio, sample_rate=48_000)
            annotation.write_text(
                """<root><events>
                <event><pitch>60</pitch><onsetSec>0.0</onsetSec><offsetSec>0.5</offsetSec><expressionStyle>NO</expressionStyle></event>
                <event><pitch>64</pitch><onsetSec>0.1</onsetSec><offsetSec>0.3</offsetSec><expressionStyle>NO</expressionStyle></event>
                <event><pitch>67</pitch><onsetSec>0.6</onsetSec><offsetSec>0.95</offsetSec><expressionStyle>NO</expressionStyle></event>
                </events></root>""",
                encoding="utf-8",
            )
            recording = SourceRecording(
                dataset_id="test",
                source_id="test_source",
                audio_path=audio,
                annotation_path=annotation,
                annotation_format="idmt_xml",
                player_id="player",
                group_id="group",
                capture_id="mono",
                split="train",
                license_id="test",
            )

            arrays, report = build_recording_arrays(recording, 40, 76)

        self.assertEqual(arrays["audio"].shape, (10, 4096))
        self.assertEqual(set(arrays["pitch_midi"].tolist()), {60, 67})
        self.assertEqual(report["notes_selected"], 2)
        self.assertGreater(report["rejected_polyphonic_requests"], 0)
        self.assertEqual(report["source_sample_rate"], 48_000)
        self.assertEqual(report["resampled"], 1)
        self.assertTrue(np.all(arrays["active"] == 1.0))

    def test_builder_adds_mono_release_and_silence_negatives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio.wav"
            annotation = root / "notes.xml"
            _write_sine_wav(audio, 261.625565, duration_s=1.0)
            annotation.write_text(
                """<root><events><event>
                <pitch>60</pitch><onsetSec>0.0</onsetSec><offsetSec>0.5</offsetSec>
                <expressionStyle>NO</expressionStyle>
                </event></events></root>""",
                encoding="utf-8",
            )
            recording = SourceRecording(
                dataset_id="test",
                source_id="inactive_test",
                audio_path=audio,
                annotation_path=annotation,
                annotation_format="idmt_xml",
                player_id="player",
                group_id="group",
                capture_id="mono",
                split="train",
                license_id="test",
            )

            arrays, report = build_recording_arrays(
                recording,
                40,
                76,
                include_inactive=True,
                release_ms=(20.0, 50.0),
                silence_per_recording=2,
                silence_guard_ms=80.0,
                seed=42,
            )

        self.assertEqual(report["active_samples"], 6)
        self.assertEqual(report["release_samples"], 2)
        self.assertEqual(report["silence_samples"], 2)
        self.assertEqual(report["inactive_samples"], 4)
        self.assertEqual(arrays["audio"].shape, (10, 4096))
        self.assertTrue(np.all(arrays["active"][:6] == 1.0))
        self.assertEqual(int(np.sum(arrays["release_phase"] > 0.5)), 2)
        self.assertEqual(int(np.sum(arrays["pitch_midi"] == -1)), 2)

    def test_builder_accepts_extended_temporal_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio.wav"
            annotation = root / "notes.xml"
            _write_sine_wav(audio, 261.625565, duration_s=1.5)
            annotation.write_text(
                """<root><events><event>
                <pitch>60</pitch><onsetSec>0.0</onsetSec><offsetSec>1.0</offsetSec>
                <expressionStyle>NO</expressionStyle>
                </event></events></root>""",
                encoding="utf-8",
            )
            recording = SourceRecording(
                dataset_id="test",
                source_id="temporal_test",
                audio_path=audio,
                annotation_path=annotation,
                annotation_format="idmt_xml",
                player_id="player",
                group_id="group",
                capture_id="mono",
                split="train",
                license_id="test",
            )
            arrays, report = build_recording_arrays(
                recording,
                40,
                76,
                sustain_ms=(120.0, 220.0, 350.0, 500.0, 750.0),
                include_inactive=True,
                release_ms=(20.0, 50.0, 100.0, 200.0),
                silence_per_recording=0,
            )

        self.assertEqual(report["active_samples"], 9)
        self.assertEqual(report["release_samples"], 4)
        self.assertEqual(arrays["audio"].shape, (13, 4096))
        self.assertTrue(np.any(np.isclose(arrays["prediction_age_ms"], 750.0)))
        self.assertTrue(np.any(np.isclose(arrays["prediction_age_ms"], 200.0)))

    def test_harmonic_extraction_recovers_sine_fundamental(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "sine.wav"
            annotation = root / "note.xml"
            _write_sine_wav(audio, 440.0)
            annotation.write_text(
                """<root><events><event>
                <pitch>69</pitch><onsetSec>0.0</onsetSec><offsetSec>0.8</offsetSec>
                <expressionStyle>NO</expressionStyle>
                </event></events></root>""",
                encoding="utf-8",
            )
            recording = SourceRecording(
                dataset_id="test",
                source_id="harmonic_sine",
                audio_path=audio,
                annotation_path=annotation,
                annotation_format="idmt_xml",
                player_id="player",
                group_id="group",
                capture_id="mono",
                split="train",
                license_id="test",
            )

            arrays, report = build_recording_arrays(
                recording, 40, 76, extract_harmonics=True
            )

        self.assertEqual(arrays["harmonic_label_valid"].shape, (6, 20))
        self.assertTrue(np.all(arrays["harmonic_label_valid"][:, 0] == 1.0))
        self.assertTrue(np.all(arrays["harmonic_present"][:, 0] == 1.0))
        self.assertTrue(np.all(arrays["harmonic_amplitude"][:, 0] > 0.99))
        self.assertLess(float(np.max(np.abs(arrays["harmonic_offset_cents"][:, 0]))), 5.0)
        self.assertEqual(report["harmonic_label_source"], "audio_fft")
        self.assertEqual(report["harmonic_labeled_notes"], 1)
        self.assertEqual(report["harmonic_labeled_samples"], 6)

    def test_explicit_manifest_split_and_group_leakage_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fieldnames = [
                "source_id", "npz_path", "player_id", "dataset_id",
                "group_id", "capture_id", "split",
            ]
            rows = []
            for split in ("train", "validation", "test"):
                npz = root / f"{split}.npz"
                np.savez(npz, audio=np.zeros((1, 4096), dtype=np.float32))
                rows.append({
                    "source_id": split,
                    "npz_path": str(npz),
                    "player_id": f"external_{split}",
                    "dataset_id": "external",
                    "group_id": split,
                    "capture_id": "mono",
                    "split": split,
                })
            manifest = root / "manifest.csv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            items = load_manifest(manifest)
            splits = split_manifest(items, ("00",), ("04",), ("05",))
            self.assertEqual({key: len(value) for key, value in splits.items()}, {
                "train": 1, "validation": 1, "test": 1,
            })

            leaked = list(items)
            leaked[1] = type(leaked[1])(
                **{**leaked[1].__dict__, "group_id": leaked[0].group_id}
            )
            with self.assertRaisesRegex(ValueError, "plusieurs splits"):
                split_manifest(leaked, ("00",), ("04",), ("05",))


if __name__ == "__main__":
    unittest.main()
