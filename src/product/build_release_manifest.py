"""Create the final cryptographic and validation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_dir.resolve()
    wav = json.loads((root / "wav_pipeline_report.json").read_text(encoding="utf-8"))
    parity = json.loads((root / "parity_report.json").read_text(encoding="utf-8"))
    onnx = json.loads((root / "onnx_report.json").read_text(encoding="utf-8"))
    backpressure = json.loads((root / "backpressure_report.json").read_text(encoding="utf-8"))
    hardware = json.loads((root / "hardware_live_report_20s.json").read_text(encoding="utf-8"))
    wav_smoke = json.loads((root / "external_smoke_guitar_techs.json").read_text(encoding="utf-8"))
    files = [
        "guitar_midi_pitch.tflite",
        "guitar_midi_transition_gate.tflite",
        "guitar_midi_pitch.onnx",
        "guitar_midi_transition_gate.onnx",
        "midi-1.0.0-py3-none-any.whl",
        "external_smoke_guitar_techs.wav",
        "external_smoke_guitar_techs.mid",
        "external_smoke_guitar_techs.json",
    ]
    manifest = {
        "product": "Guitar MIDI AI",
        "version": "1.0.0",
        "scope": "causal clean monophonic guitar MIDI 40-76",
        "profile": "safe_low_ghost",
        "artifacts": {
            name: {"bytes": (root / name).stat().st_size, "sha256": digest(root / name)}
            for name in files
        },
        "acceptance": {
            "tflite_parity": bool(parity["passed"]),
            "onnx_parity": bool(onnx["passed"]),
            "backpressure": bool(backpressure["accepted_for_product"]),
            "wav_safe_profile": bool(wav["accepted_for_product"]),
            "wav_strict_regression": bool(wav["strict_regression_accepted"]),
            "hardware_no_audio_drop": hardware["audio_hops_dropped"] == 0,
            "hardware_skip_within_validated_limit": (
                hardware["inference_skip_percent"]
                <= backpressure["max_inference_skip_percent"]
            ),
            "wav_cli_smoke": (
                wav_smoke["note_on_events"] > 0
                and (root / "external_smoke_guitar_techs.mid").read_bytes().startswith(b"MThd")
                and (root / "external_smoke_guitar_techs.mid").read_bytes().endswith(b"\x00\xff\x2f\x00")
            ),
        },
        "known_limits": [
            "Single pitch softmax: no simultaneous chord transcription.",
            "Safe profile can merge rapid repetitions of the same MIDI pitch.",
            "IDMT D2 is outside the guaranteed domain.",
        ],
    }
    required = [
        value for name, value in manifest["acceptance"].items()
        if name != "wav_strict_regression"
    ]
    manifest["release_ready_for_declared_scope"] = bool(all(required))
    output = root / "release_manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["release_ready_for_declared_scope"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
