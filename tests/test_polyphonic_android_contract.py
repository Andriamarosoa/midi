from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "guitar_midi_polyphonic_v2_2_0"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
JAVA = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "guitarmidi" / "ai"


class PolyphonicAndroidContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metadata = json.loads(
            (ARTIFACT / "metadata.json").read_text(encoding="utf-8")
        )
        cls.asset_metadata = json.loads(
            (ASSETS / "polyphonic_metadata.json").read_text(encoding="utf-8")
        )
        cls.contract = (JAVA / "PolyContract.kt").read_text(encoding="utf-8")

    def constant(self, name: str) -> str:
        match = re.search(rf"const val {name} = ([^\n]+)", self.contract)
        self.assertIsNotNone(match, name)
        return match.group(1).strip().strip('"').replace("_", "")

    def test_assets_are_the_accepted_artifact_exactly(self) -> None:
        self.assertEqual(self.asset_metadata, self.metadata)
        model = ASSETS / "guitar_midi_polyphonic.tflite"
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        self.assertEqual(digest, self.metadata["artifact"]["sha256"])
        acceptance = json.loads(
            (ARTIFACT / "runtime_acceptance.json").read_text(encoding="utf-8")
        )
        self.assertTrue(acceptance["accepted"])
        self.assertFalse(acceptance["locked_test_used"])
        self.assertEqual(acceptance["tflite_sha256"], digest)

    def test_kotlin_contract_matches_v22_metadata(self) -> None:
        pairs = {
            "PRODUCT_VERSION": ("product_version", str),
            "SAMPLE_RATE": ("sample_rate", int),
            "HOP": ("hop_samples", int),
            "WINDOW": ("max_window_samples", int),
            "MIN_PITCH": ("min_pitch", int),
            "MAX_PITCH": ("max_pitch", int),
            "MAXIMUM_POLYPHONY": ("maximum_polyphony", int),
        }
        for kotlin, (metadata, cast) in pairs.items():
            self.assertEqual(cast(self.constant(kotlin)), self.metadata[metadata])
        self.assertEqual(self.metadata["recommended_android_tflite_threads"], 1)

    def test_launcher_and_package_version_are_polyphonic_v22(self) -> None:
        manifest = (
            ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
        ).read_text(encoding="utf-8")
        gradle = (ROOT / "android" / "app" / "build.gradle.kts").read_text(
            encoding="utf-8"
        )
        self.assertIn('android:name=".PolyMainActivity"', manifest)
        self.assertNotIn('android:name=".MainActivity"', manifest)
        self.assertIn('versionName = "2.2.0"', gradle)


if __name__ == "__main__":
    unittest.main()
