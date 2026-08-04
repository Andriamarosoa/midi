from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from src.polyphonic.build_independent_note_offsets import (
    build_fundamental_offset_sidecar,
    sha256_file,
)
from src.polyphonic.data import load_independent_note_fundamental_offsets


class IndependentNoteOffsetTests(unittest.TestCase):
    def test_loader_requires_signed_sorted_train_validation_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "offsets.json"
            payload = {
                "schema_version": 1,
                "locked_test_used": False,
                "manifest_sha256": "m" * 64,
                "records": [{
                    "dataset_id": "guitarset_poly_mix",
                    "source_id": "01-demo",
                    "note_fundamental_offset_cents": [12.5, -3.0],
                }],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_independent_note_fundamental_offsets(
                path,
                expected_sha256=sha256_file(path),
                expected_manifest_sha256="m" * 64,
            )
            np.testing.assert_allclose(
                loaded[("guitarset_poly_mix", "01-demo")], [12.5, -3.0]
            )
            payload["locked_test_used"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "locked test"):
                load_independent_note_fundamental_offsets(
                    path,
                    expected_sha256=sha256_file(path),
                    expected_manifest_sha256="m" * 64,
                )

    def test_generator_refuses_test_and_preserves_fractional_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            labels = root / "labels.npz"
            np.savez_compressed(labels, note_pitch_midi=np.asarray([48], np.int16))
            manifest = root / "manifest.csv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "source_id", "dataset_id", "split", "annotation_path",
                    "harmonic_csv_path", "labels_path",
                ])
                writer.writeheader()
                writer.writerow({
                    "source_id": "01-demo", "dataset_id": "guitarset_poly_mix",
                    "split": "train", "annotation_path": "note.jams",
                    "harmonic_csv_path": "harmonics.csv", "labels_path": labels,
                })
            output = root / "offsets.json"
            tables = {"note_fundamental_offset_cents": np.asarray([37.5], np.float32)}
            with mock.patch(
                "src.polyphonic.build_independent_note_offsets.load_jams_notes",
                return_value=[object()],
            ), mock.patch(
                "src.polyphonic.build_independent_note_offsets.build_harmonic_tables",
                return_value=tables,
            ):
                report = build_fundamental_offset_sidecar(manifest, output)
            self.assertFalse(report["locked_test_used"])
            self.assertEqual(report["manifest_sha256"], sha256_file(manifest))
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["records"][0]["note_fundamental_offset_cents"], [37.5]
            )

            with manifest.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "source_id", "dataset_id", "split", "annotation_path",
                    "harmonic_csv_path", "labels_path",
                ])
                writer.writerow({
                    "source_id": "locked", "dataset_id": "guitarset_poly_mix",
                    "split": "test", "annotation_path": "note.jams",
                    "harmonic_csv_path": "harmonics.csv", "labels_path": labels,
                })
            with self.assertRaisesRegex(ValueError, "locked test"):
                build_fundamental_offset_sidecar(manifest, output)


if __name__ == "__main__":
    unittest.main()
