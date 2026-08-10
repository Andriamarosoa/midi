from __future__ import annotations

from pathlib import Path
import unittest

from src.polyphonic.harmonic_censoring_h24 import load_h24_dormant_harness_plan
from src.polyphonic.harmonic_censoring_h24_operators import (
    evaluate_h24_operator,
    evaluate_h24_rule,
    recompute_h24_persisted_evidence,
    strict_equal,
)


class HarmonicCensoringH24OperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h24_dormant_harness_plan(cls.root)

    def evaluate(self, operator: str, value: object, expected: object = None, *, rtol: float = 0.0, atol: float = 0.0) -> bool:
        return evaluate_h24_operator(
            operator,
            value,
            expected,
            rtol=rtol,
            atol=atol,
            plan_fixture_ids=self.plan.fixture_ids,
        )

    def test_strict_json_types_do_not_alias(self) -> None:
        self.assertFalse(strict_equal(True, 1))
        self.assertFalse(strict_equal(1, 1.0))
        self.assertTrue(strict_equal({"a": [1, False]}, {"a": [1, False]}))
        self.assertFalse(strict_equal(float("nan"), float("nan")))

    def test_closed_primitive_and_collection_operators(self) -> None:
        passing = {
            "eq": ([1, 2], [1, 2], 0.0, 0.0),
            "ne": (1, 2, 0.0, 0.0),
            "in": ("A", ["A", "B"], 0.0, 0.0),
            "gt": (2, 1, 0.0, 0.0),
            "ge": (1, 1, 0.0, 0.0),
            "le": (1, 2, 0.0, 0.0),
            "close": ([1.0], [1.0 + 1e-13], 0.0, 1e-12),
            "pair_equal": (["x", "x"], None, 0.0, 0.0),
            "pair_different": (["x", "y"], None, 0.0, 0.0),
            "close_pair": ([1.0, 1.0 + 1e-13], None, 0.0, 1e-12),
            "allclose_pair": ([[1.0], [1.0]], None, 0.0, 0.0),
            "all_equal": ([{"x": 1}, {"x": 1}], None, 0.0, 0.0),
            "not_all_equal": ([1, 2], None, 0.0, 0.0),
            "all_eq": (["A", "A"], "A", 0.0, 0.0),
            "all_in": (["A", "B"], ["A", "B"], 0.0, 0.0),
            "all_true": ([True, True], None, 0.0, 0.0),
            "none_in": ([1, 4], [2, 3], 0.0, 0.0),
            "all_exact_pairs": ([[1, 1], ["a", "a"]], None, 0.0, 0.0),
            "allclose_pairs": ([[1.0, 1.0], [2.0, 2.0]], None, 0.0, 0.0),
            "allclose_all": ([[1.0], [1.0]], None, 0.0, 0.0),
            "any_different_pair": ([[1, 1], [1, 2]], None, 0.0, 0.0),
            "strictly_gain_ordered": ([1.0, 2.0, 3.0], None, 0.0, 0.0),
            "nonincreasing": ([3.0, 2.0, 2.0], None, 0.0, 0.0),
            "support_formula_exact": ([[True, 440.0, True], [False, 23000.0, True]], None, 0.0, 0.0),
            "timing_components_exact": ({"window": 1, "hop": 1, "feature": 1, "inference": 1, "decoder": 1, "MIDI": 1}, None, 0.0, 0.0),
        }
        self.assertEqual(
            set(passing) | {"d08_traces_exact", "ts01_evidence_exact"},
            set(self.plan.operator_registry),
        )
        for operator, (value, expected, rtol, atol) in passing.items():
            with self.subTest(operator=operator):
                self.assertTrue(self.evaluate(operator, value, expected, rtol=rtol, atol=atol))

    def test_d08_and_ts01_specialized_operators(self) -> None:
        traces = []
        for offset in [0, 1, 255, 256, 3840, 4095]:
            event_hop = offset // 256
            states = ["INACTIVE"] + [
                "INACTIVE" if hop < event_hop else "PENDING_NEW" if hop == event_hop else "ACTIVE"
                for hop in range(16)
            ]
            if 4096 - offset < 3840:
                states.append("ACTIVE")
            traces.append(
                {
                    "offset": offset,
                    "event_hop": event_hop,
                    "states": states,
                    "target_category": "unused-by-operator",
                    "resolved_category": "unused-by-operator",
                    "pending_lifetime": 1,
                }
            )
        self.assertTrue(self.evaluate("d08_traces_exact", traces))
        split = len(self.plan.fixture_ids) // 2
        ts01 = {
            "all_fixture_ids": sorted(self.plan.fixture_ids),
            "passed_at_6": sorted(self.plan.fixture_ids)[:split],
            "failed_at_6": sorted(self.plan.fixture_ids)[split:],
            "rescued_at_16": [],
            "rescued_at_32": [],
            "regressed_at_16": [],
            "regressed_at_32": [],
        }
        self.assertTrue(self.evaluate("ts01_evidence_exact", ts01))

    def test_all_array_operators_reject_vacuous_evidence(self) -> None:
        for operator in (
            "all_equal",
            "not_all_equal",
            "all_eq",
            "all_in",
            "all_true",
            "none_in",
            "all_exact_pairs",
            "allclose_pairs",
            "allclose_all",
            "any_different_pair",
            "strictly_gain_ordered",
            "nonincreasing",
            "support_formula_exact",
            "d08_traces_exact",
        ):
            with self.subTest(operator=operator), self.assertRaises(ValueError):
                self.evaluate(operator, [], [] if operator in {"all_in", "none_in"} else None)

    def test_a02_cardinality_is_checked_before_operator(self) -> None:
        a02 = next(item for item in self.plan.tests if item.test_id == "H24-A02")
        rule = a02.as_dict()["evidence_schema"]["primary_rules"][0]
        with self.assertRaisesRegex(ValueError, "vacuous"):
            evaluate_h24_rule(self.plan, a02.test_id, "primary", rule, [])
        with self.assertRaisesRegex(ValueError, "exactly 42"):
            evaluate_h24_rule(self.plan, a02.test_id, "primary", rule, [[1.0, 1.0]])
        self.assertTrue(
            evaluate_h24_rule(
                self.plan,
                a02.test_id,
                "primary",
                rule,
                [[float(index), float(index)] for index in range(42)],
            )
        )

    def test_sentinel_expands_only_from_bound_population(self) -> None:
        rule = {
            "name": "fixture_ids",
            "operator": "eq",
            "expected": "__PLAN_FIXTURE_IDS__",
            "rtol": 0.0,
            "atol": 0.0,
        }
        self.assertTrue(
            evaluate_h24_rule(
                self.plan,
                "H24-I01",
                "primary",
                rule,
                list(self.plan.fixture_ids),
            )
        )
        bad = dict(rule)
        bad["expected"] = "__UNKNOWN__"
        with self.assertRaisesRegex(ValueError, "unknown evidence sentinel"):
            evaluate_h24_rule(
                self.plan, "H24-I01", "primary", bad, list(self.plan.fixture_ids)
            )

    def test_generic_recomputer_uses_operands_not_producer_verdict(self) -> None:
        evidence = {
            "primary": {"decision": "NO_BIRTH", "cardinalities": [1, 0, 1]},
            "inverse": {"without_old_F0_explanation": "LOST"},
        }
        result = recompute_h24_persisted_evidence(self.plan, "H24-S1", evidence)
        self.assertTrue(result.final_pass)
        with self.assertRaisesRegex(ValueError, "pass/verdict fields are forbidden"):
            recompute_h24_persisted_evidence(
                self.plan, "H24-S1", {**evidence, "verdict": "PASS"}
            )

    def test_unknown_operator_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown sealed operator"):
            self.evaluate("not_registered", 1, 1)

    def test_recomputer_rejects_non_json_operands(self) -> None:
        evidence = {
            "primary": {"decision": ("NO_BIRTH",), "cardinalities": [1, 0, 1]},
            "inverse": {"without_old_F0_explanation": "LOST"},
        }
        with self.assertRaisesRegex(ValueError, "JSON-native types only"):
            recompute_h24_persisted_evidence(self.plan, "H24-S1", evidence)


if __name__ == "__main__":
    unittest.main()
