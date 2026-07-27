"""Validate compact polyphonic labels, split isolation, and harmonics."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.polyphonic.data import load_manifest


def validate(manifest_path: Path) -> dict[str, object]:
    items = load_manifest(manifest_path)
    group_splits: dict[str, set[str]] = defaultdict(set)
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: list[str] = []
    for item in items:
        group_splits[item.group_id].add(item.split)
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
            split = summary[item.split]
            split["recordings"] += 1
            split["frames"] += len(active)
            split["valid_frames"] += int(np.sum(valid))
            split["active_frames"] += int(np.sum(valid & (active != 0)))
            split["polyphonic_frames"] += int(np.sum(valid & (polyphony > 1)))
            split["onset_frames"] += int(np.sum(valid & (onset != 0)))
            split["notes"] += note_rows
            split["harmonic_notes"] += int(np.sum(arrays["note_harmonic_valid"] > 0))
            split["evaluation_notes"] += int(np.sum(arrays["note_evaluation_valid"] > 0))

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
        "splits": {
            split: dict(values) for split, values in sorted(summary.items())
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
    args = parser.parse_args()
    report = validate(args.manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
