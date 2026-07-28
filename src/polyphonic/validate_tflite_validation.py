"""Validate a deployable TFLite model against its frozen Keras checkpoint.

This tool is deliberately validation-only.  It is used to choose a runtime
format before the held-out test split is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

from src.polyphonic.keras_compat import load_polyphonic_checkpoint
from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    dataset_balanced_validation_refs,
    load_manifest,
)
from src.polyphonic.runtime_parity import (
    OUTPUT_MAX_ABSOLUTE_ERROR,
    parity_policy_report,
)


OUTPUT_NAMES = (
    "frame", "onset", "harmonic_amplitude", "harmonic_offset_cents",
)
DECISION_AGREEMENT_MINIMUM = 0.9999
MAXIMUM_F1_DROP = 0.002
MAXIMUM_HARMONIC_METRIC_INCREASE = 0.001


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _empty_counts() -> dict[str, int]:
    return {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def _update_counts(
    counts: dict[str, int], truth: np.ndarray, predicted: np.ndarray,
) -> None:
    truth_bool = np.asarray(truth > 0.5)
    predicted_bool = np.asarray(predicted, dtype=bool)
    counts["tp"] += int(np.sum(truth_bool & predicted_bool))
    counts["fp"] += int(np.sum(~truth_bool & predicted_bool))
    counts["fn"] += int(np.sum(truth_bool & ~predicted_bool))
    counts["tn"] += int(np.sum(~truth_bool & ~predicted_bool))


def _finish_counts(counts: dict[str, int]) -> dict[str, float | int]:
    tp = int(counts["tp"])
    fp = int(counts["fp"])
    fn = int(counts["fn"])
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": int(counts["tn"]),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _empty_scope() -> dict[str, Any]:
    return {
        "examples": 0,
        "frame": {
            "keras": _empty_counts(), "tflite": _empty_counts(),
            "equal": 0, "decisions": 0,
        },
        "onset": {
            "keras": _empty_counts(), "tflite": _empty_counts(),
            "equal": 0, "decisions": 0,
        },
        "harmonics": {
            "valid_partials": 0.0,
            "offset_weight": 0.0,
            "keras_amplitude_error": 0.0,
            "tflite_amplitude_error": 0.0,
            "keras_offset_error": 0.0,
            "tflite_offset_error": 0.0,
        },
    }


def _update_scope(
    scope: dict[str, Any],
    targets: dict[str, np.ndarray],
    keras: dict[str, np.ndarray],
    tflite: dict[str, np.ndarray],
    frame_threshold: float,
    onset_threshold: float,
    harmonic_count: int,
    offset_scale_cents: float,
) -> None:
    size = int(len(targets["frame"]))
    scope["examples"] += size
    for name, threshold in (
        ("frame", frame_threshold), ("onset", onset_threshold),
    ):
        keras_decision = keras[name] >= threshold
        tflite_decision = tflite[name] >= threshold
        _update_counts(scope[name]["keras"], targets[name], keras_decision)
        _update_counts(scope[name]["tflite"], targets[name], tflite_decision)
        scope[name]["equal"] += int(np.sum(keras_decision == tflite_decision))
        scope[name]["decisions"] += int(np.size(keras_decision))

    amplitude_target = targets["harmonic_amplitude"][..., :harmonic_count]
    amplitude_valid = targets["harmonic_amplitude"][
        ..., harmonic_count:2 * harmonic_count
    ]
    valid_count = float(np.sum(amplitude_valid))
    scope["harmonics"]["valid_partials"] += valid_count
    scope["harmonics"]["keras_amplitude_error"] += float(np.sum(
        np.abs(keras["harmonic_amplitude"] - amplitude_target)
        * amplitude_valid
    ))
    scope["harmonics"]["tflite_amplitude_error"] += float(np.sum(
        np.abs(tflite["harmonic_amplitude"] - amplitude_target)
        * amplitude_valid
    ))

    offset_target = targets["harmonic_offset_cents"][..., :harmonic_count]
    offset_valid = targets["harmonic_offset_cents"][
        ..., harmonic_count:2 * harmonic_count
    ]
    offset_amplitude = targets["harmonic_offset_cents"][
        ..., 2 * harmonic_count:3 * harmonic_count
    ]
    weights = offset_valid * np.maximum(offset_amplitude, 0.0)
    weight_sum = float(np.sum(weights))
    scope["harmonics"]["offset_weight"] += weight_sum
    scope["harmonics"]["keras_offset_error"] += float(np.sum(
        np.abs(keras["harmonic_offset_cents"] - offset_target)
        / offset_scale_cents * weights
    ))
    scope["harmonics"]["tflite_offset_error"] += float(np.sum(
        np.abs(tflite["harmonic_offset_cents"] - offset_target)
        / offset_scale_cents * weights
    ))


def _finish_scope(scope: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {"examples": int(scope["examples"])}
    for name in ("frame", "onset"):
        keras = _finish_counts(scope[name]["keras"])
        tflite = _finish_counts(scope[name]["tflite"])
        decisions = int(scope[name]["decisions"])
        report[name] = {
            "keras": keras,
            "tflite": tflite,
            "f1_delta_tflite_minus_keras": (
                float(tflite["f1"]) - float(keras["f1"])
            ),
            "decision_agreement": (
                int(scope[name]["equal"]) / max(decisions, 1)
            ),
            "decision_mismatches": decisions - int(scope[name]["equal"]),
            "decisions": decisions,
        }

    harmonic = scope["harmonics"]
    valid = max(float(harmonic["valid_partials"]), 1.0)
    offset_weight = max(float(harmonic["offset_weight"]), 1.0)
    keras_amplitude = float(harmonic["keras_amplitude_error"]) / valid
    tflite_amplitude = float(harmonic["tflite_amplitude_error"]) / valid
    keras_offset = float(harmonic["keras_offset_error"]) / offset_weight
    tflite_offset = float(harmonic["tflite_offset_error"]) / offset_weight
    report["harmonics"] = {
        "valid_partials": int(round(float(harmonic["valid_partials"]))),
        "keras_amplitude_mae": keras_amplitude,
        "tflite_amplitude_mae": tflite_amplitude,
        "amplitude_mae_delta_tflite_minus_keras": (
            tflite_amplitude - keras_amplitude
        ),
        "keras_offset_normalized_mae": keras_offset,
        "tflite_offset_normalized_mae": tflite_offset,
        "offset_normalized_mae_delta_tflite_minus_keras": (
            tflite_offset - keras_offset
        ),
    }
    return report


def _scope_passes(report: dict[str, Any]) -> bool:
    return bool(
        all(
            float(report[name]["decision_agreement"])
            >= DECISION_AGREEMENT_MINIMUM
            and float(report[name]["f1_delta_tflite_minus_keras"])
            >= -MAXIMUM_F1_DROP
            for name in ("frame", "onset")
        )
        and float(
            report["harmonics"]["amplitude_mae_delta_tflite_minus_keras"]
        ) <= MAXIMUM_HARMONIC_METRIC_INCREASE
        and float(
            report["harmonics"][
                "offset_normalized_mae_delta_tflite_minus_keras"
            ]
        ) <= MAXIMUM_HARMONIC_METRIC_INCREASE
    )


def validate(
    run_dir: Path,
    artifact_dir: Path,
    output_path: Path,
    maximum_examples: int = 60_000,
    batch_size: int = 64,
) -> dict[str, Any]:
    if maximum_examples < 1 or batch_size < 1:
        raise ValueError("maximum_examples and batch_size must be positive")
    selection = json.loads((run_dir / "selection.json").read_text("utf-8"))
    if (
        selection.get("selected_on") != "validation_note_events"
        or selection.get("locked_test_used") is not False
    ):
        raise ValueError("Checkpoint selection is not frozen validation-only.")
    config = json.loads((run_dir / "config.json").read_text("utf-8"))
    thresholds = json.loads((run_dir / "thresholds.json").read_text("utf-8"))
    checkpoint = run_dir / "selected.keras"
    tflite_path = artifact_dir / "guitar_midi_polyphonic.tflite"
    metadata = json.loads((artifact_dir / "metadata.json").read_text("utf-8"))
    if _sha256(tflite_path) != metadata["artifact"]["sha256"]:
        raise ValueError("TFLite SHA256 does not match metadata.")

    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == "validation"
    ]
    corpus = PolyphonicCorpus(items)
    seed = int(config["dataset"].get("seed", 42))
    fractions = config["train"].get("validation_dataset_fractions")
    if not fractions:
        raise ValueError("A multi-source validation mixture is required.")
    refs = dataset_balanced_validation_refs(
        corpus, maximum_examples, fractions, seed + 29
    )
    sequence = PolyphonicSequence(
        corpus,
        batch_size=batch_size,
        input_samples=int(config["dataset"]["input_samples"]),
        normalization_gain=float(config["dataset"]["normalization_gain"]),
        seed=seed,
        refs=refs,
        shuffle=False,
    )

    model = load_polyphonic_checkpoint(checkpoint)
    inference = tf.keras.Model(
        model.inputs,
        {name: model.get_layer(name).output for name in OUTPUT_NAMES},
    )
    interpreter = tf.lite.Interpreter(model_path=str(tflite_path), num_threads=1)
    interpreter.allocate_tensors()
    runner = interpreter.get_signature_runner("serving_default")
    frame_threshold = float(thresholds["frame"])
    onset_threshold = float(thresholds["onset"])
    offset_scale = float(config["model"]["harmonic_offset_scale_cents"])
    global_scope = _empty_scope()
    dataset_scopes = {
        dataset_id: _empty_scope() for dataset_id in fractions
    }
    numerical = {
        name: {"maximum_absolute_error": 0.0, "absolute_error_sum": 0.0,
               "elements": 0}
        for name in OUTPUT_NAMES
    }

    corpus.preload_audio()
    try:
        for batch_index in range(len(sequence)):
            inputs, targets = sequence[batch_index]
            keras_raw = inference(inputs, training=False)
            keras = {
                name: np.asarray(keras_raw[name], dtype=np.float32)
                for name in OUTPUT_NAMES
            }
            tflite_parts = {name: [] for name in OUTPUT_NAMES}
            for row in range(len(inputs["audio"])):
                values = runner(
                    audio=inputs["audio"][row:row + 1],
                    time_mask=inputs["time_mask"][row:row + 1],
                )
                for name in OUTPUT_NAMES:
                    tflite_parts[name].append(np.asarray(values[name]))
            tflite = {
                name: np.concatenate(tflite_parts[name], axis=0)
                for name in OUTPUT_NAMES
            }

            for name in OUTPUT_NAMES:
                difference = np.abs(keras[name] - tflite[name])
                numerical[name]["maximum_absolute_error"] = max(
                    float(numerical[name]["maximum_absolute_error"]),
                    float(np.max(difference)),
                )
                numerical[name]["absolute_error_sum"] += float(np.sum(difference))
                numerical[name]["elements"] += int(np.size(difference))

            _update_scope(
                global_scope, targets, keras, tflite,
                frame_threshold, onset_threshold,
                corpus.harmonic_count, offset_scale,
            )
            start = batch_index * sequence.batch_size
            selected = sequence.order[start:start + len(inputs["audio"])]
            dataset_ids = np.asarray([
                corpus.items[int(recording_index)].dataset_id
                for recording_index in selected[:, 0]
            ])
            for dataset_id, scope in dataset_scopes.items():
                rows = np.flatnonzero(dataset_ids == dataset_id)
                if not len(rows):
                    continue
                _update_scope(
                    scope,
                    {name: value[rows] for name, value in targets.items()},
                    {name: value[rows] for name, value in keras.items()},
                    {name: value[rows] for name, value in tflite.items()},
                    frame_threshold, onset_threshold,
                    corpus.harmonic_count, offset_scale,
                )
            if (batch_index + 1) % 50 == 0 or batch_index + 1 == len(sequence):
                print(
                    f"validation {min((batch_index + 1) * batch_size, len(refs))}"
                    f"/{len(refs)}",
                    flush=True,
                )
    finally:
        corpus.close()

    numerical_report: dict[str, dict[str, float | int]] = {}
    numerical_passed = True
    for name, values in numerical.items():
        elements = int(values["elements"])
        maximum = float(values["maximum_absolute_error"])
        tolerance = float(OUTPUT_MAX_ABSOLUTE_ERROR[name])
        numerical_report[name] = {
            "maximum_absolute_error": maximum,
            "mean_absolute_error": (
                float(values["absolute_error_sum"]) / max(elements, 1)
            ),
            "elements": elements,
            "maximum_allowed": tolerance,
            "passed": maximum <= tolerance,
        }
        numerical_passed = numerical_passed and maximum <= tolerance

    global_report = _finish_scope(global_scope)
    dataset_reports = {
        name: _finish_scope(scope) for name, scope in dataset_scopes.items()
    }
    policy = {
        "minimum_frame_decision_agreement": DECISION_AGREEMENT_MINIMUM,
        "minimum_onset_decision_agreement": DECISION_AGREEMENT_MINIMUM,
        "maximum_absolute_f1_drop_per_scope": MAXIMUM_F1_DROP,
        "maximum_harmonic_metric_increase_per_scope": (
            MAXIMUM_HARMONIC_METRIC_INCREASE
        ),
        "numerical": parity_policy_report(),
    }
    passed = bool(
        numerical_passed
        and _scope_passes(global_report)
        and all(_scope_passes(row) for row in dataset_reports.values())
    )
    report = {
        "run_dir": str(run_dir),
        "artifact_dir": str(artifact_dir),
        "split": "validation",
        "locked_test_used": False,
        "selection_frozen": True,
        "thresholds_reselected": False,
        "reference_seed": seed + 29,
        "references_sha256": hashlib.sha256(
            np.ascontiguousarray(refs).tobytes()
        ).hexdigest(),
        "examples": int(len(refs)),
        "dataset_fractions": fractions,
        "thresholds_frozen": {
            "frame": frame_threshold, "onset": onset_threshold,
        },
        "tflite_sha256": _sha256(tflite_path),
        "numerical": numerical_report,
        "global": global_report,
        "datasets": dataset_reports,
        "policy": policy,
        "passed": passed,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-examples", type=int, default=60_000)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    report = validate(
        args.run_dir, args.artifact_dir, args.output,
        args.maximum_examples, args.batch_size,
    )
    print(json.dumps({
        "split": report["split"],
        "examples": report["examples"],
        "global": report["global"],
        "datasets": report["datasets"],
        "passed": report["passed"],
    }, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
