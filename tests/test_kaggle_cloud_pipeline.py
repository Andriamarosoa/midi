from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.cloud.prepare_kaggle_datasets import prepare_training
from scripts.cloud.publish_kaggle import _task_notebook


class KaggleCloudPipelineTests(unittest.TestCase):
    def test_training_package_excludes_locked_test_rows_and_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            labels = data / "processed/labels"
            labels.mkdir(parents=True)
            archive_path = data / "GuitarSet/audio.zip"
            archive_path.parent.mkdir(parents=True)
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("train.wav", b"train")
                archive.writestr("validation.wav", b"validation")
                archive.writestr("test.wav", b"test")
            for split in ("train", "validation", "test"):
                (labels / f"{split}.npz").write_bytes(split.encode())

            manifest = (
                data / "processed/polyphonic_v2_2_combined/manifest.csv"
            )
            manifest.parent.mkdir(parents=True)
            fields = [
                "source_id", "dataset_id", "player_id", "group_id", "split",
                "audio_path", "audio_member", "labels_path",
                "annotation_path", "harmonic_csv_path", "capture_id",
                "license_id",
            ]
            with manifest.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for split in ("train", "validation", "test"):
                    writer.writerow({
                        "source_id": split,
                        "dataset_id": "unit",
                        "player_id": split,
                        "group_id": split,
                        "split": split,
                        "audio_path": r"data\GuitarSet\audio.zip",
                        "audio_member": f"{split}.wav",
                        "labels_path": (
                            rf"data\processed\labels\{split}.npz"
                        ),
                        "annotation_path": f"raw/{split}.mid",
                        "harmonic_csv_path": f"raw/{split}.csv",
                        "capture_id": "clean",
                        "license_id": "CC-BY-4.0",
                    })

            output = root / "package"
            report = prepare_training(
                root=root,
                manifest_path=manifest,
                output_path=output,
            )

            packaged_manifest = (
                output / "data/processed/polyphonic_v2_2_combined/manifest.csv"
            )
            with packaged_manifest.open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            with ZipFile(output / "data/GuitarSet/audio.zip") as archive:
                members = set(archive.namelist())

            self.assertEqual(
                {row["split"] for row in rows}, {"train", "validation"}
            )
            self.assertEqual(members, {"train.wav", "validation.wav"})
            self.assertFalse(
                (output / "data/processed/labels/test.npz").exists()
            )
            self.assertFalse(report["locked_test_included"])

    def test_kernel_notebook_task_is_generated_without_other_edits(self) -> None:
        notebook = _task_notebook("rebuild")
        task_lines = [
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
            if line.startswith("TASK = ")
        ]
        self.assertEqual(len(task_lines), 1)
        self.assertIn('"rebuild"', task_lines[0])


if __name__ == "__main__":
    unittest.main()
