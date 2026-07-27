from __future__ import annotations

import numpy as np

from .ring_buffer import MonoRingBuffer


def test_progressive_writes() -> None:
    ring = MonoRingBuffer(8)
    output = np.empty(8, dtype=np.float32)

    ring.write(np.array([1, 2, 3], dtype=np.float32))
    actual = ring.copy_latest_into(output).copy()
    expected = np.array([0, 0, 0, 0, 0, 1, 2, 3], dtype=np.float32)
    np.testing.assert_array_equal(actual, expected)

    ring.write(np.array([4, 5, 6, 7], dtype=np.float32))
    actual = ring.copy_latest_into(output).copy()
    expected = np.array([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.float32)
    np.testing.assert_array_equal(actual, expected)

    ring.write(np.array([8, 9, 10], dtype=np.float32))
    actual = ring.copy_latest_into(output).copy()
    expected = np.array([3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float32)
    np.testing.assert_array_equal(actual, expected)


def test_latest_short_window() -> None:
    ring = MonoRingBuffer(8)
    ring.write(np.arange(10, dtype=np.float32))

    output = np.empty(4, dtype=np.float32)
    actual = ring.copy_latest_into(output).copy()
    expected = np.array([6, 7, 8, 9], dtype=np.float32)
    np.testing.assert_array_equal(actual, expected)


if __name__ == "__main__":
    test_progressive_writes()
    test_latest_short_window()
    print("Tous les tests ring buffer sont OK.")
