from __future__ import annotations

import unittest

from src.polyphonic.select_final_checkpoint import (
    causal_gate_candidate_eligible,
    event_selection_key,
    event_selection_metric_source,
    limit_candidates_for_evaluation,
)


class SelectFinalCheckpointTests(unittest.TestCase):
    def test_causal_gate_candidate_requires_explicit_pass(self) -> None:
        self.assertTrue(causal_gate_candidate_eligible({
            "strictly_causal_noteon": {
                "available": True,
                "gate": {"passed": True, "configured_checks": 1},
            },
        }))
        self.assertFalse(causal_gate_candidate_eligible({
            "strictly_causal_noteon": {
                "available": True,
                "gate": {"passed": False, "configured_checks": 1},
            },
        }))
        self.assertFalse(causal_gate_candidate_eligible({
            "strictly_causal_noteon": {
                "available": True,
                "gate": {"passed": True, "configured_checks": 0},
            },
        }))
        self.assertFalse(causal_gate_candidate_eligible({}))

    @staticmethod
    def _ranking_candidate(index: int) -> dict:
        return {
            "checkpoint": f"epoch-{index}.keras",
            "frame_f1": float(index),
            "onset_f1": float(10 - index),
            "harmonic_amplitude_mae": float(index),
            "harmonic_offset_normalized_mae": float(10 - index),
        }

    def test_causal_gate_disables_pre_evaluation_candidate_cap(self) -> None:
        candidates = [
            self._ranking_candidate(index) for index in range(6)
        ]

        limited = limit_candidates_for_evaluation(
            candidates, 2, causal_gate_enabled=True,
        )

        self.assertEqual(limited, candidates)

    def test_candidate_cap_is_positive_and_fills_requested_size(self) -> None:
        candidates = [
            self._ranking_candidate(index) for index in range(8)
        ]
        with self.assertRaisesRegex(ValueError, "must be positive"):
            limit_candidates_for_evaluation(
                candidates, 0, causal_gate_enabled=False,
            )

        limited = limit_candidates_for_evaluation(
            candidates, 6, causal_gate_enabled=False,
        )

        self.assertEqual(len(limited), 6)

    @staticmethod
    def _row(
        global_f1: float,
        dataset_f1: float,
        scope: str = "weighted",
        dataset_offset_f1: float = 0.4,
    ) -> dict:
        summary = {
            "onset": {
                "f1": dataset_f1,
                "precision": dataset_f1,
                "recall": dataset_f1,
            },
            "onset_offset": {"f1": dataset_offset_f1},
        }
        return {
            "onset": {
                "f1": global_f1,
                "precision": global_f1,
                "recall": global_f1,
                "onset_error_p95_absolute_ms": 20.0,
            },
            "onset_offset": {"f1": global_f1},
            "dataset_metrics": {
                "weighted": summary if scope == "weighted" else None,
                "macro": summary,
            },
        }

    def test_note_f1_wins_before_secondary_metrics(self) -> None:
        def row(f1: float, offset: float, precision: float):
            return {
                "onset": {
                    "f1": f1, "precision": precision, "recall": 0.8,
                    "onset_error_p95_absolute_ms": 20.0,
                },
                "onset_offset": {"f1": offset},
            }

        higher_f1 = row(0.70, 0.50, 0.60)
        prettier_secondary = row(0.69, 0.90, 0.95)
        self.assertGreater(
            event_selection_key(higher_f1),
            event_selection_key(prettier_secondary),
        )

    def test_offset_breaks_equal_onset_f1(self) -> None:
        base = {
            "onset": {
                "f1": 0.7, "precision": 0.7, "recall": 0.7,
                "onset_error_p95_absolute_ms": 20.0,
            },
        }
        first = {**base, "onset_offset": {"f1": 0.6}}
        second = {**base, "onset_offset": {"f1": 0.5}}
        self.assertGreater(event_selection_key(first), event_selection_key(second))

    def test_weighted_dataset_f1_wins_over_higher_global_f1(self) -> None:
        globally_pretty = self._row(global_f1=0.95, dataset_f1=0.40)
        dataset_balanced = self._row(global_f1=0.70, dataset_f1=0.60)
        self.assertGreater(
            event_selection_key(dataset_balanced),
            event_selection_key(globally_pretty),
        )
        self.assertEqual(
            event_selection_metric_source(dataset_balanced),
            "dataset_weighted",
        )

    def test_macro_dataset_f1_is_used_when_weights_are_absent(self) -> None:
        globally_pretty = self._row(
            global_f1=0.95, dataset_f1=0.40, scope="macro",
        )
        dataset_balanced = self._row(
            global_f1=0.70, dataset_f1=0.60, scope="macro",
        )
        self.assertGreater(
            event_selection_key(dataset_balanced),
            event_selection_key(globally_pretty),
        )
        self.assertEqual(
            event_selection_metric_source(dataset_balanced),
            "dataset_macro",
        )

    def test_secondary_metrics_use_the_same_dataset_scope(self) -> None:
        higher_dataset_offset = self._row(
            global_f1=0.5, dataset_f1=0.6, dataset_offset_f1=0.7,
        )
        higher_global_offset = self._row(
            global_f1=0.9, dataset_f1=0.6, dataset_offset_f1=0.5,
        )
        self.assertGreater(
            event_selection_key(higher_dataset_offset),
            event_selection_key(higher_global_offset),
        )


if __name__ == "__main__":
    unittest.main()
