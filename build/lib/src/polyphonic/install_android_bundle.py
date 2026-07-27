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
