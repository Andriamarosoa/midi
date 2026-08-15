from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_deliver_exact_thirteen_source_odb_once.py"


class TestH27ExactThirteenSourceDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h27_exact_thirteen_delivery", RUNNER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.receiver_raw = cls.module.read_receiver_blob()
        cls.blob_ids = cls.module.embedded_blob_ids(cls.receiver_raw)

    def terminal(self, **changes: object) -> bytes:
        report = {
            "status": self.module.TERMINAL_STATUS,
            "object_count": 13,
            "object_blob_ids": list(self.blob_ids),
            "source_git_database": self.module.SOURCE_GIT_DATABASE,
            "head_unchanged": True,
            "symbolic_head_unchanged": True,
            "regular_refs_unchanged": True,
            "root_refs_and_pseudorefs_unchanged": True,
            "index_unchanged": True,
            "worktree_clean": True,
            "target_odb_changed": False,
            "import_executed": False,
            "detach_executed": False,
            "downstream_executed": False,
            "science_or_locked_test": False,
        }
        report.update(changes)
        return (json.dumps(report, separators=(",", ":")) + "\n").encode()

    def test_receiver_identity_and_thirteen_unique_objects_are_exact(self) -> None:
        self.assertEqual(len(self.receiver_raw), 119406)
        self.assertEqual(len(self.blob_ids), 13)
        self.assertEqual(len(set(self.blob_ids)), 13)

    def test_success_uses_one_exact_ssh_and_byte_exact_stdin(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=self.terminal(), stderr=b"")
        with (
            mock.patch.object(self.module, "require_windows_and_zero_arguments"),
            mock.patch.object(self.module, "read_receiver_blob", return_value=self.receiver_raw),
            mock.patch.object(self.module.subprocess, "run", return_value=completed) as run,
        ):
            report = self.module.deliver_once()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], self.module.SSH_COMMAND)
        self.assertEqual(run.call_args.kwargs["input"], self.receiver_raw)
        self.assertIs(run.call_args.kwargs["shell"], False)
        self.assertEqual(run.call_args.kwargs["timeout"], 900)
        self.assertEqual(report["ssh_invocation_count"], 1)
        self.assertEqual(report["object_count"], 13)

    def test_nonzero_stderr_and_timeout_are_terminal_without_retry(self) -> None:
        cases = (
            subprocess.CompletedProcess([], 23, stdout=b"", stderr=b""),
            subprocess.CompletedProcess([], 0, stdout=self.terminal(), stderr=b"warning"),
            subprocess.TimeoutExpired(self.module.SSH_COMMAND, 900),
        )
        for outcome in cases:
            with self.subTest(outcome=type(outcome).__name__):
                effect = outcome if isinstance(outcome, BaseException) else None
                value = None if effect is not None else outcome
                with (
                    mock.patch.object(self.module, "require_windows_and_zero_arguments"),
                    mock.patch.object(self.module, "read_receiver_blob", return_value=self.receiver_raw),
                    mock.patch.object(self.module.subprocess, "run", return_value=value, side_effect=effect) as run,
                ):
                    with self.assertRaises(self.module.ConsumedDeliveryFailure):
                        self.module.deliver_once()
                self.assertEqual(run.call_count, 1)

    def test_malformed_or_wrong_terminal_json_is_rejected(self) -> None:
        outputs = (
            b"not-json\n",
            self.terminal(object_count=12),
            self.terminal(status="wrong"),
            self.terminal(science_or_locked_test=True),
            self.terminal() + b"{}\n",
        )
        for stdout in outputs:
            with self.subTest(stdout=stdout[:32]):
                with self.assertRaises(self.module.ConsumedDeliveryFailure):
                    self.module.parse_terminal_report(stdout, self.blob_ids)

    def test_source_contains_no_second_ssh_or_transfer_fallback(self) -> None:
        source = RUNNER.read_text(encoding="utf-8").lower()
        self.assertEqual(source.count("subprocess.run("), 2)
        for forbidden in ("shell=true", "scp", "sftp", "rsync", "git push", "git fetch", "git pull", "def retry"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
