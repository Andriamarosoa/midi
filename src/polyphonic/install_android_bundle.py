"""Install one fully verified polyphonic artifact bundle into Android assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def install(artifacts: Path, assets: Path) -> dict[str, object]:
    metadata_path = artifacts / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    parity = json.loads(
        (artifacts / "parity_report.json").read_text(encoding="utf-8")
    )
    latency = json.loads(
        (artifacts / "latency_report.json").read_text(encoding="utf-8")
    )
    onnx = json.loads(
        (artifacts / "onnx_report.json").read_text(encoding="utf-8")
    )
    acceptance = json.loads(
        (artifacts / "runtime_acceptance.json").read_text(encoding="utf-8")
    )
    if not parity.get("passed"):
        raise ValueError("TFLite parity has not passed.")
    if not latency.get("passed"):
        raise ValueError("TFLite p95 does not meet the causal hop budget.")
    if not onnx.get("passed"):
        raise ValueError("ONNX parity has not passed.")
    artifact = metadata["artifact"]
    model = artifacts / artifact["tflite"]
    if _sha256(model) != artifact["sha256"]:
        raise ValueError("TFLite SHA256 mismatch.")
    onnx_model = artifacts / artifact["onnx"]
    if _sha256(onnx_model) != artifact["onnx_sha256"]:
        raise ValueError("ONNX SHA256 mismatch.")
    if Path(str(metadata.get("source_checkpoint", ""))).name != "selected.keras":
        raise ValueError("Android bundle is not based on selected.keras.")
    runtime_validation = metadata.get("runtime_validation")
    if not isinstance(runtime_validation, dict):
        raise ValueError("Runtime validation metadata is missing.")
    if (
        runtime_validation.get("decision") != "accepted_on_validation"
        or runtime_validation.get("locked_test_used") is not False
        or runtime_validation.get("thresholds_reselected") is not False
    ):
        raise ValueError("Runtime format was not accepted on validation only.")
    if (
        acceptance.get("accepted") is not True
        or acceptance.get("selected_on") != "validation"
        or acceptance.get("locked_test_used") is not False
        or acceptance.get("thresholds_reselected") is not False
        or acceptance.get("tflite_sha256") != artifact["sha256"]
    ):
        raise ValueError("Runtime acceptance is invalid or test-contaminated.")
    frame_report_path = artifacts / runtime_validation["frame_report"]
    event_report_path = artifacts / runtime_validation["event_report"]
    if _sha256(frame_report_path) != acceptance["frame_report_sha256"]:
        raise ValueError("Frame validation report SHA256 mismatch.")
    if _sha256(event_report_path) != acceptance["event_report_sha256"]:
        raise ValueError("Event validation report SHA256 mismatch.")
    frame_report = json.loads(frame_report_path.read_text(encoding="utf-8"))
    event_report = json.loads(event_report_path.read_text(encoding="utf-8"))
    if (
        frame_report.get("split") != "validation"
        or frame_report.get("locked_test_used") is not False
        or frame_report.get("thresholds_reselected") is not False
        or frame_report.get("tflite_sha256") != artifact["sha256"]
    ):
        raise ValueError("Frame validation is invalid or test-contaminated.")
    frame_acceptance = acceptance.get("frame_validation", {})
    if not frame_acceptance.get("musical_guardrails_passed"):
        raise ValueError("Frame-level musical guardrails have not passed.")
    if not frame_report.get("passed") and not frame_acceptance.get(
        "numerical_outlier_exception_reviewed"
    ):
        raise ValueError("Frame numerical exception was not reviewed.")
    if (
        event_report.get("passed") is not True
        or event_report.get("split") != "validation"
        or event_report.get("locked_test_used") is not False
        or event_report.get("thresholds_reselected") is not False
        or event_report.get("tflite_sha256") != artifact["sha256"]
    ):
        raise ValueError("Event validation has not passed cleanly.")

    assets.mkdir(parents=True, exist_ok=True)
    target_model = assets / "guitar_midi_polyphonic.tflite"
    target_metadata = assets / "polyphonic_metadata.json"
    shutil.copy2(model, target_model)
    shutil.copy2(metadata_path, target_metadata)
    report = {
        "artifacts": str(artifacts),
        "assets": str(assets),
        "model": str(target_model),
        "metadata": str(target_metadata),
        "sha256": _sha256(target_model),
        "product_version": metadata["product_version"],
        "parity_passed": True,
        "latency_passed": True,
        "onnx_passed": True,
        "runtime_validation_passed": True,
        "numerical_outlier_exception_reviewed": bool(
            frame_acceptance.get("numerical_outlier_exception_reviewed")
        ),
    }
    (assets / "polyphonic_install_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--assets", type=Path,
        default=Path("android/app/src/main/assets"),
    )
    args = parser.parse_args()
    print(json.dumps(install(args.artifacts, args.assets), indent=2))


if __name__ == "__main__":
    main()
