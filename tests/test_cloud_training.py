from __future__ import annotations

import unittest
from unittest import mock

from scripts.cloud.train_polyphonic import (
    MINIMUM_FREE_GIB,
    PROCESS_RUNTIME_GRACE_MINUTES,
    _run,
    _training_process_timeout_seconds,
    validate_cloud_context,
)


class CloudTrainingContractTest(unittest.TestCase):
    def test_training_process_watchdog_includes_initialization_grace(
        self,
    ) -> None:
        self.assertEqual(
            _training_process_timeout_seconds(2.0),
            (2.0 + PROCESS_RUNTIME_GRACE_MINUTES) * 60.0,
        )

    @mock.patch("scripts.cloud.train_polyphonic.subprocess.run")
    def test_run_forwards_process_timeout(
        self, run: mock.Mock
    ) -> None:
        _run(("python", "-m", "probe"), timeout_seconds=600.0)
        run.assert_called_once_with(
            ("python", "-m", "probe"),
            cwd=mock.ANY,
            check=True,
            timeout=600.0,
        )

    def test_valid_cloud_branch_with_gpu_is_accepted(self) -> None:
        validate_cloud_context(
            platform_name="posix",
            branch="experiment/onset-gate",
            gpu_names=("GPU:0",),
            free_gib=MINIMUM_FREE_GIB,
        )

    def test_windows_training_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Windows"):
            validate_cloud_context(
                platform_name="nt",
                branch="experiment/onset-gate",
                gpu_names=("GPU:0",),
                free_gib=MINIMUM_FREE_GIB,
            )

    def test_main_branch_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "branche"):
            validate_cloud_context(
                platform_name="posix",
                branch="main",
                gpu_names=("GPU:0",),
                free_gib=MINIMUM_FREE_GIB,
            )

    def test_gpu_and_disk_are_required(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "GPU"):
            validate_cloud_context(
                platform_name="posix",
                branch="experiment/onset-gate",
                gpu_names=(),
                free_gib=MINIMUM_FREE_GIB,
            )
        with self.assertRaisesRegex(RuntimeError, "Espace"):
            validate_cloud_context(
                platform_name="posix",
                branch="experiment/onset-gate",
                gpu_names=("GPU:0",),
                free_gib=MINIMUM_FREE_GIB - 0.1,
            )


if __name__ == "__main__":
    unittest.main()
