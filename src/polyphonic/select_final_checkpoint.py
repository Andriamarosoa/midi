"""Select one deployable checkpoint using validation note events only."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from src.polyphonic.causal_event_metrics import CausalMetricGate
from src.polyphonic.decoder import default_decoder_config
from src.polyphonic.evaluate_events import evaluate_events


def _selection_metric_scope(
    row: Mapping[str, object],
) -> tuple[str, Mapping[str, object], Mapping[str, object]]:
    dataset_metrics = row.get("dataset_metrics")
    if isinstance(dataset_metrics, Mapping):
        for scope in ("weighted", "macro"):
            summary = dataset_metrics.get(scope)
            if not isinstance(summary, Mapping):
                continue
            onset = summary.get("onset")
            onset_offset = summary.get("onset_offset")
            if isinstance(onset, Mapping) and isinstance(onset_offset, Mapping):
                return f"dataset_{scope}", onset, onset_offset
    onset = row["onset"]
    onset_offset = row["onset_offset"]
    if not isinstance(onset, Mapping) or not isinstance(onset_offset, Mapping):
        raise ValueError("Candidate note-event metrics are invalid.")
    return "global_micro", onset, onset_offset


def event_selection_metric_source(row: Mapping[str, object]) -> str:
    return _selection_metric_scope(row)[0]


def event_selection_key(row: dict[str, object]) -> tuple[float, ...]:
    _, onset, onset_offset = _selection_metric_scope(row)
    global_onset = row["onset"]
    if not isinstance(global_onset, Mapping):
        raise ValueError("Candidate onset metrics are invalid.")
    return (
        float(onset["f1"]),
        float(onset_offset["f1"]),
        float(onset["precision"]),
        float(onset["recall"]),
        -float(global_onset.get("onset_error_p95_absolute_ms", 0.0)),
    )


def _candidate_rows(ranking: dict[str, object]) -> list[dict[str, object]]:
    rows = ranking["checkpoints"]
    pareto = set(ranking["pareto_candidates"])
    if not isinstance(rows, list):
        raise ValueError("Invalid checkpoint ranking.")
    selected = [row for row in rows if str(row["checkpoint"]) in pareto]
    if not selected:
        raise ValueError("Checkpoint ranking contains no Pareto candidates.")
    return selected


def causal_gate_candidate_eligible(row: Mapping[str, object]) -> bool:
    """Return whether a validation candidate passed its configured causal gate."""
    causal = row.get("strictly_causal_noteon")
    if (
        not isinstance(causal, Mapping)
        or causal.get("available") is not True
    ):
        return False
    gate = causal.get("gate")
    return (
        isinstance(gate, Mapping)
        and gate.get("passed") is True
        and int(gate.get("configured_checks", 0)) > 0
    )


def limit_candidates_for_evaluation(
    candidates: list[dict[str, object]],
    maximum_candidates: int | None,
    *,
    causal_gate_enabled: bool,
) -> list[dict[str, object]]:
    """Apply the compute cap without weakening a causal promotion gate."""
    if maximum_candidates is not None and maximum_candidates < 1:
        raise ValueError("maximum_candidates must be positive.")
    if (
        causal_gate_enabled
        or maximum_candidates is None
        or len(candidates) <= maximum_candidates
    ):
        return candidates

    leaders: list[dict[str, object]] = []
    metrics = (
        ("frame_f1", True), ("onset_f1", True),
        ("harmonic_amplitude_mae", False),
        ("harmonic_offset_normalized_mae", False),
    )
    for metric, descending in metrics:
        row = sorted(
            candidates, key=lambda value: float(value[metric]),
            reverse=descending,
        )[0]
        if row not in leaders:
            leaders.append(row)
        if len(leaders) == maximum_candidates:
            return leaders
    for row in candidates:
        if row not in leaders:
            leaders.append(row)
        if len(leaders) == maximum_candidates:
            break
    return leaders


def select(
    run_dir: Path,
    maximum_recordings: int | None = None,
    maximum_candidates: int | None = None,
    causal_gate_path: Path | None = None,
) -> dict[str, object]:
    ranking_path = run_dir / "checkpoint_ranking.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    if ranking.get("split") != "validation" or ranking.get("locked_test_used") is not False:
        raise ValueError("Checkpoint ranking is not validation-only.")
    candidates = _candidate_rows(ranking)
    causal_gate = (
        CausalMetricGate(**json.loads(
            causal_gate_path.read_text(encoding="utf-8")
        ))
        if causal_gate_path is not None
        else None
    )
    if (
        causal_gate is not None
        and causal_gate.configured_check_count() == 0
    ):
        raise ValueError(
            "The causal promotion gate must configure at least one check."
        )
    candidates = limit_candidates_for_evaluation(
        candidates,
        maximum_candidates,
        causal_gate_enabled=causal_gate is not None,
    )

    evaluated: list[dict[str, object]] = []
    for candidate in candidates:
        checkpoint = Path(str(candidate["checkpoint"]))
        thresholds_path = Path(str(candidate["thresholds"]))
        thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
        decoder = default_decoder_config(
            float(thresholds["frame"]), float(thresholds["onset"])
        )
        decoder_path = thresholds_path.with_name(
            f"{checkpoint.stem}_decoder.json"
        )
        decoder_path.write_text(
            json.dumps(asdict(decoder), indent=2), encoding="utf-8"
        )
        report = evaluate_events(
            run_dir=run_dir,
            split="validation",
            maximum_recordings=maximum_recordings,
            checkpoint_path=checkpoint,
            thresholds_path=thresholds_path,
            decoder_config_path=decoder_path,
            causal_gate=causal_gate,
        )
        evaluated_row = {
            "checkpoint": str(checkpoint),
            "thresholds": str(thresholds_path),
            "decoder_config": str(decoder_path),
            "recordings": report["recordings"],
            "selection": report.get("selection"),
            "onset": report["onset"],
            "onset_offset": report["onset_offset"],
            "dataset_metrics": report.get("dataset_metrics"),
            "strictly_causal_noteon": report.get(
                "strictly_causal_noteon"
            ),
            "retriggers": report["retriggers"],
        }
        evaluated_row["selection_metric_source"] = (
            event_selection_metric_source(evaluated_row)
        )
        evaluated.append(evaluated_row)

    eligible = (
        [
            row for row in evaluated
            if causal_gate_candidate_eligible(row)
        ]
        if causal_gate is not None
        else evaluated
    )
    if causal_gate is not None and not eligible:
        raise RuntimeError(
            "No validation checkpoint passed the configured causal "
            "NoteOn promotion gate."
        )
    chosen = max(eligible, key=event_selection_key)
    selected_checkpoint = run_dir / "selected.keras"
    shutil.copy2(Path(str(chosen["checkpoint"])), selected_checkpoint)
    shutil.copy2(Path(str(chosen["thresholds"])), run_dir / "thresholds.json")
    shutil.copy2(
        Path(str(chosen["decoder_config"])), run_dir / "decoder_config.json"
    )
    selection = {
        "selected_on": (
            "validation_note_events_with_strictly_causal_noteon_gate"
            if causal_gate is not None
            else "validation_note_events"
        ),
        "selection_metric_source": chosen["selection_metric_source"],
        "locked_test_used": False,
        "maximum_recordings": maximum_recordings,
        "candidate_count": len(evaluated),
        "maximum_candidates_requested": maximum_candidates,
        "maximum_candidates_ignored_for_causal_gate": bool(
            causal_gate is not None and maximum_candidates is not None
        ),
        "causal_gate": (
            {
                "path": str(causal_gate_path),
                "sha256": hashlib.sha256(
                    causal_gate_path.read_bytes()
                ).hexdigest(),
                "configured_checks": (
                    causal_gate.configured_check_count()
                ),
            }
            if causal_gate_path is not None and causal_gate is not None
            else None
        ),
        "causal_gate_passed_candidates": (
            len(eligible) if causal_gate is not None else None
        ),
        "selection_order": [
            "dataset_weighted_onset_f1_or_macro_or_global",
            "same_scope_onset_offset_f1", "same_scope_onset_precision",
            "same_scope_onset_recall", "global_onset_error_p95_absolute_ms",
        ],
        "selected_checkpoint": str(selected_checkpoint),
        "source_checkpoint": chosen["checkpoint"],
        "thresholds": str(run_dir / "thresholds.json"),
        "decoder_config": str(run_dir / "decoder_config.json"),
        "selected_metrics": chosen,
        "candidates": evaluated,
    }
    (run_dir / "selection.json").write_text(
        json.dumps(selection, indent=2), encoding="utf-8"
    )
    return selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--maximum-recordings", type=int)
    parser.add_argument("--maximum-candidates", type=int)
    parser.add_argument("--causal-gate", type=Path)
    args = parser.parse_args()
    result = select(
        args.run_dir, args.maximum_recordings, args.maximum_candidates,
        args.causal_gate,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
