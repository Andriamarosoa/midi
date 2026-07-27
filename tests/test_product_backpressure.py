from __future__ import annotations

import unittest

from src.product.backpressure import LiveBackpressure


class LiveBackpressureTests(unittest.TestCase):
    def test_skip_budget_never_exceeds_two_of_thirty_two(self) -> None:
        policy = LiveBackpressure(max_backlog_hops=3)
        decisions = [policy.decide(4) for _ in range(96)]
        for start in range(len(decisions) - 31):
            self.assertLessEqual(sum(decisions[start:start + 32]), 2)

    def test_no_skip_at_or_below_soft_limit(self) -> None:
        policy = LiveBackpressure(max_backlog_hops=3)
        self.assertFalse(any(policy.decide(3) for _ in range(40)))

    def test_dangerous_backlog_stops_processing(self) -> None:
        policy = LiveBackpressure(max_backlog_hops=3)
        with self.assertRaises(RuntimeError):
            policy.decide(17)


if __name__ == "__main__":
    unittest.main()
