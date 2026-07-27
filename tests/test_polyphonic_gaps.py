from __future__ import annotations

import unittest

from src.polyphonic.build_gaps import assign_splits


class GapsPolyphonicBuilderTests(unittest.TestCase):
    def test_validation_group_never_leaks_into_train_or_official_test(self) -> None:
        rows = [
            {"id": "a1", "split": "train", "scorehash": "A"},
            {"id": "a2", "split": "train", "scorehash": "A"},
            {"id": "b", "split": "train", "scorehash": "B"},
            {"id": "c", "split": "test", "scorehash": "C"},
            {"id": "unused", "split": "", "scorehash": "D"},
        ]
        split, report = assign_splits(rows, validation_recordings=1, seed=42)
        self.assertEqual(split["a1"], split["a2"])
        self.assertEqual(split["c"], "test")
        self.assertNotIn("unused", split)
        self.assertEqual(report["group_overlap"], [])

    def test_exact_case_scorehashes_remain_distinct(self) -> None:
        rows = [
            {"id": "upper", "split": "train", "scorehash": "Score"},
            {"id": "lower", "split": "test", "scorehash": "score"},
        ]
        split, _ = assign_splits(rows, validation_recordings=1, seed=1)
        self.assertEqual(split["lower"], "test")
        self.assertEqual(split["upper"], "validation")


if __name__ == "__main__":
    unittest.main()
