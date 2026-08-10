from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


class ProvisionalResolutionFrameFallbackH21ZeroSciencePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.path = cls.root / "configs/provisional_resolution_frame_fallback_h21_zero_science_preflight.json"
        cls.raw = cls.path.read_bytes()
        cls.seal = json.loads(cls.raw)
        cls.helper_path = cls.root / "scripts/build_provisional_resolution_frame_fallback_h21_zero_science_preflight.py"
        cls.helper_source = cls.helper_path.read_text(encoding="utf-8")

    def test_status_population_and_canonical_serialization_are_exact(self):
        self.assertEqual(
            self.seal["status"],
            "provisional_resolution_frame_fallback_h21_zero_science_preflight_sealed",
        )
        population = self.seal["population"]
        self.assertEqual(population["recording_count"], 146)
        self.assertEqual(population["leakage_group_count"], 51)
        self.assertEqual(len(population["inventory"]), 146)
        self.assertEqual(population["unique_audio_path_count"], 87)
        self.assertEqual(population["unique_label_path_count"], 146)
        self.assertEqual(
            self.raw,
            (json.dumps(self.seal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        self.assertEqual(
            hashlib.sha256(self.raw).hexdigest(),
            "acb8ced104ec99afd7f6f966be17b84ce4d436e5582137b6ec6048a90dfe3331",
        )

    def test_inventory_is_exactly_the_h18a_population(self):
        h18a = json.loads(
            (self.root / "configs/provisional_resolution_frame_fallback_h18_metadata_audit.json").read_text(
                encoding="utf-8"
            )
        )["fresh_discovery_population"]
        expected = {
            record["recording_key"]: group["leakage_group_key"]
            for group in h18a["groups"]
            for record in group["recordings"]
        }
        actual = {
            record["recording_key"]: record["leakage_group_key"]
            for record in self.seal["population"]["inventory"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 146)
        required = {
            "corpus_category", "audio_member", "audio_logical_path", "audio_resolved_path",
            "audio_size_bytes", "audio_sha256", "label_logical_path", "label_resolved_path",
            "label_size_bytes", "label_sha256",
        }
        for record in self.seal["population"]["inventory"]:
            self.assertTrue(required.issubset(record))
            self.assertRegex(record["audio_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(record["label_sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(record["audio_size_bytes"], 0)
            self.assertGreater(record["label_size_bytes"], 0)

    def test_scientific_bindings_are_verified_before_asset_hashing(self):
        bindings = self.seal["bindings"]
        self.assertEqual(bindings["h20_commit"], "79c02c0aa07df4c17cda2bb4eac9fd9cf47f97c5")
        self.assertEqual(bindings["h20_contract_git_blob"], "65c64ddb031839facb26e5b9fb8b1844883449e0")
        expected_files = {
            "h17_contract_git_blob": "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json",
            "h17a_amendment_contract_git_blob": "configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json",
            "h19a_contract_git_blob": "configs/provisional_resolution_frame_fallback_h19_synthetic_conformance.json",
            "h19a_implementation_git_blob": "src/polyphonic/provisional_resolution_frame_fallback_h19.py",
            "decoder_git_blob": "src/polyphonic/decoder.py",
            "exact_causal_target_extractor_git_blob": "src/polyphonic/provisional_resolution_age1.py",
            "canonical_group_universe_engine_git_blob": "src/polyphonic/provisional_resolution_age1_metrics.py",
            "grouping_implementation_git_blob": "src/polyphonic/decoder_candidate_provenance.py",
            "evaluate_events_target_source_git_blob": "src/polyphonic/evaluate_events.py",
            "decoder_candidate_labels_target_source_git_blob": "src/polyphonic/decoder_candidate_labels.py",
            "causal_event_metrics_target_source_git_blob": "src/polyphonic/causal_event_metrics.py",
        }
        for field, relative in expected_files.items():
            actual = subprocess.check_output(
                ["git", "hash-object", relative], cwd=self.root, text=True
            ).strip()
            self.assertEqual(bindings[field], actual, field)
        source = self.helper_source
        first_asset_hash = source.index("_, h18a_raw_sha = sha256_stream(h18a_path)")
        self.assertLess(source.index("for name, (relative, expected) in SCIENTIFIC_BINDINGS.items()"), first_asset_hash)

    def test_runtime_checkpoint_and_future_paths_are_sealed_without_science(self):
        runtime = self.seal["runtime"]
        self.assertEqual(runtime["python_executable"], "/Users/amcarene/midi-worker/.venv/bin/python")
        self.assertEqual(runtime["python_implementation"], "CPython")
        self.assertEqual(runtime["os_system"], "Darwin")
        self.assertEqual(runtime["machine"], "arm64")
        self.assertEqual(runtime["future_execution_environment"], {"MIDI_FORCE_CPU": "1"})
        checkpoint = self.seal["checkpoint"]
        self.assertEqual(checkpoint["raw_sha256"], "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325")
        self.assertFalse(checkpoint["deserialized"])
        paths = self.seal["future_paths"]
        self.assertFalse(paths["destination_exists"])
        self.assertFalse(paths["authorization_marker_created"])
        self.assertFalse(paths["claimed_marker_created"])
        self.assertFalse(paths["consumption_state_created"])
        self.assertIsNone(self.seal["unresolved"]["future_runner_source_blob"])

    def test_success_and_forbidden_flags_are_exact(self):
        flags = self.seal["flags"]
        true_flags = {
            "zero_science_preflight", "h20_bindings_verified", "h18a_population_identity_verified",
            "runtime_identity_sealed", "checkpoint_raw_sha256_verified", "asset_paths_sealed",
            "audio_raw_sha256_sealed", "label_raw_sha256_sealed",
            "future_result_destination_sealed", "future_authorization_marker_path_sealed",
            "raw_asset_bytes_read_for_sha256",
        }
        false_flags = set(flags) - true_flags
        self.assertEqual({name for name, value in flags.items() if value}, true_flags)
        self.assertTrue(all(flags[name] is False for name in false_flags))
        for name in (
            "scientific_content_interpreted", "audio_decoded", "labels_parsed",
            "checkpoint_deserialized", "tensorflow_imported", "model_loaded", "inference_run",
            "decoder_run", "real_reasons_inspected", "real_targets_extracted",
            "real_metrics_computed", "runner_implemented", "runner_imported", "runner_invoked",
            "authorization_created", "scientific_execution_authorized", "fresh_population_consumed",
            "locked_test_used",
        ):
            self.assertIn(name, false_flags)

    def test_helper_is_standard_library_streaming_atomic_and_non_scientific(self):
        tree = ast.parse(self.helper_source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {
            "__future__", "argparse", "csv", "hashlib", "importlib", "json", "os",
            "pathlib", "platform", "re", "subprocess", "sys", "tempfile",
        })
        self.assertIn("CHUNK_SIZE = 1024 * 1024", self.helper_source)
        self.assertIn("os.fsync(handle.fileno())", self.helper_source)
        self.assertIn("os.replace(temporary, path)", self.helper_source)
        self.assertNotIn("import tensorflow", self.helper_source)
        self.assertNotIn("import numpy", self.helper_source)
        self.assertNotIn("load_model", self.helper_source)

    def test_lf_rules_cover_every_h21_artifact(self):
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for relative in (
            "configs/provisional_resolution_frame_fallback_h21_zero_science_preflight.json",
            "scripts/build_provisional_resolution_frame_fallback_h21_zero_science_preflight.py",
            "tests/test_provisional_resolution_frame_fallback_h21_zero_science_preflight.py",
            "readme/results/2026-08-10_provisional-resolution-frame-fallback-h21-zero-science-preflight.md",
        ):
            self.assertIn(f"{relative} text eol=lf", attributes)


if __name__ == "__main__":
    unittest.main()
