"""Export the accepted V6.0 + V6.3.3 stack and verify numerical parity."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from src.product import PRODUCT_VERSION
from src.product.contracts import FEATURE_NAMES, PITCH_OUTPUTS
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pitch_examples(
    manifest: Path, gain: float, limit: int = 96
) -> tuple[np.ndarray, np.ndarray]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "test"]
    audio_parts: list[np.ndarray] = []
    mask_parts: list[np.ndarray] = []
    per_source = max(1, int(np.ceil(limit / max(len(rows), 1))))
    for row in rows:
        with np.load(Path(row["npz_path"])) as data:
            count = min(per_source, len(data["audio"]))
            if count == 0:
                continue
            indices = np.linspace(0, len(data["audio"]) - 1, count).astype(int)
            audio = np.asarray(data["audio"][indices], dtype=np.float32).copy()
            visible = np.asarray(data["visible_window"][indices], dtype=np.int32)
        masks = np.zeros_like(audio, dtype=np.float32)
        for index, window in enumerate(visible):
            window = int(np.clip(window, 1, audio.shape[1]))
            audio[index, :-window] = 0.0
            masks[index, -window:] = 1.0
        audio *= float(gain)
        np.clip(audio, -1.0, 1.0, out=audio)
        audio_parts.append(audio[..., None])
        mask_parts.append(masks)
        if sum(len(value) for value in audio_parts) >= limit:
            break
    if not audio_parts:
        raise ValueError("Aucun exemple pitch disponible pour la parite.")
    return (
        np.concatenate(audio_parts)[:limit],
        np.concatenate(mask_parts)[:limit],
    )


def load_gate_examples(manifest: Path, limit: int = 512) -> np.ndarray:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "test"]
    parts: list[np.ndarray] = []
    for row in rows:
        with np.load(Path(row["npz_path"])) as data:
            parts.append(np.asarray(data["features"], dtype=np.float32))
        if sum(len(value) for value in parts) >= limit:
            break
    if not parts:
        raise ValueError("Aucun exemple gate disponible pour la parite.")
    return np.concatenate(parts)[:limit]


def tflite_signature(path: Path, threads: int = 1):
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(path), num_threads=threads)
    interpreter.allocate_tensors()
    signatures = interpreter.get_signature_list()
    if "serving_default" not in signatures:
        raise ValueError(f"Signature serving_default absente: {signatures}")
    return interpreter, interpreter.get_signature_runner("serving_default")


def benchmark_tflite(
    path: Path,
    inputs: dict[str, np.ndarray],
    repeats: int = 300,
) -> dict[str, object]:
    report: dict[str, object] = {}
    for threads in (1, 2, 4):
        _, runner = tflite_signature(path, threads)
        sample = {name: value[:1] for name, value in inputs.items()}
        for _ in range(20):
            runner(**sample)
        timings: list[float] = []
        for _ in range(repeats):
            started = time.perf_counter()
            runner(**sample)
            timings.append((time.perf_counter() - started) * 1000.0)
        values = np.asarray(timings, dtype=np.float64)
        report[str(threads)] = {
            "mean_ms": float(np.mean(values)),
            "p50_ms": float(np.percentile(values, 50.0)),
            "p95_ms": float(np.percentile(values, 95.0)),
            "max_ms": float(np.max(values)),
        }
    best = min(report, key=lambda key: (report[key]["p95_ms"], report[key]["mean_ms"]))
    return {"threads": report, "recommended_threads": int(best)}


def export(
    v60_run: Path,
    gate_run: Path,
    output_dir: Path,
    pitch_manifest: Path,
    gate_manifest: Path,
) -> dict[str, object]:
    import tensorflow as tf

    if output_dir.exists():
        raise FileExistsError(
            f"Sortie deja presente; choisir un nouveau dossier: {output_dir}"
        )
    output_dir.mkdir(parents=True)
    v60_selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    gate_selection = json.loads(
        (gate_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    decoder_selection = json.loads(
        (gate_run / "decoder_threshold_selection.json").read_text(encoding="utf-8")
    )
    config = json.loads((v60_run / "config.json").read_text(encoding="utf-8"))
    dataset = config["dataset"]
    gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    pitch_model = tf.keras.models.load_model(
        v60_run / v60_selection["selected_checkpoint"], compile=False
    )
    gate_model = tf.keras.models.load_model(
        gate_run / gate_selection["selected_checkpoint"], compile=False
    )

    class PitchModule(tf.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        @tf.function(input_signature=[
            tf.TensorSpec((1, 4096, 1), tf.float32, name="audio"),
            tf.TensorSpec((1, 4096), tf.float32, name="time_mask"),
        ])
        def infer(self, audio, time_mask):
            values = self.model(
                {"audio": audio, "time_mask": time_mask}, training=False
            )
            return {name: tf.identity(values[name], name=name) for name in PITCH_OUTPUTS}

    class GateModule(tf.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        @tf.function(input_signature=[
            tf.TensorSpec((1, len(FEATURE_NAMES)), tf.float32, name="features"),
        ])
        def infer(self, features):
            return {"allow_transition": tf.identity(
                self.model(features, training=False), name="allow_transition"
            )}

    pitch_module = PitchModule(pitch_model)
    gate_module = GateModule(gate_model)
    pitch_concrete = pitch_module.infer.get_concrete_function()
    gate_concrete = gate_module.infer.get_concrete_function()
    pitch_saved = output_dir / "saved_model_pitch"
    gate_saved = output_dir / "saved_model_transition_gate"
    tf.saved_model.save(
        pitch_module, str(pitch_saved), signatures={"serving_default": pitch_concrete}
    )
    tf.saved_model.save(
        gate_module, str(gate_saved), signatures={"serving_default": gate_concrete}
    )

    def convert(module, concrete, destination: Path, optimize: bool) -> None:
        converter = tf.lite.TFLiteConverter.from_concrete_functions(
            [concrete], module
        )
        if optimize:
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        destination.write_bytes(converter.convert())

    pitch_tflite = output_dir / "guitar_midi_pitch.tflite"
    gate_tflite = output_dir / "guitar_midi_transition_gate.tflite"
    convert(pitch_module, pitch_concrete, pitch_tflite, optimize=False)
    convert(gate_module, gate_concrete, gate_tflite, optimize=True)

    pitch_audio, pitch_mask = load_pitch_examples(pitch_manifest, gain)
    gate_features = load_gate_examples(gate_manifest)
    pitch_tf = pitch_model(
        {"audio": pitch_audio, "time_mask": pitch_mask}, training=False
    )
    _, pitch_runner = tflite_signature(pitch_tflite, 4)
    pitch_lite_parts = {name: [] for name in PITCH_OUTPUTS}
    for index in range(len(pitch_audio)):
        values = pitch_runner(
            audio=pitch_audio[index:index + 1],
            time_mask=pitch_mask[index:index + 1],
        )
        for name in PITCH_OUTPUTS:
            pitch_lite_parts[name].append(np.asarray(values[name]))
    pitch_lite = {
        name: np.concatenate(values) for name, values in pitch_lite_parts.items()
    }
    pitch_parity = {}
    for name in PITCH_OUTPUTS:
        expected = np.asarray(pitch_tf[name], dtype=np.float32)
        actual = pitch_lite[name]
        difference = np.abs(expected - actual)
        pitch_parity[name] = {
            "max_absolute_error": float(np.max(difference)),
            "mean_absolute_error": float(np.mean(difference)),
        }
    pitch_parity["pitch_argmax_agreement"] = float(np.mean(
        np.argmax(np.asarray(pitch_tf["pitch"]), axis=1)
        == np.argmax(pitch_lite["pitch"], axis=1)
    ))
    active_threshold = float(v60_selection["active_threshold"])
    pitch_parity["active_decision_agreement"] = float(np.mean(
        (np.asarray(pitch_tf["active"]).reshape(-1) >= active_threshold)
        == (pitch_lite["active"].reshape(-1) >= active_threshold)
    ))

    gate_tf = np.asarray(gate_model(gate_features, training=False)).reshape(-1)
    _, gate_runner = tflite_signature(gate_tflite, 1)
    gate_lite = np.concatenate([
        np.asarray(gate_runner(features=gate_features[index:index + 1])[
            "allow_transition"
        ]).reshape(-1)
        for index in range(len(gate_features))
    ])
    gate_difference = np.abs(gate_tf - gate_lite)
    gate_threshold = float(decoder_selection["decoder_transition_threshold"])
    gate_parity = {
        "max_absolute_error": float(np.max(gate_difference)),
        "mean_absolute_error": float(np.mean(gate_difference)),
        "decision_agreement": float(np.mean(
            (gate_tf >= gate_threshold) == (gate_lite >= gate_threshold)
        )),
    }
    parity = {
        "pitch_examples": len(pitch_audio),
        "gate_examples": len(gate_features),
        "pitch": pitch_parity,
        "transition_gate": gate_parity,
        "passed": bool(
            pitch_parity["pitch_argmax_agreement"] == 1.0
            and pitch_parity["active_decision_agreement"] == 1.0
            and gate_parity["decision_agreement"] == 1.0
            and max(
                pitch_parity[name]["max_absolute_error"] for name in PITCH_OUTPUTS
            ) < 0.01
            and gate_parity["max_absolute_error"] < 0.01
        ),
    }
    if not parity["passed"]:
        raise RuntimeError(f"Parite TFLite insuffisante: {parity}")
    latency = {
        "hop_budget_ms": int(dataset["hop_size"]) / int(dataset["sample_rate"]) * 1000.0,
        "pitch_tflite": benchmark_tflite(
            pitch_tflite, {"audio": pitch_audio, "time_mask": pitch_mask}
        ),
        "transition_gate_tflite": benchmark_tflite(
            gate_tflite, {"features": gate_features}
        ),
    }
    metadata = {
        "product_version": PRODUCT_VERSION,
        "model_stack": "V6.0 pitch-active-harmonics + V6.3.3 transition utility gate",
        "sample_rate": int(dataset["sample_rate"]),
        "hop_samples": int(dataset["hop_size"]),
        "max_window_samples": int(dataset["max_window"]),
        "progressive_windows": [512, 1024, 2048, 4096],
        "normalization_gain": gain,
        "min_pitch": int(dataset["min_pitch"]),
        "max_pitch": int(dataset["max_pitch"]),
        "active_threshold": active_threshold,
        "transition_threshold": gate_threshold,
        "stability_frames": 2,
        "minimum_retrigger_ms": 80.0,
        "feature_names": list(FEATURE_NAMES),
        "pitch_outputs": list(PITCH_OUTPUTS),
        "artifacts": {
            "pitch_tflite": pitch_tflite.name,
            "transition_gate_tflite": gate_tflite.name,
            "pitch_sha256": sha256(pitch_tflite),
            "transition_gate_sha256": sha256(gate_tflite),
        },
        "recommended_tflite_threads": latency["pitch_tflite"]["recommended_threads"],
        "validation": {
            "decoder_report": str(
                gate_run / "continuous_transition_gate_ablation" / "aggregate.json"
            ),
            "tflite_parity_report": "parity_report.json",
            "latency_report": "latency_report.json",
        },
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument("--gate-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--pitch-manifest", type=Path,
        default=Path("data/dataset/v6_0_active/manifest.csv"),
    )
    parser.add_argument(
        "--gate-manifest", type=Path,
        default=Path("data/dataset/v6_3_3_transition_utility/manifest.csv"),
    )
    args = parser.parse_args()
    print(json.dumps(export(
        args.v60_run.resolve(), args.gate_run.resolve(), args.output_dir,
        args.pitch_manifest, args.gate_manifest,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
