from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "guitar_midi_v1_0_0"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
CONTRACT = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "guitarmidi" / "ai" / "Contract.kt"


class AndroidContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metadata = json.loads((ARTIFACT / "metadata.json").read_text(encoding="utf-8"))
        cls.source = CONTRACT.read_text(encoding="utf-8")

    def constant(self, name: str) -> str:
        match = re.search(rf"const val {name} = ([^\n]+)", self.source)
        self.assertIsNotNone(match, name)
        return match.group(1).strip().rstrip("f").strip('"')

    def test_scalar_contract_matches_product_metadata(self) -> None:
        pairs = {
            "PRODUCT_VERSION": ("product_version", str),
            "SAMPLE_RATE": ("sample_rate", int),
            "HOP": ("hop_samples", int),
            "WINDOW": ("max_window_samples", int),
            "MIN_PITCH": ("min_pitch", int),
            "MAX_PITCH": ("max_pitch", int),
        }
        for kotlin, (metadata, cast) in pairs.items():
            self.assertEqual(cast(self.constant(kotlin)), self.metadata[metadata])
        floats = {
            "NORMALIZATION_GAIN": "normalization_gain",
            "ACTIVE_THRESHOLD": "active_threshold",
            "TRANSITION_THRESHOLD": "transition_threshold",
            "MINIMUM_RETRIGGER_MS": "minimum_retrigger_ms",
        }
        for kotlin, metadata in floats.items():
            self.assertAlmostEqual(float(self.constant(kotlin)), self.metadata[metadata], places=6)

    def test_feature_order_matches(self) -> None:
        block = self.source.split("val FEATURE_NAMES = arrayOf(", 1)[1].split(")", 1)[0]
        names = re.findall(r'"([a-z_]+)"', block)
        self.assertEqual(names, self.metadata["feature_names"])

    def test_android_assets_are_exact_verified_models(self) -> None:
        artifacts = self.metadata["artifacts"]
        for name, hash_name in (
            ("guitar_midi_pitch.tflite", "pitch_sha256"),
            ("guitar_midi_transition_gate.tflite", "transition_gate_sha256"),
        ):
            digest = hashlib.sha256((ASSETS / name).read_bytes()).hexdigest()
            self.assertEqual(digest, artifacts[hash_name])


if __name__ == "__main__":
    unittest.main()
