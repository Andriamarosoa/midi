from __future__ import annotations

import hashlib
import io
import json
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.cloud.kaggle_entrypoint import (
    RESUME_IMPORT_MARKER,
    install_resume_run_from_input,
)
from scripts.cloud.publish_kaggle import _task_notebook, publish_kernel
from scripts.cloud.train_polyphonic import _validate_writable_resume_run


class KaggleResumeTransportTests(unittest.TestCase):
    @staticmethod
    def _write_resume_output(
        input_root: Path,
        *,
        run_name: str = "dual-bass-run",
        locked_test_used: bool = False,
        archive_builder=None,
    ) -> tuple[Path, Path]:
        output = input_root / "previous-kernel/guitar-midi-results"
        output.mkdir(parents=True)
        archive_path = output / "guitar-midi-train-results.tar"
        if archive_builder is None:
            source = input_root / "archive-source"
            run = source / "run" / run_name
            run.mkdir(parents=True)
            pipeline = {
                "task": "train",
                "run_dir": f"/kaggle/working/midi/runs/polyphonic/{run_name}",
                "locked_test_used": locked_test_used,
            }
            (run / "cloud_pipeline.json").write_text(
                json.dumps(pipeline),
                encoding="utf-8",
            )
            (run / "history.csv").write_text(
                "epoch,loss\n1,0.5\n",
                encoding="utf-8",
            )
            (run / "paused.keras").write_bytes(b"compiled-model")
            with tarfile.open(archive_path, "w") as archive:
                archive.add(run, arcname=f"run/{run_name}")
        else:
            archive_builder(archive_path, run_name)
        archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        manifest = {
            "task": "train",
            "archive": archive_path.name,
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": archive_sha256,
            "locked_test_used": locked_test_used,
            "pipeline": {
                "task": "train",
                "run_dir": f"/kaggle/working/midi/runs/polyphonic/{run_name}",
                "locked_test_used": locked_test_used,
            },
        }
        manifest_path = output / "output_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        return manifest_path, archive_path

    def test_readonly_input_archive_is_installed_as_writable_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            runs_root = root / "workspace/runs/polyphonic"
            _manifest, archive = self._write_resume_output(input_root)
            archive.chmod(stat.S_IREAD)

            installed = install_resume_run_from_input(
                input_root,
                runs_root=runs_root,
            )

            self.assertEqual(installed, runs_root / "dual-bass-run")
            self.assertFalse(installed.is_symlink())
            self.assertNotIn(input_root.resolve(), installed.resolve().parents)
            self.assertEqual(
                (installed / "paused.keras").read_bytes(),
                b"compiled-model",
            )
            marker = json.loads(
                (installed / RESUME_IMPORT_MARKER).read_text(encoding="utf-8")
            )
            self.assertFalse(marker["locked_test_used"])
            probe = installed / "writable-after-import.txt"
            probe.write_text("ok", encoding="utf-8")
            self.assertEqual(probe.read_text(encoding="utf-8"), "ok")

            # A notebook cell retry must reuse the verified import rather than
            # overwrite or duplicate the run.
            second = install_resume_run_from_input(
                input_root,
                runs_root=runs_root,
            )
            self.assertEqual(second, installed)
            self.assertEqual(
                (installed / "paused.keras").read_bytes(),
                b"compiled-model",
            )

    def test_corrupted_resume_archive_is_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            runs_root = root / "workspace/runs/polyphonic"
            _manifest, archive = self._write_resume_output(input_root)
            with archive.open("ab") as handle:
                handle.write(b"corruption")

            with self.assertRaisesRegex(ValueError, "byte length"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=runs_root,
                )

            self.assertFalse(runs_root.exists())

    def test_same_length_archive_corruption_fails_sha256_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            runs_root = root / "workspace/runs/polyphonic"
            _manifest, archive = self._write_resume_output(input_root)
            with archive.open("r+b") as handle:
                first = handle.read(1)
                handle.seek(0)
                handle.write(bytes([first[0] ^ 0xFF]))

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=runs_root,
                )

            self.assertFalse(runs_root.exists())

    def test_resume_archive_path_traversal_is_rejected(self) -> None:
        def build(archive_path: Path, run_name: str) -> None:
            with tarfile.open(archive_path, "w") as archive:
                payload = b"escape"
                member = tarfile.TarInfo("../../outside.txt")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            runs_root = root / "workspace/runs/polyphonic"
            self._write_resume_output(input_root, archive_builder=build)

            with self.assertRaisesRegex(ValueError, "Unsafe resume archive"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=runs_root,
                )

            self.assertFalse((root / "outside.txt").exists())

    def test_resume_archive_symlink_is_rejected(self) -> None:
        def build(archive_path: Path, run_name: str) -> None:
            with tarfile.open(archive_path, "w") as archive:
                run = tarfile.TarInfo(f"run/{run_name}")
                run.type = tarfile.DIRTYPE
                archive.addfile(run)
                link = tarfile.TarInfo(f"run/{run_name}/paused.keras")
                link.type = tarfile.SYMTYPE
                link.linkname = "/etc/passwd"
                archive.addfile(link)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            self._write_resume_output(input_root, archive_builder=build)

            with self.assertRaisesRegex(ValueError, "Unsafe resume archive"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=root / "workspace/runs/polyphonic",
                )

    def test_resume_archive_requires_exactly_one_run(self) -> None:
        def build(archive_path: Path, run_name: str) -> None:
            source = archive_path.parent / "two-runs"
            for name in (run_name, "other-run"):
                run = source / name
                run.mkdir(parents=True)
                (run / "cloud_pipeline.json").write_text(
                    json.dumps({
                        "run_dir": (
                            f"/kaggle/working/midi/runs/polyphonic/{name}"
                        ),
                        "locked_test_used": False,
                    }),
                    encoding="utf-8",
                )
            with tarfile.open(archive_path, "w") as archive:
                for run in sorted(source.iterdir()):
                    archive.add(run, arcname=f"run/{run.name}")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            self._write_resume_output(input_root, archive_builder=build)

            with self.assertRaisesRegex(ValueError, "exactly one run"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=root / "workspace/runs/polyphonic",
                )

    def test_locked_test_resume_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            self._write_resume_output(
                input_root,
                locked_test_used=True,
            )

            with self.assertRaisesRegex(ValueError, "locked test"):
                install_resume_run_from_input(
                    input_root,
                    runs_root=root / "workspace/runs/polyphonic",
                )

    def test_train_orchestrator_requires_run_below_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "runs/polyphonic"
            run = output_root / "run-1"
            run.mkdir(parents=True)
            (run / "history.csv").write_text("epoch\n", encoding="utf-8")
            self.assertEqual(
                _validate_writable_resume_run(
                    run,
                    output_root=output_root,
                ),
                run.resolve(),
            )
            outside = root / "readonly-input/run-1"
            outside.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "must be below"):
                _validate_writable_resume_run(
                    outside,
                    output_root=output_root,
                )

    def test_publisher_attaches_previous_kernel_and_enables_resume(self) -> None:
        notebook = _task_notebook(
            "train",
            source_dataset_slug="guitar-midi-polyphonic-code-resume",
            resume_from_input=True,
        )
        source = "".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )
        self.assertIn("RESUME_FROM_INPUT = True", source)
        self.assertIn('command.append("--resume-from-input")', source)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "kernel"
            with (
                mock.patch("scripts.cloud.publish_kaggle._run"),
                mock.patch(
                    "scripts.cloud.publish_kaggle._kaggle",
                    return_value="kaggle",
                ),
            ):
                kernel_id = publish_kernel(
                    owner="owner",
                    dataset_handles=[
                        *[
                            "data-owner/"
                            "guitar-midi-polyphonic-data-part-"
                            f"{index:02d}"
                            for index in range(1, 17)
                        ],
                        "owner/guitar-midi-polyphonic-code-resume",
                    ],
                    task="train",
                    output_dir=output,
                    kernel_slug="resume-run",
                    resume_kernel_source="owner/previous-train",
                )
            metadata = json.loads(
                (output / "kernel-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(kernel_id, "owner/resume-run")
            self.assertEqual(
                metadata["kernel_sources"],
                ["owner/previous-train"],
            )


if __name__ == "__main__":
    unittest.main()
