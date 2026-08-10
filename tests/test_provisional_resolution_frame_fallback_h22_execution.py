from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from src.polyphonic import run_provisional_resolution_frame_fallback_h17 as h22


class H22ExecutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.contract_path = cls.root / h22.EXECUTION_CONTRACT_RELATIVE
        cls.raw = cls.contract_path.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.runner_path = cls.root / "src/polyphonic/run_provisional_resolution_frame_fallback_h17.py"

    def test_contract_is_canonical_and_binds_h21_and_runner(self):
        self.assertEqual(
            self.raw,
            (json.dumps(self.contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), "decb9e9398819294f797938dde834aa83cddb41bf537b757df74cf1291ea9ae6")
        self.assertEqual(self.contract["parent_h21_commit"], "384b0248106cd94344c6eaef5fbd5975d78a46ad")
        self.assertEqual(self.contract["h21_raw_sha256"], h22.H21_RAW_SHA256)
        self.assertEqual(
            self.contract["runner_git_blob"],
            __import__("subprocess").check_output(
                ["git", "hash-object", str(self.runner_path)], cwd=self.root, text=True
            ).strip(),
        )

    def test_scientific_contract_and_one_shot_values_are_frozen(self):
        population = self.contract["population"]
        self.assertEqual((population["recording_count"], population["leakage_group_count"]), (146, 51))
        self.assertFalse(population["manual_or_outcome_based_reselection_allowed"])
        science = self.contract["scientific_contract"]
        self.assertEqual(science["metric"], "RD_false")
        self.assertEqual(science["positive_threshold_inclusive"], 0.1)
        self.assertEqual((science["bootstrap_replicates"], science["bootstrap_seed"]), (10000, 721629268))
        self.assertEqual(science["minimum_valid_bootstrap_replicates"], 9500)
        one_shot = self.contract["one_shot"]
        self.assertTrue(one_shot["claim_atomic"])
        self.assertTrue(one_shot["consumption_state_before_first_scientific_open"])
        self.assertFalse(one_shot["automatic_retry"])
        self.assertFalse(one_shot["same_population_rerun"])
        self.assertFalse(self.contract["locked_test_used"])

    def test_h22a_snapshot_is_exactly_one_commit_above_reviewed_h22(self):
        self.assertEqual(h22.EXPECTED_EXECUTION_PARENT_COMMIT, "5810061e10685b7d13088f3b0d8ad549f5ac48d4")
        expected = {
            "configs/provisional_resolution_frame_fallback_h22_execution_contract.json",
            "readme/README.md",
            "readme/results/2026-08-10_provisional-resolution-frame-fallback-h22-runner.md",
            "src/polyphonic/run_provisional_resolution_frame_fallback_h17.py",
            "tests/test_provisional_resolution_frame_fallback_h22_execution.py",
        }
        self.assertEqual(set(self.contract["execution_commit_changed_files"]), expected)
        source = self.runner_path.read_text(encoding="utf-8")
        self.assertIn('"rev-parse", "HEAD^"', source)
        self.assertIn('"rev-list", "--count"', source)
        self.assertIn('"diff", "--name-only"', source)

    def test_import_is_zero_science_and_runner_has_no_caller_overrides(self):
        tree = ast.parse(self.runner_path.read_text(encoding="utf-8"))
        top_imports = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module.split(".")[0])
        self.assertFalse(top_imports.intersection({"tensorflow", "keras", "numpy", "yaml", "scipy", "soundfile", "librosa"}))
        self.assertNotIn("argparse", top_imports)
        self.assertIn('if len(sys.argv) != 1:', self.runner_path.read_text(encoding="utf-8"))

    def _fake_paths(self, root: Path) -> h22.H17Paths:
        marker = root / "authorization.json"
        return h22.H17Paths(
            repository=self.root,
            execution_contract=self.contract_path,
            h20=self.root / h22.H20_RELATIVE,
            h21=self.root / h22.H21_RELATIVE,
            model_config=root / "model.yaml", decoder_config=root / "decoder.json",
            audio_policy=root / "audio.json", checkpoint=root / "checkpoint.keras",
            destination=root / "result", marker=marker,
            claimed=Path(str(marker) + ".claimed"), state=Path(str(marker) + ".state.json"),
            phase=Path(str(marker) + ".phase.json"), failure=root / "result.failure.json",
        )

    def test_consumption_is_persisted_before_first_scientific_adapter_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._fake_paths(root)
            records = tuple(
                h22.SealedH17Recording(
                    recording_key=f"corpus|group|source{i}|capture", leakage_group_key=f"group:{i % 51}",
                    corpus_category="corpus", audio_path=root / "audio", audio_member="",
                    audio_size_bytes=1, audio_sha256="0" * 64, label_path=root / "label",
                    label_size_bytes=1, label_sha256="1" * 64,
                )
                for i in range(146)
            )
            groups = tuple(f"group:{i}" for i in range(51))
            report = SimpleNamespace(
                emitted_noteons_initially_considered=0,
                audio_aware_activation_noteons_in_h17_population=0,
                frame_fallback_noteons=0, comparator_noteons=0,
                excluded_harmonic_strong_frame_count=0, excluded_legacy_count=0,
                excluded_retrigger_count=0, target_unmatchable_or_excluded_count=0,
                malformed_reason_count=0, malformed_or_nonfinite_target_count=0,
            )
            calls = []

            class FakeAdapter:
                def __init__(self, _paths): pass
                def process(self, record, *, record_phase, recording_index):
                    state = json.loads(paths.state.read_text(encoding="utf-8"))
                    if state["fresh_population_consumed"] is not True:
                        raise AssertionError("consumption boundary was not persisted")
                    calls.append(recording_index)
                    return (), {"recording_key": record.recording_key}

            with (
                patch.object(h22, "_load_and_verify_preflight", return_value=(paths, records, groups, self.contract, "a" * 64)),
                patch.object(h22, "_claim_marker", return_value={"execution_commit": "b" * 40}),
                patch.object(h22, "_ScientificAdapter", FakeAdapter),
                patch("src.polyphonic.provisional_resolution_frame_fallback_h19.evaluate_h19_synthetic_metrics", return_value=report),
                patch.object(h22, "_metric_payload", return_value={"status": "frame_fallback_signal_insufficient_valid_observations"}),
                patch.object(h22, "_runtime_identity", return_value={"MIDI_FORCE_CPU": "1"}),
            ):
                result = h22.run()
            self.assertEqual(len(calls), 146)
            self.assertEqual(result["status"], "frame_fallback_signal_insufficient_valid_observations")
            final_state = json.loads(paths.state.read_text(encoding="utf-8"))
            self.assertEqual(final_state["state"], "completed")
            self.assertTrue(final_state["fresh_population_consumed"])
            self.assertTrue(paths.destination.is_dir())
            self.assertFalse(paths.failure.exists())

    def test_failure_after_consumption_is_persisted_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._fake_paths(root)
            record = h22.SealedH17Recording(
                recording_key="corpus|group|source|capture", leakage_group_key="group:0",
                corpus_category="corpus", audio_path=root / "audio", audio_member="",
                audio_size_bytes=1, audio_sha256="0" * 64, label_path=root / "label",
                label_size_bytes=1, label_sha256="1" * 64,
            )
            calls = []

            class FailingAdapter:
                def __init__(self, _paths): pass
                def process(self, *_args, **_kwargs):
                    calls.append(1)
                    raise OSError("synthetic operational failure")

            with (
                patch.object(h22, "_load_and_verify_preflight", return_value=(paths, (record,), ("group:0",), self.contract, "a" * 64)),
                patch.object(h22, "_claim_marker", return_value={"execution_commit": "b" * 40}),
                patch.object(h22, "_ScientificAdapter", FailingAdapter),
            ):
                with self.assertRaises(OSError):
                    h22.run()
            self.assertEqual(calls, [1])
            failure = json.loads(paths.failure.read_text(encoding="utf-8"))
            self.assertTrue(failure["fresh_population_consumed"])
            self.assertFalse(failure["automatic_retry_allowed"])
            self.assertFalse(paths.destination.exists())


if __name__ == "__main__":
    unittest.main()
