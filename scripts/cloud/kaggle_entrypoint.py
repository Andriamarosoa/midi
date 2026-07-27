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


def materialize_training_archive(input_root: Path) -> Path:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", choices=("smoke", "train", "rebuild"), required=True
    )
    parser.add_argument(
        "--input-root", type=Path, default=Path("/kaggle/input")
    )
    parser.add_argument("--workers", type=int, default=4)
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
        materialized_input = materialize_training_archive(args.input_root)
        data_root = find_training_data_root(materialized_input)
        manifest = stage_training_data(data_root)
        validation = validate_training_manifest(manifest)
        command = [
            sys.executable,
            "scripts/cloud/train_polyphonic.py",
        ]
        if args.task == "smoke":
            command.append("--smoke-test")
        if args.resume_run is not None:
            command.extend(["--resume-run", str(args.resume_run)])
        _run(command)
        report = {
            "task": args.task,
            "data_root": str(data_root),
            "manifest": str(manifest),
            "validation": validation,
        }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
