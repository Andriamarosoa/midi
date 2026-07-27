from __future__ import annotations

import unittest

from scripts.cloud.train_polyphonic import (
    MINIMUM_FREE_GIB,
    validate_cloud_context,
)


class CloudTrainingContractTest(unittest.TestCase):
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
