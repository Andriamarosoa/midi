from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from src.polyphonic import run_h25_preclaim_admin_lifecycle_qualification as entrypoint


class H25AdministrativeQualificationEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = Path(__file__).resolve().parents[1]
        cls.output = (
            cls.repository
            / "tmp/local/h25_preclaim_admin_lifecycle_qualification_20260811"
        )

    def _output_snapshot(self) -> tuple[bool, tuple[str, ...]]:
        return (
            self.output.exists(),
            tuple(
                sorted(
                    path.relative_to(self.output).as_posix()
                    for path in self.output.rglob("*")
                )
            )
            if self.output.exists()
            else (),
        )

    def test_python_m_entrypoint_check_imports_without_qualification(self) -> None:
        before = self._output_snapshot()
        environment = dict(os.environ)
        environment.pop(entrypoint.EXECUTE_ENV, None)
        environment.pop(entrypoint.EXPECTED_COMMIT_ENV, None)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.polyphonic.run_h25_preclaim_admin_lifecycle_qualification",
                "--entrypoint-check",
            ],
            cwd=self.repository,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(
            payload,
            {
                "entrypoint": (
                    "src.polyphonic."
                    "run_h25_preclaim_admin_lifecycle_qualification"
                ),
                "qualification_executed": False,
                "status": "H25_ADMIN_QUALIFICATION_ENTRYPOINT_READY",
            },
        )
        self.assertEqual(completed.stderr, "")
        self.assertEqual(self._output_snapshot(), before)

    def test_entrypoint_check_refuses_execution_acknowledgement(self) -> None:
        before = self._output_snapshot()
        environment = dict(os.environ)
        environment[entrypoint.EXECUTE_ENV] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.polyphonic.run_h25_preclaim_admin_lifecycle_qualification",
                "--entrypoint-check",
            ],
            cwd=self.repository,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("refuses an execution acknowledgement", completed.stderr)
        self.assertEqual(self._output_snapshot(), before)

    def test_execution_requires_ack_before_git_or_output(self) -> None:
        before = self._output_snapshot()
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                entrypoint,
                "git",
                side_effect=AssertionError("git must remain unreachable"),
            ):
                with self.assertRaisesRegex(
                    PermissionError, "literal acknowledgement"
                ):
                    entrypoint.main()
        self.assertEqual(self._output_snapshot(), before)

    def test_execution_requires_full_reviewed_commit_before_git(self) -> None:
        before = self._output_snapshot()
        with mock.patch.dict(
                os.environ,
                {
                    entrypoint.EXECUTE_ENV: "1",
                    entrypoint.EXPECTED_COMMIT_ENV: "a2cbed8",
                },
                clear=True,
            ):
            with mock.patch.object(
                entrypoint,
                "git",
                side_effect=AssertionError("git must remain unreachable"),
            ):
                with self.assertRaisesRegex(PermissionError, "full lowercase SHA"):
                    entrypoint.main()
        self.assertEqual(self._output_snapshot(), before)

    def test_unknown_argument_cannot_reach_qualification(self) -> None:
        before = self._output_snapshot()
        with mock.patch.object(
            entrypoint,
            "main",
            side_effect=AssertionError("qualification must remain unreachable"),
        ):
            with self.assertRaises(SystemExit):
                entrypoint.cli(["--unknown"])
        self.assertEqual(self._output_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
