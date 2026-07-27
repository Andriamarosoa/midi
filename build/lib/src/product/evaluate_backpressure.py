"""Validate bounded inference skipping before enabling live backpressure.

The policy is selected exclusively on GuitarSet player 04.  Player 05 is
evaluated once with the locked worst-case burst pattern.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.product.decoder import StreamingTransitionDecoder
from src.product.evaluate_stride import SimpleDecision
from src.v5.external_data import discover_guitarset
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v6.continuous_onset_v63_ablation import DEFAULT_SOURCES
from src.v6.select_transition_gate_decoder import (
    VALIDATION_SOURCES,
    aggregate_metrics,
    prepare_source,
    source_metrics,
)


POLICIES = {
    "none": (1, 0),
    "periodic_6pct": (16, 1),
    "burst_6pct": (32, 2),
    "periodic_10pct": (10, 1),
    "burst_10pct": (20, 2),
}


def should_skip(index: int, period: int, count: int) -> bool:
    return count > 0 and index % period >= period - count


def decode_policy(item: dict[str, object], gate_predict, policy: tuple[int, int]):
    count = len(item["active_probability"])
    active = np.zeros(count, dtype=bool)
    pitch = np.full(count, -1, dtype=np.int32)
    retrigger = np.zeros(count, dtype=bool)
    decisions = []
    period, skipped = policy
    decoder = StreamingTransitionDecoder(
        gate_predict=gate_predict,
        min_pitch=int(item["min_pitch"]),
        max_pitch=int(item["max_pitch"]),
        active_threshold=float(item["active_threshold"]),
        transition_threshold=float(item["transition_threshold"]),
        hop_ms=int(item["hop_size"]) / int(item["sample_rate"]) * 1000.0,
        required_frames=2,
        minimum_retrigger_ms=80.0,
    )
    stream = item["stream_features"]
    for index in range(count):
        stream_values = {
            name: float(stream[name][index])
            for name in (
                "detected_onset", "onset_confidence", "onset_age", "rms_level",
                "rms_growth_ratio", "spectral_flux",
            )
        }
        if should_skip(index, period, skipped):
            value = decoder.skip(stream_values)
        else:
            value = decoder.step(
                float(item["active_probability"][index]),
                item["pitch_probability"][index],
                item["harmonic_amplitude"][index],
                stream_values,
            )
        active[index] = value.active
        pitch[index] = value.pitch
        retrigger[index] = value.retrigger
        if value.transition_score is not None:
            decisions.append(SimpleDecision(
                value.transition_score, not value.transition_veto
            ))
    return active, pitch, retrigger, decisions


def metrics(prepared, gate_predict, policy: tuple[int, int]) -> dict[str, object]:
    values = []
    for item in prepared:
        active, pitch, retrigger, decisions = decode_policy(
            item, gate_predict, policy
        )
        values.append(source_metrics(item, active, pitch, retrigger, decisions))
    return aggregate_metrics(values)


def acceptance(candidate: dict, baseline: dict) -> dict[str, bool]:
    return {
        "missing_not_worse": candidate["missing"] <= baseline["missing"],
        "ghosts_not_worse": (
            candidate["ghost_events_per_minute"]
            <= baseline["ghost_events_per_minute"]
        ),
        "unsupported_retriggers_not_worse": (
            candidate["unsupported_retriggers"]
            <= baseline["unsupported_retriggers"]
        ),
        "joint_within_tolerance": (
            candidate["joint_frame_accuracy"]
            >= baseline["joint_frame_accuracy"] - 0.002
        ),
        "active_f1_within_tolerance": (
            candidate["active_f1"] >= baseline["active_f1"] - 0.002
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument("--gate-run", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    import tensorflow as tf

    v60_run = args.v60_run.resolve()
    gate_run = args.gate_run.resolve()
    v60_selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    gate_selection = json.loads(
        (gate_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    decoder_selection = json.loads(
        (gate_run / "decoder_threshold_selection.json").read_text(encoding="utf-8")
    )
    dataset = json.loads((v60_run / "config.json").read_text(encoding="utf-8"))[
        "dataset"
    ]
    gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    active_threshold = float(v60_selection["active_threshold"])
    transition_threshold = float(
        decoder_selection["decoder_transition_threshold"]
    )
    v60_model = tf.keras.models.load_model(
        v60_run / v60_selection["selected_checkpoint"], compile=False
    )
    gate_model = tf.keras.models.load_model(
        gate_run / gate_selection["selected_checkpoint"], compile=False
    )

    @tf.function(input_signature=[
        tf.TensorSpec((None, 4096, 1), tf.float32),
        tf.TensorSpec((None, 4096), tf.float32),
    ], autograph=False)
    def v60_inference(audio, mask):
        return v60_model({"audio": audio, "time_mask": mask}, training=False)

    @tf.function(
        input_signature=[tf.TensorSpec((None, 20), tf.float32)],
        autograph=False,
    )
    def gate_inference(features):
        return gate_model(features, training=False)

    def gate_predict(features):
        return np.asarray(gate_inference(features), dtype=np.float32)

    recordings = {
        value.source_id: value for value in discover_guitarset("data/GuitarSet")
    }

    def prepare(source_ids):
        values = [
            prepare_source(
                v60_model, v60_inference, recordings[source],
                int(dataset["sample_rate"]), int(dataset["hop_size"]),
                int(dataset["min_pitch"]), int(dataset["max_pitch"]), gain,
                active_threshold, args.batch_size,
            )
            for source in source_ids
        ]
        for value in values:
            value["transition_threshold"] = transition_threshold
        return values

    validation = prepare(VALIDATION_SOURCES)
    validation_metrics = {
        name: metrics(validation, gate_predict, policy)
        for name, policy in POLICIES.items()
    }
    baseline = validation_metrics["none"]
    validation_acceptance = {}
    for name, value in validation_metrics.items():
        checks = acceptance(value, baseline)
        validation_acceptance[name] = checks
        value["accepted"] = all(checks.values())

    # The live trace was 5.56%; lock the harsher contiguous 2/32 pattern.
    locked_policy = "burst_6pct"
    validation_accepted = bool(validation_metrics[locked_policy]["accepted"])
    test = prepare(DEFAULT_SOURCES)
    test_metrics = {
        "none": metrics(test, gate_predict, POLICIES["none"]),
        locked_policy: metrics(test, gate_predict, POLICIES[locked_policy]),
    }
    test_acceptance = acceptance(test_metrics[locked_policy], test_metrics["none"])
    accepted = validation_accepted and all(test_acceptance.values())
    report = {
        "selection_basis": "player_04_four_solos_only",
        "hardware_observed_skip_percent": 5.56,
        "locked_policy": locked_policy,
        "locked_policy_skip_percent": 6.25,
        "validation_tolerance_absolute": 0.002,
        "validation": validation_metrics,
        "validation_acceptance": validation_acceptance,
        "test_sources_locked": list(DEFAULT_SOURCES),
        "test": test_metrics,
        "test_acceptance": test_acceptance,
        "accepted_for_product": accepted,
        "max_inference_skip_percent": 6.25 if accepted else 0.0,
    }
    output = args.artifact_dir / "backpressure_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata_path = args.artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["max_live_backlog_hops"] = 3 if accepted else 0
    metadata["max_inference_skip_percent"] = report["max_inference_skip_percent"]
    metadata["validation"]["backpressure_report"] = output.name
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
