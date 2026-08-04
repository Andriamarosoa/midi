from __future__ import annotations

import unittest

from src.polyphonic.train import _rss_to_mib


class MacPortabilityTests(unittest.TestCase):
    def test_rss_bytes_are_normalized_on_macos(self) -> None:
        self.assertEqual(
            _rss_to_mib(512 * 1024**2, platform_name="darwin"),
            512.0,
        )

    def test_rss_kib_are_normalized_on_linux(self) -> None:
        self.assertEqual(
            _rss_to_mib(512 * 1024, platform_name="linux"),
            512.0,
        )


if __name__ == "__main__":
    unittest.main()
