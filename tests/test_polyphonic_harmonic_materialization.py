from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.polyphonic.materialize_harmonic_supervision import materialize
from src.polyphonic.validate_dataset import validate


FIELDS = (
    "source_id",
    "dataset_id",
    "player_id",
    "group_id",
    "split",
    "audio_path",
    "audio_member",
    "labels_path",
    "annotation_path",
    "harmonic_csv_path",
    "capture_id",
    "license_id",
)


def _write_labels(path: Path) -> None:
    np.savez_compressed(
        path,
        active_bits=np.asarray([1, 0], np.uint64),
        onset_bits=np.asarray([1, 0], np.uint64),
        polyphony=np.asarray([1, 0], np.uint8),
        valid=np.ones(2, np.uint8),
        slot_pitch=np.asarray([[0], [-1]], np.int8),
        slot_note_id=np.asarray([[0], [-1]], np.int32),
        note_harmonic_present=np.asarray([[1, 1]], np.uint8),
        note_harmonic_amplitude=np.asarray([[1.0, 0.1]], np.float16),
        note_harmonic_offset_cents=np.zeros((1, 2), np.float16),
        note_harmonic_valid=np.ones(1, np.uint8),
        note_pitch_midi=np.asarray([40], np.int16),
        note_start_s=np.asarray([0.0], np.float32),
        note_end_s=np.asarray([1.0], np.float32),
        note_evaluation_valid=np.ones(1, np.uint8),
        sample_rate=np.int32(44_100),
        hop_size=np.int32(256),
        audio_frames=np.int64(44_100),
        midi_min=np.int16(40),
        midi_max=np.int16(76),
    )


def _write_jams(path: Path) -> None:
    path.write_text(json.dumps({
        "annotations": [{
            "namespace": "note_midi",
            "annotation_metadata": {"data_source": 0},
            "data": [{"time": 0.0, "duration": 1.0, "value": 40}],
        }],
    }), encoding="utf-8")


def _write_harmonics(path: Path) -> None:
    path.write_text(
        "note_id,channel,start_s,end_s,fundamental_hz,harmonic_number,"
        "expected_hz,measured_hz,relative_db,frames_measured\n"
        "0,0,0.0,1.0,82.4069,1,82.4069,82.4069,20,4\n"
        "0,0,0.0,1.0,82.4069,2,164.8138,164.8138,-70,2\n",
        encoding="utf-8",
    )


def _row(
    source_id: str,
    split: str,
    labels: str,
    annotation: str,
    harmonics: str,
    *,
    dataset_id: str = "guitarset_poly_mix",
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "dataset_id": dataset_id,
        "player_id": source_id,
        "group_id": f"group_{source_id}",
        "split": split,
        "audio_path": "audio.wav",
        "audio_member": "",
        "labels_path": labels,
        "annotation_path": annotation,
        "harmonic_csv_path": harmonics,
        "capture_id": "unit",
        "license_id": "unit",
    }


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class HarmonicMaterializationTests(unittest.TestCase):
    def test_materializer_excludes_test_without_resolving_its_artifacts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio.wav").write_bytes(b"unit")
            for split in ("train", "validation"):
                _write_labels(root / f"{split}.npz")
                _write_jams(root / f"{split}.jams")
                _write_harmonics(root / f"{split}.csv")
            _write_labels(root / "gaps.npz")
            manifest = root / "source.csv"
            _write_manifest(manifest, [
                _row("train", "train", "train.npz", "train.jams", "train.csv"),
                _row(
                    "validation", "validation", "validation.npz",
                    "validation.jams", "validation.csv",
                ),
                _row(
                    "gaps", "train", "gaps.npz", "", "",
                    dataset_id="gaps_poly_mix",
                ),
                _row(
                    "locked", "test", "missing-test.npz",
                    "missing-test.jams", "missing-test.csv",
                ),
            ])

            report = materialize(
                manifest, root / "output", repository_root=root
            )
            output_manifest = Path(report["manifest"])
            self.assertEqual(
                output_manifest.name, "manifest_train_validation.csv"
            )
            with output_manifest.open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))

            self.assertFalse(report["locked_test_used"])
            self.assertTrue(report["validator_passed"])
            self.assertEqual(report["excluded_rows_by_split"], {"test": 1})
            self.assertNotIn("locked", {row["source_id"] for row in rows})
            self.assertEqual({row["split"] for row in rows}, {
                "train", "validation",
            })
            self.assertTrue(all(not Path(row["audio_path"]).is_absolute() for row in rows))
            self.assertTrue(all(not Path(row["labels_path"]).is_absolute() for row in rows))
            self.assertEqual(len(report["guitarset_artifacts"]), 2)
            self.assertEqual(len(report["manifest_sha256"]), 64)
            self.assertFalse((root / "missing-test.npz").exists())

            guitarset_row = next(
                row for row in rows if row["source_id"] == "train"
            )
            with np.load(
                output_manifest.parent / guitarset_row["labels_path"],
                allow_pickle=False,
            ) as arrays:
                self.assertEqual(
                    int(arrays["harmonic_supervision_schema_version"]), 3
                )
                self.assertEqual(
                    str(arrays["harmonic_reliability_formula"]),
                    "sqrt(n/(n+1))",
                )
                self.assertEqual(
                    arrays["note_harmonic_supervised"][0, :2].tolist(), [1, 1]
                )
                self.assertEqual(
                    arrays["note_harmonic_present"][0, :2].tolist(), [1, 0]
                )
                np.testing.assert_allclose(
                    arrays["note_harmonic_amplitude"][0, :2],
                    [1.0, 10.0 ** (-90.0 / 20.0)],
                    atol=2e-3,
                )

    def test_strict_validator_rejects_legacy_harmonic_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio.wav").write_bytes(b"unit")
            _write_labels(root / "legacy.npz")
            manifest = root / "manifest.csv"
            _write_manifest(manifest, [
                _row(
                    "legacy", "train", str(root / "legacy.npz"), "", ""
                ),
            ])

            report = validate(
                manifest,
                require_harmonic_schema_version=3,
                harmonic_dataset_ids={"guitarset_poly_mix"},
                allowed_splits={"train"},
                required_splits={"train"},
            )

            self.assertFalse(report["passed"])
            self.assertTrue(any(
                "schema 3 is required" in failure
                for failure in report["failures"]
            ))


if __name__ == "__main__":
    unittest.main()
