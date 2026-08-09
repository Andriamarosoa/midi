from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from src.polyphonic import run_causal_candidate_v2_independent_validation_execution as runner


class IndependentV2ExecutionRunnerTests(unittest.TestCase):
    def test_import_has_no_tensorflow_or_scientific_modules(self) -> None:
        code = (
            "import sys; "
            "import src.polyphonic.run_causal_candidate_v2_independent_validation_execution; "
            "raise SystemExit(int('tensorflow' in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_is_fail_closed_without_one_job_capability(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.main([])

    def test_forged_capability_is_rejected(self) -> None:
        forged = runner.IndependentV2OneJobCapability(
            runner_commit="0" * 40,
            execution_contract_sha256="0" * 64,
            device="cpu",
            wall_timeout_seconds=900,
            job_id="forged",
        )
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.require_sealed_one_job_capability(forged)

    def test_authorized_path_rejects_before_scientific_execution(self) -> None:
        forged = runner.IndependentV2OneJobCapability(
            runner_commit="0" * 40,
            execution_contract_sha256="0" * 64,
            device="cpu",
            wall_timeout_seconds=900,
            job_id="forged",
        )
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            runner.run_authorized_independent_v2(Path(__file__).resolve().parents[1], forged)


if __name__ == "__main__":
    unittest.main()
