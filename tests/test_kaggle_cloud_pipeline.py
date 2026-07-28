from __future__ import annotations

import csv
import json
import tempfile
import tarfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from zipfile import ZipFile

from scripts.cloud.kaggle_upload_progress import (
    query_upload_progress,
    upload_info_path,
    uploaded_bytes_from_range,
)
from scripts.cloud.prepare_kaggle_datasets import (
    prepare_training,
    prepare_training_archive,
)
from scripts.cloud.prepare_kaggle_source import prepare_source_dataset
from scripts.cloud.package_kaggle_outputs import package_outputs
from scripts.cloud.publish_kaggle import (
    _read_package_report,
    _task_notebook,
    publish_kernel,
)
from scripts.cloud.supervise_kaggle import STATUS_PATTERN
from scripts.project_summary import update_project_summary


class KaggleCloudPipelineTests(unittest.TestCase):
    def test_kaggle_upload_progress_uses_server_acknowledged_range(self) -> None:
        class Response:
            code = 308

            def __init__(self) -> None:
                self.headers = Message()
                self.headers["Range"] = "bytes=0-1048575"

            def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            upload = root / "payload.tar"
            upload.write_bytes(b"x" * 2_097_152)
            sidecars = root / "uploads"
            sidecars.mkdir()
            sidecar = upload_info_path(
                upload, upload_info_dir=sidecars
            )
            sidecar.write_text(
                json.dumps({
                    "path": str(upload.resolve()),
                    "start_blob_upload_request": {
                        "contentLength": upload.stat().st_size,
                    },
                    "start_blob_upload_response": {
                        "createUrl": "https://upload.example/session-secret",
                    },
                }),
                encoding="utf-8",
            )

            result = query_upload_progress(
                upload,
                upload_info_dir=sidecars,
                opener=lambda request, timeout: Response(),
            )

            self.assertEqual(result["status"], "uploading")
            self.assertEqual(result["bytes_uploaded"], 1_048_576)
            self.assertEqual(result["remaining_bytes"], 1_048_576)
            self.assertEqual(result["percent"], 50.0)
            self.assertEqual(
                uploaded_bytes_from_range("bytes=0-0"), 1
            )

    def test_training_package_excludes_locked_test_rows_and_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            labels = data / "processed/labels"
            labels.mkdir(parents=True)
            archive_path = data / "GuitarSet/audio.zip"
            archive_path.parent.mkdir(parents=True)
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("train#.wav", b"train")
                archive.writestr("validation.wav", b"validation")
                archive.writestr("test.wav", b"test")
            for split in ("train", "validation", "test"):
                suffix = "#" if split == "train" else ""
                (labels / f"{split}{suffix}.npz").write_bytes(split.encode())

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
                    suffix = "#" if split == "train" else ""
                    writer.writerow({
                        "source_id": split,
                        "dataset_id": "unit",
                        "player_id": split,
                        "group_id": split,
                        "split": split,
                        "audio_path": r"data\GuitarSet\audio.zip",
                        "audio_member": f"{split}{suffix}.wav",
                        "labels_path": (
                            rf"data\processed\labels\{split}{suffix}.npz"
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
            self.assertEqual(members, {"train#.wav", "validation.wav"})
            self.assertFalse(
                (output / "data/processed/labels/test.npz").exists()
            )
            self.assertFalse(report["locked_test_included"])

            upload = root / "upload"
            upload_report = prepare_training_archive(
                package_path=output, output_path=upload,
                part_bytes=16 * 1024 * 1024,
            )
            index = json.loads((upload / "training_archive_index.json").read_text())
            indexed_paths = {item["path"] for item in index["files"]}
            self.assertEqual(upload_report["archive_format"], "kaggle_chunked_tar_v1")
            self.assertIn("data/processed/labels/train#.npz", indexed_paths)
            self.assertNotIn("data/processed/labels/test.npz", indexed_paths)
            for archive_info in index["archives"]:
                with tarfile.open(upload / archive_info["name"], "r") as archive:
                    self.assertTrue(all(
                        name.startswith("parts/") for name in archive.getnames()
                    ))
                    self.assertFalse(any("#" in name for name in archive.getnames()))
            self.assertEqual(_read_package_report(upload)["archive_format"], "kaggle_chunked_tar_v1")

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
        source = "".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )
        self.assertIn("< (3, 13)", source)
        self.assertIn("for attempt in range(1, 4)", source)
        self.assertIn('rglob("midi_source.tar.gz")', source)
        self.assertNotIn('"pip", "install"', source)

    def test_kernel_accepts_multiple_unique_dataset_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "kernel"
            with (
                mock.patch("scripts.cloud.publish_kaggle._run"),
                mock.patch(
                    "scripts.cloud.publish_kaggle._kaggle",
                    return_value="kaggle",
                ),
            ):
                kernel = publish_kernel(
                    owner="owner",
                    dataset_handles=[
                        "owner/data-part-01",
                        "owner/data-part-02",
                    ],
                    task="smoke",
                    output_dir=output,
                    kernel_slug="smoke-shards",
                )
            metadata = json.loads(
                (output / "kernel-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(kernel, "owner/smoke-shards")
            self.assertEqual(metadata["title"], "smoke shards")
            self.assertEqual(
                metadata["dataset_sources"],
                ["owner/data-part-01", "owner/data-part-02"],
            )

    def test_source_dataset_contains_only_tracked_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "source"
            report = prepare_source_dataset(
                output_dir=output,
                handle="owner/source",
                title="Source",
            )
            self.assertTrue((output / "midi_source.tar.gz").is_file())
            self.assertFalse(report["datasets_included"])
            self.assertFalse(report["locked_test_included"])
            with tarfile.open(output / "midi_source.tar.gz", "r:gz") as archive:
                names = set(archive.getnames())
            self.assertIn("scripts/cloud/kaggle_entrypoint.py", names)
            self.assertFalse(any(
                name.startswith("data/processed/")
                and name != "data/processed/.gitkeep"
                for name in names
            ))

    def test_training_outputs_are_packaged_without_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "runs/polyphonic/run-1"
            run.mkdir(parents=True)
            (run / "best.keras").write_bytes(b"model")
            artifact = root / "artifacts/generated/run-1"
            artifact.mkdir(parents=True)
            (artifact / "model.tflite").write_bytes(b"tflite")
            result = root / "readme/results/result.md"
            result.parent.mkdir(parents=True)
            result.write_text("# result\n", encoding="utf-8")
            data = root / "data/processed"
            data.mkdir(parents=True)
            (data / "must-not-be-packaged.npz").write_bytes(b"private")
            pipeline = {
                "run_dir": str(run),
                "artifact_dir": str(artifact),
                "result_readme": str(result),
                "locked_test_used": False,
            }
            (run / "cloud_pipeline.json").write_text(
                json.dumps(pipeline), encoding="utf-8"
            )

            output = root / "output"
            manifest = package_outputs(
                task="train", output_dir=output, root=root
            )
            with tarfile.open(output / manifest["archive"], "r") as archive:
                names = set(archive.getnames())

            self.assertIn("run/run-1/best.keras", names)
            self.assertIn("artifacts/run-1/model.tflite", names)
            self.assertIn("readme/results/result.md", names)
            self.assertFalse(any(name.startswith("data/") for name in names))
            self.assertFalse(manifest["locked_test_used"])

    def test_kaggle_kernel_status_is_parsed(self) -> None:
        output = (
            'tinahandriamarosoa/guitar-midi-polyphonic-smoke '
            'has status "complete"'
        )
        match = STATUS_PATTERN.search(output)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "complete")

    def test_project_summary_updates_status_and_deduplicates_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = Path(temporary) / "README.md"
            summary.write_text(
                "# Summary\n\n"
                "<!-- CURRENT_STATUS_START -->\nold\n"
                "<!-- CURRENT_STATUS_END -->\n\n"
                "<!-- JOURNAL_START -->\n"
                "<!-- JOURNAL_END -->\n",
                encoding="utf-8",
            )
            moment = datetime(2026, 7, 28, tzinfo=timezone.utc)
            first = update_project_summary(
                task_id="kaggle_smoke",
                phase="smoke_running",
                status="en cours",
                detail="smoke actif",
                next_steps=("attendre",),
                summary_path=summary,
                timestamp=moment,
            )
            second = update_project_summary(
                task_id="kaggle_smoke",
                phase="smoke_passed",
                status="terminé",
                detail="smoke réussi",
                next_steps=("comparer",),
                summary_path=summary,
                timestamp=moment,
            )
            text = summary.read_text(encoding="utf-8")

            self.assertTrue(first)
            self.assertFalse(second)
            self.assertIn("- Étape : `smoke_passed`", text)
            self.assertIn("1. comparer", text)
            self.assertNotIn("smoke actif", text)
            self.assertEqual(text.count("smoke réussi"), 2)
            self.assertEqual(
                text.count("PROJECT_TASK:kaggle_smoke:START"), 1
            )


if __name__ == "__main__":
    unittest.main()
