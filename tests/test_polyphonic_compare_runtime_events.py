from __future__ import annotations

import copy
import unittest

from src.polyphonic.compare_runtime_events import event_policy_passes


def _report() -> dict:
    metric = {
        "f1": 0.5, "false_positive_notes": 100, "missing_notes": 100,
    }
    dataset = {"onset": {"f1": 0.5}, "onset_offset": {"f1": 0.3}}
    return {
        "onset": dict(metric),
        "onset_offset": dict(metric),
        "dataset_metrics": {"per_dataset": {"source": dataset}},
        "retriggers": 100,
        "diagnostics": {"excess_fragments": 100},
    }


class RuntimeEventPolicyTests(unittest.TestCase):
    def test_identical_runtime_passes(self) -> None:
        baseline = _report()
        self.assertTrue(event_policy_passes(baseline, copy.deepcopy(baseline)))

    def test_dataset_f1_drop_fails(self) -> None:
        baseline = _report()
        candidate = copy.deepcopy(baseline)
        candidate["dataset_metrics"]["per_dataset"]["source"]["onset"][
            "f1"
        ] -= 0.006
        self.assertFalse(event_policy_passes(baseline, candidate))

    def test_count_regression_above_one_percent_fails(self) -> None:
        baseline = _report()
        candidate = copy.deepcopy(baseline)
        candidate["onset"]["false_positive_notes"] += 2
        self.assertFalse(event_policy_passes(baseline, candidate))


if __name__ == "__main__":
    unittest.main()
