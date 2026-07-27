from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.polyphonic.install_android_bundle import install


class AndroidPolyphonicInstallTests(unittest.TestCase):
    def test_only_complete_verified_bundle_is_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            assets = root / "assets"
            artifacts.mkdir()
            tflite = artifacts / "guitar_midi_polyphonic.tflite"
            onnx = artifacts / "guitar_midi_polyphonic.onnx"
            tflite.write_bytes(b"tflite")
            onnx.write_bytes(b"onnx")
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            frame_report = artifacts / "validation_runtime_fp16_60k.json"
            event_report = artifacts / "validation_runtime_events_fp16.json"
            frame_report.write_text(json.dumps({
                "split": "validation", "locked_test_used": False,
                "thresholds_reselected": False,
                "tflite_sha256": sha(tflite), "passed": False,
            }), encoding="utf-8")
            event_report.write_text(json.dumps({
                "split": "validation", "locked_test_used": False,
                "thresholds_reselected": False,
                "tflite_sha256": sha(tflite), "passed": True,
            }), encoding="utf-8")
            (artifacts / "metadata.json").write_text(json.dumps({
                "product_version": "2.2.0",
                "source_checkpoint": "run/selected.keras",
                "runtime_validation": {
                    "decision": "accepted_on_validation",
                    "locked_test_used": False,
                    "thresholds_reselected": False,
                    "frame_report": frame_report.name,
                    "event_report": event_report.name,
                },
                "artifact": {
                    "tflite": tflite.name, "sha256": sha(tflite),
                    "onnx": onnx.name, "onnx_sha256": sha(onnx),
                },
            }), encoding="utf-8")
            (artifacts / "runtime_acceptance.json").write_text(json.dumps({
                "accepted": True,
                "selected_on": "validation",
                "locked_test_used": False,
                "thresholds_reselected": False,
                "tflite_sha256": sha(tflite),
                "frame_report_sha256": sha(frame_report),
                "event_report_sha256": sha(event_report),
                "frame_validation": {
                    "musical_guardrails_passed": True,
                    "numerical_outlier_exception_reviewed": True,
                },
            }), encoding="utf-8")
            for name, value in (
                ("parity_report.json", {"passed": True}),
                ("latency_report.json", {"passed": True}),
                ("onnx_report.json", {"passed": True}),
            ):
                (artifacts / name).write_text(json.dumps(value), encoding="utf-8")
            report = install(artifacts, assets)
            self.assertEqual(
                (assets / "guitar_midi_polyphonic.tflite").read_bytes(), b"tflite"
            )
            self.assertEqual(report["sha256"], sha(tflite))
            self.assertTrue(report["runtime_validation_passed"])

    def test_latency_failure_prevents_asset_directory_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            assets = root / "assets"
            artifacts.mkdir()
            (artifacts / "metadata.json").write_text("{}", encoding="utf-8")
            (artifacts / "parity_report.json").write_text(
                '{"passed": true}', encoding="utf-8"
            )
            (artifacts / "latency_report.json").write_text(
                '{"passed": false}', encoding="utf-8"
            )
            (artifacts / "onnx_report.json").write_text(
                '{"passed": true}', encoding="utf-8"
            )
            (artifacts / "runtime_acceptance.json").write_text(
                '{"accepted": false}', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "hop budget"):
                install(artifacts, assets)
            self.assertFalse(assets.exists())


if __name__ == "__main__":
    unittest.main()
