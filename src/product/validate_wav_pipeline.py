"""End-to-end validation of the shipped TFLite audio-to-MIDI pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.product.engine import GuitarMidiEngine
from src.product.tflite_runtime import (
    ProductBundle,
    TFLitePitchModel,
    TFLiteTransitionGate,
)
from src.product.transcribe import transcribe_waveform
from src.v5.external_data import discover_guitarset
from src.v6.continuous_onset_v63_ablation import DEFAULT_SOURCES, _load_waveform
from src.v6.continuous_validate import frame_labels
from src.v6.select_transition_gate_decoder import (
    VALIDATION_SOURCES,
    aggregate_metrics,
    source_metrics,
)


def build_item(recording, waveform, notes, metadata) -> dict[str, object]:
    sample_rate = int(metadata["sample_rate"])
    hop_size = int(metadata["hop_samples"])
    min_pitch = int(metadata["min_pitch"])
    max_pitch = int(metadata["max_pitch"])
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    return {
        "source_id": recording.source_id,
        "waveform": waveform[:len(end_samples) * hop_size],
        "notes": notes,
        "end_samples": end_samples,
        "frame_times": frame_times,
        "active_sets": active_sets,
        "evaluable": evaluable,
        "target_pitch": target_pitch,
        "sample_rate": sample_rate,
        "hop_size": hop_size,
        "min_pitch": min_pitch,
        "max_pitch": max_pitch,
    }


def compare(candidate: dict, reference: dict) -> dict[str, bool]:
    return {
        "missing_not_worse": candidate["missing"] <= reference["missing"],
        "ghosts_not_worse": (
            candidate["ghost_events_per_minute"]
            <= reference["ghost_events_per_minute"]
        ),
        "unsupported_retriggers_not_worse": (
            candidate["unsupported_retriggers"]
            <= reference["unsupported_retriggers"]
        ),
        "joint_within_tolerance": (
            candidate["joint_frame_accuracy"]
            >= reference["joint_frame_accuracy"] - 0.002
        ),
        "active_f1_within_tolerance": (
            candidate["active_f1"] >= reference["active_f1"] - 0.002
        ),
    }


def safe_profile_acceptance(candidate: dict, reference: dict) -> dict[str, bool]:
    """Acceptance for the explicitly low-ghost product profile."""
    return {
        "ghosts_reduced_at_least_25_percent": (
            candidate["ghost_events_per_minute"]
            <= reference["ghost_events_per_minute"] * 0.75
        ),
        "missing_increase_bounded_to_ten_notes": (
            candidate["missing"] <= reference["missing"] + 10
        ),
        "unsupported_retriggers_not_worse": (
            candidate["unsupported_retriggers"]
            <= reference["unsupported_retriggers"]
        ),
        "joint_accuracy_floor": candidate["joint_frame_accuracy"] >= 0.75,
        "active_f1_floor": candidate["active_f1"] >= 0.80,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--guitarset", type=Path, default=Path("data/GuitarSet"))
    parser.add_argument(
        "--quick-source",
        help="Evalue un seul source_id sans ecrire le rapport produit.",
    )
    parser.add_argument("--onset-rearm-ratio", type=float)
    parser.add_argument("--retrigger-confidence-threshold", type=float)
    parser.add_argument("--minimum-retrigger-ms", type=float)
    parser.add_argument("--fixed-window", action="store_true")
    parser.add_argument("--require-joint-onset-evidence", action="store_true")
    parser.add_argument("--onset-peak-rearm", action="store_true")
    args = parser.parse_args()
    bundle = ProductBundle(args.artifact_dir)
    pitch_model = TFLitePitchModel(bundle, threads=1)
    gate = TFLiteTransitionGate(bundle)
    engine = GuitarMidiEngine(
        bundle, pitch_model, gate, calibration_s=1.0,
        onset_rearm_ratio=args.onset_rearm_ratio,
        retrigger_confidence_threshold=args.retrigger_confidence_threshold,
        minimum_retrigger_ms=args.minimum_retrigger_ms,
        progressive_windows_enabled=False if args.fixed_window else None,
        require_joint_onset_evidence=(
            True if args.require_joint_onset_evidence else None
        ),
        onset_peak_rearm=True if args.onset_peak_rearm else None,
    )
    recordings = {
        value.source_id: value for value in discover_guitarset(args.guitarset)
    }

    def evaluate(source_ids):
        rows = []
        inference = []
        for source_id in source_ids:
            recording = recordings[source_id]
            waveform, notes = _load_waveform(recording, engine.sample_rate)
            item = build_item(recording, waveform, notes, bundle.metadata)
            result = transcribe_waveform(
                engine, item["waveform"], include_padded_tail=False
            )
            rows.append(source_metrics(
                item, result.active, result.pitch, result.retrigger, []
            ))
            inference.append(result.inference_ms)
            print(f"{source_id}: {len(result.active)} hops")
        aggregate = aggregate_metrics(rows)
        values = np.concatenate(inference).astype(np.float64)
        aggregate["tflite_inference_mean_ms"] = float(np.mean(values))
        aggregate["tflite_inference_p95_ms"] = float(np.percentile(values, 95.0))
        return aggregate

    if args.quick_source:
        selected = tuple(
            value.strip() for value in args.quick_source.split(",") if value.strip()
        )
        print(json.dumps(evaluate(selected), indent=2))
        return 0

    validation = evaluate(VALIDATION_SOURCES)
    test = evaluate(DEFAULT_SOURCES)
    reference = json.loads(
        (args.artifact_dir / "backpressure_report.json").read_text(encoding="utf-8")
    )
    validation_checks = compare(validation, reference["validation"]["none"])
    test_checks = compare(test, reference["test"]["none"])
    validation_safe = safe_profile_acceptance(
        validation, reference["validation"]["none"]
    )
    test_safe = safe_profile_acceptance(test, reference["test"]["none"])
    strict_accepted = all(validation_checks.values()) and all(test_checks.values())
    accepted = all(validation_safe.values()) and all(test_safe.values())
    report = {
        "pipeline": "WAV -> causal frontend -> TFLite pitch -> TFLite gate -> MIDI state",
        "calibration": "one second of prepended silence, identical live engine",
        "validation_sources": list(VALIDATION_SOURCES),
        "validation": validation,
        "validation_reference": reference["validation"]["none"],
        "validation_acceptance": validation_checks,
        "validation_safe_profile_acceptance": validation_safe,
        "test_sources_locked": list(DEFAULT_SOURCES),
        "test": test,
        "test_reference": reference["test"]["none"],
        "test_acceptance": test_checks,
        "test_safe_profile_acceptance": test_safe,
        "strict_regression_accepted": strict_accepted,
        "acceptance_profile": "safe_low_ghost",
        "accepted_for_product": accepted,
    }
    output = args.artifact_dir / "wav_pipeline_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata_path = args.artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["validation"]["wav_pipeline_report"] = output.name
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
