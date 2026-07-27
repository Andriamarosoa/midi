"""Verify ONNX Runtime against the already accepted TFLite signatures."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np

from src.product.export_models import (
    PITCH_OUTPUTS,
    load_gate_examples,
    load_pitch_examples,
    sha256,
    tflite_signature,
)


def make_session(path: Path, threads: int):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(
        str(path), sess_options=options, providers=["CPUExecutionProvider"]
    )


def identify_pitch_outputs(
    output_names: list[str],
    values: dict[str, np.ndarray],
    expected: dict[str, np.ndarray],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    unresolved_outputs = set(output_names)
    for target in ("active", "pitch"):
        shape = expected[target].shape[1:]
        candidates = [
            name for name in unresolved_outputs if values[name].shape[1:] == shape
        ]
        if len(candidates) != 1:
            raise ValueError(f"Sortie ONNX {target} ambigue: {candidates}")
        mapping[target] = candidates[0]
        unresolved_outputs.remove(candidates[0])
    harmonic_targets = ("harmonic_amplitude", "harmonic_offset_cents")
    best = min(
        itertools.permutations(unresolved_outputs, len(harmonic_targets)),
        key=lambda names: sum(
            float(np.mean(np.abs(expected[target] - values[name])))
            for target, name in zip(harmonic_targets, names)
        ),
    )
    mapping.update(dict(zip(harmonic_targets, best)))
    return mapping


def benchmark(path: Path, inputs: dict[str, np.ndarray]) -> dict[str, object]:
    report: dict[str, object] = {}
    for threads in (1, 2, 4):
        session = make_session(path, threads)
        names = {value.name: value.shape for value in session.get_inputs()}
        feed = {}
        for name, shape in names.items():
            if list(shape) == [1, 4096, 1]:
                feed[name] = inputs["audio"][:1]
            elif list(shape) == [1, 4096]:
                feed[name] = inputs["time_mask"][:1]
            elif list(shape) == [1, 20]:
                feed[name] = inputs["features"][:1]
            else:
                raise ValueError(f"Entree ONNX inattendue: {name} {shape}")
        for _ in range(20):
            session.run(None, feed)
        timings = []
        for _ in range(300):
            started = time.perf_counter()
            session.run(None, feed)
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


def verify(
    artifact_dir: Path,
    pitch_manifest: Path,
    gate_manifest: Path,
) -> dict[str, object]:
    import onnx

    metadata_path = artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    gain = float(metadata["normalization_gain"])
    pitch_audio, pitch_mask = load_pitch_examples(pitch_manifest, gain, limit=96)
    gate_features = load_gate_examples(gate_manifest, limit=512)
    pitch_tflite = artifact_dir / metadata["artifacts"]["pitch_tflite"]
    gate_tflite = artifact_dir / metadata["artifacts"]["transition_gate_tflite"]
    pitch_onnx = artifact_dir / "guitar_midi_pitch.onnx"
    gate_onnx = artifact_dir / "guitar_midi_transition_gate.onnx"
    for path in (pitch_onnx, gate_onnx):
        onnx.checker.check_model(onnx.load(str(path)))

    _, pitch_lite_runner = tflite_signature(pitch_tflite, 1)
    pitch_expected_parts = {name: [] for name in PITCH_OUTPUTS}
    for index in range(len(pitch_audio)):
        result = pitch_lite_runner(
            audio=pitch_audio[index:index + 1],
            time_mask=pitch_mask[index:index + 1],
        )
        for name in PITCH_OUTPUTS:
            pitch_expected_parts[name].append(np.asarray(result[name]))
    pitch_expected = {
        name: np.concatenate(values) for name, values in pitch_expected_parts.items()
    }

    pitch_session = make_session(pitch_onnx, 1)
    pitch_input_names = {value.name: value.shape for value in pitch_session.get_inputs()}
    pitch_output_names = [value.name for value in pitch_session.get_outputs()]
    onnx_parts = {name: [] for name in pitch_output_names}
    for index in range(len(pitch_audio)):
        feed = {}
        for name, shape in pitch_input_names.items():
            feed[name] = (
                pitch_audio[index:index + 1]
                if list(shape) == [1, 4096, 1]
                else pitch_mask[index:index + 1]
            )
        outputs = pitch_session.run(None, feed)
        for name, value in zip(pitch_output_names, outputs):
            onnx_parts[name].append(np.asarray(value))
    pitch_actual_raw = {
        name: np.concatenate(values) for name, values in onnx_parts.items()
    }
    mapping = identify_pitch_outputs(
        pitch_output_names, pitch_actual_raw, pitch_expected
    )
    pitch_metrics = {}
    for target, output_name in mapping.items():
        difference = np.abs(pitch_expected[target] - pitch_actual_raw[output_name])
        pitch_metrics[target] = {
            "onnx_output": output_name,
            "max_absolute_error": float(np.max(difference)),
            "mean_absolute_error": float(np.mean(difference)),
        }
    pitch_metrics["pitch_argmax_agreement"] = float(np.mean(
        np.argmax(pitch_expected["pitch"], axis=1)
        == np.argmax(pitch_actual_raw[mapping["pitch"]], axis=1)
    ))
    active_threshold = float(metadata["active_threshold"])
    pitch_metrics["active_decision_agreement"] = float(np.mean(
        (pitch_expected["active"].reshape(-1) >= active_threshold)
        == (pitch_actual_raw[mapping["active"]].reshape(-1) >= active_threshold)
    ))

    _, gate_lite_runner = tflite_signature(gate_tflite, 1)
    gate_expected = np.concatenate([
        np.asarray(gate_lite_runner(features=gate_features[index:index + 1])[
            "allow_transition"
        ]).reshape(-1)
        for index in range(len(gate_features))
    ])
    gate_session = make_session(gate_onnx, 1)
    gate_input = gate_session.get_inputs()[0].name
    gate_actual = np.concatenate([
        np.asarray(gate_session.run(None, {
            gate_input: gate_features[index:index + 1]
        })[0]).reshape(-1)
        for index in range(len(gate_features))
    ])
    gate_difference = np.abs(gate_expected - gate_actual)
    transition_threshold = float(metadata["transition_threshold"])
    gate_metrics = {
        "max_absolute_error": float(np.max(gate_difference)),
        "mean_absolute_error": float(np.mean(gate_difference)),
        "decision_agreement": float(np.mean(
            (gate_expected >= transition_threshold)
            == (gate_actual >= transition_threshold)
        )),
    }
    passed = bool(
        pitch_metrics["pitch_argmax_agreement"] == 1.0
        and pitch_metrics["active_decision_agreement"] == 1.0
        and gate_metrics["decision_agreement"] == 1.0
        and max(
            pitch_metrics[name]["max_absolute_error"] for name in PITCH_OUTPUTS
        ) < 1e-3
        and gate_metrics["max_absolute_error"] < 1e-3
    )
    latency = {
        "pitch_onnx": benchmark(
            pitch_onnx, {"audio": pitch_audio, "time_mask": pitch_mask}
        ),
        "transition_gate_onnx": benchmark(
            gate_onnx, {"features": gate_features}
        ),
    }
    report = {
        "opset": 18,
        "pitch_examples": len(pitch_audio),
        "gate_examples": len(gate_features),
        "pitch": pitch_metrics,
        "transition_gate": gate_metrics,
        "latency": latency,
        "passed": passed,
    }
    if not passed:
        raise RuntimeError(f"Parite ONNX insuffisante: {report}")
    (artifact_dir / "onnx_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    metadata["artifacts"].update({
        "pitch_onnx": pitch_onnx.name,
        "transition_gate_onnx": gate_onnx.name,
        "pitch_onnx_sha256": sha256(pitch_onnx),
        "transition_gate_onnx_sha256": sha256(gate_onnx),
    })
    metadata["validation"]["onnx_report"] = "onnx_report.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--pitch-manifest", type=Path,
        default=Path("data/dataset/v6_0_active/manifest.csv"),
    )
    parser.add_argument(
        "--gate-manifest", type=Path,
        default=Path("data/dataset/v6_3_3_transition_utility/manifest.csv"),
    )
    args = parser.parse_args()
    print(json.dumps(verify(
        args.artifact_dir, args.pitch_manifest, args.gate_manifest
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
