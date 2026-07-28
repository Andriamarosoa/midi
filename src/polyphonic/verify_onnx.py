"""Verify ONNX parity and latency against the accepted TFLite export."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import time
from pathlib import Path

import numpy as np

from src.polyphonic.runtime_parity import parity_passes, parity_policy_report


OUTPUT_NAMES = (
    "frame", "onset", "harmonic_amplitude", "harmonic_offset_cents",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _session(path: Path, threads: int):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(
        str(path), sess_options=options, providers=["CPUExecutionProvider"]
    )


def _mapping(
    raw: dict[str, np.ndarray],
    expected: dict[str, np.ndarray],
) -> dict[str, str]:
    result: dict[str, str] = {}
    groups = (("frame", "onset"), ("harmonic_amplitude", "harmonic_offset_cents"))
    available = set(raw)
    for targets in groups:
        shape = expected[targets[0]].shape[1:]
        candidates = [name for name in available if raw[name].shape[1:] == shape]
        if len(candidates) != len(targets):
            raise ValueError(f"Ambiguous ONNX outputs for {targets}: {candidates}")
        best = min(
            itertools.permutations(candidates),
            key=lambda names: sum(
                float(np.mean(np.abs(expected[target] - raw[name])))
                for target, name in zip(targets, names)
            ),
        )
        for target, name in zip(targets, best):
            result[target] = name
            available.remove(name)
    return result


def _feed(session, audio: np.ndarray, mask: np.ndarray) -> dict[str, np.ndarray]:
    feed = {}
    for item in session.get_inputs():
        shape = list(item.shape)
        if len(shape) == 3 and shape[0] == 1 and shape[-1] == 1:
            if shape[1] != audio.shape[1]:
                raise ValueError(
                    f"ONNX audio length {shape[1]} != {audio.shape[1]}"
                )
            feed[item.name] = audio
        elif len(shape) == 2 and shape[0] == 1:
            if shape[1] != mask.shape[1]:
                raise ValueError(
                    f"ONNX mask length {shape[1]} != {mask.shape[1]}"
                )
            feed[item.name] = mask
        else:
            raise ValueError(f"Unexpected ONNX input: {item.name} {item.shape}")
    return feed


def verify(artifact_dir: Path) -> dict[str, object]:
    import onnx

    metadata_path = artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    onnx_path = artifact_dir / "guitar_midi_polyphonic.onnx"
    onnx.checker.check_model(onnx.load(str(onnx_path)))
    with np.load(artifact_dir / metadata["artifact"]["parity_examples"]) as data:
        audio = np.asarray(data["audio"], np.float32)
        mask = np.asarray(data["time_mask"], np.float32)
        expected = {
            name: np.asarray(data[f"tflite_{name}"], np.float32)
            for name in OUTPUT_NAMES
        }
    session = _session(onnx_path, 1)
    output_names = [item.name for item in session.get_outputs()]
    parts = {name: [] for name in output_names}
    for index in range(len(audio)):
        values = session.run(None, _feed(
            session, audio[index:index + 1], mask[index:index + 1]
        ))
        for name, value in zip(output_names, values):
            parts[name].append(np.asarray(value))
    raw = {name: np.concatenate(values) for name, values in parts.items()}
    mapping = _mapping(raw, expected)
    metrics: dict[str, object] = {}
    for target, output_name in mapping.items():
        difference = np.abs(expected[target] - raw[output_name])
        metrics[target] = {
            "onnx_output": output_name,
            "maximum_absolute_error": float(np.max(difference)),
            "mean_absolute_error": float(np.mean(difference)),
        }
    frame_threshold = float(metadata["frame_threshold"])
    onset_threshold = float(metadata["onset_threshold"])
    frame_equal = (
        (expected["frame"] >= frame_threshold)
        == (raw[mapping["frame"]] >= frame_threshold)
    )
    onset_equal = (
        (expected["onset"] >= onset_threshold)
        == (raw[mapping["onset"]] >= onset_threshold)
    )
    metrics["frame_decision_agreement"] = float(np.mean(frame_equal))
    metrics["frame_decision_mismatches"] = int(
        np.size(frame_equal) - np.sum(frame_equal)
    )
    metrics["onset_decision_agreement"] = float(np.mean(onset_equal))
    metrics["onset_decision_mismatches"] = int(
        np.size(onset_equal) - np.sum(onset_equal)
    )
    metrics["policy"] = parity_policy_report()
    passed = parity_passes(metrics)
    latency: dict[str, object] = {}
    for threads in (1, 2, 4):
        benchmark_session = _session(onnx_path, threads)
        feed = _feed(benchmark_session, audio[:1], mask[:1])
        for _ in range(20):
            benchmark_session.run(None, feed)
        timings = []
        for _ in range(300):
            started = time.perf_counter()
            benchmark_session.run(None, feed)
            timings.append((time.perf_counter() - started) * 1000.0)
        values = np.asarray(timings)
        latency[str(threads)] = {
            "mean_ms": float(np.mean(values)),
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "max_ms": float(np.max(values)),
        }
    recommended_threads = min(
        latency,
        key=lambda key: (latency[key]["p95_ms"], latency[key]["mean_ms"]),
    )
    hop_budget_ms = 256 / 44_100 * 1000.0
    latency_summary = {
        "threads": latency,
        "recommended_threads": int(recommended_threads),
        "recommended_p95_ms": float(
            latency[recommended_threads]["p95_ms"]
        ),
        "hop_budget_ms": hop_budget_ms,
        "meets_hop_budget_p95": bool(
            latency[recommended_threads]["p95_ms"] <= hop_budget_ms
        ),
    }
    report = {
        "opset": 18,
        "examples": len(audio),
        "outputs": metrics,
        "latency": latency_summary,
        "passed": passed,
    }
    if not passed:
        raise RuntimeError(f"ONNX parity failed: {report}")
    (artifact_dir / "onnx_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    metadata["artifact"].update({
        "onnx": onnx_path.name,
        "onnx_sha256": _sha256(onnx_path),
    })
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.artifact_dir), indent=2))


if __name__ == "__main__":
    main()
