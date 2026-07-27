from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from src.polyphonic.data import ManifestItem
from src.polyphonic.evaluate_events import NoteInterval, match_notes
from src.polyphonic.validate_product_inverse import (
    select_held_out_recordings,
    spectral_inverse_diagnostics,
)


class ProductInverseTests(unittest.TestCase):
    def test_only_locked_test_items_can_be_selected(self) -> None:
        train = ManifestItem(
            "train", "d", "p", "g1", "train", Path("a"), "",
            Path("a"), "c", "l"
        )
        test = ManifestItem(
            "test", "d", "p", "g2", "test", Path("b"), "",
            Path("b"), "c", "l"
        )
        selected = select_held_out_recordings(
            [train, test], 1, score=lambda item: 100 if item.split == "train" else 1
        )
        self.assertEqual([item.source_id for item in selected], ["test"])

    def test_excluded_groups_cannot_enter_final_test(self) -> None:
        first = ManifestItem(
            "first", "d", "p", "contaminated", "test", Path("a"), "",
            Path("a"), "c", "l"
        )
        second = ManifestItem(
            "second", "d", "p", "clean", "test", Path("b"), "",
            Path("b"), "c", "l"
        )
        selected = select_held_out_recordings(
            [first, second], 1, score=lambda item: 100,
            excluded_group_ids={"contaminated"},
        )
        self.assertEqual([item.source_id for item in selected], ["second"])

    def test_spectral_diagnostic_supports_an_aligned_sine_note(self) -> None:
        sample_rate = 44_100
        time = np.arange(sample_rate, dtype=np.float64) / sample_rate
        waveform = np.sin(2.0 * np.pi * 440.0 * time).astype(np.float32)
        reference = [NoteInterval(69, 0.25, 0.75)]
        estimated = [NoteInterval(69, 0.25, 0.75)]
        report, _, missing = spectral_inverse_diagnostics(
            waveform, sample_rate, 256, reference, estimated,
            match_notes(reference, estimated),
        )
        self.assertEqual(
            report["generated_to_wav"]["class_counts"],
            {"annotation_supported": 1},
        )
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
