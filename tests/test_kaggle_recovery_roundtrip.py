from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.cloud.verify_recovery_checkpoint import (
    verify_recovery_roundtrip,
)
from src.polyphonic.recovery import RecoverySnapshot


class KaggleRecoveryRoundtripTest(unittest.TestCase):
    def test_roundtrip_uses_signatures_and_writes_locked_test_safe_report(
        self,
    ) -> None:
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            recovery_dir = run_dir / "recovery"
            recovery_dir.mkdir(parents=True)
            state = {
                "generation": 4,
                "slot": "b",
                "epoch": 1,
                "next_batch": 32,
                "optimizer_iterations": 128,
                "learning_rate": 0.0005,
                "model_sha256": "b" * 64,
                "plan_sha256": digest,
                "config_sha256": "c" * 64,
                "manifest_sha256": "d" * 64,
                "commit": "deadbeef",
                "locked_test_used": False,
            }
            (recovery_dir / "recovery-b.json").write_text(
                json.dumps(state),
                encoding="utf-8",
            )
            snapshot = RecoverySnapshot(
                model=object(),
                state=state,
                model_path=recovery_dir / "recovery-b.keras",
                state_path=recovery_dir / "recovery-b.json",
                slot="b",
            )

            with mock.patch(
                "scripts.cloud.verify_recovery_checkpoint."
                "load_latest_recovery_checkpoint",
                return_value=snapshot,
            ) as loader:
                report = verify_recovery_roundtrip(run_dir)

            self.assertTrue(report["passed"])
            self.assertFalse(report["locked_test_used"])
            self.assertEqual(report["generation"], 4)
            self.assertEqual(report["optimizer_iterations"], 128)
            self.assertEqual(
                loader.call_args.kwargs["signatures"].plan_sha256,
                digest,
            )
            persisted = json.loads(
                (run_dir / "recovery_roundtrip.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(persisted, report)
            self.assertIn("tensorflow", report["runtime"])

    def test_roundtrip_refuses_missing_valid_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            (run_dir / "recovery").mkdir(parents=True)
            (run_dir / "recovery" / "recovery-a.json").write_text(
                "{broken",
                encoding="utf-8",
            )
            with self.assertRaises(FileNotFoundError):
                verify_recovery_roundtrip(run_dir)

    def test_roundtrip_rejects_fallback_from_corrupt_newest_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            recovery_dir = run_dir / "recovery"
            recovery_dir.mkdir(parents=True)
            base = {
                "epoch": 0,
                "next_batch": 16,
                "optimizer_iterations": 16,
                "learning_rate": 0.001,
                "plan_sha256": "a" * 64,
                "config_sha256": "b" * 64,
                "manifest_sha256": "c" * 64,
                "commit": "deadbeef",
                "locked_test_used": False,
            }
            newest = {
                **base,
                "generation": 2,
                "slot": "b",
                "model_sha256": "d" * 64,
            }
            fallback = {
                **base,
                "generation": 1,
                "slot": "a",
                "model_sha256": "e" * 64,
            }
            (recovery_dir / "recovery-b.json").write_text(
                json.dumps(newest),
                encoding="utf-8",
            )
            snapshot = RecoverySnapshot(
                model=object(),
                state=fallback,
                model_path=recovery_dir / "recovery-a.keras",
                state_path=recovery_dir / "recovery-a.json",
                slot="a",
            )
            with mock.patch(
                "scripts.cloud.verify_recovery_checkpoint."
                "load_latest_recovery_checkpoint",
                return_value=snapshot,
            ):
                with self.assertRaisesRegex(RuntimeError, "did not round-trip"):
                    verify_recovery_roundtrip(run_dir)
            self.assertFalse(
                (run_dir / "recovery_roundtrip.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
