from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "scripts" / "remote" / "wallclock_exec.py"


@unittest.skipUnless(os.name == "posix", "POSIX process groups are required")
class MacWallClockExecTests(unittest.TestCase):
    def _paths(self, directory: pathlib.Path) -> list[str]:
        return [
            "--process-state",
            str(directory / "process.env"),
            "--active-owner",
            str(directory / "active.owner.env"),
            "--timeout-marker",
            str(directory / "timed_out.env"),
        ]

    def test_successful_command_finishes_without_timeout_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = pathlib.Path(raw_directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SUPERVISOR),
                    "--timeout-seconds",
                    "5",
                    "--grace-seconds",
                    "1",
                    "--job-id",
                    "success",
                    "--token",
                    "a" * 32,
                    *self._paths(directory),
                    "--",
                    sys.executable,
                    "-c",
                    "print('ok')",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "ok")
            self.assertFalse((directory / "timed_out.env").exists())
            self.assertIn("job_id=success", (directory / "process.env").read_text())

    def test_timeout_terminates_the_isolated_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = pathlib.Path(raw_directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SUPERVISOR),
                    "--timeout-seconds",
                    "1",
                    "--grace-seconds",
                    "1",
                    "--job-id",
                    "timeout",
                    "--token",
                    "b" * 32,
                    *self._paths(directory),
                    "--",
                    sys.executable,
                    "-c",
                    "import time; time.sleep(60)",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 124, result.stderr)
            self.assertTrue((directory / "timed_out.env").is_file())
            state = dict(
                line.split("=", 1)
                for line in (directory / "process.env").read_text().splitlines()
            )
            pgid = int(state["pgid"])
            with self.assertRaises(ProcessLookupError):
                os.killpg(pgid, 0)

    def test_sigterm_stops_the_owned_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = pathlib.Path(raw_directory)
            command = [
                sys.executable,
                str(SUPERVISOR),
                "--timeout-seconds",
                "30",
                "--grace-seconds",
                "1",
                "--job-id",
                "stop",
                "--token",
                "c" * 32,
                *self._paths(directory),
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(60)",
            ]
            process = subprocess.Popen(command)
            state_path = directory / "process.env"
            deadline = time.monotonic() + 10
            while not state_path.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(state_path.is_file(), "supervisor handshake missing")
            state = dict(
                line.split("=", 1) for line in state_path.read_text().splitlines()
            )
            os.kill(process.pid, signal.SIGTERM)
            self.assertEqual(process.wait(timeout=10), 128 + signal.SIGTERM)
            with self.assertRaises(ProcessLookupError):
                os.killpg(int(state["pgid"]), 0)


if __name__ == "__main__":
    unittest.main()
