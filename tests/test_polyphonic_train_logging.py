from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

from src.polyphonic.train import BatchProgressLogger, EpochProgressLogger


class PolyphonicTrainLoggingTests(unittest.TestCase):
    def test_epoch_progress_is_persisted_and_flushed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "epoch_progress.json"
            callback = EpochProgressLogger(
                path,
                total_epochs=8,
                initial_epoch=2,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                callback.on_train_begin()
                callback.on_epoch_begin(2)
                callback.on_epoch_end(
                    2,
                    {
                        "loss": np.float32(0.25),
                        "val_frame_micro_f1": np.float32(0.5),
                    },
                )

            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "epoch_completed")
            self.assertEqual(report["epoch"], 3)
            self.assertEqual(report["total_epochs"], 8)
            self.assertAlmostEqual(report["metrics"]["loss"], 0.25)
            self.assertAlmostEqual(
                report["metrics"]["val_frame_micro_f1"],
                0.5,
            )
            self.assertIn(
                '"status":"epoch_completed"',
                output.getvalue(),
            )

    def test_batch_progress_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "batch_progress.json"
            callback = BatchProgressLogger(
                path,
                total_batches=4,
                total_epochs=2,
                batch_size=8,
                every_batches=2,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                callback.on_train_begin()
                callback.on_epoch_begin(0)
                callback.on_train_batch_begin(0)
                callback.on_train_batch_end(
                    0, {"loss": np.float32(0.5)}
                )
                callback.on_train_batch_begin(1)
                callback.on_train_batch_end(
                    1, {"loss": np.float32(0.4)}
                )

            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "running")
            self.assertEqual(report["epoch"], 1)
            self.assertEqual(report["batch"], 2)
            self.assertEqual(report["total_batches"], 4)
            self.assertEqual(report["batch_size"], 8)
            self.assertGreater(report["examples_per_second"], 0.0)
            self.assertGreater(report["projected_epoch_seconds"], 0.0)
            self.assertAlmostEqual(report["metrics"]["loss"], 0.4)
            self.assertIn('"batch":2', output.getvalue())
