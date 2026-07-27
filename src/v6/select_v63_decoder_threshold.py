"""Select the V6.3 decoder threshold on player 04, then lock it for player 05."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.v5.external_data import discover_guitarset
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v6.continuous_onset_ablation import (
    _reference_coverage,
    stabilize_with_model_onset,
)
from src.v6.continuous_onset_v63_ablation import (
    DEFAULT_SOURCES,
    _infer_onset,
    _load_waveform,
    aggregate_variant,
    evaluate_source,
)
from src.v6.continuous_validate import (
    _classified_event_rows,
    _infer,
    decode_events,
    frame_labels,
    progressive_windows,
    stabilize_predictions,
)


VALIDATION_SOURCES = tuple(value.replace("gsmono_05_", "gsmono_04_") for value in DEFAULT_SOURCES)


def prepare_source(
    v60_model,
    onset_model,
    recording,
    sample_rate: int,
    hop_size: int,
    min_pitch: int,
    max_pitch: int,
    v60_gain: float,
    active_threshold: float,
    onset_gain: float,
    batch_size: int,
) -> dict[str, object]:
    waveform, notes = _load_waveform(recording, sample_rate)
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    visible, detected_onset = progressive_windows(
        waveform, sample_rate, hop_size, end_samples
    )
    active_probability, _, pitch_class, _ = _infer(
        v60_model, waveform, end_samples, visible, v60_gain, batch_size
    )
    onset_probability, _ = _infer_onset(
        onset_model, waveform, end_samples, onset_gain, batch_size
    )
    predicted_active = active_probability >= active_threshold
    predicted_pitch = pitch_class.astype(np.int32) + min_pitch
    baseline_active, baseline_pitch, baseline_retrigger = stabilize_predictions(
        predicted_active,
        predicted_pitch,
        detected_onset,
        hop_size / sample_rate * 1000.0,
        required_frames=2,
    )
    return {
        "source_id": recording.source_id,
        "waveform": waveform,
        "notes": notes,
        "end_samples": end_samples,
        "frame_times": frame_times,
        "active_sets": active_sets,
        "evaluable": evaluable,
        "target_pitch": target_pitch,
        "predicted_active": predicted_active,
        "predicted_pitch": predicted_pitch,
        "onset_probability": onset_probability,
        "detected_onset": detected_onset,
        "baseline_active": baseline_active,
        "baseline_pitch": baseline_pitch,
        "baseline_retrigger": baseline_retrigger,
        "sample_rate": sample_rate,
        "hop_size": hop_size,
        "min_pitch": min_pitch,
        "max_pitch": max_pitch,
    }


def quick_metrics(
    item: dict[str, object],
    active: np.ndarray,
    pitch: np.ndarray,
    retrigger: np.ndarray,
) -> dict[str, object]:
    waveform = item["waveform"]
    notes = item["notes"]
    end_samples = item["end_samples"]
    frame_times = item["frame_times"]
    active_sets = item["active_sets"]
    evaluable = item["evaluable"]
    target_pitch = item["target_pitch"]
    sample_rate = int(item["sample_rate"])
    min_pitch = int(item["min_pitch"])
    max_pitch = int(item["max_pitch"])
    target_active = target_pitch >= 0
    positive = evaluable & target_active
    pitch_correct = pitch == target_pitch
    joint = (
        (evaluable & ~target_active & ~active)
        | (positive & active & pitch_correct)
    )
    events = decode_events(
        active,
        pitch,
        frame_times,
        len(waveform) / sample_rate,
        retrigger=retrigger,
    )
    _, classes = _classified_event_rows(
        events,
        active_sets,
        waveform,
        end_samples,
        sample_rate,
        min_pitch,
        max_pitch,
    )
    reference = _reference_coverage(
        notes,
        frame_times,
        evaluable,
        target_pitch,
        active,
        pitch,
        min_pitch,
        max_pitch,
    )
    reference_starts = np.asarray(
        [note.start_s for note in notes], dtype=np.float64
    )
    retrigger_indices = np.flatnonzero(retrigger)
    unsupported_retriggers = int(sum(
        not np.any(np.abs(reference_starts - frame_times[index]) <= 0.05)
        for index in retrigger_indices
    ))
    return {
        "duration_s": len(waveform) / sample_rate,
        "evaluable_frames": int(np.sum(evaluable)),
        "positive_frames": int(np.sum(positive)),
        "joint_correct": int(np.sum(joint)),
        "gated_correct": int(np.sum(positive & active & pitch_correct)),
        "events": len(events),
        "ghosts": int(classes["harmonic_suspect"] + classes["unsupported"]),
        "unsupported_retriggers": unsupported_retriggers,
        "controlled_retriggers": int(len(retrigger_indices)),
        "missing": int(reference["missing"]),
        "covered_majority": int(reference["covered_majority"]),
        "reference_notes": int(reference["evaluable"]),
    }


def aggregate_quick(values: list[dict[str, object]]) -> dict[str, object]:
    duration_s = sum(float(item["duration_s"]) for item in values)
    evaluable = sum(int(item["evaluable_frames"]) for item in values)
    positives = sum(int(item["positive_frames"]) for item in values)
    return {
        "duration_s": duration_s,
        "joint_frame_accuracy": sum(
            int(item["joint_correct"]) for item in values
        ) / max(evaluable, 1),
        "gated_correct_pitch_recall": sum(
            int(item["gated_correct"]) for item in values
        ) / max(positives, 1),
        "ghost_events_per_minute": sum(
            int(item["ghosts"]) for item in values
        ) / max(duration_s / 60.0, 1e-12),
        "events": sum(int(item["events"]) for item in values),
        "missing": sum(int(item["missing"]) for item in values),
        "covered_majority": sum(
            int(item["covered_majority"]) for item in values
        ),
        "reference_notes": sum(
            int(item["reference_notes"]) for item in values
        ),
        "unsupported_retriggers": sum(
            int(item["unsupported_retriggers"]) for item in values
        ),
        "controlled_retriggers": sum(
            int(item["controlled_retriggers"]) for item in values
        ),
    }


def metrics_at_threshold(
    prepared: list[dict[str, object]], threshold: float | None
) -> dict[str, object]:
    values: list[dict[str, object]] = []
    for item in prepared:
        if threshold is None:
            active = item["baseline_active"]
            pitch = item["baseline_pitch"]
            retrigger = item["baseline_retrigger"]
        else:
            active, pitch, retrigger, _ = stabilize_with_model_onset(
                item["predicted_active"],
                item["predicted_pitch"],
                item["onset_probability"],
                threshold,
                int(item["hop_size"]) / int(item["sample_rate"]) * 1000.0,
                retrigger_onset=item["detected_onset"],
                required_frames=2,
            )
        values.append(quick_metrics(item, active, pitch, retrigger))
    return aggregate_quick(values)


def select_threshold(
    prepared: list[dict[str, object]],
    original_threshold: float,
) -> tuple[float, dict[str, object]]:
    probabilities = np.concatenate([
        item["onset_probability"] for item in prepared
    ])
    candidates = np.unique(np.r_[
        np.quantile(probabilities, np.linspace(0.0, 99.9, 301) / 100.0),
        original_threshold,
    ])
    baseline = metrics_at_threshold(prepared, None)
    rows: list[dict[str, object]] = []
    for threshold in candidates:
        metrics = metrics_at_threshold(prepared, float(threshold))
        feasible = (
            metrics["missing"] <= baseline["missing"]
            and metrics["joint_frame_accuracy"] >= baseline["joint_frame_accuracy"]
            and metrics["unsupported_retriggers"] <= baseline["unsupported_retriggers"]
        )
        rows.append({
            "threshold": float(threshold),
            "feasible": bool(feasible),
            **metrics,
        })
    feasible_rows = [row for row in rows if row["feasible"]]
    if feasible_rows:
        selected = min(
            feasible_rows,
            key=lambda row: (
                row["ghost_events_per_minute"],
                row["unsupported_retriggers"],
                -row["joint_frame_accuracy"],
                -row["threshold"],
            ),
        )
        rule = (
            "minimize_validation_ghosts_subject_to_missing_joint_and_unsupported_"
            "retriggers_not_worse_than_v6_0"
        )
    else:
        selected = min(
            rows,
            key=lambda row: (
                max(0, row["missing"] - baseline["missing"]),
                max(0.0, baseline["joint_frame_accuracy"] - row["joint_frame_accuracy"]),
                max(0, row["unsupported_retriggers"] - baseline["unsupported_retriggers"]),
                row["ghost_events_per_minute"],
            ),
        )
        rule = "least_validation_constraint_violation_no_feasible_threshold"
    return float(selected["threshold"]), {
        "selection_basis": "player_04_four_solos_only",
        "selection_rule": rule,
        "baseline": baseline,
        "selected": selected,
        "candidate_count": len(rows),
        "feasible_candidate_count": len(feasible_rows),
        "candidates": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument("--onset-run", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    import tensorflow as tf

    v60_run = args.v60_run.resolve()
    onset_run = args.onset_run.resolve()
    v60_selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    onset_selection_path = onset_run / "selected_checkpoint_corrected.json"
    if not onset_selection_path.exists():
        onset_selection_path = onset_run / "selected_checkpoint.json"
    onset_selection = json.loads(
        onset_selection_path.read_text(encoding="utf-8")
    )
    dataset = json.loads(
        (v60_run / "config.json").read_text(encoding="utf-8")
    )["dataset"]
    sample_rate = int(dataset["sample_rate"])
    hop_size = int(dataset["hop_size"])
    min_pitch = int(dataset["min_pitch"])
    max_pitch = int(dataset["max_pitch"])
    v60_gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    onset_gain = float(json.loads(
        (onset_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    active_threshold = float(v60_selection["active_threshold"])
    original_threshold = float(onset_selection["onset_threshold"])
    v60_model = tf.keras.models.load_model(
        v60_run / v60_selection["selected_checkpoint"], compile=False
    )
    onset_model = tf.keras.models.load_model(
        onset_run / onset_selection["selected_checkpoint"], compile=False
    )
    recordings = {
        item.source_id: item for item in discover_guitarset("data/GuitarSet")
    }
    prepared = [
        prepare_source(
            v60_model, onset_model, recordings[source], sample_rate, hop_size,
            min_pitch, max_pitch, v60_gain, active_threshold, onset_gain,
            args.batch_size,
        )
        for source in VALIDATION_SOURCES
    ]
    threshold, selection = select_threshold(prepared, original_threshold)
    (onset_run / "decoder_threshold_selection_external_retrigger.json").write_text(
        json.dumps({
            "decoder_onset_threshold": threshold,
            "model_event_threshold": original_threshold,
            "validation_sources": list(VALIDATION_SOURCES),
            **selection,
        }, indent=2), encoding="utf-8"
    )

    output_root = onset_run / "continuous_decoder_ablation_v63_external_retrigger"
    test_reports = [
        evaluate_source(
            v60_model, onset_model, recordings[source], output_root / source,
            sample_rate, hop_size, min_pitch, max_pitch, v60_gain,
            active_threshold, onset_gain, threshold, args.batch_size,
        )
        for source in DEFAULT_SOURCES
    ]
    test = {
        "sources": list(DEFAULT_SOURCES),
        "threshold_locked_from_player_04": threshold,
        "validation_selection": {
            key: value for key, value in selection.items() if key != "candidates"
        },
        "variants": {
            name: aggregate_variant(test_reports, name)
            for name in ("v6_0_baseline", "v6_3_onset_gate")
        },
    }
    baseline = test["variants"]["v6_0_baseline"]
    candidate = test["variants"]["v6_3_onset_gate"]
    test["acceptance"] = {
        "ghosts_not_worse": (
            candidate["events"]["ghost_events_per_minute"]
            <= baseline["events"]["ghost_events_per_minute"]
        ),
        "missing_not_worse": (
            candidate["reference_notes"]["missing"]
            <= baseline["reference_notes"]["missing"]
        ),
        "joint_not_worse": (
            candidate["joint_frame_accuracy"] >= baseline["joint_frame_accuracy"]
        ),
        "unsupported_retriggers_not_worse": (
            candidate["events"]["unsupported_same_midi_retriggers"]
            <= baseline["events"]["unsupported_same_midi_retriggers"]
        ),
    }
    (output_root / "aggregate.json").write_text(
        json.dumps(test, indent=2), encoding="utf-8"
    )
    print(json.dumps(test, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
