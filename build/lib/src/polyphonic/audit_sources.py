"""Audit note annotations before building a polyphonic training set.

The audit is deliberately annotation-only: it is fast, reproducible, and
detects whether a source really contains overlapping notes before any large
audio cache is built.  Audio/annotation alignment is validated separately by
the dataset builder.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from src.v5.external_data import (
    NoteEvent,
    parse_guitarset_notes,
    parse_idmt_notes,
    parse_midi_notes,
)


DEFAULT_MIDI_MIN = 40
DEFAULT_MIDI_MAX = 76


@dataclass(frozen=True)
class AnnotationRecording:
    dataset: str
    subset: str
    recording_id: str
    split: str
    annotation_path: Path
    annotation_format: str


@dataclass(frozen=True)
class RecordingAudit:
    dataset: str
    subset: str
    recording_id: str
    split: str
    annotation_path: str
    note_count: int
    unique_pitch_count: int
    minimum_pitch: int | None
    maximum_pitch: int | None
    notes_in_scope: int
    notes_below_scope: int
    notes_above_scope: int
    maximum_polyphony: int
    annotated_duration_s: float
    active_duration_s: float
    polyphonic_duration_s: float
    polyphonic_duration_ratio: float


def _parse(recording: AnnotationRecording) -> list[NoteEvent]:
    if recording.annotation_format == "midi":
        return parse_midi_notes(recording.annotation_path)
    if recording.annotation_format == "guitarset_jams":
        return parse_guitarset_notes(recording.annotation_path)
    if recording.annotation_format == "idmt_xml":
        return parse_idmt_notes(recording.annotation_path)
    raise ValueError(f"Unsupported annotation format: {recording.annotation_format}")


def _activity_durations(notes: Iterable[NoteEvent]) -> tuple[int, float, float]:
    """Return maximum polyphony, active duration, and polyphonic duration."""
    changes: dict[float, int] = {}
    for note in notes:
        if note.end_s <= note.start_s:
            continue
        changes[note.start_s] = changes.get(note.start_s, 0) + 1
        changes[note.end_s] = changes.get(note.end_s, 0) - 1

    previous_time: float | None = None
    active = 0
    maximum = 0
    active_duration = 0.0
    polyphonic_duration = 0.0
    for time_s in sorted(changes):
        if previous_time is not None:
            duration = time_s - previous_time
            if active > 0:
                active_duration += duration
            if active > 1:
                polyphonic_duration += duration
        active += changes[time_s]
        if active < 0:
            raise ValueError("Negative note activity: malformed annotation timeline")
        maximum = max(maximum, active)
        previous_time = time_s
    if active != 0:
        raise ValueError("Unbalanced note activity: malformed annotation timeline")
    return maximum, active_duration, polyphonic_duration


def audit_notes(
    recording: AnnotationRecording,
    notes: Sequence[NoteEvent],
    midi_min: int = DEFAULT_MIDI_MIN,
    midi_max: int = DEFAULT_MIDI_MAX,
) -> RecordingAudit:
    pitches = [int(note.pitch_midi) for note in notes]
    maximum_polyphony, active_duration, polyphonic_duration = (
        _activity_durations(notes)
    )
    annotated_duration = max((note.end_s for note in notes), default=0.0)
    return RecordingAudit(
        dataset=recording.dataset,
        subset=recording.subset,
        recording_id=recording.recording_id,
        split=recording.split,
        annotation_path=str(recording.annotation_path),
        note_count=len(notes),
        unique_pitch_count=len(set(pitches)),
        minimum_pitch=min(pitches) if pitches else None,
        maximum_pitch=max(pitches) if pitches else None,
        notes_in_scope=sum(midi_min <= pitch <= midi_max for pitch in pitches),
        notes_below_scope=sum(pitch < midi_min for pitch in pitches),
        notes_above_scope=sum(pitch > midi_max for pitch in pitches),
        maximum_polyphony=maximum_polyphony,
        annotated_duration_s=annotated_duration,
        active_duration_s=active_duration,
        polyphonic_duration_s=polyphonic_duration,
        polyphonic_duration_ratio=(
            polyphonic_duration / active_duration if active_duration else 0.0
        ),
    )


def discover_guitarset(root: Path) -> list[AnnotationRecording]:
    split_by_player = {
        **{f"{player:02d}": "train" for player in range(4)},
        "04": "validation",
        "05": "test",
    }
    recordings: list[AnnotationRecording] = []
    for annotation in sorted((root / "annotation").glob("*.jams")):
        player = annotation.stem[:2]
        recordings.append(AnnotationRecording(
            dataset="guitarset",
            subset="mix",
            recording_id=annotation.stem,
            split=split_by_player.get(player, "unassigned"),
            annotation_path=annotation,
            annotation_format="guitarset_jams",
        ))
    return recordings


def discover_gaps(root: Path) -> list[AnnotationRecording]:
    metadata = root / "gaps_metadata_with_splits.csv"
    recordings: list[AnnotationRecording] = []
    with metadata.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            recording_id = (row.get("id") or "").strip()
            midi_relative = (row.get("midi_path") or "").strip()
            if not recording_id or not midi_relative:
                continue
            annotation = root.joinpath(*midi_relative.replace("\\", "/").split("/"))
            if not annotation.is_file():
                continue
            recordings.append(AnnotationRecording(
                dataset="gaps",
                subset="aligned_performance",
                recording_id=recording_id,
                split=(row.get("split") or "unassigned").strip() or "unassigned",
                annotation_path=annotation,
                annotation_format="midi",
            ))
    return recordings


def discover_guitar_techs(root: Path) -> list[AnnotationRecording]:
    recordings: list[AnnotationRecording] = []
    for category in sorted(path for path in root.iterdir() if path.is_dir()):
        if category.name.startswith("__"):
            continue
        for annotation in sorted((category / "midi").glob("*.mid")):
            player = category.name[:2].lower()
            recordings.append(AnnotationRecording(
                dataset="guitar_techs",
                subset=category.name,
                recording_id=f"{category.name}_{annotation.stem}",
                split=f"external_{player}",
                annotation_path=annotation,
                annotation_format="midi",
            ))
    return recordings


def discover_idmt(root: Path) -> list[AnnotationRecording]:
    recordings: list[AnnotationRecording] = []
    for annotation in sorted(root.rglob("*.xml")):
        relative = annotation.relative_to(root)
        dataset_part = relative.parts[0] if relative.parts else "unknown"
        subset = relative.parts[1] if len(relative.parts) > 2 else dataset_part
        recordings.append(AnnotationRecording(
            dataset="idmt_smt_guitar",
            subset=f"{dataset_part}/{subset}",
            recording_id="_".join(relative.with_suffix("").parts),
            split="external",
            annotation_path=annotation,
            annotation_format="idmt_xml",
        ))
    return recordings


def discover_all(data_root: Path) -> list[AnnotationRecording]:
    idmt_root = data_root / "IDMT-SMT-Guitar" / "IDMT-SMT-GUITAR_V2"
    return [
        *discover_guitarset(data_root / "GuitarSet"),
        *discover_gaps(data_root / "GAPS"),
        *discover_guitar_techs(data_root / "Guitar-TECHS"),
        *discover_idmt(idmt_root),
    ]


def summarize(
    audits: Sequence[RecordingAudit],
    failures: Sequence[dict[str, str]],
) -> dict[str, object]:
    source_summaries: dict[str, dict[str, object]] = {}
    for dataset in sorted({audit.dataset for audit in audits}):
        rows = [audit for audit in audits if audit.dataset == dataset]
        active_duration = sum(row.active_duration_s for row in rows)
        poly_duration = sum(row.polyphonic_duration_s for row in rows)
        split_counts = Counter(row.split for row in rows)
        source_summaries[dataset] = {
            "recordings": len(rows),
            "recordings_with_polyphony": sum(
                row.maximum_polyphony > 1 for row in rows
            ),
            "notes": sum(row.note_count for row in rows),
            "notes_in_scope": sum(row.notes_in_scope for row in rows),
            "notes_below_scope": sum(row.notes_below_scope for row in rows),
            "notes_above_scope": sum(row.notes_above_scope for row in rows),
            "minimum_pitch": min(
                (row.minimum_pitch for row in rows if row.minimum_pitch is not None),
                default=None,
            ),
            "maximum_pitch": max(
                (row.maximum_pitch for row in rows if row.maximum_pitch is not None),
                default=None,
            ),
            "maximum_polyphony": max(
                (row.maximum_polyphony for row in rows), default=0
            ),
            "active_duration_hours": active_duration / 3600.0,
            "polyphonic_duration_hours": poly_duration / 3600.0,
            "polyphonic_duration_ratio": (
                poly_duration / active_duration if active_duration else 0.0
            ),
            "split_recordings": dict(sorted(split_counts.items())),
        }
    return {
        "schema_version": 1,
        "midi_scope": [DEFAULT_MIDI_MIN, DEFAULT_MIDI_MAX],
        "sources": source_summaries,
        "totals": {
            "recordings": len(audits),
            "failures": len(failures),
            "notes": sum(row.note_count for row in audits),
            "recordings_with_polyphony": sum(
                row.maximum_polyphony > 1 for row in audits
            ),
        },
        "failures": list(failures),
        "recordings": [asdict(row) for row in audits],
    }


def run_audit(data_root: Path) -> dict[str, object]:
    audits: list[RecordingAudit] = []
    failures: list[dict[str, str]] = []
    for recording in discover_all(data_root):
        try:
            notes = _parse(recording)
            audits.append(audit_notes(recording, notes))
        except Exception as error:  # Keep the complete audit actionable.
            failures.append({
                "dataset": recording.dataset,
                "recording_id": recording.recording_id,
                "annotation_path": str(recording.annotation_path),
                "error": f"{type(error).__name__}: {error}",
            })
    return summarize(audits, failures)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/polyphonic/source_audit.json"),
    )
    args = parser.parse_args()
    report = run_audit(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({
        "output": str(args.output),
        "sources": report["sources"],
        "totals": report["totals"],
        "failures": report["failures"][:10],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
