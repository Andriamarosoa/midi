from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import run_causal_candidate_validation as runner


class SealedCausalCandidateValidationRunnerTests(unittest.TestCase):
    def test_execution_acknowledgement_is_required_before_paths_or_tensorflow(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DECODER_CANDIDATE_VALIDATION_EXECUTE=1"):
                runner.run_sealed_validation()

    def test_paths_are_internal_and_preserve_the_historical_cr_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker_root = Path(directory) / "midi-worker"
            repository_root = worker_root / "repository"
            repository_root.mkdir(parents=True)
            paths = runner.sealed_validation_paths(repository_root, worker_root)
        self.assertEqual(paths["repository_root"], repository_root.resolve())
        self.assertEqual(paths["run_dir"].name, runner.VALIDATION_RUN_DIRECTORY_NAME)
        self.assertEqual(paths["fit_report_path"].parent.name, runner.FIT_ARTIFACT_DIRECTORY_NAME)
        self.assertTrue(paths["fit_report_path"].parent.name.endswith("\r"))
        self.assertEqual(paths["checkpoint_path"].name, f"{runner.TRANSCRIPTION_CHECKPOINT_SHA256}.keras")

    def test_runner_has_no_cli_or_caller_controlled_execution_paths(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn("argparse", source)
        self.assertIn('VALIDATION_EXECUTE_ENV = "DECODER_CANDIDATE_VALIDATION_EXECUTE"', source)
        self.assertIn("FIT_ARTIFACT_DIRECTORY_NAME", source)
        self.assertIn("def run_sealed_validation()", source)
        self.assertIn('report_suffix="causal_candidate_fit_v1_ab"', source)


if __name__ == "__main__":
    unittest.main()
