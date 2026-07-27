"""Choose a real-time inference stride on player 04, then lock player 05."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.product.decoder import StreamingTransitionDecoder
from src.v5.external_data import discover_guitarset
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v6.continuous_onset_v63_ablation import DEFAULT_SOURCES
from src.v6.select_transition_gate_decoder import (
    VALIDATION_SOURCES,
    aggregate_metrics,
    prepare_source,
    source_metrics,
)


def decode_stride(item: dict[str, object], gate_predict, stride: int):
    if stride < 1:
        raise ValueError("stride doit etre positif.")
    count = len(item["active_probability"])
    active = np.zeros(count, dtype=bool)
    pitch = np.full(count, -1, dtype=np.int32)
    retrigger = np.zeros(count, dtype=bool)
    decisions = []
    decoder = StreamingTransitionDecoder(
        gate_predict=gate_predict,
        min_pitch=int(item["min_pitch"]),
        max_pitch=int(item["max_pitch"]),
        active_threshold=float(item["active_threshold"]),
        transition_threshold=float(item["transition_threshold"]),
        hop_ms=(
            int(item["hop_size"]) / int(item["sample_rate"]) * 1000.0 * stride
        ),
        required_frames=2,
        minimum_retrigger_ms=80.0,
    )
    stream = item["stream_features"]
    latest_active = False
    latest_pitch = -1
    previous_sampled = 0
    for index in range(count):
        if index % stride == 0:
            onset_start = previous_sampled if index else 0
            stream_values = {
                name: float(stream[name][index])
                for name in (
                    "onset_age", "rms_level", "rms_growth_ratio", "spectral_flux",
                )
            }
            stream_values["detected_onset"] = float(np.max(
                stream["detected_onset"][onset_start:index + 1]
            ))
            stream_values["onset_confidence"] = float(np.max(
                stream["onset_confidence"][onset_start:index + 1]
            ))
            value = decoder.step(
                float(item["active_probability"][index]),
                item["pitch_probability"][index],
                item["harmonic_amplitude"][index],
                stream_values,
            )
            latest_active = value.active
            latest_pitch = value.pitch
            retrigger[index] = value.retrigger
            if value.transition_score is not None:
                decisions.append(SimpleDecision(
                    value.transition_score,
                    not value.transition_veto,
                ))
            previous_sampled = index + 1
        active[index] = latest_active
        pitch[index] = latest_pitch
    return active, pitch, retrigger, decisions


class SimpleDecision:
    def __init__(self, score: float, allowed: bool) -> None:
        self.score = score
        self.allowed = allowed
        self.feature = np.zeros(20, dtype=np.float32)


def metrics(prepared, gate_predict, stride: int) -> dict[str, object]:
    values = []
    for item in prepared:
        active, pitch, retrigger, decisions = decode_stride(
            item, gate_predict, stride
        )
        values.append(source_metrics(item, active, pitch, retrigger, decisions))
    return aggregate_metrics(values)


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
    dataset = json.loads(
        (v60_run / "config.json").read_text(encoding="utf-8")
    )["dataset"]
    gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    active_threshold = float(v60_selection["active_threshold"])
    transition_threshold = float(decoder_selection["decoder_transition_threshold"])
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

    @tf.function(input_signature=[tf.TensorSpec((None, 20), tf.float32)], autograph=False)
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
                int(dataset["min_pitch"]), int(dataset["max_pitch"]),
                gain, active_threshold, args.batch_size,
            )
            for source in source_ids
        ]
        for value in values:
            value["transition_threshold"] = transition_threshold
        return values

    validation = prepare(VALIDATION_SOURCES)
    validation_metrics = {
        str(stride): metrics(validation, gate_predict, stride)
        for stride in (1, 2, 3)
    }
    baseline = validation_metrics["1"]
    feasible = []
    for stride in (1, 2, 3):
        value = validation_metrics[str(stride)]
        value["feasible"] = bool(
            value["missing"] <= baseline["missing"]
            and value["ghost_events_per_minute"] <= baseline["ghost_events_per_minute"]
            and value["unsupported_retriggers"] <= baseline["unsupported_retriggers"]
            and value["joint_frame_accuracy"] >= baseline["joint_frame_accuracy"] - 0.002
            and value["active_f1"] >= baseline["active_f1"] - 0.002
        )
        if value["feasible"]:
            feasible.append(stride)
    selected_stride = max(feasible)
    test = prepare(DEFAULT_SOURCES)
    test_metrics = {
        "stride_1_reference": metrics(test, gate_predict, 1),
        f"stride_{selected_stride}_locked": metrics(
            test, gate_predict, selected_stride
        ),
    }
    test_baseline = test_metrics["stride_1_reference"]
    test_candidate = test_metrics[f"stride_{selected_stride}_locked"]
    acceptance = {
        "missing_not_worse": test_candidate["missing"] <= test_baseline["missing"],
        "ghosts_not_worse": (
            test_candidate["ghost_events_per_minute"]
            <= test_baseline["ghost_events_per_minute"]
        ),
        "unsupported_retriggers_not_worse": (
            test_candidate["unsupported_retriggers"]
            <= test_baseline["unsupported_retriggers"]
        ),
        "joint_within_validation_tolerance": (
            test_candidate["joint_frame_accuracy"]
            >= test_baseline["joint_frame_accuracy"] - 0.002
        ),
        "active_f1_within_validation_tolerance": (
            test_candidate["active_f1"] >= test_baseline["active_f1"] - 0.002
        ),
    }
    accepted = bool(all(acceptance.values()))
    report = {
        "selection_basis": "player_04_four_solos_only",
        "validation_tolerance_absolute": 0.002,
        "validation": validation_metrics,
        "selected_stride": selected_stride,
        "additional_max_note_on_delay_ms": (
            selected_stride - 1
        ) * int(dataset["hop_size"]) / int(dataset["sample_rate"]) * 1000.0,
        "test_sources_locked": list(DEFAULT_SOURCES),
        "test": test_metrics,
        "test_acceptance": acceptance,
        "accepted_for_product": accepted,
        "product_stride": selected_stride if accepted else 1,
    }
    output = args.artifact_dir / "stride_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata_path = args.artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["inference_stride_hops"] = report["product_stride"]
    metadata["validation"]["stride_report"] = output.name
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
