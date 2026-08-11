from pathlib import Path
import unittest
from unittest import mock
from src.polyphonic import harmonic_censoring_h26_scientific_runner_dormant as runner

class DormantScientificRunnerTests(unittest.TestCase):
    def test_fake_sequence_only(self):
        p0=mock.Mock(return_value="zero"); p1=mock.Mock(return_value="one"); p2=mock.Mock(return_value="two")
        trace=runner.exercise_h26_scientific_sequence_with_fakes(fake_population_identity="fake:synthetic-contract-test",fake_p0=p0,fake_p1=p1,fake_p2=p2)
        p0.assert_called_once_with(); p1.assert_called_once_with("zero"); p2.assert_called_once_with("one")
        self.assertEqual(trace.stages,("P0_FAKE","P1_FAKE","P2_FAKE")); self.assertFalse(trace.locked_test_used); self.assertFalse(trace.real_science_executed)
    def test_non_fake_population_rejected_before_stages(self):
        calls=[mock.Mock(),mock.Mock(),mock.Mock()]
        with self.assertRaises(ValueError): runner.exercise_h26_scientific_sequence_with_fakes(fake_population_identity="real:forbidden",fake_p0=calls[0],fake_p1=calls[1],fake_p2=calls[2])
        for call in calls: call.assert_not_called()
    def test_real_engine_and_locked_test_symbols_absent(self):
        source=Path(runner.__file__).read_text(); self.assertNotIn("harmonic_censoring_h26_engine",source); self.assertNotIn("harmonic_censoring_h26_recomputer",source); self.assertNotIn("locked_test",source.replace("locked_test_used",""))
if __name__=="__main__": unittest.main()
