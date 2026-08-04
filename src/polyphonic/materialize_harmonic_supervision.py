"""Materialize schema-3 harmonic labels for train/validation only.

The source combined manifest may inventory a locked test split, but this
materializer never resolves, opens, copies, or emits a test artifact. Only
GuitarSet label NPZ files are enriched; other train/validation corpora remain
referenced read-only through absolute paths.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.dataset.build_stream_dataset import load_jams_notes
from src.polyphonic.dataset_builder import (
    HARMONIC_PRESENCE_FLOOR_DB,
    HARMONIC_RELIABILITY_FORMULA,
    HARMONIC_SUPERVISION_SCHEMA_VERSION,
    build_harmonic_tables,
)
from src.polyphonic.validate_dataset import validate


ALLOWED_SPLITS = {"train", "validation"}
HARMONIC_DATASET_ID = "guitarset_poly_mix"
PATH_FIELDS = (
    "audio_path",
    "labels_path",
    "annotation_path",
    "harmonic_csv_path",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(value: str, repository_root: Path) -> Path:
    path = Path(value.replace("\\", "/"))
    if not path.is_absolute():
        path = repository_root / path
    return path.resolve(strict=True)


def _absolute_row(
    row: dict[str, str], repository_root: Path
) -> dict[str, str]:
    result = dict(row)
    for name in PATH_FIELDS:
        value = result.get(name, "")
        if value:
            result[name] = str(_resolve_path(value, repository_root))
    return result


def _portable_row(
    row: dict[str, str],
    repository_root: Path,
    manifest_directory: Path,
) -> dict[str, str]:
    """Serialize project-owned paths relative to the manifest directory."""
    result = dict(row)
    for name in PATH_FIELDS:
        value = result.get(name, "")
        if not value:
            continue
        resolved = Path(value).resolve(strict=True)
        try:
            resolved.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                f"{name} must remain inside repository_root: {resolved}"
            ) from exc
        result[name] = Path(
            os.path.relpath(resolved, start=manifest_directory)
        ).as_posix()
    return result


def _schema_metadata() -> dict[str, np.ndarray]:
    return {
        "harmonic_supervision_schema_version": np.int8(
            HARMONIC_SUPERVISION_SCHEMA_VERSION
        ),
        "harmonic_presence_floor_db": np.float32(
            HARMONIC_PRESENCE_FLOOR_DB
        ),
        "harmonic_reliability_formula": np.asarray(
            HARMONIC_RELIABILITY_FORMULA
        ),
    }


def _materialize_guitarset_label(
    row: dict[str, str],
    destination: Path,
) -> dict[str, object]:
    source_labels = Path(row["labels_path"])
    annotation = Path(row["annotation_path"])
    harmonic_csv = Path(row["harmonic_csv_path"])
    notes = load_jams_notes(annotation)
    harmonics = build_harmonic_tables(notes, harmonic_csv)
    with np.load(source_labels, allow_pickle=False) as source:
        arrays = {name: np.asarray(source[name]) for name in source.files}
    arrays.update(harmonics)
    arrays.pop("harmonic_reliability_full_frames", None)
    arrays.update(_schema_metadata())
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **arrays)
    return {
        "source_id": row["source_id"],
        "split": row["split"],
        "notes": len(notes),
        "supervised_partials": int(np.sum(
            harmonics["note_harmonic_supervised"] > 0
        )),
        "present_partials": int(np.sum(
            harmonics["note_harmonic_present"] > 0
        )),
        "absent_partials": int(np.sum(
            (harmonics["note_harmonic_supervised"] > 0)
            & (harmonics["note_harmonic_present"] == 0)
        )),
        "source_labels": str(source_labels),
        "source_labels_sha256": _sha256(source_labels),
        "annotation_sha256": _sha256(annotation),
        "harmonic_csv_sha256": _sha256(harmonic_csv),
        "output_labels": str(destination),
        "output_labels_bytes": destination.stat().st_size,
        "output_labels_sha256": _sha256(destination),
    }


def materialize(
    source_manifest: Path,
    output_root: Path,
    *,
    repository_root: Path | None = None,
) -> dict[str, object]:
    repository_root = (repository_root or Path.cwd()).resolve(strict=True)
    source_manifest = (
        source_manifest
        if source_manifest.is_absolute()
        else repository_root / source_manifest
    ).resolve(strict=True)
    output_root = (
        output_root
        if output_root.is_absolute()
        else repository_root / output_root
    ).resolve()
    if output_root.exists():
        raise FileExistsError(f"Output root already exists: {output_root}")
    output_root.mkdir(parents=True, exist_ok=False)

    with source_manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        source_rows = [dict(row) for row in reader]
    if not source_rows or not fieldnames:
        raise ValueError("Source manifest is empty")

    selected = [row for row in source_rows if row.get("split") in ALLOWED_SPLITS]
    selected.sort(
        key=lambda row: (row["dataset_id"], row["split"], row["source_id"])
    )
    if {row["split"] for row in selected} != ALLOWED_SPLITS:
        raise ValueError("Both train and validation splits are required")
    keys = [(row["dataset_id"], row["source_id"]) for row in selected]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate dataset/source IDs in source manifest")

    rows: list[dict[str, str]] = []
    artifacts: list[dict[str, object]] = []
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for source_row in selected:
        row = _absolute_row(source_row, repository_root)
        if row["dataset_id"] == HARMONIC_DATASET_ID:
            if not row.get("annotation_path") or not row.get("harmonic_csv_path"):
                raise ValueError(
                    f"{row['source_id']}: GuitarSet harmonic sources missing"
                )
            destination = (
                output_root
                / "labels"
                / HARMONIC_DATASET_ID
                / f"{row['source_id']}.npz"
            ).resolve()
            artifacts.append(_materialize_guitarset_label(row, destination))
            row["labels_path"] = str(destination)
        rows.append(row)
        counts[row["dataset_id"]][row["split"]] += 1

    if any(row["split"] not in ALLOWED_SPLITS for row in rows):
        raise AssertionError("Forbidden split reached output rows")
    manifest_path = (output_root / "manifest_train_validation.csv").resolve()
    portable_rows = [
        _portable_row(row, repository_root, manifest_path.parent)
        for row in rows
    ]
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(portable_rows)

    validation = validate(
        manifest_path,
        require_harmonic_schema_version=HARMONIC_SUPERVISION_SCHEMA_VERSION,
        harmonic_dataset_ids={HARMONIC_DATASET_ID},
        allowed_splits=ALLOWED_SPLITS,
        required_splits=ALLOWED_SPLITS,
    )
    validation_path = (output_root / "validation_report.json").resolve()
    validation_path.write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    if not validation["passed"] or validation["locked_test_used"]:
        raise ValueError(
            "Strict materialized-dataset validation failed: "
            f"{validation['failures']}"
        )

    excluded_by_split: dict[str, int] = defaultdict(int)
    for row in source_rows:
        if row.get("split") not in ALLOWED_SPLITS:
            excluded_by_split[str(row.get("split"))] += 1
    report = {
        "status": "complete",
        "schema_version": 1,
        "harmonic_supervision_schema_version": (
            HARMONIC_SUPERVISION_SCHEMA_VERSION
        ),
        "harmonic_presence_floor_db": HARMONIC_PRESENCE_FLOOR_DB,
        "harmonic_reliability_formula": HARMONIC_RELIABILITY_FORMULA,
        "locked_test_used": False,
        "allowed_splits": sorted(ALLOWED_SPLITS),
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": _sha256(source_manifest),
        "source_rows": len(source_rows),
        "excluded_rows_by_split": dict(sorted(excluded_by_split.items())),
        "output_root": str(output_root),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "output_rows": len(rows),
        "counts": {
            dataset: dict(sorted(splits.items()))
            for dataset, splits in sorted(counts.items())
        },
        "guitarset_artifacts": artifacts,
        "validation_report": str(validation_path),
        "validation_report_sha256": _sha256(validation_path),
        "validator_passed": True,
        "script": str(Path(__file__).resolve()),
        "script_sha256": _sha256(Path(__file__).resolve()),
    }
    report_path = (output_root / "materialization_report.json").resolve()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = materialize(
        args.source_manifest,
        args.output_root,
        repository_root=args.repository_root,
    )
    print(json.dumps({
        "status": report["status"],
        "manifest": report["manifest"],
        "manifest_sha256": report["manifest_sha256"],
        "output_rows": report["output_rows"],
        "counts": report["counts"],
        "locked_test_used": report["locked_test_used"],
        "validator_passed": report["validator_passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
