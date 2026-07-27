from __future__ import annotations

import unittest
from pathlib import Path

from src.polyphonic.build_idmt import exercise_group, split_group


class IdmtBuilderTests(unittest.TestCase):
    def test_repeated_instrument_capture_ids_share_exercise_group(self) -> None:
        first = Path("dataset1/setup_a/annotation/G53-40100-1111-00001.xml")
        second = Path("dataset1/setup_b/annotation/G53-40100-1111-235.xml")
        self.assertEqual(exercise_group(first), exercise_group(second))

    def test_chord_stems_share_group_across_setups(self) -> None:
        first = Path("dataset1/setup_a/annotation/1-E1-Major 00.xml")
        second = Path("dataset1/setup_b/annotation/1-E1-Major 00.xml")
        self.assertEqual(exercise_group(first), exercise_group(second))

    def test_split_is_stable_per_group(self) -> None:
        group = "idmt_dataset1_g53_40100_1111"
        self.assertEqual(split_group(group, 42), split_group(group, 42))
        self.assertIn(split_group(group, 42), {"train", "validation", "test"})


if __name__ == "__main__":
    unittest.main()
