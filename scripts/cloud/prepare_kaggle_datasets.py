"""Prepare private Kaggle input datasets without duplicating large local files.

Two packages are supported:

``training``
    Contains train/validation audio and labels only. Test rows, test labels and
    test-only audio members are excluded.

``raw``
    Contains the minimum preserved sources needed by
    ``scripts/data/rebuild_processed.py``. IDMT and unused GuitarSet captures
    are intentionally excluded.

Files are hard-linked when possible so staging does not consume another copy
of the large datasets. The resulting directories are ignored by Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import BinaryIO
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(
    "data/processed/polyphonic_v2_2_combined/manifest.csv"
)
TRAINING_SPLITS = frozenset({"train", "validation"})
DEFAULT_ARCHIVE_PART_BYTES = 512 * 1024 * 1024


def _portable_path(value: str) -> Path:
    return Path(value.replace("\\", "/"))


def _source_and_relative(root: Path, value: str) -> tuple[Path, Path]:
    path = _portable_path(value)
    source = path if path.is_absolute() else root / path
    source = source.resolve()
    root = root.resolve()
    if source != root and root not in source.parents:
        raise ValueError(f"Path escapes project root: {value}")
    return source, source.relative_to(root)


def _link_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def _new_output(path: Path) -> Path:
    output = path.resolve()
    if output.exists():
        raise FileExistsError(
            f"Output already exists: {output}. Remove it explicitly first."
        )
    output.mkdir(parents=True)
    return output


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _copy_filtered_archive(
    source: Path,
    destination: Path,
    members: set[str],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as input_archive:
        available = set(input_archive.namelist())
        missing = sorted(members - available)
        if missing:
            raise FileNotFoundError(
                f"{source}: {len(missing)} archive members are missing"
            )
        with ZipFile(destination, "w", allowZip64=True) as output_archive:
            for member in sorted(members):
                info = input_archive.getinfo(member)
                with (
                    input_archive.open(info, "r") as input_file,
                    output_archive.open(
                        info, "w", force_zip64=True
                    ) as output_file,
                ):
                    shutil.copyfileobj(
                        input_file, output_file, length=1024 * 1024
                    )


def _validate_training_package(
    output: Path,
    manifest_relative: Path,
) -> dict[str, object]:
    manifest = output / manifest_relative
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    splits = Counter(row["split"] for row in rows)
    if set(splits) != set(TRAINING_SPLITS):
        raise ValueError(f"Unexpected package splits: {dict(splits)}")

    archives: dict[Path, set[str]] = defaultdict(set)
    for row in rows:
        audio = output / _portable_path(row["audio_path"])
        labels = output / _portable_path(row["labels_path"])
        if not audio.is_file():
            raise FileNotFoundError(audio)
        if not labels.is_file():
            raise FileNotFoundError(labels)
        if row["audio_member"]:
            archives[audio].add(row["audio_member"])
    for archive_path, members in archives.items():
        with ZipFile(archive_path) as archive:
            missing = members - set(archive.namelist())
        if missing:
            raise FileNotFoundError(
                f"{archive_path}: {len(missing)} members missing"
            )

    files = [path for path in output.rglob("*") if path.is_file()]
    return {
        "passed": True,
        "locked_test_included": False,
        "splits": dict(sorted(splits.items())),
        "datasets": dict(sorted(Counter(
            row["dataset_id"] for row in rows
        ).items())),
        "licenses": dict(sorted(Counter(
            row["license_id"] for row in rows
        ).items())),
        "recordings": len(rows),
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
    }


def prepare_training(
    *,
    root: Path,
    manifest_path: Path,
    output_path: Path,
    source_ids: set[str] | None = None,
) -> dict[str, object]:
    output = _new_output(output_path)
    with manifest_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [
            dict(row) for row in reader
            if row.get("split") in TRAINING_SPLITS
            and (source_ids is None or row.get("source_id") in source_ids)
        ]
    if not rows:
        raise ValueError("No train/validation rows found.")
    if any(row["split"] == "test" for row in rows):
        raise ValueError("Locked test rows must not enter the Kaggle package.")

    archives: dict[tuple[Path, Path], set[str]] = defaultdict(set)
    ordinary_files: dict[Path, Path] = {}
    for row in rows:
        audio_source, audio_relative = _source_and_relative(
            root, row["audio_path"]
        )
        label_source, label_relative = _source_and_relative(
            root, row["labels_path"]
        )
        if not audio_source.is_file():
            raise FileNotFoundError(audio_source)
        if not label_source.is_file():
            raise FileNotFoundError(label_source)
        row["audio_path"] = audio_relative.as_posix()
        row["labels_path"] = label_relative.as_posix()
        # Raw annotations are not needed for training or validation selection.
        # Keeping them out avoids accidentally packaging locked-test sources.
        if "annotation_path" in row:
            row["annotation_path"] = ""
        if "harmonic_csv_path" in row:
            row["harmonic_csv_path"] = ""
        ordinary_files[label_source] = label_relative
        if row["audio_member"]:
            archives[(audio_source, audio_relative)].add(row["audio_member"])
        else:
            ordinary_files[audio_source] = audio_relative

    methods = Counter()
    for source, relative in sorted(
        ordinary_files.items(), key=lambda item: item[1].as_posix()
    ):
        methods[_link_or_copy(source, output / relative)] += 1
    for (source, relative), members in sorted(
        archives.items(), key=lambda item: item[0][1].as_posix()
    ):
        _copy_filtered_archive(source, output / relative, members)
        methods["filtered_zip"] += 1

    _, source_manifest_relative = _source_and_relative(
        root, str(manifest_path)
    )
    package_manifest = output / source_manifest_relative
    package_manifest.parent.mkdir(parents=True, exist_ok=True)
    with package_manifest.open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = _validate_training_package(
        output, source_manifest_relative
    )
    report.update({
        "schema_version": 1,
        "kind": "polyphonic_train_validation",
        "manifest": source_manifest_relative.as_posix(),
        "staging_methods": dict(sorted(methods.items())),
    })
    _write_json(output / "package_report.json", report)
    return report


def prepare_training_shards(
    *, root: Path, manifest_path: Path, output_path: Path, shard_count: int
) -> dict[str, object]:
    """Create visible Kaggle datasets containing real recordings, not byteslices.

    A source recording is assigned deterministically by SHA-256.  Shards are
    checked to contain both train and validation examples without ever
    duplicating a recording or the locked test.
    """
    if shard_count < 2:
        raise ValueError("At least two visible data shards are required.")
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [
            dict(row) for row in csv.DictReader(handle)
            if row.get("split") in TRAINING_SPLITS
        ]
    groups: dict[int, set[str]] = {index: set() for index in range(shard_count)}
    for row in rows:
        key = row["source_id"].encode("utf-8")
        groups[int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % shard_count].add(
            row["source_id"]
        )
    output = _new_output(output_path)
    shards: list[dict[str, object]] = []
    for index in range(shard_count):
        destination = output / f"part-{index + 1:02d}"
        report = prepare_training(
            root=root,
            manifest_path=manifest_path,
            output_path=destination,
            source_ids=groups[index],
        )
        if set(report["splits"]) != set(TRAINING_SPLITS):
            raise ValueError(f"Shard {index + 1} is missing a split.")
        report.update({
            "kaggle_visible_shard": True,
            "shard_part": index + 1,
            "shard_count": shard_count,
        })
        _write_json(destination / "package_report.json", report)
        shards.append({
            "part": index + 1,
            "directory": destination.name,
            "recordings": report["recordings"],
            "bytes": report["bytes"],
            "splits": report["splits"],
            "locked_test_included": False,
        })
    result = {
        "schema_version": 1,
        "kind": "polyphonic_training_data_shards",
        "shard_count": shard_count,
        "recordings": sum(int(item["recordings"]) for item in shards),
        "bytes": sum(int(item["bytes"]) for item in shards),
        "locked_test_included": False,
        "shards": shards,
    }
    _write_json(output / "shards_report.json", result)
    return result


def prepare_raw(*, root: Path, output_path: Path) -> dict[str, object]:
    output = _new_output(output_path)
    selected: list[Path] = [
        Path("data/GuitarSet/annotation.zip"),
        Path("data/GuitarSet/audio_hex-pickup_debleeded.zip"),
        Path("data/GuitarSet/audio_mono-pickup_mix.zip"),
        Path("data/GAPS/gaps_metadata_with_splits.csv"),
        Path("data/GAPS/README.md"),
    ]
    selected.extend(sorted(
        path.relative_to(root)
        for path in (root / "data/GAPS/audio").rglob("*")
        if path.is_file()
    ))
    selected.extend(sorted(
        path.relative_to(root)
        for path in (root / "data/GAPS/midi").rglob("*")
        if path.is_file()
    ))
    selected.extend(sorted(
        path.relative_to(root)
        for path in (root / "data/Guitar-TECHS").glob("P*.zip")
        if path.is_file()
    ))
    if not selected:
        raise ValueError("No raw source files selected.")

    methods = Counter()
    total_bytes = 0
    for relative in selected:
        source = (root / relative).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        methods[_link_or_copy(source, output / relative)] += 1
        total_bytes += source.stat().st_size

    report = {
        "schema_version": 1,
        "kind": "polyphonic_raw_sources",
        "files": len(selected),
        "bytes": total_bytes,
        "staging_methods": dict(sorted(methods.items())),
        "included_sources": ["GuitarSet", "GAPS", "Guitar-TECHS"],
        "excluded_sources": ["IDMT-SMT-Guitar"],
        "passed": True,
    }
    _write_json(output / "package_report.json", report)
    return report


class _FileSlice:
    """Expose one bounded slice of a file to ``tarfile`` without staging it."""

    def __init__(self, source: Path, offset: int, size: int) -> None:
        self._handle: BinaryIO = source.open("rb")
        self._handle.seek(offset)
        self._remaining = size

    def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        if size < 0 or size > self._remaining:
            size = self._remaining
        value = self._handle.read(size)
        self._remaining -= len(value)
        return value

    def close(self) -> None:
        self._handle.close()


def _package_files(package: Path) -> list[Path]:
    return sorted(
        (path for path in (package / "data").rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(package).as_posix(),
    )


def _write_chunked_archives(
    *, package: Path, output: Path, part_bytes: int
) -> dict[str, object]:
    """Write bounded TARs whose members have only neutral generated names.

    Kaggle validates uploaded member paths.  The source dataset contains valid
    musical names such as ``C#`` that Kaggle rejects, so original paths must
    not be visible in upload TAR headers.  A small index restores every file
    byte-for-byte inside the Kaggle working directory.
    """
    if part_bytes < 16 * 1024 * 1024:
        raise ValueError("Archive part size must be at least 16 MiB.")
    files = _package_files(package)
    if not files:
        raise ValueError("Training package contains no data files.")

    index_files: list[dict[str, object]] = []
    archives: list[dict[str, object]] = []
    archive: tarfile.TarFile | None = None
    archive_bytes = 0
    archive_parts = 0

    def open_archive() -> tarfile.TarFile:
        nonlocal archive_bytes, archive_parts
        name = f"training_data_{len(archives):03d}.tar"
        archives.append({"name": name, "payload_bytes": 0, "parts": 0})
        archive_bytes = 0
        archive_parts = 0
        return tarfile.open(output / name, "w", format=tarfile.PAX_FORMAT)

    try:
        for file_index, source in enumerate(files):
            relative = source.relative_to(package).as_posix()
            file_size = source.stat().st_size
            offset = 0
            parts: list[dict[str, object]] = []
            while offset < file_size or (file_size == 0 and not parts):
                remaining_space = part_bytes - archive_bytes
                if archive is None or remaining_space <= 0:
                    if archive is not None:
                        archive.close()
                    archive = open_archive()
                    remaining_space = part_bytes
                size = min(remaining_space, file_size - offset)
                if file_size == 0:
                    size = 0
                member = f"parts/{file_index:06d}_{len(parts):06d}.bin"
                info = tarfile.TarInfo(member)
                info.size = size
                info.mode = 0o600
                info.mtime = 0
                reader = _FileSlice(source, offset, size)
                try:
                    archive.addfile(info, reader)
                finally:
                    reader.close()
                part = {
                    "archive": archives[-1]["name"],
                    "member": member,
                    "bytes": size,
                }
                parts.append(part)
                archives[-1]["payload_bytes"] = int(
                    archives[-1]["payload_bytes"]
                ) + size
                archives[-1]["parts"] = int(archives[-1]["parts"]) + 1
                archive_bytes += size
                archive_parts += 1
                offset += size
                if file_size == 0:
                    break
            index_files.append({"path": relative, "bytes": file_size, "parts": parts})
    finally:
        if archive is not None:
            archive.close()

    index = {
        "schema_version": 1,
        "format": "kaggle_chunked_tar_v1",
        "files": index_files,
        "archives": archives,
    }
    _write_json(output / "training_archive_index.json", index)
    return index


def prepare_training_archive(
    *, package_path: Path, output_path: Path,
    part_bytes: int = DEFAULT_ARCHIVE_PART_BYTES,
) -> dict[str, object]:
    package = package_path.resolve()
    report_path = package / "package_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("passed") is not True
        or report.get("locked_test_included") is not False
        or report.get("kind") != "polyphonic_train_validation"
    ):
        raise ValueError("Training package is not safe for Kaggle upload.")
    output = _new_output(output_path)
    index = _write_chunked_archives(
        package=package, output=output, part_bytes=part_bytes
    )
    shutil.copy2(report_path, output / "package_report.json")
    upload_report = {
        **report,
        "upload_files": len(index["archives"]) + 2,
        "archive_format": index["format"],
        "archive_index": "training_archive_index.json",
        "archive_part_payload_bytes": part_bytes,
        "archives": index["archives"],
        "archive_payload_bytes": sum(
            int(item["payload_bytes"]) for item in index["archives"]
        ),
    }
    _write_json(output / "package_report.json", upload_report)
    return upload_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    training = subparsers.add_parser("training")
    training.add_argument("--root", type=Path, default=ROOT)
    training.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST
    )
    training.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/kaggle/polyphonic-train-validation"),
    )

    raw = subparsers.add_parser("raw")
    raw.add_argument("--root", type=Path, default=ROOT)
    raw.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/kaggle/polyphonic-raw-sources"),
    )

    archive = subparsers.add_parser("archive-training")
    archive.add_argument(
        "--package",
        type=Path,
        default=Path("tmp/kaggle/polyphonic-train-validation"),
    )
    shards = subparsers.add_parser("training-shards")
    shards.add_argument("--root", type=Path, default=ROOT)
    shards.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    shards.add_argument(
        "--output", type=Path,
        default=Path("tmp/kaggle/polyphonic-training-data-shards"),
    )
    shards.add_argument("--count", type=int, default=16)
    archive.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/kaggle/polyphonic-train-validation-upload"),
    )
    archive.add_argument(
        "--part-mib", type=int, default=512,
        help="Maximum payload per upload TAR (minimum 16 MiB).",
    )

    args = parser.parse_args()
    os.chdir(ROOT)
    if args.kind == "training":
        report = prepare_training(
            root=args.root.resolve(),
            manifest_path=args.manifest.resolve(),
            output_path=args.output,
        )
    elif args.kind == "raw":
        report = prepare_raw(
            root=args.root.resolve(), output_path=args.output
        )
    elif args.kind == "archive-training":
        report = prepare_training_archive(
            package_path=args.package, output_path=args.output,
            part_bytes=args.part_mib * 1024 * 1024,
        )
    else:
        report = prepare_training_shards(
            root=args.root.resolve(), manifest_path=args.manifest.resolve(),
            output_path=args.output, shard_count=args.count,
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
