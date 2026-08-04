"""Materialize train/validation fundamental-tuning offsets for note labels.

The existing compact harmonic labels predate ``note_fundamental_offset_cents``.
Rebuilding the multi-gigabyte processed corpus just to add that one note-level
array would be wasteful.  This tool derives a small, deterministic sidecar
from the already-authorized train/validation manifest and the GuitarSet JAMS +
harmonic CSV provenance.  It never reads a test row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from src.dataset.build_stream_dataset import load_jams_notes
from src.polyphonic.dataset_builder import build_harmonic_tables


SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_manifest_path(value: str, manifest_directory: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (manifest_directory / path).resolve()


def _record_key(record: dict[str, Any]) -> tuple[str, str]:
    return str(record["dataset_id"]), str(record["source_id"])


def build_fundamental_offset_sidecar(
    manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    """Write a compact, provenance-bound sidecar for GuitarSet records.

    The input manifest is allowed to contain train and validation rows only.
    Any test row is an immediate hard failure even though this function would
    otherwise skip it.
    """

    manifest_path = manifest_path.resolve(strict=True)
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "source_id", "dataset_id", "split", "annotation_path",
        "harmonic_csv_path", "labels_path",
    }
    if not rows:
        raise ValueError("Fundamental-offset manifest is empty.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Fundamental-offset manifest lacks {sorted(missing)}")
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts.get("test", 0):
        raise ValueError("Fail closed: sidecar input includes locked test rows.")
    unexpected_splits = set(split_counts) - {"train", "validation"}
    if unexpected_splits:
        raise ValueError(f"Unexpected manifest splits: {sorted(unexpected_splits)}")

    records: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in sorted(rows, key=lambda value: (value["dataset_id"], value["source_id"])):
        dataset_id = str(row["dataset_id"])
        if dataset_id != "guitarset_poly_mix":
            continue
        key = (dataset_id, str(row["source_id"]))
        if key in seen:
            raise ValueError(f"Duplicate sidecar key {key!r}")
        seen.add(key)
        annotation = _resolve_manifest_path(
            str(row["annotation_path"]), manifest_path.parent
        )
        harmonic_csv = _resolve_manifest_path(
            str(row["harmonic_csv_path"]), manifest_path.parent
        )
        labels_path = _resolve_manifest_path(
            str(row["labels_path"]), manifest_path.parent
        )
        notes = load_jams_notes(annotation)
        tables = build_harmonic_tables(notes, harmonic_csv)
        offsets = np.asarray(
            tables["note_fundamental_offset_cents"], dtype=np.float32
        )
        with np.load(labels_path, allow_pickle=False) as labels:
            if "note_pitch_midi" not in labels.files:
                raise ValueError(f"{key!r}: label archive has no note_pitch_midi")
            if len(labels["note_pitch_midi"]) != len(offsets):
                raise ValueError(
                    f"{key!r}: note offset rows do not match label note rows"
                )
        if not np.all(np.isfinite(offsets)):
            raise ValueError(f"{key!r}: non-finite fundamental offset")
        records.append({
            "dataset_id": dataset_id,
            "source_id": str(row["source_id"]),
            "split": str(row["split"]),
            "labels_sha256": sha256_file(labels_path),
            "note_fundamental_offset_cents": [
                float(value) for value in offsets.tolist()
            ],
        })

    if not records:
        raise ValueError("No GuitarSet train/validation records were materialized.")
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "locked_test_used": False,
        "manifest_sha256": sha256_file(manifest_path),
        "records": records,
        "counts": {
            "manifest_rows": len(rows),
            "records": len(records),
            "by_split": dict(sorted(Counter(record["split"] for record in records).items())),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(output_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_fundamental_offset_sidecar(args.manifest, args.output)
    print(json.dumps({
        "schema_version": report["schema_version"],
        "locked_test_used": report["locked_test_used"],
        "manifest_sha256": report["manifest_sha256"],
        "counts": report["counts"],
        "output": str(args.output),
        "sha256": sha256_file(args.output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
