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
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(
    "data/processed/polyphonic_v2_2_combined/manifest.csv"
)
TRAINING_SPLITS = frozenset({"train", "validation"})


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

    args = parser.parse_args()
    os.chdir(ROOT)
    if args.kind == "training":
        report = prepare_training(
            root=args.root.resolve(),
            manifest_path=args.manifest.resolve(),
            output_path=args.output,
        )
    else:
        report = prepare_raw(
            root=args.root.resolve(), output_path=args.output
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
