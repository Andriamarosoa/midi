"""Stage attached Kaggle inputs and run one cloud task safely.

The training input must contain only train/validation rows. The locked test is
rejected before TensorFlow is imported. The reconstruction task accepts the
minimal raw-source package produced by ``prepare_kaggle_datasets.py raw``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SUFFIX = Path(
    "data/processed/polyphonic_v2_2_combined/manifest.csv"
)
REQUIRED_RAW = (
    Path("GuitarSet/annotation.zip"),
    Path("GuitarSet/audio_hex-pickup_debleeded.zip"),
    Path("GuitarSet/audio_mono-pickup_mix.zip"),
    Path("GAPS/gaps_metadata_with_splits.csv"),
)
DEFAULT_STAGING_FREE_RESERVE_BYTES = 2 * 1024**3
DEFAULT_SMOKE_EXAMPLES = 8192
DEFAULT_SMOKE_VALIDATION_EXAMPLES = 2048
DEFAULT_LOG_EVERY_BATCHES = 25
DEFAULT_SMOKE_RUNTIME_MINUTES = 30.0
DEFAULT_TRAIN_RUNTIME_MINUTES = 600.0


def _portable_path(value: str) -> Path:
    return Path(value.replace("\\", "/"))


def _run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _data_root_from_manifest(manifest: Path) -> Path:
    for parent in manifest.parents:
        if parent.name == "data" and (parent / "processed").is_dir():
            return parent
    raise ValueError(f"Cannot locate packaged data root above {manifest}")


def find_training_data_root(input_root: Path) -> Path:
    candidates = sorted(input_root.rglob(MANIFEST_SUFFIX.name))
    candidates = [
        path for path in candidates
        if path.as_posix().endswith(MANIFEST_SUFFIX.as_posix())
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one attached train/validation manifest, "
            f"found {len(candidates)}."
        )
    return _data_root_from_manifest(candidates[0])


def find_training_shard_manifests(input_root: Path) -> list[Path]:
    """Find the real-data manifests from individually published shards."""
    candidates = sorted(input_root.rglob("manifest_kaggle_safe.csv"))
    return [
        path for path in candidates
        if _data_root_from_manifest(path)
        and path.as_posix().endswith(
            "data/processed/polyphonic_v2_2_combined/manifest_kaggle_safe.csv"
        )
    ]


def find_checkpoint_run(input_root: Path) -> Path:
    """Find one attached checkpoint run without consulting generated outputs."""
    candidates = []
    for history in input_root.rglob("history.csv"):
        run_dir = history.parent
        if (
            (run_dir / "config.json").is_file()
            and (run_dir / "epochs").is_dir()
            and list((run_dir / "epochs").glob("epoch-*.keras"))
        ):
            candidates.append(run_dir)
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one attached checkpoint run, "
            f"found {len(candidates)}."
        )
    return candidates[0]


def materialize_training_archive(input_root: Path) -> Path:
    index_paths = sorted(input_root.rglob("training_archive_index.json"))
    if index_paths:
        if len(index_paths) != 1:
            raise ValueError("Expected exactly one training archive index.")
        index_path = index_paths[0]
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if index.get("format") != "kaggle_chunked_tar_v1":
            raise ValueError("Unsupported training archive index format.")
        destination = Path("/kaggle/working/guitar-midi-input")
        if destination.exists():
            raise FileExistsError(destination)
        parts_root = destination / ".parts"
        parts_root.mkdir(parents=True)
        declared_archives = {item["name"] for item in index.get("archives", [])}
        if not declared_archives:
            raise ValueError("Training archive index contains no archives.")
        for archive_name in sorted(declared_archives):
            archive_path = index_path.parent / archive_name
            if not archive_path.is_file():
                raise FileNotFoundError(archive_path)
            with tarfile.open(archive_path, "r") as archive:
                for member in archive.getmembers():
                    if not member.isfile() or not member.name.startswith("parts/"):
                        raise ValueError(f"Unsafe archive member: {member.name}")
                    target = (parts_root / member.name).resolve()
                    if parts_root.resolve() not in target.parents:
                        raise ValueError(f"Archive member escapes parts: {member.name}")
                archive.extractall(parts_root)
        for item in index.get("files", []):
            relative = _portable_path(str(item["path"]))
            target = (destination / relative).resolve()
            if destination.resolve() not in target.parents:
                raise ValueError(f"Indexed path escapes destination: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with target.open("wb") as output:
                for part in item.get("parts", []):
                    source = parts_root / str(part["member"])
                    if not source.is_file():
                        raise FileNotFoundError(source)
                    expected = int(part["bytes"])
                    if source.stat().st_size != expected:
                        raise ValueError(f"Invalid part length: {source}")
                    with source.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output, length=1024 * 1024)
                    written += expected
            if written != int(item["bytes"]):
                raise ValueError(f"Reconstructed file length mismatch: {relative}")
        shutil.rmtree(parts_root)
        return destination
    archives = sorted(
        input_root.rglob("polyphonic_train_validation.tar")
    )
    if not archives:
        return input_root
    if len(archives) != 1:
        raise ValueError(
            "Expected at most one attached training archive, "
            f"found {len(archives)}."
        )
    destination = Path("/kaggle/working/guitar-midi-input")
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    with tarfile.open(archives[0], "r") as archive:
        resolved_destination = destination.resolve()
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if (
                target != resolved_destination
                and resolved_destination not in target.parents
            ):
                raise ValueError(
                    f"Archive member escapes destination: {member.name}"
                )
        archive.extractall(destination)
    return destination


def find_raw_data_root(input_root: Path) -> Path:
    candidates: list[Path] = []
    for annotation in input_root.rglob("annotation.zip"):
        if annotation.parent.name != "GuitarSet":
            continue
        data_root = annotation.parent.parent
        if all((data_root / relative).is_file() for relative in REQUIRED_RAW):
            if list((data_root / "Guitar-TECHS").glob("P*.zip")):
                candidates.append(data_root)
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one attached raw-source data root, "
            f"found {len(candidates)}."
        )
    return candidates[0]


def _clear_tracked_data_placeholder(destination: Path) -> None:
    if destination.is_symlink():
        destination.unlink()
        return
    if not destination.exists():
        return
    contents = list(destination.iterdir())
    if any(path.name != "processed" for path in contents):
        raise RuntimeError(
            f"Refusing to replace non-placeholder data directory: {destination}"
        )
    processed = destination / "processed"
    if processed.exists():
        processed_contents = list(processed.iterdir())
        if any(path.name != ".gitkeep" for path in processed_contents):
            raise RuntimeError(
                f"Refusing to replace non-placeholder directory: {processed}"
            )
        for path in processed_contents:
            path.unlink()
        processed.rmdir()
    destination.rmdir()


def stage_training_data(source: Path) -> Path:
    destination = ROOT / "data"
    _clear_tracked_data_placeholder(destination)
    os.symlink(source, destination, target_is_directory=True)
    return destination / MANIFEST_SUFFIX.relative_to("data")


def _rebase_shard_path(value: str, shard_name: str) -> str:
    relative = _portable_path(value)
    if relative.parts[:1] != ("data",):
        raise ValueError(f"Shard path must start with data/: {value}")
    return (Path("data") / "shards" / shard_name / Path(*relative.parts[1:])).as_posix()


def _resolve_visible_shard_path(data_root: Path, value: str) -> str:
    """Resolve Kaggle's 105-character path truncation deterministically."""
    relative = _portable_path(value)
    if relative.parts[:1] != ("data",):
        raise ValueError(f"Shard path must start with data/: {value}")
    expected = data_root / Path(*relative.parts[1:])
    if expected.is_file():
        return relative.as_posix()
    if not expected.parent.is_dir():
        raise FileNotFoundError(expected)
    candidates = [
        path
        for path in expected.parent.iterdir()
        if path.is_file() and expected.name.startswith(path.name)
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Cannot resolve Kaggle-truncated path {expected}; "
            f"matching candidates={candidates}"
        )
    resolved = candidates[0].relative_to(data_root)
    return (Path("data") / resolved).as_posix()


def _resolve_visible_audio_location(
    data_root: Path, audio_path: str, audio_member: str
) -> tuple[str, str]:
    """Resolve either a retained ZIP or Kaggle's auto-extracted member."""
    try:
        return (
            _resolve_visible_shard_path(data_root, audio_path),
            audio_member,
        )
    except FileNotFoundError as archive_error:
        relative = _portable_path(audio_path)
        if not audio_member or relative.suffix.lower() != ".zip":
            raise
        extracted = relative.with_suffix("") / audio_member
        try:
            return (
                _resolve_visible_shard_path(
                    data_root, extracted.as_posix()
                ),
                "",
            )
        except FileNotFoundError as extracted_error:
            raise FileNotFoundError(
                f"Cannot resolve retained archive {audio_path} or "
                f"auto-extracted member {extracted}: "
                f"archive_error={archive_error}; "
                f"member_error={extracted_error}"
            ) from extracted_error


def _visible_shard_source(data_root: Path, value: str) -> Path:
    relative = _portable_path(value)
    if relative.parts[:1] != ("data",):
        raise ValueError(f"Shard path must start with data/: {value}")
    source = data_root / Path(*relative.parts[1:])
    if not source.is_file():
        raise FileNotFoundError(source)
    return source


def _plan_staged_file(
    planned_files: dict[Path, Path],
    *,
    source: Path,
    destination: Path,
) -> None:
    existing = planned_files.get(destination)
    if existing is not None and existing != source:
        raise ValueError(
            f"Conflicting shard files for {destination}: "
            f"{existing} and {source}"
        )
    planned_files[destination] = source


def _check_staging_disk_space(
    *,
    required_bytes: int,
    minimum_free_bytes: int,
) -> None:
    if minimum_free_bytes < 0:
        raise ValueError("minimum_free_bytes must be non-negative.")
    available_bytes = int(shutil.disk_usage(ROOT).free)
    remaining_bytes = available_bytes - required_bytes
    print(
        "Kaggle shard materialization: "
        f"required={required_bytes} bytes, "
        f"available={available_bytes} bytes, "
        f"reserved={minimum_free_bytes} bytes.",
        flush=True,
    )
    if remaining_bytes < minimum_free_bytes:
        raise OSError(
            "Insufficient writable Kaggle disk for shard materialization: "
            f"required={required_bytes}, available={available_bytes}, "
            f"required_free_after_copy={minimum_free_bytes}."
        )


def stage_training_shards(
    manifests: list[Path],
    *,
    minimum_free_bytes: int = DEFAULT_STAGING_FREE_RESERVE_BYTES,
) -> Path:
    """Materialize attached shard files and write one safe combined manifest.

    Kaggle datasets are mounted under ``/kaggle/input``.  Reading labels and
    waveforms there repeatedly is substantially slower than reading the local
    writable filesystem, so only the train/validation files referenced by the
    shard manifests are copied below ``ROOT/data``.  Logical filenames are
    restored when Kaggle truncated a visible filename, and auto-extracted ZIP
    members remain ordinary audio files with an empty ``audio_member`` field.
    """
    if len(manifests) < 2:
        raise ValueError("Expected at least two visible Kaggle data shards.")

    combined_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    seen_sources: set[str] = set()
    parsed_shards: list[tuple[str, Path, list[dict[str, str]]]] = []

    # Validate the complete split contract before resolving or opening any
    # referenced audio/label file.  A contaminated manifest therefore cannot
    # cause even a partial staging of locked-test material.
    for index, manifest in enumerate(manifests, start=1):
        data_root = _data_root_from_manifest(manifest)
        shard_name = f"part-{index:02d}"
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            if fieldnames is None:
                fieldnames = list(reader.fieldnames or [])
        for row in rows:
            if row.get("split") not in {"train", "validation"}:
                raise ValueError("Locked test row found in visible data shard.")
            source_id = row.get("source_id", "")
            if source_id in seen_sources:
                raise ValueError(f"Duplicate source across shards: {source_id}")
            seen_sources.add(source_id)
        parsed_shards.append((shard_name, data_root, rows))

    if not fieldnames:
        raise ValueError("No shard manifest rows found.")
    splits = {
        row["split"]
        for _shard_name, _data_root, rows in parsed_shards
        for row in rows
    }
    if splits != {"train", "validation"}:
        raise ValueError(
            "Combined shard manifest must contain train and validation only; "
            f"got {sorted(splits)}."
        )

    planned_files: dict[Path, Path] = {}
    for shard_name, data_root, rows in parsed_shards:
        for row in rows:
            original_audio_path = row["audio_path"]
            original_audio_member = row.get("audio_member", "")
            audio_path, audio_member = _resolve_visible_audio_location(
                data_root,
                original_audio_path,
                original_audio_member,
            )
            labels_path = _resolve_visible_shard_path(
                data_root, row["labels_path"]
            )

            if audio_member:
                logical_audio_path = _portable_path(original_audio_path).as_posix()
            else:
                original = _portable_path(original_audio_path)
                logical_audio_path = (
                    (original.with_suffix("") / original_audio_member).as_posix()
                    if original_audio_member
                    else original.as_posix()
                )

            staged_audio_path = _rebase_shard_path(
                logical_audio_path, shard_name
            )
            staged_labels_path = _rebase_shard_path(
                row["labels_path"], shard_name
            )
            _plan_staged_file(
                planned_files,
                source=_visible_shard_source(data_root, audio_path),
                destination=_portable_path(staged_audio_path),
            )
            _plan_staged_file(
                planned_files,
                source=_visible_shard_source(data_root, labels_path),
                destination=_portable_path(staged_labels_path),
            )
            row["audio_path"] = staged_audio_path
            row["audio_member"] = audio_member
            row["labels_path"] = staged_labels_path
            combined_rows.append(row)

    required_bytes = sum(
        source.stat().st_size for source in planned_files.values()
    )
    _check_staging_disk_space(
        required_bytes=required_bytes,
        minimum_free_bytes=minimum_free_bytes,
    )

    destination = ROOT / "data"
    staging = ROOT / ".kaggle-training-data-staging"
    if staging.exists():
        raise FileExistsError(staging)
    staging.mkdir()
    try:
        file_count = len(planned_files)
        copied_bytes = 0
        for file_index, (relative, source) in enumerate(
            sorted(planned_files.items(), key=lambda item: item[0].as_posix()),
            start=1,
        ):
            target = staging / Path(*relative.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_bytes = source.stat().st_size
            if target.stat().st_size != source_bytes:
                raise OSError(
                    f"Staged file length mismatch: {source} -> {target}"
                )
            copied_bytes += source_bytes
            print(
                "Kaggle shard materialization: "
                f"file={file_index}/{file_count}, "
                f"bytes={copied_bytes}/{required_bytes}.",
                flush=True,
            )

        combined = staging / MANIFEST_SUFFIX.relative_to("data")
        combined.parent.mkdir(parents=True)
        with combined.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_rows)

        _clear_tracked_data_placeholder(destination)
        staging.replace(destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination / MANIFEST_SUFFIX.relative_to("data")


def _symlink_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(source, destination)


def stage_raw_data(source: Path) -> Path:
    destination = ROOT / "data"
    _clear_tracked_data_placeholder(destination)
    destination.mkdir()
    guitarset = destination / "GuitarSet"
    guitarset.mkdir()
    for name in (
        "annotation.zip",
        "audio_hex-pickup_debleeded.zip",
        "audio_mono-pickup_mix.zip",
    ):
        _symlink_file(source / "GuitarSet" / name, guitarset / name)
    os.symlink(
        source / "GAPS", destination / "GAPS", target_is_directory=True
    )
    guitar_techs = destination / "Guitar-TECHS"
    guitar_techs.mkdir()
    for archive in sorted((source / "Guitar-TECHS").glob("P*.zip")):
        _symlink_file(archive, guitar_techs / archive.name)
    (destination / "processed").mkdir()
    return destination


def validate_training_manifest(manifest: Path) -> dict[str, object]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    splits = Counter(row["split"] for row in rows)
    if set(splits) != {"train", "validation"}:
        raise ValueError(
            "Training package must contain train and validation only; "
            f"got {dict(splits)}."
        )
    archives: dict[Path, set[str]] = defaultdict(set)
    for row in rows:
        audio = ROOT / _portable_path(row["audio_path"])
        labels = ROOT / _portable_path(row["labels_path"])
        if not audio.is_file():
            raise FileNotFoundError(audio)
        if not labels.is_file():
            raise FileNotFoundError(labels)
        if row["audio_member"]:
            archives[audio].add(row["audio_member"])
    for path, members in archives.items():
        with ZipFile(path) as archive:
            missing = members - set(archive.namelist())
        if missing:
            raise FileNotFoundError(
                f"{path}: {len(missing)} archive members missing"
            )
    return {
        "recordings": len(rows),
        "splits": dict(sorted(splits.items())),
        "datasets": dict(sorted(Counter(
            row["dataset_id"] for row in rows
        ).items())),
        "locked_test_included": False,
    }


def _training_control_arguments(
    *,
    task: str,
    workers: int,
    smoke_examples: int,
    smoke_validation_examples: int,
    log_every_batches: int,
    maximum_runtime_minutes: float | None,
) -> list[str]:
    """Return the cloud controls forwarded to ``train_polyphonic.py``."""
    if task not in {"smoke", "train"}:
        raise ValueError(f"Unsupported training task: {task}")
    if workers < 1:
        raise ValueError("workers must be positive.")
    if smoke_examples < 1 or smoke_validation_examples < 1:
        raise ValueError("Smoke example counts must be positive.")
    if log_every_batches < 1:
        raise ValueError("log_every_batches must be positive.")
    runtime_minutes = (
        maximum_runtime_minutes
        if maximum_runtime_minutes is not None
        else (
            DEFAULT_SMOKE_RUNTIME_MINUTES
            if task == "smoke"
            else DEFAULT_TRAIN_RUNTIME_MINUTES
        )
    )
    if runtime_minutes <= 0:
        raise ValueError("maximum_runtime_minutes must be positive.")

    arguments = [
        "--workers",
        str(workers),
        "--log-every-batches",
        str(log_every_batches),
        "--maximum-runtime-minutes",
        str(float(runtime_minutes)),
    ]
    if task == "smoke":
        arguments.extend([
            "--smoke-test",
            "--representative-smoke",
            "--smoke-examples",
            str(smoke_examples),
            "--smoke-validation-examples",
            str(smoke_validation_examples),
        ])
    else:
        # Ranking, musical selection and export are intentionally separate
        # validation-only kernels after the bounded training kernel completes.
        arguments.append("--skip-post-train")
    return arguments


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", choices=("smoke", "train", "rank", "select", "rebuild"),
        required=True,
    )
    parser.add_argument(
        "--input-root", type=Path, default=Path("/kaggle/input")
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/polyphonic_train.yaml"),
    )
    parser.add_argument(
        "--initial-checkpoint-name",
        default="",
        help="Unique checkpoint basename mounted under /kaggle/input.",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--maximum-examples", type=int, default=60_000)
    parser.add_argument("--maximum-recordings", type=int, default=12)
    parser.add_argument("--maximum-candidates", type=int, default=8)
    parser.add_argument(
        "--smoke-examples", type=int, default=DEFAULT_SMOKE_EXAMPLES
    )
    parser.add_argument(
        "--smoke-validation-examples",
        type=int,
        default=DEFAULT_SMOKE_VALIDATION_EXAMPLES,
    )
    parser.add_argument(
        "--log-every-batches",
        type=int,
        default=DEFAULT_LOG_EVERY_BATCHES,
    )
    parser.add_argument("--maximum-runtime-minutes", type=float)
    parser.add_argument("--resume-run", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)

    if os.name == "nt":
        raise RuntimeError("This entrypoint must run inside Kaggle Linux.")
    if args.task == "rebuild":
        raw_root = find_raw_data_root(args.input_root)
        stage_raw_data(raw_root)
        _run([
            sys.executable,
            "scripts/data/rebuild_processed.py",
            "--workers",
            str(args.workers),
        ])
        report = {
            "task": "rebuild",
            "raw_data_root": str(raw_root),
            "processed_root": str(ROOT / "data/processed"),
            "locked_test_used_for_model_selection": False,
        }
    else:
        shard_manifests = find_training_shard_manifests(args.input_root)
        if shard_manifests:
            manifest = stage_training_shards(shard_manifests)
            data_root = ROOT / "data"
        else:
            materialized_input = materialize_training_archive(args.input_root)
            data_root = find_training_data_root(materialized_input)
            manifest = stage_training_data(data_root)
        validation = validate_training_manifest(manifest)
        if args.task in {"rank", "select"}:
            source_run = find_checkpoint_run(args.input_root)
            run_dir = ROOT / "runs/polyphonic" / source_run.name
            run_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_run, run_dir)
            if args.task == "rank":
                _run([
                    sys.executable,
                    "-m",
                    "src.polyphonic.rank_checkpoints",
                    "--run-dir",
                    str(run_dir),
                    "--maximum-examples",
                    str(args.maximum_examples),
                ])
            else:
                _run([
                    sys.executable,
                    "-m",
                    "src.polyphonic.select_final_checkpoint",
                    "--run-dir",
                    str(run_dir),
                    "--maximum-recordings",
                    str(args.maximum_recordings),
                    "--maximum-candidates",
                    str(args.maximum_candidates),
                ])
            pipeline = {
                "task": args.task,
                "run_dir": str(run_dir),
                "artifact_dir": None,
                "result_readme": None,
                "locked_test_used": False,
            }
            (run_dir / "cloud_pipeline.json").write_text(
                json.dumps(pipeline, indent=2) + "\n", encoding="utf-8"
            )
        else:
            command = [
                sys.executable,
                "scripts/cloud/train_polyphonic.py",
                "--config",
                str(args.config),
            ]
            command.extend(_training_control_arguments(
                task=args.task,
                workers=args.workers,
                smoke_examples=args.smoke_examples,
                smoke_validation_examples=args.smoke_validation_examples,
                log_every_batches=args.log_every_batches,
                maximum_runtime_minutes=args.maximum_runtime_minutes,
            ))
            if args.initial_checkpoint_name:
                checkpoint_candidates = sorted(
                    args.input_root.rglob(args.initial_checkpoint_name)
                )
                if len(checkpoint_candidates) != 1:
                    raise RuntimeError(
                        "Expected exactly one initial checkpoint named "
                        f"{args.initial_checkpoint_name!r}, got "
                        f"{checkpoint_candidates}"
                    )
                command.extend([
                    "--initial-checkpoint",
                    str(checkpoint_candidates[0]),
                ])
            if args.resume_run is not None:
                command.extend(["--resume-run", str(args.resume_run)])
            _run(command)
        report = {
            "task": args.task,
            "data_root": str(data_root),
            "manifest": str(manifest),
            "validation": validation,
        }
        if args.task in {"rank", "select"}:
            report["run_dir"] = str(run_dir)
            if args.task == "rank":
                report["maximum_examples"] = args.maximum_examples
            else:
                report["maximum_recordings"] = args.maximum_recordings
                report["maximum_candidates"] = args.maximum_candidates
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
