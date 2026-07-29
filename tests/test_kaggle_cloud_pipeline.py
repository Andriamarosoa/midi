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
from scripts.cloud.kaggle_entrypoint import (
    find_checkpoint_run,
    _resolve_visible_audio_location,
    _resolve_visible_shard_path,
    _training_control_arguments,
    stage_training_shards,
)
from scripts.cloud.prepare_kaggle_datasets import (
    prepare_training,
    prepare_training_archive,
)
from scripts.cloud.prepare_kaggle_source import prepare_source_dataset
from scripts.cloud.prepare_kaggle_selection import (
    prepare_selection_kernel,
)
from scripts.cloud.package_kaggle_outputs import package_outputs
from scripts.cloud.publish_kaggle import (
    _read_package_report,
    _task_notebook,
    publish_kernel,
)
from scripts.cloud.supervise_kaggle import STATUS_PATTERN
from scripts.cloud.train_polyphonic import (
    _recovery_roundtrip_command,
    _src_training_arguments,
)
from scripts.project_summary import update_project_summary


class KaggleCloudPipelineTests(unittest.TestCase):
    @staticmethod
    def _write_visible_shard(
        root: Path,
        *,
        source_id: str,
        split: str,
        audio_path: str,
        audio_member: str,
        labels_path: str,
        actual_audio_path: str,
        actual_labels_path: str,
    ) -> Path:
        data_root = root / "data"
        audio = data_root / Path(actual_audio_path).relative_to("data")
        labels = data_root / Path(actual_labels_path).relative_to("data")
        audio.parent.mkdir(parents=True, exist_ok=True)
        labels.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(f"audio-{source_id}".encode())
        labels.write_bytes(f"labels-{source_id}".encode())
        manifest = (
            data_root
            / "processed/polyphonic_v2_2_combined/"
            "manifest_kaggle_safe.csv"
        )
        manifest.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "source_id", "dataset_id", "player_id", "group_id", "split",
            "audio_path", "audio_member", "labels_path",
            "annotation_path", "harmonic_csv_path", "capture_id",
            "license_id",
        ]
        with manifest.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "source_id": source_id,
                "dataset_id": "unit",
                "player_id": source_id,
                "group_id": source_id,
                "split": split,
                "audio_path": audio_path,
                "audio_member": audio_member,
                "labels_path": labels_path,
                "annotation_path": "",
                "harmonic_csv_path": "",
                "capture_id": "clean",
                "license_id": "CC-BY-4.0",
            })
        return manifest

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
        notebook = _task_notebook(
            "rebuild",
            source_dataset_slug="guitar-midi-polyphonic-code-6ce57898",
            config_path="configs/polyphonic_dual_stream_bass.yaml",
            initial_checkpoint_name="epoch-08.keras",
        )
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
        self.assertNotIn('"git", "clone"', source)
        self.assertIn('rglob("midi_source.tar.gz")', source)
        self.assertIn('rglob("midi_source")', source)
        self.assertIn(
            'SOURCE_DATASET_SLUG = "guitar-midi-polyphonic-code-6ce57898"',
            source,
        )
        self.assertIn("MAXIMUM_EXAMPLES = 60000", source)
        self.assertIn(
            'CONFIG_PATH = "configs/polyphonic_dual_stream_bass.yaml"',
            source,
        )
        self.assertIn('"--config", CONFIG_PATH', source)
        self.assertIn(
            'INITIAL_CHECKPOINT_NAME = "epoch-08.keras"',
            source,
        )
        self.assertIn('"--initial-checkpoint-name"', source)
        self.assertIn("MAXIMUM_RECORDINGS = 12", source)
        self.assertIn("MAXIMUM_CANDIDATES = 8", source)
        self.assertIn("WORKERS = 4", source)
        self.assertIn("SMOKE_EXAMPLES = 8192", source)
        self.assertIn("SMOKE_VALIDATION_EXAMPLES = 2048", source)
        self.assertIn("LOG_EVERY_BATCHES = 25", source)
        self.assertIn("RECOVERY_CHUNK_BATCHES = 250", source)
        self.assertIn("MAXIMUM_RUNTIME_MINUTES = 600.0", source)
        self.assertIn(
            '"--maximum-examples", str(MAXIMUM_EXAMPLES)',
            source,
        )
        self.assertIn('"--workers", str(WORKERS)', source)
        self.assertIn('"--smoke-examples", str(SMOKE_EXAMPLES)', source)
        self.assertIn(
            '"--smoke-validation-examples", '
            "str(SMOKE_VALIDATION_EXAMPLES)",
            source,
        )
        self.assertIn(
            '"--log-every-batches", str(LOG_EVERY_BATCHES)', source
        )
        self.assertIn(
            '"--recovery-chunk-batches", '
            "str(RECOVERY_CHUNK_BATCHES)",
            source,
        )
        self.assertIn(
            '"--maximum-runtime-minutes", '
            "str(MAXIMUM_RUNTIME_MINUTES)",
            source,
        )
        self.assertIn('"keras"', source)
        self.assertIn('subprocess.run(["nvidia-smi"]', source)
        self.assertIn('"PYTHONUNBUFFERED"', source)
        self.assertIn("write_through=True", source)
        self.assertIn("mounted_roots", source)
        self.assertIn('input_root.rglob("pyproject.toml")', source)
        self.assertIn(
            'expected_source_root.rglob("source_metadata.json")',
            source,
        )
        self.assertIn('"mounted_inputs"', source)
        self.assertIn("shutil.copytree(source_snapshot, workspace)", source)
        self.assertNotIn('"pip", "install"', source)

    def test_rank_probe_injects_validation_example_limit(self) -> None:
        notebook = _task_notebook(
            "rank",
            source_dataset_slug="guitar-midi-polyphonic-code-probe",
            maximum_examples=128,
        )
        source = "".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )
        self.assertIn("MAXIMUM_EXAMPLES = 128", source)

    def test_smoke_kernel_injects_representative_runtime_controls(self) -> None:
        notebook = _task_notebook(
            "smoke",
            source_dataset_slug="guitar-midi-polyphonic-code-smoke",
            workers=3,
            smoke_examples=4096,
            smoke_validation_examples=1024,
            log_every_batches=10,
            recovery_chunk_batches=32,
            maximum_runtime_minutes=27.5,
        )
        source = "".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )
        self.assertIn("WORKERS = 3", source)
        self.assertIn("SMOKE_EXAMPLES = 4096", source)
        self.assertIn("SMOKE_VALIDATION_EXAMPLES = 1024", source)
        self.assertIn("LOG_EVERY_BATCHES = 10", source)
        self.assertIn("RECOVERY_CHUNK_BATCHES = 32", source)
        self.assertIn("MAXIMUM_RUNTIME_MINUTES = 27.5", source)

    def test_entrypoint_separates_smoke_and_train_controls(self) -> None:
        smoke = _training_control_arguments(
            task="smoke",
            workers=3,
            smoke_examples=8192,
            smoke_validation_examples=2048,
            log_every_batches=25,
            recovery_chunk_batches=32,
            maximum_runtime_minutes=None,
        )
        train = _training_control_arguments(
            task="train",
            workers=2,
            smoke_examples=8192,
            smoke_validation_examples=2048,
            log_every_batches=25,
            recovery_chunk_batches=250,
            maximum_runtime_minutes=None,
        )
        self.assertIn("--representative-smoke", smoke)
        self.assertIn("--smoke-test", smoke)
        self.assertEqual(
            smoke[smoke.index("--maximum-runtime-minutes") + 1], "30.0"
        )
        self.assertEqual(
            smoke[smoke.index("--recovery-chunk-batches") + 1], "32"
        )
        self.assertNotIn("--skip-post-train", smoke)
        self.assertIn("--skip-post-train", train)
        self.assertNotIn("--smoke-test", train)
        self.assertEqual(
            train[train.index("--maximum-runtime-minutes") + 1], "600.0"
        )

    def test_cloud_orchestrator_forwards_workers_to_src_trainer(self) -> None:
        arguments = _src_training_arguments(
            workers=3,
            smoke_test=True,
            representative_smoke=True,
            smoke_examples=8192,
            smoke_validation_examples=2048,
            log_every_batches=25,
            recovery_chunk_batches=32,
            maximum_runtime_minutes=None,
        )
        self.assertEqual(arguments[arguments.index("--workers") + 1], "3")
        self.assertIn("--representative-smoke", arguments)
        self.assertEqual(
            arguments[arguments.index("--maximum-runtime-minutes") + 1],
            "30.0",
        )
        self.assertEqual(
            arguments[arguments.index("--recovery-chunk-batches") + 1],
            "32",
        )

    def test_recovery_roundtrip_runs_as_importable_module(self) -> None:
        command = _recovery_roundtrip_command(Path("runs/polyphonic/probe"))
        self.assertEqual(command[1:3], (
            "-m",
            "scripts.cloud.verify_recovery_checkpoint",
        ))
        self.assertNotIn("verify_recovery_checkpoint.py", command)

    def test_select_injects_event_evaluation_limits(self) -> None:
        notebook = _task_notebook(
            "select",
            source_dataset_slug="guitar-midi-polyphonic-code-select",
            maximum_recordings=12,
            maximum_candidates=8,
        )
        source = "".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )
        self.assertIn('TASK = "select"', source)
        self.assertIn("MAXIMUM_RECORDINGS = 12", source)
        self.assertIn("MAXIMUM_CANDIDATES = 8", source)

    def test_selection_kernel_reuses_private_rank_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "selection"
            kernel = prepare_selection_kernel(
                output_dir=output,
                owner="owner",
                kernel_slug="validation-selection",
                source_dataset="owner/guitar-midi-polyphonic-code-d8ce1392",
                data_datasets=["data/part-01", "data/part-02"],
                rank_kernel="owner/rank-full",
            )
            metadata = json.loads(
                (output / "kernel-metadata.json").read_text(encoding="utf-8")
            )
            notebook = json.loads(
                (output / "polyphonic_select.ipynb").read_text(
                    encoding="utf-8"
                )
            )
            source = "".join(
                line
                for cell in notebook["cells"]
                for line in cell.get("source", [])
            )
            self.assertEqual(kernel, "owner/validation-selection")
            self.assertEqual(metadata["kernel_sources"], ["owner/rank-full"])
            self.assertNotIn("owner/local-checkpoints", metadata["dataset_sources"])
            self.assertIn("guitar-midi-rank-results.tar", source)
            self.assertIn("sys.path.insert(0, str(workspace))", source)
            self.assertIn('"src.polyphonic.select_final_checkpoint"', source)
            self.assertIn('task="select"', source)

    def test_kernel_accepts_multiple_unique_dataset_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "kernel"
            shards = [
                "data-owner/guitar-midi-polyphonic-data-part-"
                f"{index:02d}"
                for index in range(1, 17)
            ]
            with (
                mock.patch(
                    "scripts.cloud.publish_kaggle._run"
                ) as run_mock,
                mock.patch(
                    "scripts.cloud.publish_kaggle._kaggle",
                    return_value="kaggle",
                ),
            ):
                kernel = publish_kernel(
                    owner="owner",
                    dataset_handles=shards + [
                        "owner/guitar-midi-polyphonic-code-6ce57898"
                    ],
                    task="smoke",
                    output_dir=output,
                    kernel_slug="smoke-shards",
                    accelerator="NvidiaTeslaT4",
                )
            metadata = json.loads(
                (output / "kernel-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(kernel, "owner/smoke-shards")
            self.assertEqual(metadata["title"], "smoke shards")
            self.assertEqual(
                metadata["dataset_sources"],
                shards
                + ["owner/guitar-midi-polyphonic-code-6ce57898"],
            )
            notebook = json.loads(
                (output / "polyphonic_smoke.ipynb").read_text(
                    encoding="utf-8"
                )
            )
            source = "".join(
                line
                for cell in notebook["cells"]
                for line in cell.get("source", [])
            )
            self.assertIn(
                'SOURCE_DATASET_SLUG = '
                '"guitar-midi-polyphonic-code-6ce57898"',
                source,
            )
            self.assertEqual(
                run_mock.call_args.args[0][-2:],
                ["--accelerator", "NvidiaTeslaT4"],
            )

    def test_smoke_kernel_refuses_missing_visible_training_shards(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "all 16"):
                publish_kernel(
                    owner="owner",
                    dataset_handles=[
                        "owner/guitar-midi-polyphonic-code-probe",
                        "owner/checkpoints",
                    ],
                    task="smoke",
                    output_dir=Path(temporary) / "kernel",
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
            package_report = _read_package_report(output)
            self.assertTrue(package_report["passed"])
            self.assertEqual(package_report["kind"], "source_snapshot")
            self.assertFalse(package_report["datasets_included"])
            self.assertFalse(package_report["locked_test_included"])
            with tarfile.open(output / "midi_source.tar.gz", "r:gz") as archive:
                names = set(archive.getnames())
            self.assertIn("scripts/cloud/kaggle_entrypoint.py", names)
            self.assertFalse(any(name.startswith("data/") for name in names))
            self.assertFalse(any(name.startswith("artifacts/") for name in names))
            self.assertFalse(any(name.startswith("runs/") for name in names))

    def test_kaggle_truncated_shard_path_is_resolved_uniquely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary) / "data"
            directory = (
                data_root
                / "processed/polyphonic_v2_2_guitar_techs/audio"
            )
            directory.mkdir(parents=True)
            truncated = directory / "gtech_long_directin"
            truncated.write_bytes(b"audio")
            resolved = _resolve_visible_shard_path(
                data_root,
                "data/processed/polyphonic_v2_2_guitar_techs/audio/"
                "gtech_long_directinput.npy",
            )
            self.assertEqual(
                resolved,
                "data/processed/polyphonic_v2_2_guitar_techs/audio/"
                "gtech_long_directin",
            )

    def test_checkpoint_run_discovery_requires_one_complete_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "attached/run-1"
            epochs = run / "epochs"
            epochs.mkdir(parents=True)
            (run / "history.csv").write_text("epoch\n", encoding="utf-8")
            (run / "config.json").write_text("{}", encoding="utf-8")
            (epochs / "epoch-01.keras").write_bytes(b"model")

            self.assertEqual(find_checkpoint_run(root), run)

    def test_kaggle_auto_extracted_zip_member_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary) / "data"
            audio = (
                data_root
                / "GuitarSet/audio_mono-pickup_mix/00_example.wav"
            )
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"wav")

            resolved, member = _resolve_visible_audio_location(
                data_root,
                "data/GuitarSet/audio_mono-pickup_mix.zip",
                "00_example.wav",
            )

            self.assertEqual(
                resolved,
                "data/GuitarSet/audio_mono-pickup_mix/00_example.wav",
            )
            self.assertEqual(member, "")

    def test_training_shards_are_materialized_with_logical_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            project = temporary_root / "workspace"
            (project / "data/processed").mkdir(parents=True)
            (project / "data/processed/.gitkeep").touch()
            train_manifest = self._write_visible_shard(
                temporary_root / "part-01",
                source_id="train-recording",
                split="train",
                audio_path="data/processed/audio/train-recording.npy",
                audio_member="",
                labels_path="data/processed/labels/train-recording.npz",
                actual_audio_path="data/processed/audio/train-recording.np",
                actual_labels_path="data/processed/labels/train-recording.np",
            )
            validation_manifest = self._write_visible_shard(
                temporary_root / "part-02",
                source_id="validation-recording",
                split="validation",
                audio_path="data/GuitarSet/audio.zip",
                audio_member="validation.wav",
                labels_path="data/processed/labels/validation-recording.npz",
                actual_audio_path=(
                    "data/GuitarSet/audio/validation.wav"
                ),
                actual_labels_path=(
                    "data/processed/labels/validation-recording.npz"
                ),
            )

            with mock.patch(
                "scripts.cloud.kaggle_entrypoint.ROOT", project
            ):
                combined = stage_training_shards(
                    [train_manifest, validation_manifest],
                    minimum_free_bytes=0,
                )

            with combined.open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                rows = {
                    row["source_id"]: row for row in csv.DictReader(handle)
                }
            train = rows["train-recording"]
            validation = rows["validation-recording"]
            self.assertEqual(
                train["audio_path"],
                "data/shards/part-01/processed/audio/train-recording.npy",
            )
            self.assertEqual(
                train["labels_path"],
                "data/shards/part-01/processed/labels/train-recording.npz",
            )
            self.assertEqual(
                validation["audio_path"],
                "data/shards/part-02/GuitarSet/audio/validation.wav",
            )
            self.assertEqual(validation["audio_member"], "")
            self.assertEqual(
                {row["split"] for row in rows.values()},
                {"train", "validation"},
            )
            self.assertFalse((project / "data/shards/part-01").is_symlink())
            self.assertEqual(
                (project / train["audio_path"]).read_bytes(),
                b"audio-train-recording",
            )
            self.assertEqual(
                (project / validation["audio_path"]).read_bytes(),
                b"audio-validation-recording",
            )

    def test_training_shard_space_guard_runs_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            project = temporary_root / "workspace"
            (project / "data/processed").mkdir(parents=True)
            (project / "data/processed/.gitkeep").touch()
            train_manifest = self._write_visible_shard(
                temporary_root / "part-01",
                source_id="train-recording",
                split="train",
                audio_path="data/audio/train.npy",
                audio_member="",
                labels_path="data/labels/train.npz",
                actual_audio_path="data/audio/train.npy",
                actual_labels_path="data/labels/train.npz",
            )
            validation_manifest = self._write_visible_shard(
                temporary_root / "part-02",
                source_id="validation-recording",
                split="validation",
                audio_path="data/audio/validation.npy",
                audio_member="",
                labels_path="data/labels/validation.npz",
                actual_audio_path="data/audio/validation.npy",
                actual_labels_path="data/labels/validation.npz",
            )

            with (
                mock.patch(
                    "scripts.cloud.kaggle_entrypoint.ROOT", project
                ),
                mock.patch(
                    "scripts.cloud.kaggle_entrypoint.shutil.disk_usage",
                    return_value=mock.Mock(free=1),
                ),
            ):
                with self.assertRaisesRegex(
                    OSError, "Insufficient writable Kaggle disk"
                ):
                    stage_training_shards(
                        [train_manifest, validation_manifest],
                        minimum_free_bytes=1,
                    )

            self.assertTrue((project / "data/processed/.gitkeep").is_file())
            self.assertFalse(
                (project / ".kaggle-training-data-staging").exists()
            )

    def test_training_shard_rejects_test_before_resolving_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            project = temporary_root / "workspace"
            (project / "data/processed").mkdir(parents=True)
            (project / "data/processed/.gitkeep").touch()
            train_manifest = self._write_visible_shard(
                temporary_root / "part-01",
                source_id="train-recording",
                split="train",
                audio_path="data/audio/train.npy",
                audio_member="",
                labels_path="data/labels/train.npz",
                actual_audio_path="data/audio/train.npy",
                actual_labels_path="data/labels/train.npz",
            )
            test_manifest = self._write_visible_shard(
                temporary_root / "part-02",
                source_id="locked-test-recording",
                split="test",
                audio_path="data/audio/test.npy",
                audio_member="",
                labels_path="data/labels/test.npz",
                actual_audio_path="data/audio/test.npy",
                actual_labels_path="data/labels/test.npz",
            )

            with (
                mock.patch(
                    "scripts.cloud.kaggle_entrypoint.ROOT", project
                ),
                mock.patch(
                    "scripts.cloud.kaggle_entrypoint."
                    "_resolve_visible_audio_location"
                ) as resolver,
            ):
                with self.assertRaisesRegex(
                    ValueError, "Locked test row"
                ):
                    stage_training_shards(
                        [train_manifest, test_manifest],
                        minimum_free_bytes=0,
                    )

            resolver.assert_not_called()
            self.assertTrue((project / "data/processed/.gitkeep").is_file())

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

    def test_rank_outputs_do_not_require_a_result_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "runs/polyphonic/run-1"
            run.mkdir(parents=True)
            (run / "checkpoint_ranking.json").write_text(
                '{"locked_test_used": false}', encoding="utf-8"
            )
            (run / "cloud_pipeline.json").write_text(
                json.dumps({
                    "task": "rank",
                    "run_dir": str(run),
                    "artifact_dir": None,
                    "result_readme": None,
                    "locked_test_used": False,
                }),
                encoding="utf-8",
            )

            output = root / "output"
            manifest = package_outputs(
                task="rank", output_dir=output, root=root
            )

            self.assertFalse(manifest["locked_test_used"])
            with tarfile.open(output / manifest["archive"]) as archive:
                self.assertIn(
                    "run/run-1/checkpoint_ranking.json",
                    archive.getnames(),
                )

    def test_select_outputs_include_final_validation_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "runs/polyphonic/run-1"
            run.mkdir(parents=True)
            for name in (
                "selection.json",
                "selected.keras",
                "thresholds.json",
                "decoder_config.json",
            ):
                (run / name).write_bytes(b"validated")
            (run / "cloud_pipeline.json").write_text(
                json.dumps({
                    "task": "select",
                    "run_dir": str(run),
                    "artifact_dir": None,
                    "result_readme": None,
                    "locked_test_used": False,
                }),
                encoding="utf-8",
            )

            output = root / "output"
            manifest = package_outputs(
                task="select", output_dir=output, root=root
            )

            self.assertFalse(manifest["locked_test_used"])
            with tarfile.open(output / manifest["archive"]) as archive:
                names = set(archive.getnames())
            self.assertIn("run/run-1/selection.json", names)
            self.assertIn("run/run-1/selected.keras", names)
            self.assertIn("run/run-1/thresholds.json", names)
            self.assertIn("run/run-1/decoder_config.json", names)

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
