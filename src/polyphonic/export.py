"""Export the selected polyphonic checkpoint to TensorFlow Lite."""

from __future__ import annotations

import argparse
import gc
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
from src.polyphonic.runtime_parity import parity_passes, parity_policy_report


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


def _examples(
    config: dict,
    limit: int,
    split: str = "validation",
) -> tuple[np.ndarray, np.ndarray]:
    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == split
    ]
    if not items:
        raise ValueError(f"No {split!r} examples are available for export checks.")
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
    repeats: int = 600,
    sessions: int = 3,
    hop_budget_ms: float = 256 / 44_100 * 1000.0,
) -> dict[str, object]:
    if repeats < 1 or sessions < 1:
        raise ValueError("repeats and sessions must be positive")

    def summarize(timings: list[float]) -> dict[str, float | int]:
        values = np.asarray(timings, np.float64)
        misses = values > hop_budget_ms
        longest = current = 0
        for missed in misses:
            current = current + 1 if bool(missed) else 0
            longest = max(longest, current)
        return {
            "samples": int(len(values)),
            "mean_ms": float(np.mean(values)),
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "p99_ms": float(np.percentile(values, 99)),
            "max_ms": float(np.max(values)),
            "over_hop_rate": float(np.mean(misses)),
            "longest_consecutive_hop_misses": int(longest),
        }

    thread_counts = (1, 2, 3, 4)
    per_thread: dict[int, list[dict[str, float | int]]] = {
        value: [] for value in thread_counts
    }
    for session_index in range(sessions):
        ordered = thread_counts[session_index:] + thread_counts[:session_index]
        for threads in ordered:
            _, runner = _signature(model_path, threads)
            for index in range(100):
                sample_index = index % len(audio)
                runner(
                    audio=audio[sample_index:sample_index + 1],
                    time_mask=mask[sample_index:sample_index + 1],
                )
            timings: list[float] = []
            gc.disable()
            try:
                for index in range(repeats):
                    sample_index = index % len(audio)
                    started = time.perf_counter_ns()
                    runner(
                        audio=audio[sample_index:sample_index + 1],
                        time_mask=mask[sample_index:sample_index + 1],
                    )
                    timings.append(
                        (time.perf_counter_ns() - started) / 1_000_000.0
                    )
            finally:
                gc.enable()
            per_thread[threads].append(summarize(timings))

    results: dict[str, dict[str, object]] = {}
    for threads, session_rows in per_thread.items():
        p95_values = [float(row["p95_ms"]) for row in session_rows]
        p95_variation = (
            (max(p95_values) - min(p95_values)) / max(min(p95_values), 1e-9)
        )
        summary: dict[str, object] = {
            "sessions": session_rows,
            "mean_ms": max(float(row["mean_ms"]) for row in session_rows),
            "p50_ms": max(float(row["p50_ms"]) for row in session_rows),
            "p95_ms": max(p95_values),
            "p99_ms": max(float(row["p99_ms"]) for row in session_rows),
            "max_ms": max(float(row["max_ms"]) for row in session_rows),
            "over_hop_rate": max(
                float(row["over_hop_rate"]) for row in session_rows
            ),
            "longest_consecutive_hop_misses": max(
                int(row["longest_consecutive_hop_misses"])
                for row in session_rows
            ),
            "p95_inter_session_variation": p95_variation,
        }
        summary["eligible"] = bool(
            float(summary["p95_ms"]) <= 0.75 * hop_budget_ms
            and float(summary["p99_ms"]) <= hop_budget_ms
            and float(summary["over_hop_rate"]) <= 0.001
            and float(summary["max_ms"]) <= 2.0 * hop_budget_ms
            and int(summary["longest_consecutive_hop_misses"]) <= 1
            and float(summary["p95_inter_session_variation"]) <= 0.15
        )
        results[str(threads)] = summary

    eligible = [key for key, row in results.items() if bool(row["eligible"])]
    # Prefer the smallest eligible pool.  Once every candidate has ample
    # headroom, extra inference threads only compete with the PortAudio and
    # synthesizer callbacks during live use.  Latency still decides whether a
    # thread count is eligible; resource isolation decides between eligible
    # counts.
    recommended = min(eligible, key=int) if eligible else None
    return {
        "protocol": {
            "kind": "saturated_multisession_smoke",
            "sessions": sessions,
            "repeats_per_session": repeats,
            "warmup_calls": 100,
            "thread_counts": list(thread_counts),
            "thread_order_rotated": True,
            "selection_uses_worst_session": True,
            "portable_process_priority": "normal",
            "portable_affinity": "os_default",
            "thread_selection": "smallest_eligible_to_limit_live_contention",
        },
        "eligibility": {
            "p95_limit_ms": 0.75 * hop_budget_ms,
            "p99_limit_ms": hop_budget_ms,
            "maximum_over_hop_rate": 0.001,
            "maximum_single_inference_ms": 2.0 * hop_budget_ms,
            "maximum_consecutive_hop_misses": 1,
            "maximum_p95_inter_session_variation": 0.15,
        },
        "threads": results,
        "recommended_threads": int(recommended) if recommended else None,
    }


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
            "silence_release_frames": 14,
            "maximum_polyphony": 6,
            "harmonic_suppression_strength": 0.25,
            "harmonic_tolerance_cents": 35.0,
            "audio_onset_lookback_frames": 10,
            "unattacked_frame_threshold": 0.90,
            "harmonic_support_threshold": 0.60,
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
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_path = output_dir / "guitar_midi_polyphonic.tflite"
    tflite_path.write_bytes(converter.convert())

    export_check_split = "validation"
    audio, mask = _examples(config, examples, split=export_check_split)
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
    frame_equal = (
        (expected_all["frame"] >= float(thresholds["frame"]))
        == (actual_all["frame"] >= float(thresholds["frame"]))
    )
    onset_equal = (
        (expected_all["onset"] >= float(thresholds["onset"]))
        == (actual_all["onset"] >= float(thresholds["onset"]))
    )
    parity["frame_decision_agreement"] = float(np.mean(frame_equal))
    parity["frame_decision_mismatches"] = int(np.size(frame_equal) - np.sum(frame_equal))
    parity["onset_decision_agreement"] = float(np.mean(onset_equal))
    parity["onset_decision_mismatches"] = int(np.size(onset_equal) - np.sum(onset_equal))
    parity["data_split"] = export_check_split
    parity["examples"] = int(len(audio))
    parity["policy"] = parity_policy_report()
    parity["passed"] = parity_passes(parity)
    if not parity["passed"]:
        raise RuntimeError(f"TFLite parity failed: {parity}")
    np.savez_compressed(
        output_dir / "parity_examples.npz",
        audio=audio,
        time_mask=mask,
        **{f"tflite_{name}": value for name, value in actual_all.items()},
    )
    hop_budget_ms = 256 / 44_100 * 1000.0
    tflite_latency = _benchmark(
        tflite_path, audio, mask, hop_budget_ms=hop_budget_ms
    )
    recommended_threads = tflite_latency["recommended_threads"]
    recommended = str(recommended_threads) if recommended_threads else None
    recommended_p95 = (
        float(tflite_latency["threads"][recommended]["p95_ms"])
        if recommended else None
    )
    tflite_latency["recommended_p95_ms"] = recommended_p95
    tflite_latency["meets_hop_budget_p95"] = bool(
        recommended_p95 is not None and recommended_p95 <= hop_budget_ms
    )
    latency = {
        "hop_budget_ms": hop_budget_ms,
        "data_split": export_check_split,
        "tflite": tflite_latency,
        "passed": bool(tflite_latency["meets_hop_budget_p95"]),
    }
    metadata = {
        "product_version": "2.2.1",
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
        "recommended_android_tflite_threads": 1,
        "tflite_weight_quantization": "float16",
        "tflite_io_dtype": "float32",
        "export_checks_split": export_check_split,
        "decoder_runtime_policy": {
            "unattacked_frame_threshold_enforced": True,
            "recent_physical_attack_uses_frame_on_threshold": True,
            "pitch_specific_model_onset_remains_available": True,
            "decision": "accepted_for_desktop_anti_ghost",
            "locked_test_used": False,
        },
        "audio_evidence": {
            "fft_size": 512,
            "onset_cooldown_ms": 80.0,
            "onset_rearm_ratio": 1.35,
            "onset_rearm_stable_hops": 3,
            "onset_rearm_attack_ratio": 3.0,
            "onset_rearm_flux_ratio": 2.0,
            "onset_rearm_growth_ratio": 8.0,
            "require_joint_temporal_evidence": True,
            "continuity_warmup_hops": 2,
        },
        "automatic_model_input_level": {
            "enabled_by_default": False,
            "target_capture_peak_dbfs": -12.0,
            "minimum_gain_db": 0.0,
            "maximum_gain_db": 18.0,
            "recovery_db_per_second": 1.0,
            "model_headroom_peak": 0.98,
            "domain": "model_input_only_after_manual_capture_gain",
            "session_policy": "amplification_only_opt_in",
            "safety_attenuation_enabled": True,
            "default_decision": (
                "disabled_after_validation_due_to_false_positive_"
                "and_fragmentation_regression"
            ),
        },
        "manual_audio_gain": {
            "domain": "before_audio_evidence_recording_and_model",
            "default": 1.0,
        },
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
