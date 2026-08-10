"""H11 one-shot orchestration for the future H7 discovery execution.

This module is deliberately free of TensorFlow and project asset readers.  It
seals the execution state machine and the exact ordering around injected
scientific adapters, so its tests cannot accidentally open an H8 asset.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping, Protocol, Sequence

from .provisional_resolution_age1 import (
    Age1ScientificRow,
    Age1SignalRecord,
    Age1TargetRecord,
    join_age1_signals_and_targets,
)
from .provisional_resolution_age1_metrics import (
    GroupedAge1EvaluationRow,
    H7SyntheticMetricReport,
)


H11_STATUS = "provisional_resolution_age1_persistence_h11_execution_contract_sealed"
EXECUTION_INVALID = "age1_signal_execution_invalid"
EXPECTED_RECORDINGS = 101
EXPECTED_GROUPS = 31


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def require_raw_sha256s(
    paths: Mapping[str, Path], expected: Mapping[str, str]
) -> None:
    """Verify every sealed byte input before a caller may load a model."""
    if set(paths) != set(expected):
        raise RuntimeError("H11 sealed input names do not reconcile.")
    for name in sorted(paths):
        if sha256_file(Path(paths[name]).resolve(strict=True)) != expected[name]:
            raise RuntimeError(f"H11 sealed input SHA-256 mismatch: {name}")


@dataclass(frozen=True)
class H11Recording:
    recording_key: str
    corpus_category: str
    leakage_group_key: str
    partition: str
    audio_size_bytes: int
    audio_sha256: str
    labels_size_bytes: int
    labels_sha256: str
    source_manifest_sha256: str
    source_partition_plan_sha256: str
    audio_member_identity: str = ""

    def __post_init__(self) -> None:
        for name in ("recording_key", "corpus_category", "leakage_group_key"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{name} must be a canonical non-empty string.")
        if self.partition != "dev":
            raise ValueError("H11 accepts only the sealed Policy-A dev partition.")
        for name in ("audio_size_bytes", "labels_size_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive JSON-native integer.")
        for name in (
            "audio_sha256", "labels_sha256", "source_manifest_sha256",
            "source_partition_plan_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be a lowercase SHA-256.")


@dataclass(frozen=True)
class H11DecodedRecording:
    emitted_events: tuple[Any, ...]
    signals: tuple[Age1SignalRecord, ...]
    pending_age1: int


class H11ScientificAdapter(Protocol):
    def verify_provenance(self, recording: H11Recording) -> None: ...
    def open_recording(self, recording: H11Recording) -> AbstractContextManager[Any]: ...
    def infer_once(self, opened: Any) -> Any: ...
    def decode_once(
        self, opened: Any, predictions: Any, recording: H11Recording
    ) -> H11DecodedRecording: ...
    def extract_targets(
        self, opened: Any, emitted_events: Sequence[Any]
    ) -> Sequence[Age1TargetRecord]: ...


@dataclass(frozen=True)
class H11RunSummary:
    processed_recordings: int
    leakage_groups: int
    grouped_rows: tuple[GroupedAge1EvaluationRow, ...]
    per_recording_attrition: tuple[dict[str, object], ...]


def require_h11_cohort(
    recordings: Sequence[H11Recording],
    *,
    forbidden_groups: Sequence[str],
    expected_manifest_sha256: str,
    expected_plan_sha256: str,
) -> tuple[H11Recording, ...]:
    checked = tuple(recordings)
    if len(checked) != EXPECTED_RECORDINGS:
        raise RuntimeError(f"{EXECUTION_INVALID}: expected exactly 101 recordings")
    if len({item.recording_key for item in checked}) != len(checked):
        raise RuntimeError(f"{EXECUTION_INVALID}: duplicate recording identity")
    groups = {item.leakage_group_key for item in checked}
    if len(groups) != EXPECTED_GROUPS:
        raise RuntimeError(f"{EXECUTION_INVALID}: expected exactly 31 leakage groups")
    if groups.intersection(forbidden_groups):
        raise RuntimeError(f"{EXECUTION_INVALID}: forbidden cohort group present")
    for item in checked:
        if item.source_manifest_sha256 != expected_manifest_sha256:
            raise RuntimeError(f"{EXECUTION_INVALID}: manifest provenance mismatch")
        if item.source_partition_plan_sha256 != expected_plan_sha256:
            raise RuntimeError(f"{EXECUTION_INVALID}: partition-plan provenance mismatch")
    return tuple(sorted(checked, key=lambda item: item.recording_key))


def process_h11_recording(
    recording: H11Recording,
    adapter: H11ScientificAdapter,
    *,
    mark_consumed: Callable[[H11Recording], None],
) -> tuple[tuple[GroupedAge1EvaluationRow, ...], dict[str, object]]:
    """Execute one frozen-order recording pipeline with one inference call."""
    adapter.verify_provenance(recording)
    # Conservatively cross the irrevocable consumption boundary before the
    # adapter can open or parse any scientific asset.
    mark_consumed(recording)
    with adapter.open_recording(recording) as opened:
        predictions = adapter.infer_once(opened)
        decoded = adapter.decode_once(opened, predictions, recording)
        if not isinstance(decoded, H11DecodedRecording):
            raise RuntimeError(f"{EXECUTION_INVALID}: decoder result type mismatch")
        if decoded.pending_age1 != 0:
            raise RuntimeError(f"{EXECUTION_INVALID}: unresolved_age1_pending_at_end_of_recording")
        targets = tuple(adapter.extract_targets(opened, decoded.emitted_events))
    rows = join_age1_signals_and_targets(decoded.signals, targets)
    emitted_noteons = sum(getattr(event, "kind", None) == "note_on" for event in decoded.emitted_events)
    if emitted_noteons != len(decoded.signals) or len(targets) != len(decoded.signals):
        raise RuntimeError(f"{EXECUTION_INVALID}: emitted/signal/target identity reconciliation failed")
    grouped = tuple(
        GroupedAge1EvaluationRow(
            recording_key=recording.recording_key,
            corpus_category=recording.corpus_category,
            leakage_group_key=recording.leakage_group_key,
            scientific_row=row,
        )
        for row in rows
    )
    return grouped, {
        "recording_key": recording.recording_key,
        "emitted_noteons": emitted_noteons,
        "signals": len(decoded.signals),
        "targets": len(targets),
        "joined_rows": len(grouped),
        "pending_age1": 0,
    }


def orchestrate_h11_discovery(
    recordings: Sequence[H11Recording],
    adapter: H11ScientificAdapter,
    metric_callable: Callable[[Sequence[GroupedAge1EvaluationRow]], H7SyntheticMetricReport],
    *,
    forbidden_groups: Sequence[str],
    expected_manifest_sha256: str,
    expected_plan_sha256: str,
    mark_consumed: Callable[[H11Recording], None],
) -> tuple[H11RunSummary, H7SyntheticMetricReport]:
    cohort = require_h11_cohort(
        recordings,
        forbidden_groups=forbidden_groups,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_plan_sha256=expected_plan_sha256,
    )
    all_rows: list[GroupedAge1EvaluationRow] = []
    attrition: list[dict[str, object]] = []
    for recording in cohort:  # Deliberately no retry loop.
        rows, summary = process_h11_recording(
            recording, adapter, mark_consumed=mark_consumed
        )
        all_rows.extend(rows)
        attrition.append(summary)
    if len(attrition) != EXPECTED_RECORDINGS:
        raise RuntimeError(f"{EXECUTION_INVALID}: partial cohort before metrics")
    metric = metric_callable(tuple(all_rows))
    return H11RunSummary(
        processed_recordings=len(attrition),
        leakage_groups=len({item.leakage_group_key for item in cohort}),
        grouped_rows=tuple(all_rows),
        per_recording_attrition=tuple(attrition),
    ), metric


def claim_one_shot_authorization(
    marker_path: Path,
    *,
    expected_contract_sha256: str,
) -> Path:
    marker = Path(marker_path)
    if not marker.is_file():
        raise PermissionError("H11 real runner requires a separately created authorization marker.")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    if payload != {
        "contract_sha256": expected_contract_sha256,
        "purpose": "provisional_resolution_age1_h7_discovery_one_shot_authorization",
        "scientific_execution_authorized": True,
        "single_use": True,
    }:
        raise PermissionError("H11 authorization marker payload mismatch.")
    claimed = marker.with_suffix(marker.suffix + ".claimed")
    if claimed.exists():
        raise FileExistsError("H11 authorization was already claimed.")
    os.replace(marker, claimed)
    return claimed


def publish_h11_success_atomically(
    destination: Path,
    summary: H11RunSummary,
    metric: H7SyntheticMetricReport,
    provenance: Mapping[str, object],
) -> None:
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("H11 final destination already exists.")
    staging = destination.parent / f".{destination.name}.staging-{os.getpid()}"
    if staging.exists():
        raise FileExistsError("H11 staging destination already exists.")
    try:
        staging.mkdir(parents=False)
        rows_payload = [
            {
                "recording_key": row.recording_key,
                "corpus_category": row.corpus_category,
                "leakage_group_key": row.leakage_group_key,
                "scientific_row": row.scientific_row.__dict__,
            }
            for row in summary.grouped_rows
        ]
        (staging / "grouped_rows.json").write_bytes(canonical_json_bytes(rows_payload))
        (staging / "attrition.json").write_bytes(canonical_json_bytes(summary.per_recording_attrition))
        (staging / "h7_metric_report.json").write_bytes(metric.canonical_json_bytes())
        (staging / "execution_provenance.json").write_bytes(canonical_json_bytes(dict(provenance)))
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def run_h11_once(
    *,
    marker_path: Path,
    expected_contract_sha256: str,
    destination: Path,
    recordings: Sequence[H11Recording],
    adapter: H11ScientificAdapter,
    metric_callable: Callable[[Sequence[GroupedAge1EvaluationRow]], H7SyntheticMetricReport],
    forbidden_groups: Sequence[str],
    expected_manifest_sha256: str,
    expected_plan_sha256: str,
) -> tuple[H11RunSummary, H7SyntheticMetricReport]:
    """Claim one authorization, run once, and publish only complete success."""
    claimed = claim_one_shot_authorization(
        marker_path, expected_contract_sha256=expected_contract_sha256
    )
    consumed = False

    def mark_consumed(_recording: H11Recording) -> None:
        nonlocal consumed
        if not consumed:
            consumed = True
            claimed.with_suffix(claimed.suffix + ".state.json").write_bytes(
                canonical_json_bytes({
                    "h8_discovery_consumed": True,
                    "state": "claimed_running",
                })
            )

    try:
        summary, metric = orchestrate_h11_discovery(
            recordings,
            adapter,
            metric_callable,
            forbidden_groups=forbidden_groups,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_plan_sha256=expected_plan_sha256,
            mark_consumed=mark_consumed,
        )
        publish_h11_success_atomically(
            destination,
            summary,
            metric,
            {
                "contract_sha256": expected_contract_sha256,
                "h8_discovery_consumed": consumed,
                "processed_recordings": summary.processed_recordings,
                "state": "completed",
            },
        )
        return summary, metric
    except Exception as error:
        failure = Path(destination).with_suffix(Path(destination).suffix + ".failure.json")
        if failure.exists():
            raise RuntimeError("H11 failure provenance already exists.") from error
        failure.write_bytes(canonical_json_bytes({
            "contract_sha256": expected_contract_sha256,
            "error_type": type(error).__name__,
            "h8_discovery_consumed": consumed,
            "state": "failed",
        }))
        raise


__all__ = [
    "EXECUTION_INVALID", "EXPECTED_GROUPS", "EXPECTED_RECORDINGS", "H11DecodedRecording",
    "H11Recording", "H11RunSummary", "H11ScientificAdapter", "H11_STATUS",
    "canonical_json_bytes", "claim_one_shot_authorization", "orchestrate_h11_discovery",
    "process_h11_recording", "publish_h11_success_atomically", "require_h11_cohort",
    "require_raw_sha256s", "run_h11_once", "sha256_file",
]
