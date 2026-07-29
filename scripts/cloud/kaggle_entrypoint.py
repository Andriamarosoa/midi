"""Stage attached Kaggle inputs and run one cloud task safely.

The training input must contain only train/validation rows. The locked test is
rejected before TensorFlow is imported. The reconstruction task accepts the
minimal raw-source package produced by ``prepare_kaggle_datasets.py raw``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
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
DEFAULT_RECOVERY_CHUNK_BATCHES = 250
DEFAULT_SMOKE_RUNTIME_MINUTES = 30.0
DEFAULT_TRAIN_RUNTIME_MINUTES = 600.0
RESUME_IMPORT_MARKER = ".cloud_resume_source.json"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(candidate: Path, root: Path) -> bool:
    resolved = candidate.resolve()
    resolved_root = root.resolve()
    return (
        resolved == resolved_root
        or resolved_root in resolved.parents
    )


def _load_resume_output(input_root: Path) -> tuple[Path, Path, dict[str, object]]:
    manifests = sorted(input_root.rglob("output_manifest.json"))
    if len(manifests) != 1:
        raise ValueError(
            "Expected exactly one attached resume output_manifest.json, "
            f"found {len(manifests)}."
        )
    manifest_path = manifests[0]
    if not _inside(manifest_path, input_root):
        raise ValueError("Resume output manifest escapes the input root.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Invalid resume output manifest: {manifest_path}"
        ) from error
    if not isinstance(manifest, dict):
        raise ValueError("Resume output manifest must be a JSON object.")
    if manifest.get("task") != "train":
        raise ValueError("Only a previous train output can be resumed.")
    if manifest.get("locked_test_used") is not False:
        raise ValueError("Resume output did not keep the locked test excluded.")
    pipeline = manifest.get("pipeline")
    if (
        not isinstance(pipeline, dict)
        or pipeline.get("locked_test_used") is not False
    ):
        raise ValueError(
            "Resume output pipeline did not keep the locked test excluded."
        )

    archive_name = manifest.get("archive")
    if (
        not isinstance(archive_name, str)
        or not archive_name
        or Path(archive_name).name != archive_name
        or "\\" in archive_name
    ):
        raise ValueError("Resume output archive must be a plain filename.")
    archive_path = manifest_path.parent / archive_name
    if not archive_path.is_file() or not _inside(archive_path, input_root):
        raise FileNotFoundError(archive_path)

    expected_bytes = manifest.get("archive_bytes")
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes < 1
        or archive_path.stat().st_size != expected_bytes
    ):
        raise ValueError("Resume archive byte length does not match its manifest.")
    expected_sha256 = str(manifest.get("archive_sha256", "")).lower()
    if SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise ValueError("Resume archive manifest has no valid SHA-256.")
    actual_sha256 = _file_sha256(archive_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "Resume archive SHA-256 mismatch: "
            f"expected={expected_sha256}, actual={actual_sha256}."
        )
    return manifest_path, archive_path, manifest


def _safe_tar_member_path(member: tarfile.TarInfo) -> Path:
    if not member.name or "\\" in member.name:
        raise ValueError(f"Unsafe resume archive member: {member.name!r}")
    relative = PurePosixPath(member.name)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or not (member.isdir() or member.isfile())
    ):
        raise ValueError(f"Unsafe resume archive member: {member.name}")
    return Path(*relative.parts)


def _extract_resume_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        relative_paths = [_safe_tar_member_path(member) for member in members]
        if len(set(relative_paths)) != len(relative_paths):
            raise ValueError("Resume archive contains duplicate member paths.")
        resolved_destination = destination.resolve()
        for member, relative in zip(members, relative_paths):
            target = destination / relative
            resolved_target = target.resolve()
            if (
                resolved_target == resolved_destination
                or resolved_destination not in resolved_target.parents
            ):
                raise ValueError(
                    f"Resume archive member escapes destination: {member.name}"
                )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(
                    f"Cannot read resume archive member: {member.name}"
                )
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if target.stat().st_size != member.size:
                raise ValueError(
                    f"Resume archive member length mismatch: {member.name}"
                )


def _validate_resume_run_contents(
    extracted: Path,
    *,
    manifest: dict[str, object],
) -> Path:
    run_container = extracted / "run"
    if not run_container.is_dir() or run_container.is_symlink():
        raise ValueError("Resume archive does not contain a run/ directory.")
    children = list(run_container.iterdir())
    if (
        len(children) != 1
        or not children[0].is_dir()
        or children[0].is_symlink()
    ):
        raise ValueError(
            "Resume archive must contain exactly one run directory."
        )
    run_dir = children[0]
    if run_dir.name in {"", ".", ".."}:
        raise ValueError("Resume archive has an invalid run name.")
    pipeline_path = run_dir / "cloud_pipeline.json"
    if not pipeline_path.is_file() or pipeline_path.is_symlink():
        raise ValueError("Resume run has no safe cloud_pipeline.json.")
    try:
        pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Resume run has an invalid cloud_pipeline.json.") from error
    if (
        not isinstance(pipeline, dict)
        or pipeline.get("locked_test_used") is not False
    ):
        raise ValueError(
            "Resume run did not keep the locked test excluded."
        )
    manifest_pipeline = manifest["pipeline"]
    if (
        not isinstance(manifest_pipeline, dict)
        or Path(str(manifest_pipeline.get("run_dir", ""))).name
        != run_dir.name
        or Path(str(pipeline.get("run_dir", ""))).name != run_dir.name
    ):
        raise ValueError(
            "Resume run identity does not match the output manifest."
        )
    return run_dir


def validate_writable_resume_run(
    run_dir: Path,
    *,
    runs_root: Path | None = None,
) -> Path:
    """Require a real, writable run below this source snapshot's runs tree."""
    allowed_root = (
        ROOT / "runs/polyphonic"
        if runs_root is None
        else runs_root
    ).resolve()
    resolved = run_dir.resolve()
    kaggle_input = Path("/kaggle/input").resolve()
    if resolved == kaggle_input or kaggle_input in resolved.parents:
        raise ValueError(
            "A read-only /kaggle/input run cannot be resumed directly; "
            "use --resume-from-input."
        )
    if resolved == allowed_root or allowed_root not in resolved.parents:
        raise ValueError(
            f"Resume run must be below writable {allowed_root}: {resolved}"
        )
    if not resolved.is_dir() or resolved.is_symlink():
        raise FileNotFoundError(resolved)
    symlinks = [path for path in resolved.rglob("*") if path.is_symlink()]
    if symlinks:
        raise ValueError(
            f"Resume run contains a symbolic link: {symlinks[0]}"
        )
    probe_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".resume-write-probe-",
            dir=resolved,
            delete=False,
        ) as probe:
            probe.write(b"writable")
            probe_path = Path(probe.name)
    except OSError as error:
        raise PermissionError(f"Resume run is not writable: {resolved}") from error
    finally:
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)
    return resolved


def install_resume_run_from_input(
    input_root: Path,
    *,
    runs_root: Path | None = None,
) -> Path:
    """Validate and install one attached train output on writable storage."""
    manifest_path, archive_path, manifest = _load_resume_output(input_root)
    expected_sha256 = str(manifest["archive_sha256"]).lower()
    destination_root = (
        ROOT / "runs/polyphonic"
        if runs_root is None
        else runs_root
    ).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=".resume-import-",
        dir=destination_root,
    ))
    try:
        extracted = staging / "extracted"
        _extract_resume_archive(archive_path, extracted)
        extracted_run = _validate_resume_run_contents(
            extracted,
            manifest=manifest,
        )
        destination = destination_root / extracted_run.name
        if not _inside(destination, destination_root):
            raise ValueError("Resume run destination escapes the runs root.")
        marker = {
            "format": "guitar_midi_cloud_resume_v1",
            "archive": archive_path.name,
            "archive_sha256": expected_sha256,
            "output_manifest": manifest_path.name,
            "locked_test_used": False,
        }
        extracted_marker = extracted_run / RESUME_IMPORT_MARKER
        extracted_marker.write_text(
            json.dumps(marker, indent=2) + "\n",
            encoding="utf-8",
        )

        if destination.exists():
            destination_marker = destination / RESUME_IMPORT_MARKER
            try:
                installed = json.loads(
                    destination_marker.read_text(encoding="utf-8")
                )
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
            ) as error:
                raise FileExistsError(
                    "A non-idempotent resume run already exists: "
                    f"{destination}"
                ) from error
            if (
                not isinstance(installed, dict)
                or installed.get("archive_sha256") != expected_sha256
                or installed.get("locked_test_used") is not False
            ):
                raise FileExistsError(
                    "A different resume run already exists: "
                    f"{destination}"
                )
        else:
            extracted_run.replace(destination)
        return validate_writable_resume_run(
            destination,
            runs_root=destination_root,
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging)


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
    recovery_chunk_batches: int,
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
    if recovery_chunk_batches < 1:
        raise ValueError("recovery_chunk_batches must be positive.")
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
        "--recovery-chunk-batches",
        str(recovery_chunk_batches),
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
    parser.add_argument(
        "--recovery-chunk-batches",
        type=int,
        default=DEFAULT_RECOVERY_CHUNK_BATCHES,
    )
    parser.add_argument("--maximum-runtime-minutes", type=float)
    resume = parser.add_mutually_exclusive_group()
    resume.add_argument(
        "--resume-run",
        type=Path,
        help=(
            "Existing writable run below ROOT/runs/polyphonic. Paths mounted "
            "under /kaggle/input are rejected."
        ),
    )
    resume.add_argument(
        "--resume-from-input",
        action="store_true",
        help=(
            "Validate and install exactly one attached train output archive "
            "before resuming it from writable storage."
        ),
    )
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
                recovery_chunk_batches=args.recovery_chunk_batches,
                maximum_runtime_minutes=args.maximum_runtime_minutes,
            ))
            if args.initial_checkpoint_name:
                if args.resume_run is not None or args.resume_from_input:
                    raise ValueError(
                        "Initial checkpoint and resume input are mutually "
                        "exclusive."
                    )
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
            resume_run: Path | None = None
            if args.resume_from_input:
                if args.task != "train":
                    raise ValueError(
                        "--resume-from-input is only valid for task=train."
                    )
                resume_run = install_resume_run_from_input(args.input_root)
            elif args.resume_run is not None:
                if args.task != "train":
                    raise ValueError(
                        "--resume-run is only valid for task=train."
                    )
                resume_run = validate_writable_resume_run(args.resume_run)
            if resume_run is not None:
                command.extend(["--resume-run", str(resume_run)])
            _run(command)
        report = {
            "task": args.task,
            "data_root": str(data_root),
            "manifest": str(manifest),
            "validation": validation,
        }
        if args.task not in {"rank", "select"} and resume_run is not None:
            report["resume_run"] = str(resume_run)
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
