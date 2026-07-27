"""Select V6.3.2 on player 04 and evaluate once on locked player 05 solos."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from src.v5.external_data import discover_guitarset
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v6.continuous_onset_ablation import _variant_report
from src.v6.continuous_onset_v63_ablation import (
    DEFAULT_SOURCES,
    _load_waveform,
    aggregate_variant,
)
from src.v6.continuous_validate import frame_labels, stabilize_predictions
from src.v6.select_v63_decoder_threshold import quick_metrics
from src.v6.transition_gate import (
    FEATURE_NAMES,
    infer_v60_outputs,
    progressive_stream_features,
    stabilize_with_transition_gate,
)


VALIDATION_SOURCES = tuple(
    value.replace("gsmono_05_", "gsmono_04_") for value in DEFAULT_SOURCES
)


class CachedGate:
    """Cache exact causal feature vectors across the decoder threshold sweep."""

    def __init__(self, predict_function) -> None:
        self.predict_function = predict_function
        self.cache: dict[bytes, float] = {}

    def __call__(self, values: np.ndarray) -> np.ndarray:
        array = np.asarray(values, dtype=np.float32)
        if array.shape != (1, len(FEATURE_NAMES)):
            raise ValueError(f"Feature gate inattendue: {array.shape}")
        key = array.tobytes()
        if key not in self.cache:
            score = np.asarray(
                self.predict_function(array), dtype=np.float32
            ).reshape(-1)
            if score.size != 1:
                raise ValueError("Sortie gate inattendue.")
            self.cache[key] = float(score[0])
        return np.asarray([[self.cache[key]]], dtype=np.float32)


def prepare_source(
    v60_model,
    v60_inference,
    recording,
    sample_rate: int,
    hop_size: int,
    min_pitch: int,
    max_pitch: int,
    gain: float,
    active_threshold: float,
    batch_size: int,
) -> dict[str, object]:
    waveform, notes = _load_waveform(recording, sample_rate)
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    visible, stream = progressive_stream_features(
        waveform, sample_rate, hop_size, end_samples
    )
    predictions, inference_s = infer_v60_outputs(
        v60_model, waveform, end_samples, visible, gain, batch_size,
        inference_function=v60_inference,
    )
    predicted_active = predictions["active"] >= active_threshold
    predicted_pitch = (
        np.argmax(predictions["pitch"], axis=1).astype(np.int32) + min_pitch
    )
    baseline = stabilize_predictions(
        predicted_active,
        predicted_pitch,
        np.asarray(stream["detected_onset"]) >= 0.5,
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
        "active_probability": predictions["active"],
        "pitch_probability": predictions["pitch"],
        "harmonic_amplitude": predictions["harmonic_amplitude"],
        "stream_features": stream,
        "baseline_active": baseline[0],
        "baseline_pitch": baseline[1],
        "baseline_retrigger": baseline[2],
        "sample_rate": sample_rate,
        "hop_size": hop_size,
        "min_pitch": min_pitch,
        "max_pitch": max_pitch,
        "active_threshold": active_threshold,
        "v6_0_inference_s": inference_s,
    }


def decode_source(
    item: dict[str, object], gate: CachedGate, threshold: float
):
    return stabilize_with_transition_gate(
        item["active_probability"],
        item["pitch_probability"],
        item["harmonic_amplitude"],
        item["stream_features"],
        float(item["active_threshold"]),
        threshold,
        gate,
        int(item["min_pitch"]),
        int(item["max_pitch"]),
        int(item["hop_size"]) / int(item["sample_rate"]) * 1000.0,
        required_frames=2,
    )


def source_metrics(
    item: dict[str, object], active, pitch, retrigger, decisions
) -> dict[str, object]:
    result = quick_metrics(item, active, pitch, retrigger)
    evaluable = np.asarray(item["evaluable"], dtype=bool)
    target_active = np.asarray(item["target_pitch"]) >= 0
    active = np.asarray(active, dtype=bool)
    result.update({
        "active_tp": int(np.sum(evaluable & target_active & active)),
        "active_fp": int(np.sum(evaluable & ~target_active & active)),
        "active_fn": int(np.sum(evaluable & target_active & ~active)),
        "transition_decisions": len(decisions),
        "transition_vetoes": int(sum(not value.allowed for value in decisions)),
        "harmonic_evidence_vetoes": int(sum(
            not value.allowed
            and (
                value.feature[FEATURE_NAMES.index("harmonic_match_strength")] > 0.0
                or value.feature[FEATURE_NAMES.index("strongest_harmonic_match")] > 0.5
            )
            for value in decisions
        )),
    })
    return result


def aggregate_metrics(values: list[dict[str, object]]) -> dict[str, object]:
    duration = sum(float(value["duration_s"]) for value in values)
    evaluable = sum(int(value["evaluable_frames"]) for value in values)
    positives = sum(int(value["positive_frames"]) for value in values)
    tp = sum(int(value["active_tp"]) for value in values)
    fp = sum(int(value["active_fp"]) for value in values)
    fn = sum(int(value["active_fn"]) for value in values)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "duration_s": duration,
        "active_f1": 2.0 * precision * recall / max(precision + recall, 1e-12),
        "joint_frame_accuracy": sum(
            int(value["joint_correct"]) for value in values
        ) / max(evaluable, 1),
        "gated_correct_pitch_recall": sum(
            int(value["gated_correct"]) for value in values
        ) / max(positives, 1),
        "ghost_events_per_minute": sum(
            int(value["ghosts"]) for value in values
        ) / max(duration / 60.0, 1e-12),
        "events": sum(int(value["events"]) for value in values),
        "missing": sum(int(value["missing"]) for value in values),
        "covered_majority": sum(
            int(value["covered_majority"]) for value in values
        ),
        "reference_notes": sum(
            int(value["reference_notes"]) for value in values
        ),
        "unsupported_retriggers": sum(
            int(value["unsupported_retriggers"]) for value in values
        ),
        "controlled_retriggers": sum(
            int(value["controlled_retriggers"]) for value in values
        ),
        "transition_decisions": sum(
            int(value["transition_decisions"]) for value in values
        ),
        "transition_vetoes": sum(
            int(value["transition_vetoes"]) for value in values
        ),
        "harmonic_evidence_vetoes": sum(
            int(value["harmonic_evidence_vetoes"]) for value in values
        ),
    }


def metrics_at_threshold(
    prepared: list[dict[str, object]], gate: CachedGate, threshold: float | None
) -> dict[str, object]:
    values = []
    for item in prepared:
        if threshold is None:
            active = item["baseline_active"]
            pitch = item["baseline_pitch"]
            retrigger = item["baseline_retrigger"]
            decisions = []
        else:
            active, pitch, retrigger, _, decisions = decode_source(
                item, gate, threshold
            )
        values.append(source_metrics(item, active, pitch, retrigger, decisions))
    return aggregate_metrics(values)


def zero_threshold_invariant(
    prepared: list[dict[str, object]], gate: CachedGate
) -> dict[str, object]:
    per_source: dict[str, bool] = {}
    for item in prepared:
        active, pitch, retrigger, veto, _ = decode_source(item, gate, 0.0)
        per_source[str(item["source_id"])] = bool(
            np.array_equal(active, item["baseline_active"])
            and np.array_equal(pitch, item["baseline_pitch"])
            and np.array_equal(retrigger, item["baseline_retrigger"])
            and not np.any(veto)
        )
    return {"passed": all(per_source.values()), "sources": per_source}


def select_threshold(
    prepared: list[dict[str, object]],
    gate: CachedGate,
    classifier_threshold: float,
) -> tuple[float, dict[str, object]]:
    baseline = metrics_at_threshold(prepared, gate, None)
    baseline_decisions = [
        decision
        for item in prepared
        for decision in decode_source(item, gate, 0.0)[4]
    ]
    scores = np.asarray([value.score for value in baseline_decisions], dtype=np.float32)
    candidates = np.unique(np.r_[
        0.0,
        classifier_threshold,
        np.quantile(scores, np.linspace(0.0, 1.0, 201)) if len(scores) else 1.0,
        1.0,
    ])
    rows: list[dict[str, object]] = []
    for threshold in candidates:
        metrics = metrics_at_threshold(prepared, gate, float(threshold))
        feasible = bool(
            metrics["missing"] <= baseline["missing"]
            and metrics["joint_frame_accuracy"] >= baseline["joint_frame_accuracy"]
            and metrics["active_f1"] >= baseline["active_f1"]
            and metrics["unsupported_retriggers"] <= baseline["unsupported_retriggers"]
        )
        rows.append({"threshold": float(threshold), "feasible": feasible, **metrics})
    feasible = [value for value in rows if value["feasible"]]
    selected = min(feasible, key=lambda value: (
        value["ghost_events_per_minute"],
        value["missing"],
        -value["joint_frame_accuracy"],
        -value["active_f1"],
        -value["threshold"],
    ))
    return float(selected["threshold"]), {
        "selection_basis": "four_player_04_solos_only",
        "selection_rule": (
            "minimize_ghosts_subject_to_missing_joint_active_f1_and_"
            "unsupported_retriggers_not_worse_than_frozen_v6_0"
        ),
        "baseline": baseline,
        "selected": selected,
        "candidate_count": len(rows),
        "feasible_candidate_count": len(feasible),
        "candidates": rows,
    }


def write_decisions(path: Path, item: dict[str, object], decisions) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_times = np.asarray(item["frame_times"])
    rows = []
    for value in decisions:
        feature = value.feature
        rows.append({
            "frame_index": value.frame_index,
            "time_s": float(frame_times[value.frame_index]),
            "current_pitch": value.current_pitch,
            "candidate_pitch": value.candidate_pitch,
            "interval": value.candidate_pitch - value.current_pitch,
            "score": value.score,
            "allowed": int(value.allowed),
            **{name: float(feature[index]) for index, name in enumerate(FEATURE_NAMES)},
        })
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def full_reports(
    prepared: list[dict[str, object]],
    gate: CachedGate,
    threshold: float,
    output_root: Path,
    variant_name: str,
) -> list[dict[str, object]]:
    reports = []
    for item in prepared:
        active, pitch, retrigger, veto, decisions = decode_source(
            item, gate, threshold
        )
        source_root = output_root / str(item["source_id"])
        source_root.mkdir(parents=True, exist_ok=True)
        variants = {
            "v6_0_baseline": _variant_report(
                "v6_0_baseline", source_root,
                item["baseline_active"], item["baseline_pitch"],
                item["baseline_retrigger"], np.zeros(len(active), dtype=bool),
                item["active_sets"], item["evaluable"], item["target_pitch"],
                item["notes"], item["frame_times"], item["waveform"],
                item["end_samples"], int(item["sample_rate"]),
                int(item["min_pitch"]), int(item["max_pitch"]),
            ),
            variant_name: _variant_report(
                variant_name, source_root,
                active, pitch, retrigger, veto,
                item["active_sets"], item["evaluable"], item["target_pitch"],
                item["notes"], item["frame_times"], item["waveform"],
                item["end_samples"], int(item["sample_rate"]),
                int(item["min_pitch"]), int(item["max_pitch"]),
            ),
        }
        write_decisions(source_root / "transition_decisions.csv", item, decisions)
        report = {
            "source_id": item["source_id"],
            "duration_s": len(item["waveform"]) / int(item["sample_rate"]),
            "transition_threshold_locked_from_player_04": threshold,
            "transition_decisions": len(decisions),
            "transition_vetoes": int(sum(not value.allowed for value in decisions)),
            "variants": variants,
        }
        (source_root / "summary.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        reports.append(report)
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument("--gate-run", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    import tensorflow as tf

    v60_run = args.v60_run.resolve()
    gate_run = args.gate_run.resolve()
    variant_name = (
        "v6_3_3_transition_utility_gate"
        if "v6_3_3" in gate_run.name
        else "v6_3_2_transition_gate"
    )
    reference_name = "v6_3_3" if "v6_3_3" in gate_run.name else "v6_3_2"
    v60_selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    gate_selection = json.loads(
        (gate_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    dataset = json.loads(
        (v60_run / "config.json").read_text(encoding="utf-8")
    )["dataset"]
    sample_rate = int(dataset["sample_rate"])
    hop_size = int(dataset["hop_size"])
    min_pitch = int(dataset["min_pitch"])
    max_pitch = int(dataset["max_pitch"])
    gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    active_threshold = float(v60_selection["active_threshold"])
    classifier_threshold = float(gate_selection["transition_threshold"])
    v60_model = tf.keras.models.load_model(
        v60_run / v60_selection["selected_checkpoint"], compile=False
    )
    gate_model = tf.keras.models.load_model(
        gate_run / gate_selection["selected_checkpoint"], compile=False
    )

    @tf.function(
        input_signature=[
            tf.TensorSpec((None, 4096, 1), tf.float32),
            tf.TensorSpec((None, 4096), tf.float32),
        ],
        autograph=False,
    )
    def v60_inference(audio, mask):
        return v60_model({"audio": audio, "time_mask": mask}, training=False)

    @tf.function(
        input_signature=[tf.TensorSpec((None, len(FEATURE_NAMES)), tf.float32)],
        autograph=False,
    )
    def gate_inference(features):
        return gate_model(features, training=False)

    gate = CachedGate(gate_inference)
    recordings = {
        value.source_id: value for value in discover_guitarset("data/GuitarSet")
    }
    required_sources = set(VALIDATION_SOURCES) | set(DEFAULT_SOURCES)
    unknown = required_sources - set(recordings)
    if unknown:
        raise ValueError(f"Sources GuitarSet inconnues: {sorted(unknown)}")
    if any(recordings[value].player_id != "04" for value in VALIDATION_SOURCES):
        raise ValueError("La selection doit rester sur le joueur 04.")
    if any(recordings[value].player_id != "05" for value in DEFAULT_SOURCES):
        raise ValueError("Le test verrouille doit rester sur le joueur 05.")

    validation = [
        prepare_source(
            v60_model, v60_inference, recordings[source], sample_rate, hop_size,
            min_pitch, max_pitch, gain, active_threshold, args.batch_size,
        )
        for source in VALIDATION_SOURCES
    ]
    validation_invariant = zero_threshold_invariant(validation, gate)
    if not validation_invariant["passed"]:
        raise RuntimeError("Le gate a modifie V6.0 au seuil zero en validation.")
    threshold, selection = select_threshold(
        validation, gate, classifier_threshold
    )
    selection_document = {
        "decoder_transition_threshold": threshold,
        "classifier_f1_threshold": classifier_threshold,
        "validation_sources": list(VALIDATION_SOURCES),
        "zero_threshold_inverse_validation": validation_invariant,
        **selection,
    }
    (gate_run / "decoder_threshold_selection.json").write_text(
        json.dumps(selection_document, indent=2), encoding="utf-8"
    )

    test = [
        prepare_source(
            v60_model, v60_inference, recordings[source], sample_rate, hop_size,
            min_pitch, max_pitch, gain, active_threshold, args.batch_size,
        )
        for source in DEFAULT_SOURCES
    ]
    test_invariant = zero_threshold_invariant(test, gate)
    if not test_invariant["passed"]:
        raise RuntimeError("Le gate a modifie V6.0 au seuil zero sur le test.")
    output_root = gate_run / "continuous_transition_gate_ablation"
    reports = full_reports(test, gate, threshold, output_root, variant_name)
    variants = {
        name: aggregate_variant(reports, name)
        for name in ("v6_0_baseline", variant_name)
    }
    baseline = variants["v6_0_baseline"]
    candidate = variants[variant_name]
    acceptance = {
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
        "active_f1_not_worse": candidate["active_f1"] >= baseline["active_f1"],
        "unsupported_retriggers_not_worse": (
            candidate["events"]["unsupported_same_midi_retriggers"]
            <= baseline["events"]["unsupported_same_midi_retriggers"]
        ),
    }
    strict_ghost_improvement = bool(
        candidate["events"]["ghost_events_per_minute"]
        < baseline["events"]["ghost_events_per_minute"]
    )
    accepted = bool(all(acceptance.values()) and strict_ghost_improvement)
    aggregate = {
        "sources": list(DEFAULT_SOURCES),
        "threshold_locked_from_player_04": threshold,
        "classifier_f1_threshold_not_used_for_decoder_selection": classifier_threshold,
        "validation_selection": {
            key: value for key, value in selection.items() if key != "candidates"
        },
        "zero_threshold_inverse_validation": {
            "validation": validation_invariant,
            "test": test_invariant,
        },
        "latency_contract": {
            "algorithmic_lookahead_ms": 0.0,
            "additional_stability_frames": 0,
            "gate_called_only_at_stable_active_to_active_candidates": True,
            "measured_gate_latency": json.loads(
                (gate_run / "latency.json").read_text(encoding="utf-8")
            ),
        },
        "variants": variants,
        "acceptance": acceptance,
        "strict_ghost_improvement": strict_ghost_improvement,
        "accepted_for_live_integration": accepted,
        "reference_after_evaluation": reference_name if accepted else "v6_0",
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    (gate_run / "deployment_decision.json").write_text(
        json.dumps({
            "accepted_for_live_integration": accepted,
            "reference": reference_name if accepted else "v6_0",
            "reason": (
                "all_locked_test_constraints_pass_and_ghosts_strictly_improve"
                if accepted else
                "locked_test_does_not_show_a_safe_strict_ghost_improvement"
            ),
            "aggregate_report": str(output_root / "aggregate.json"),
        }, indent=2), encoding="utf-8"
    )
    print(json.dumps(aggregate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
