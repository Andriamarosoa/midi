from __future__ import annotations

import unittest

from src.polyphonic.tflite_runtime import resolve_tflite_threads


class TFLiteRuntimeThreadTests(unittest.TestCase):
    def test_null_recommendation_falls_back_to_one_thread(self) -> None:
        self.assertEqual(
            resolve_tflite_threads(
                {"recommended_tflite_threads": None},
                None,
            ),
            1,
        )

    def test_explicit_thread_count_overrides_metadata(self) -> None:
        self.assertEqual(
            resolve_tflite_threads(
                {"recommended_tflite_threads": None},
                3,
            ),
            3,
        )

    def test_non_positive_thread_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            resolve_tflite_threads(
                {"recommended_tflite_threads": 0},
                None,
            )


if __name__ == "__main__":
    unittest.main()
