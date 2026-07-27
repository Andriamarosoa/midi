"""Export the selected polyphonic checkpoint to TensorFlow Lite."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    load_manifest,
    natural_validation_refs,
)


OUTPUT_NAMES = (
    "frame", "onset", "harmonic_amplitude", "harmonic_offset_cents",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _signature(path: Path, threads: int):
    interpreter = tf.lite.Interpreter(model_path=str(path), num_threads=threads)
    interpreter.allocate_tensors()
    return interpreter, interpreter.get_signature_runner("serving_default")


def _examples(config: dict, limit: int) -> tuple[np.ndarray, np.ndarray]:
    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == "test"
    ]
    corpus = PolyphonicCorpus(items)
    refs = natural_validation_refs(corpus, limit, int(config["dataset"]["seed"]) + 99)
    sequence = PolyphonicSequence(
        corpus,
        batch_size=limit,
        input_samples=int(config["dataset"]["input_samples"]),
        normalization_gain=float(config["dataset"]["normalization_gain"]),
        seed=0,
        refs=refs,
        shuffle=False,
    )
    try:
        inputs, _ = sequence[0]
    finally:
        corpus.close()
    return inputs["audio"], inputs["time_mask"]


def _benchmark(
    model_path: Path,
    audio: np.ndarray,
    mask: np.ndarray,
    repeats: int = 300,
) -> dict[str, object]:
    results: dict[str, dict[str, float]] = {}
    sample = {"audio": audio[:1], "time_mask": mask[:1]}
    for threads in (1, 2, 4):
        _, runner = _signature(model_path, threads)
        for _ in range(20):
            runner(**sample)
        timings = []
        for _ in range(repeats):
            started = time.perf_counter()
            runner(**sample)
            timings.append((time.perf_counter() - started) * 1000.0)
        values = np.asarray(timings)
        results[str(threads)] = {
            "mean_ms": float(np.mean(values)),
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "max_ms": float(np.max(values)),
        }
    best = min(results, key=lambda key: (
        results[key]["p95_ms"], results[key]["mean_ms"]
    ))
    return {"threads": results, "recommended_threads": int(best)}


def export(run_dir: Path, output_dir: Path, examples: int = 96) -> dict[str, object]:
    selection_path = run_dir / "selection.json"
    checkpoint = run_dir / "selected.keras"
    if not selection_path.is_file() or not checkpoint.is_file():
        raise ValueError(
            "Export requires selected.keras chosen on validation note events."
        )
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if (
        selection.get("selected_on") != "validation_note_events"
        or selection.get("locked_test_used") is not False
    ):
        raise ValueError("Invalid or test-contaminated checkpoint selection.")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    thresholds = json.loads((run_dir / "thresholds.json").read_text(encoding="utf-8"))
    decoder_path = run_dir / "decoder_config.json"
    frame_threshold = float(thresholds["frame"])
    decoder_config = (
        json.loads(decoder_path.read_text(encoding="utf-8"))
        if decoder_path.is_file()
        else {
            "midi_min": 40,
            "midi_max": 76,
            "frame_on_threshold": frame_threshold,
            "strong_frame_threshold": min(0.95, max(0.80, frame_threshold + 0.25)),
            "frame_off_threshold": max(0.05, frame_threshold * 0.60),
            "onset_threshold": float(thresholds["onset"]),
            "activation_frames": 2,
            "release_frames": 3,
            "minimum_retrigger_frames": 14,
            "silence_release_frames": 2,
            "maximum_polyphony": 6,
            "harmonic_suppression_strength": 0.25,
            "harmonic_tolerance_cents": 35.0,
        }
    )
    model = tf.keras.models.load_model(checkpoint, compile=False)

    class ExportModule(tf.Module):
        def __init__(self, keras_model):
            super().__init__()
            self.keras_model = keras_model

        @tf.function(input_signature=[
            tf.TensorSpec((1, 4096, 1), tf.float32, name="audio"),
            tf.TensorSpec((1, 4096), tf.float32, name="time_mask"),
        ])
        def infer(self, audio, time_mask):
            values = self.keras_model(
                {"audio": audio, "time_mask": time_mask}, training=False
            )
            return {
                name: tf.identity(values[name], name=name)
                for name in OUTPUT_NAMES
            }

    module = ExportModule(model)
    concrete = module.infer.get_concrete_function()
    saved_model = output_dir / "saved_model_polyphonic"
    tf.saved_model.save(
        module, str(saved_model), signatures={"serving_default": concrete}
    )
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete], module)
    tflite_path = output_dir / "guitar_midi_polyphonic.tflite"
    tflite_path.write_bytes(converter.convert())

    audio, mask = _examples(config, examples)
    expected_parts: dict[str, list[np.ndarray]] = {name: [] for name in OUTPUT_NAMES}
    actual_parts: dict[str, list[np.ndarray]] = {name: [] for name in OUTPUT_NAMES}
    _, runner = _signature(tflite_path, 1)
    for index in range(len(audio)):
        expected = model(
            {"audio": audio[index:index + 1], "time_mask": mask[index:index + 1]},
            training=False,
        )
        actual = runner(
            audio=audio[index:index + 1], time_mask=mask[index:index + 1]
        )
        for name in OUTPUT_NAMES:
            expected_parts[name].append(np.asarray(expected[name]))
            actual_parts[name].append(np.asarray(actual[name]))
    expected_all = {
        name: np.concatenate(values) for name, values in expected_parts.items()
    }
    actual_all = {
        name: np.concatenate(values) for name, values in actual_parts.items()
    }
    parity: dict[str, object] = {}
    for name in OUTPUT_NAMES:
        difference = np.abs(expected_all[name] - actual_all[name])
        parity[name] = {
            "maximum_absolute_error": float(np.max(difference)),
            "mean_absolute_error": float(np.mean(difference)),
        }
    parity["frame_decision_agreement"] = float(np.mean(
        (expected_all["frame"] >= float(thresholds["frame"]))
        == (actual_all["frame"] >= float(thresholds["frame"]))
    ))
    parity["onset_decision_agreement"] = float(np.mean(
        (expected_all["onset"] >= float(thresholds["onset"]))
        == (actual_all["onset"] >= float(thresholds["onset"]))
    ))
    parity["passed"] = bool(
        parity["frame_decision_agreement"] == 1.0
        and parity["onset_decision_agreement"] == 1.0
        and max(
            parity[name]["maximum_absolute_error"] for name in OUTPUT_NAMES
        ) < 0.01
    )
    if not parity["passed"]:
        raise RuntimeError(f"TFLite parity failed: {parity}")
    np.savez_compressed(
        output_dir / "parity_examples.npz",
        audio=audio,
        time_mask=mask,
        **{f"tflite_{name}": value for name, value in actual_all.items()},
    )
    hop_budget_ms = 256 / 44_100 * 1000.0
    tflite_latency = _benchmark(tflite_path, audio, mask)
    recommended = str(tflite_latency["recommended_threads"])
    recommended_p95 = float(tflite_latency["threads"][recommended]["p95_ms"])
    tflite_latency["recommended_p95_ms"] = recommended_p95
    tflite_latency["meets_hop_budget_p95"] = recommended_p95 <= hop_budget_ms
    latency = {
        "hop_budget_ms": hop_budget_ms,
        "tflite": tflite_latency,
        "passed": bool(tflite_latency["meets_hop_budget_p95"]),
    }
    metadata = {
        "product_version": "2.0.0",
        "model_stack": "causal polyphonic frame+onset+20-partial harmonics",
        "sample_rate": 44_100,
        "hop_samples": 256,
        "max_window_samples": 4096,
        "normalization_gain": float(config["dataset"]["normalization_gain"]),
        "min_pitch": 40,
        "max_pitch": 76,
        "maximum_polyphony": 6,
        "polyphony_supported": True,
        "frame_threshold": float(thresholds["frame"]),
        "onset_threshold": float(thresholds["onset"]),
        "decoder": decoder_config,
        "outputs": list(OUTPUT_NAMES),
        "recommended_tflite_threads": latency["tflite"]["recommended_threads"],
        "artifact": {
            "tflite": tflite_path.name,
            "sha256": sha256(tflite_path),
            "parity_examples": "parity_examples.npz",
        },
        "source_run": str(run_dir),
        "source_checkpoint": str(checkpoint),
    }
    (output_dir / "parity_report.json").write_text(
        json.dumps(parity, indent=2), encoding="utf-8"
    )
    (output_dir / "latency_report.json").write_text(
        json.dumps(latency, indent=2), encoding="utf-8"
    )
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return {"output_dir": str(output_dir), "parity": parity, "latency": latency}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=96)
    args = parser.parse_args()
    print(json.dumps(export(args.run_dir, args.output_dir, args.examples), indent=2))


if __name__ == "__main__":
    main()
