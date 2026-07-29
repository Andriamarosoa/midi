from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.polyphonic.data import (
    FramePools,
    PlanBatchSlice,
    PolyphonicEpochPlan,
    PolyphonicSequence,
)


class _PlanOnlyCorpus:
    pass


class _IndexSequence(PolyphonicSequence):
    def __getitem__(self, batch_index: int):
        return int(batch_index)


def _refs(recording_index: int, first_frame: int) -> np.ndarray:
    return np.asarray(
        [
            [recording_index, first_frame],
            [recording_index, first_frame + 1],
            [recording_index, first_frame + 2],
            [recording_index, first_frame + 3],
        ],
        dtype=np.int32,
    )


def _sequence(sequence_type=PolyphonicSequence) -> PolyphonicSequence:
    pools = FramePools(
        onset=_refs(0, 0),
        polyphonic=_refs(1, 10),
        monophonic=_refs(2, 20),
        silence=_refs(3, 30),
    )
    return sequence_type(
        _PlanOnlyCorpus(),
        batch_size=4,
        input_samples=8,
        normalization_gain=1.0,
        seed=41,
        pools=pools,
        examples_per_epoch=19,
        sampling_fractions={
            "onset": 0.25,
            "polyphonic": 0.25,
            "monophonic": 0.25,
            "silence": 0.25,
        },
        augmentation_gain_db=6.0,
        workers=3,
        max_queue_size=7,
    )


class PolyphonicEpochPlanTests(unittest.TestCase):
    def test_plan_for_epoch_is_history_independent_and_read_only(self) -> None:
        first = _sequence()
        expected = first.plan_for_epoch(7)
        installed_epoch = first.epoch
        installed_sha256 = first.plan_sha256

        first.on_epoch_end()
        first.on_epoch_end()
        actual = first.plan_for_epoch(7)
        second = _sequence().plan_for_epoch(7)

        self.assertEqual(installed_epoch, 0)
        self.assertNotEqual(installed_sha256, first.plan_sha256)
        self.assertEqual(actual.sha256, expected.sha256)
        self.assertEqual(second.sha256, expected.sha256)
        np.testing.assert_array_equal(actual.order, expected.order)
        np.testing.assert_array_equal(
            actual.augmentation_gains, expected.augmentation_gains
        )
        self.assertFalse(actual.order.flags.writeable)
        self.assertFalse(actual.augmentation_gains.flags.writeable)
        with self.assertRaises(ValueError):
            actual.order[0, 0] = 99
        with self.assertRaises(ValueError):
            actual.augmentation_gains[0] = 1.0

    def test_export_round_trip_authenticates_and_installs_exact_plan(self) -> None:
        sequence = _sequence()
        plan = sequence.plan_for_epoch(5)
        exported = plan.export()
        self.assertTrue(all(
            not value.flags.writeable for value in exported.values()
        ))

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "epoch-plan.npz"
            np.savez(path, **exported)
            with np.load(path, allow_pickle=False) as payload:
                restored = PolyphonicEpochPlan.from_export(payload)
                installed = sequence.install_plan(payload)

        self.assertEqual(restored.sha256, plan.sha256)
        self.assertEqual(installed.sha256, plan.sha256)
        self.assertEqual(sequence.epoch, 5)
        self.assertEqual(sequence.plan_sha256, plan.sha256)
        self.assertFalse(sequence.order.flags.writeable)
        self.assertFalse(sequence.augmentation_gains.flags.writeable)
        np.testing.assert_array_equal(sequence.order, plan.order)
        np.testing.assert_array_equal(
            sequence.augmentation_gains, plan.augmentation_gains
        )

        tampered = {
            name: np.array(value, copy=True)
            for name, value in exported.items()
        }
        tampered["order"][0, 1] += 1
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            PolyphonicEpochPlan.from_export(tampered)
        with self.assertRaisesRegex(ValueError, "example count"):
            sequence.install_plan(PolyphonicEpochPlan(
                epoch=5,
                order=plan.order[:-1],
                augmentation_gains=plan.augmentation_gains[:-1],
            ))
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            PolyphonicEpochPlan(
                epoch=0,
                order=np.asarray([[0, 0]], np.int32),
                augmentation_gains=np.asarray([0.0], np.float32),
            )

    def test_batch_slice_translates_indices_and_never_advances_plan(self) -> None:
        sequence = _sequence(_IndexSequence)
        original_epoch = sequence.epoch
        original_sha256 = sequence.plan_sha256
        sliced = PlanBatchSlice(sequence, start_batch=2, end_batch=5)

        self.assertEqual(len(sliced), 3)
        self.assertEqual(sliced[0], 2)
        self.assertEqual(sliced[2], 4)
        self.assertEqual(sliced.workers, 3)
        self.assertEqual(sliced.max_queue_size, 7)
        sliced.on_epoch_end()
        self.assertEqual(sequence.epoch, original_epoch)
        self.assertEqual(sequence.plan_sha256, original_sha256)
        with self.assertRaises(IndexError):
            sliced[3]

        sequence.on_epoch_end()
        with self.assertRaisesRegex(RuntimeError, "parent epoch plan changed"):
            sliced[0]

    def test_plan_digest_has_a_fixed_canonical_test_vector(self) -> None:
        plan = PolyphonicEpochPlan(
            epoch=3,
            order=np.asarray([[1, 2], [3, 4]], dtype=np.int64),
            augmentation_gains=np.asarray([0.5, 1.25], dtype=np.float64),
        )
        self.assertEqual(
            plan.sha256,
            "6c3e0844fe533f93d83249f31973febe"
            "11650067d4ba44a9034cdf72b54bb1c9",
        )


if __name__ == "__main__":
    unittest.main()
