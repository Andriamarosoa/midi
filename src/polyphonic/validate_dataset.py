"""Validate compact polyphonic labels, split isolation, and harmonics."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.polyphonic.data import load_manifest


HARMONIC_SCHEMA_ARRAYS = {
    "note_harmonic_supervised",
    "note_harmonic_reliability",
    "note_harmonic_relative_db",
    "note_harmonic_frames_measured",
}
HARMONIC_SCHEMA_METADATA = {
    "harmonic_supervision_schema_version",
    "harmonic_presence_floor_db",
    "harmonic_reliability_formula",
}
HARMONIC_RELIABILITY_FORMULA = "sqrt(n/(n+1))"


def _scalar(arrays, name: str):
    value = np.asarray(arrays[name])
    if value.shape != ():
        raise ValueError(f"{name} must be scalar")
    return value.item()


def _binary(values: np.ndarray) -> bool:
    return bool(
        np.all(np.isfinite(values))
        and np.all((values == 0.0) | (values == 1.0))
    )


def _harmonic_contract_failures(
    source_id: str,
    arrays,
    note_rows: int,
    *,
    required_schema_version: int | None,
) -> tuple[list[str], dict[str, float | int]]:
    failures: list[str] = []
    files = set(arrays.files)
    available = (HARMONIC_SCHEMA_ARRAYS | HARMONIC_SCHEMA_METADATA) & files
    required = HARMONIC_SCHEMA_ARRAYS | HARMONIC_SCHEMA_METADATA
    if not available:
        if required_schema_version is not None:
            failures.append(
                f"{source_id}: harmonic supervision schema "
                f"{required_schema_version} is required"
            )
        return failures, {}
    if available != required:
        failures.append(f"{source_id}: incomplete harmonic supervision contract")
        return failures, {}

    try:
        schema_version = int(_scalar(
            arrays, "harmonic_supervision_schema_version"
        ))
        presence_floor_db = float(_scalar(
            arrays, "harmonic_presence_floor_db"
        ))
        reliability_formula = str(_scalar(
            arrays, "harmonic_reliability_formula"
        ))
    except (TypeError, ValueError) as error:
        failures.append(f"{source_id}: invalid harmonic metadata: {error}")
        return failures, {}
    if required_schema_version is not None and schema_version != int(
        required_schema_version
    ):
        failures.append(
            f"{source_id}: harmonic schema {schema_version} != "
            f"{required_schema_version}"
        )
    if not math.isfinite(presence_floor_db) or presence_floor_db >= 0.0:
        failures.append(f"{source_id}: invalid harmonic presence floor")
    if reliability_formula != HARMONIC_RELIABILITY_FORMULA:
        failures.append(f"{source_id}: invalid harmonic reliability formula")

    present = np.asarray(arrays["note_harmonic_present"], np.float32)
    amplitude = np.asarray(arrays["note_harmonic_amplitude"], np.float32)
    offset = np.asarray(arrays["note_harmonic_offset_cents"], np.float32)
    supervised = np.asarray(arrays["note_harmonic_supervised"], np.float32)
    reliability = np.asarray(arrays["note_harmonic_reliability"], np.float32)
    relative_db = np.asarray(arrays["note_harmonic_relative_db"], np.float32)
    raw_frames = np.asarray(arrays["note_harmonic_frames_measured"])
    expected_shape = present.shape
    tables = {
        "amplitude": amplitude,
        "offset": offset,
        "supervised": supervised,
        "reliability": reliability,
        "relative_db": relative_db,
        "frames_measured": raw_frames,
    }
    if present.ndim != 2 or present.shape[0] != note_rows:
        failures.append(f"{source_id}: invalid harmonic table shape")
        return failures, {}
    for name, values in tables.items():
        if values.shape != expected_shape:
            failures.append(
                f"{source_id}: harmonic supervision shape mismatch {name}"
            )
    if failures:
        return failures, {}

    if not _binary(present):
        failures.append(f"{source_id}: harmonic presence must be binary")
    if not _binary(supervised):
        failures.append(f"{source_id}: harmonic supervision must be binary")
    if np.any(present > supervised):
        failures.append(f"{source_id}: presence without supervision")
    if (
        np.any(~np.isfinite(amplitude))
        or np.any(amplitude < 0.0)
        or np.any(amplitude > 1.0 + 1e-4)
    ):
        failures.append(f"{source_id}: invalid harmonic amplitude")
    if np.any(~np.isfinite(offset)):
        failures.append(f"{source_id}: invalid harmonic offset")
    if (
        np.any(~np.isfinite(reliability))
        or np.any(reliability < 0.0)
        or np.any(reliability > 1.0)
    ):
        failures.append(f"{source_id}: invalid harmonic reliability")
    if raw_frames.dtype.kind not in {"i", "u"} or np.any(raw_frames < 0):
        failures.append(f"{source_id}: invalid frames_measured")

    supervised_mask = supervised > 0.5
    unavailable_mask = ~supervised_mask
    if np.any(raw_frames[supervised_mask] <= 0):
        failures.append(f"{source_id}: supervised partial without frames")
    if np.any(reliability[unavailable_mask] != 0.0):
        failures.append(f"{source_id}: reliability without supervision")
    if np.any(amplitude[unavailable_mask] != 0.0):
        failures.append(f"{source_id}: amplitude without supervision")
    if np.any(present[unavailable_mask] != 0.0):
        failures.append(f"{source_id}: presence without measured frames")
    if np.any(~np.isfinite(relative_db[supervised_mask])):
        failures.append(f"{source_id}: supervised partial without relative_db")

    if np.any(supervised_mask):
        expected_reliability = np.sqrt(
            raw_frames[supervised_mask].astype(np.float64)
            / (raw_frames[supervised_mask].astype(np.float64) + 1.0)
        )
        if not np.allclose(
            reliability[supervised_mask],
            expected_reliability,
            rtol=2e-3,
            atol=2e-3,
        ):
            failures.append(f"{source_id}: reliability formula mismatch")
        expected_presence = (
            relative_db[supervised_mask] >= presence_floor_db
        ).astype(np.float32)
        if not np.array_equal(present[supervised_mask], expected_presence):
            failures.append(f"{source_id}: presence floor mismatch")

    expected_amplitude = np.zeros_like(amplitude)
    for note_index in range(note_rows):
        note_mask = supervised_mask[note_index]
        if not np.any(note_mask):
            continue
        raw = relative_db[note_index, note_mask]
        expected_amplitude[note_index, note_mask] = np.power(
            np.float32(10.0),
            (raw - np.max(raw)) / np.float32(20.0),
        )
    if not np.allclose(amplitude, expected_amplitude, rtol=2e-3, atol=2e-3):
        failures.append(f"{source_id}: relative harmonic strength mismatch")

    note_valid = np.asarray(arrays["note_harmonic_valid"], np.float32)
    if not _binary(note_valid):
        failures.append(f"{source_id}: note_harmonic_valid must be binary")
    elif not np.array_equal(
        note_valid > 0.5, np.any(supervised_mask, axis=1)
    ):
        failures.append(f"{source_id}: note_harmonic_valid mismatch")

    weights = supervised * reliability
    return failures, {
        "schema_version": schema_version,
        "supervised_partials": int(np.sum(supervised_mask)),
        "present_partials": int(np.sum(present[supervised_mask])),
        "absent_partials": int(np.sum(1.0 - present[supervised_mask])),
        "supervision_weight": float(np.sum(weights)),
        "present_weight": float(np.sum(weights * present)),
        "absent_weight": float(np.sum(weights * (1.0 - present))),
    }


def validate(
    manifest_path: Path,
    *,
    require_harmonic_schema_version: int | None = None,
    harmonic_dataset_ids: set[str] | None = None,
    allowed_splits: set[str] | None = None,
    required_splits: set[str] | None = None,
) -> dict[str, object]:
    items = load_manifest(manifest_path)
    harmonic_dataset_ids = (
        None if harmonic_dataset_ids is None else set(harmonic_dataset_ids)
    )
    allowed_splits = None if allowed_splits is None else set(allowed_splits)
    required_splits = set(required_splits or ())
    group_splits: dict[str, set[str]] = defaultdict(set)
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    harmonic_summary: dict[str, dict[str, float | int]] = defaultdict(
        lambda: defaultdict(float)
    )
    harmonic_by_dataset: dict[str, dict[str, float | int]] = defaultdict(
        lambda: defaultdict(float)
    )
    failures: list[str] = []
    validated_splits: set[str] = set()
    validated_recordings = 0
    for item in items:
        group_splits[item.group_id].add(item.split)
        if allowed_splits is not None and item.split not in allowed_splits:
            failures.append(f"{item.source_id}: forbidden split {item.split}")
            continue
        validated_splits.add(item.split)
        validated_recordings += 1
        with np.load(item.labels_path, allow_pickle=False) as arrays:
            active = np.asarray(arrays["active_bits"], np.uint64)
            onset = np.asarray(arrays["onset_bits"], np.uint64)
            valid = np.asarray(arrays["valid"] > 0)
            polyphony = np.asarray(arrays["polyphony"], np.int16)
            pitch_classes = int(arrays["midi_max"] - arrays["midi_min"] + 1)
            permitted = (np.uint64(1) << np.uint64(pitch_classes)) - np.uint64(1)
            if np.any(active & ~permitted) or np.any(onset & ~permitted):
                failures.append(f"{item.source_id}: bits outside MIDI scope")
            if np.any(onset & ~active):
                failures.append(f"{item.source_id}: onset outside active frame")
            bit_count = np.unpackbits(
                active.view(np.uint8).reshape(-1, 8), axis=1
            ).sum(axis=1, dtype=np.int16)
            if np.any(valid & (bit_count != polyphony)):
                failures.append(f"{item.source_id}: valid polyphony/bit mismatch")
            slots = np.asarray(arrays["slot_pitch"], np.int16)
            slot_note_id = np.asarray(arrays["slot_note_id"], np.int64)
            if slots.shape != slot_note_id.shape or slots.shape[0] != len(active):
                failures.append(f"{item.source_id}: inconsistent slot arrays")
            else:
                slot_count = np.sum(slots >= 0, axis=1)
                if np.any(valid & (slot_count != bit_count)):
                    failures.append(f"{item.source_id}: valid slot/bit mismatch")
            note_rows = len(arrays["note_harmonic_valid"])
            for name in (
                "note_harmonic_present", "note_harmonic_amplitude",
                "note_harmonic_offset_cents", "note_pitch_midi",
                "note_start_s", "note_end_s", "note_evaluation_valid",
            ):
                if len(arrays[name]) != note_rows:
                    failures.append(f"{item.source_id}: note table mismatch {name}")
            if slot_note_id.shape == slots.shape and (
                np.any(slot_note_id < -1)
                or np.any(slot_note_id >= note_rows)
                or np.any((slots < 0) != (slot_note_id < 0))
            ):
                failures.append(f"{item.source_id}: invalid slot note_id")

            strict_for_item = (
                require_harmonic_schema_version
                if harmonic_dataset_ids is None
                or item.dataset_id in harmonic_dataset_ids
                else None
            )
            contract_failures, contract_summary = _harmonic_contract_failures(
                item.source_id,
                arrays,
                note_rows,
                required_schema_version=strict_for_item,
            )
            failures.extend(contract_failures)
            if contract_summary:
                for destination in (
                    harmonic_summary[item.split],
                    harmonic_by_dataset[f"{item.split}:{item.dataset_id}"],
                ):
                    destination["recordings"] += 1
                    for key in (
                        "supervised_partials", "present_partials",
                        "absent_partials", "supervision_weight",
                        "present_weight", "absent_weight",
                    ):
                        destination[key] += contract_summary[key]

            split = summary[item.split]
            split["recordings"] += 1
            split["frames"] += len(active)
            split["valid_frames"] += int(np.sum(valid))
            split["active_frames"] += int(np.sum(valid & (active != 0)))
            split["polyphonic_frames"] += int(np.sum(valid & (polyphony > 1)))
            split["onset_frames"] += int(np.sum(valid & (onset != 0)))
            split["notes"] += note_rows
            split["harmonic_notes"] += int(
                np.sum(arrays["note_harmonic_valid"] > 0)
            )
            split["evaluation_notes"] += int(
                np.sum(arrays["note_evaluation_valid"] > 0)
            )

    missing_splits = required_splits - validated_splits
    if missing_splits:
        failures.append(f"required splits missing: {sorted(missing_splits)}")
    leaking_groups = {
        group: sorted(splits)
        for group, splits in group_splits.items()
        if len(splits) > 1
    }
    if leaking_groups:
        failures.append(f"{len(leaking_groups)} groups cross split boundaries")
    report = {
        "manifest": str(manifest_path),
        "recordings": len(items),
        "validated_recordings": validated_recordings,
        "validated_splits": sorted(validated_splits),
        "locked_test_used": "test" in validated_splits,
        "strict_contract": {
            "harmonic_schema_version": require_harmonic_schema_version,
            "harmonic_dataset_ids": sorted(harmonic_dataset_ids or ()),
            "allowed_splits": (
                None if allowed_splits is None else sorted(allowed_splits)
            ),
            "required_splits": sorted(required_splits),
        },
        "splits": {
            split: dict(values) for split, values in sorted(summary.items())
        },
        "harmonic_splits": {
            split: dict(values)
            for split, values in sorted(harmonic_summary.items())
        },
        "harmonic_datasets": {
            name: dict(values)
            for name, values in sorted(harmonic_by_dataset.items())
        },
        "leaking_groups": leaking_groups,
        "failures": failures,
        "passed": not failures,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-harmonic-schema-version", type=int)
    parser.add_argument("--harmonic-dataset-id", action="append")
    parser.add_argument("--allowed-split", action="append")
    parser.add_argument("--required-split", action="append")
    args = parser.parse_args()
    report = validate(
        args.manifest,
        require_harmonic_schema_version=args.require_harmonic_schema_version,
        harmonic_dataset_ids=(
            None
            if args.harmonic_dataset_id is None
            else set(args.harmonic_dataset_id)
        ),
        allowed_splits=(
            None if args.allowed_split is None else set(args.allowed_split)
        ),
        required_splits=set(args.required_split or ()),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
