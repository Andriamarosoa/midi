from __future__ import annotations

from pathlib import Path
import inspect
import unittest

from src.polyphonic import run_harmonic_censoring_h23_synthetic as runner
from src.polyphonic.harmonic_censoring_h23 import load_h23_harness_plan


class HarmonicCensoringH23ExactOracleRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h23_harness_plan(cls.root)

    def test_evaluator_and_recomputer_registries_are_exactly_72_of_72(self) -> None:
        expected = set(self.plan.test_ids)
        self.assertEqual(len(expected), 72)
        self.assertEqual(set(runner._H23_EXACT_EVALUATORS), expected)
        self.assertEqual(set(runner.EXACT_H23_ORACLE_REGISTRY), expected)
        self.assertEqual(
            {function.__name__ for function in runner._H23_EXACT_EVALUATORS.values()},
            {f"_measure_{test_id}" for test_id in expected},
        )

    def test_every_test_has_nonempty_exact_primary_and_inverse_measurements(self) -> None:
        for test_id in self.plan.test_ids:
            spec = runner.EXACT_H23_ORACLE_REGISTRY[test_id]
            with self.subTest(test_id=test_id):
                self.assertGreaterEqual(len(spec.primary), 1)
                self.assertGreaterEqual(len(spec.inverse), 1)
                self.assertEqual(
                    len({rule.name for rule in spec.primary}), len(spec.primary)
                )
                self.assertEqual(
                    len({rule.name for rule in spec.inverse}), len(spec.inverse)
                )

    def test_recomputer_rejects_missing_extra_or_wrong_measurement_keys(self) -> None:
        test = self.plan.tests[0]
        with self.assertRaisesRegex(ValueError, "primary/inverse only"):
            runner.recompute_h23_exact_oracle(
                test,
                {"primary": {}, "inverse": {}, "passed": True},
                plan_fixture_ids=self.plan.fixture_ids,
            )

    def test_recomputer_uses_json_types_not_python_bool_integer_aliasing(self) -> None:
        test = next(item for item in self.plan.tests if item.test_id == "A08")
        recomputed = runner.recompute_h23_exact_oracle(
            test,
            {
                "primary": {"maximum_future_sample_offset": False},
                "inverse": {"injected_future_sample_offset": 1},
            },
            plan_fixture_ids=self.plan.fixture_ids,
        )
        self.assertFalse(recomputed.primary_pass)
        self.assertTrue(recomputed.inverse_pass)
        self.assertFalse(recomputed.final_pass)
        with self.assertRaisesRegex(ValueError, "primary measurement keys mismatch"):
            runner.recompute_h23_exact_oracle(
                test,
                {"primary": {}, "inverse": {"mutated_edges": [[2, 1]]}},
                plan_fixture_ids=self.plan.fixture_ids,
            )

    def test_runner_has_no_test_family_prefix_fallback(self) -> None:
        source = (
            self.root
            / "src/polyphonic/run_harmonic_censoring_h23_synthetic.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("test.test_id.startswith", source)
        self.assertNotIn("_legacy_unapproved_h23_generic_evaluator", source)
        self.assertNotIn("inverse_mutation_detected", source)

    def test_semantic_evaluators_execute_their_preregistered_procedures(self) -> None:
        required_calls = {
            "D04": (
                "_projected_harmonic_waveform",
                "_spectral_representation",
                "_scalar_pitch_curves",
            ),
            "D08": ("_replay_window_boundary_state_machine",),
            "K01": ("_fixture_sources", "_pitch_cardinalities_for_sources"),
            "K02": ("_fixture_sources",),
            "G02": ("_technique_offsets", "_soft_continuity_decision"),
            "G04": ("_fixture_waveform", "previous_energy", "repeated_energy"),
            "G05": ("_pitch_cardinalities_for_sources",),
            "G07": ("_source_birth_tuple",),
            "G08": ("_fixture_sources", "math.log2"),
            "P04": ("time.perf_counter_ns", "_spectral_representation", "stress_cutoffs"),
            "TS01": ("evaluate_grid(cutoff_6)", "evaluate_grid(cutoff_16)", "evaluate_grid(cutoff_32)"),
        }
        for test_id, needles in required_calls.items():
            source = inspect.getsource(runner._H23_EXACT_EVALUATORS[test_id])
            with self.subTest(test_id=test_id):
                for needle in needles:
                    self.assertIn(needle, source)

    def test_named_inverse_examples_are_computed_not_literal_answers(self) -> None:
        requirements = {
            "A02": "_spectral_representation",
            "A05": "collapsed.append",
            "D12": "has_rebound(mutated)",
            "F03": "_nnls_active_set",
            "P04": "stress = run(stress_cutoffs)",
        }
        for test_id, needle in requirements.items():
            source = inspect.getsource(runner._H23_EXACT_EVALUATORS[test_id])
            with self.subTest(test_id=test_id):
                self.assertIn(needle, source)


if __name__ == "__main__":
    unittest.main()
