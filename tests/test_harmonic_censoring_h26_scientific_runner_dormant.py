from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h26_scientific_runner_dormant as runner

class DormantScientificRunnerTests(unittest.TestCase):
    def test_fake_sequence_only(self):
        fake_sequence = runner.make_h26_fake_only_sequence(
            fake_population_identity="fake:synthetic-contract-test"
        )
        trace = runner.exercise_h26_scientific_sequence_with_fakes(
            fake_sequence=fake_sequence
        )
        self.assertEqual(trace.stages, ("P0_FAKE", "P1_FAKE", "P2_FAKE"))
        self.assertEqual(
            trace.results,
            (
                "P0_FAKE_COMPLETE",
                ("P1_FAKE_COMPLETE", "P0_FAKE_COMPLETE"),
                (
                    "P2_FAKE_COMPLETE",
                    ("P1_FAKE_COMPLETE", "P0_FAKE_COMPLETE"),
                ),
            ),
        )
        self.assertFalse(trace.locked_test_used)
        self.assertFalse(trace.real_science_executed)

    def test_non_fake_population_rejected_before_stages(self):
        with self.assertRaises(ValueError):
            runner.make_h26_fake_only_sequence(
                fake_population_identity="real:forbidden"
            )

    def test_arbitrary_callable_rejected_before_first_call(self):
        class Probe:
            def __init__(self):
                self.calls = 0

            def __call__(self):
                self.calls += 1

        probe = Probe()
        with self.assertRaises(TypeError):
            runner.exercise_h26_scientific_sequence_with_fakes(
                fake_sequence=probe
            )
        self.assertEqual(probe.calls, 0)

    def test_real_engine_and_locked_test_symbols_absent(self):
        source = Path(runner.__file__).read_text()
        self.assertNotIn("harmonic_censoring_h26_engine", source)
        self.assertNotIn("harmonic_censoring_h26_recomputer", source)
        self.assertNotIn("Callable", source)
        self.assertNotIn("locked_test", source.replace("locked_test_used", ""))
if __name__=="__main__": unittest.main()
