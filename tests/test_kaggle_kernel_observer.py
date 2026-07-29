from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.cloud.observe_kaggle_kernel import (
    DEFAULT_OUTPUT_PATTERNS,
    KernelStatus,
    _atomic_write_json,
    _redact_secrets,
    download_selected_outputs,
    observe_once,
    parse_kernel_status,
    parse_output_listing,
    parse_quota,
    select_output_names,
)


class KaggleKernelObserverTests(unittest.TestCase):
    def test_status_keeps_exact_enum_and_normalizes_terminal_outcome(self) -> None:
        running = parse_kernel_status(
            'owner/kernel has status "KernelWorkerStatus.RUNNING"'
        )
        complete = parse_kernel_status(
            'owner/kernel has status "KernelWorkerStatus.COMPLETE"'
        )
        failed = parse_kernel_status(
            'owner/kernel has status "KernelWorkerStatus.ERROR"'
        )

        self.assertEqual(running.raw, "KernelWorkerStatus.RUNNING")
        self.assertEqual(running.canonical, "running")
        self.assertFalse(running.terminal)
        self.assertEqual(complete.outcome, "complete")
        self.assertTrue(complete.terminal)
        self.assertEqual(failed.outcome, "error")
        self.assertTrue(failed.terminal)

    def test_quota_values_are_preserved_verbatim(self) -> None:
        quota = parse_quota(
            'notice\n[{"resource":"GPU","used":"12.34h",'
            '"remaining":"17.66h","total":"30.00h",'
            '"refreshAt":"2026-08-01T00:00:00"}]'
        )

        self.assertEqual(quota[0]["used"], "12.34h")
        self.assertEqual(quota[0]["remaining"], "17.66h")
        self.assertEqual(quota[0]["refreshAt"], "2026-08-01T00:00:00")

    def test_output_selection_is_allowlisted_and_path_safe(self) -> None:
        listing = parse_output_listing(json.dumps([
            {"name": "output_manifest.json", "size": 12},
            {"name": "result.tar", "size": 50},
            {"name": "secret.keras", "size": 80},
            {"name": "../escape.log", "size": 1},
        ]))

        selected = select_output_names(listing, DEFAULT_OUTPUT_PATTERNS)

        self.assertEqual(selected, ["output_manifest.json", "result.tar"])

    def test_atomic_state_write_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "observer.json"
            _atomic_write_json(path, {"status": "running"})

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["status"],
                "running",
            )
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_running_poll_never_downloads_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_kernel_status",
                    return_value=KernelStatus(
                        "KernelWorkerStatus.RUNNING",
                        "running",
                        False,
                        None,
                    ),
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_quota",
                    return_value=[{
                        "resource": "GPU",
                        "used": "1.00h",
                        "remaining": "29.00h",
                        "total": "30.00h",
                        "refreshAt": "later",
                    }],
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel._terminal_artifacts"
                ) as terminal_artifacts,
            ):
                state, status = observe_once(
                    cli="kaggle",
                    handle="owner/kernel",
                    state_path=root / "state.json",
                    output_dir=root / "outputs",
                )

            self.assertFalse(status.terminal)
            self.assertEqual(state["status_raw"], "KernelWorkerStatus.RUNNING")
            terminal_artifacts.assert_not_called()
            self.assertFalse((root / "outputs").exists())

    def test_complete_poll_fetches_terminal_artifacts_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = {
                "completed_at_utc": "now",
                "execution_log": {"path": "log"},
                "available_outputs": [],
                "selected_output_names": [],
                "outputs": [],
            }
            with (
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_kernel_status",
                    return_value=KernelStatus(
                        "KernelWorkerStatus.COMPLETE",
                        "complete",
                        True,
                        "complete",
                    ),
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_quota",
                    return_value=[],
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel._terminal_artifacts",
                    return_value=artifacts,
                ) as terminal_artifacts,
            ):
                first, _ = observe_once(
                    cli="kaggle",
                    handle="owner/kernel",
                    state_path=root / "state.json",
                    output_dir=root / "outputs",
                )
                second, _ = observe_once(
                    cli="kaggle",
                    handle="owner/kernel",
                    state_path=root / "state.json",
                    output_dir=root / "outputs",
                )

            self.assertEqual(first["terminal_artifacts"], artifacts)
            self.assertEqual(second["terminal_artifacts"], artifacts)
            terminal_artifacts.assert_called_once()

    def test_terminal_download_failure_is_sanitized_in_atomic_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token = "KGATnot-a-real-secret-789"
            with (
                mock.patch.dict(os.environ, {"KAGGLE_MCP_TOKEN": token}),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_kernel_status",
                    return_value=KernelStatus(
                        "KernelWorkerStatus.ERROR",
                        "error",
                        True,
                        "error",
                    ),
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel.query_quota",
                    return_value=[],
                ),
                mock.patch(
                    "scripts.cloud.observe_kaggle_kernel._terminal_artifacts",
                    side_effect=RuntimeError(f"download failed {token}"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    observe_once(
                        cli="kaggle",
                        handle="owner/kernel",
                        state_path=root / "state.json",
                        output_dir=root / "outputs",
                    )

            text = (root / "state.json").read_text(encoding="utf-8")
            state = json.loads(text)
            self.assertNotIn(token, text)
            self.assertIn("<redacted>", state["artifact_download_error"])

    @mock.patch("scripts.cloud.observe_kaggle_kernel._run_cli")
    def test_targeted_download_accepts_hidden_working_prefix_and_drops_cli_log(
        self,
        run_cli: mock.Mock,
    ) -> None:
        def write_cli_outputs(
            cli: str,
            arguments: tuple[str, ...],
            *,
            timeout_seconds: float,
        ) -> mock.Mock:
            del cli, timeout_seconds
            staging = Path(arguments[arguments.index("--path") + 1])
            nested = staging / "guitar-midi-results"
            nested.mkdir(parents=True)
            (nested / "output_manifest.json").write_text(
                '{"locked_test_used": false}',
                encoding="utf-8",
            )
            (staging / "kernel.log").write_text("duplicate", encoding="utf-8")
            result = mock.Mock()
            result.returncode = 0
            return result

        run_cli.side_effect = write_cli_outputs
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "outputs"
            downloaded = download_selected_outputs(
                "kaggle",
                "owner/kernel",
                output_dir,
                ["output_manifest.json"],
                timeout_seconds=1.0,
            )

            self.assertTrue(
                (output_dir / "guitar-midi-results/output_manifest.json").is_file()
            )
            self.assertFalse((output_dir / "kernel.log").exists())
            self.assertEqual(
                [item["name"] for item in downloaded],
                ["guitar-midi-results/output_manifest.json"],
            )
            pattern = run_cli.call_args.args[1][
                run_cli.call_args.args[1].index("--file-pattern") + 1
            ]
            self.assertTrue(pattern.startswith("(?:^|/)"))

    def test_secrets_are_redacted_from_diagnostics(self) -> None:
        token = "KGATnot-a-real-secret-123"
        with mock.patch.dict(os.environ, {"KAGGLE_MCP_TOKEN": token}):
            redacted = _redact_secrets(f"failed token={token}")

        self.assertNotIn(token, redacted)
        self.assertIn("<redacted>", redacted)

    @mock.patch("scripts.cloud.observe_kaggle_kernel.subprocess.run")
    def test_cli_forces_utf8_without_putting_tokens_in_arguments(
        self,
        run: mock.Mock,
    ) -> None:
        from scripts.cloud.observe_kaggle_kernel import _run_cli

        run.return_value.returncode = 0
        run.return_value.stdout = "ok"
        run.return_value.stderr = ""
        token = "KGATnot-a-real-secret-456"
        with mock.patch.dict(os.environ, {"KAGGLE_MCP_TOKEN": token}):
            _run_cli("kaggle", ("quota",), timeout_seconds=1.0)

        arguments = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertNotIn(token, arguments)
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(environment["PYTHONUTF8"], "1")


if __name__ == "__main__":
    unittest.main()
