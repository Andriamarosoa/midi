from pathlib import Path
import unittest
from unittest import mock
from src.polyphonic import harmonic_censoring_h26_materialization_orchestrator as orchestrator
from src.polyphonic.harmonic_censoring_h26_materialization_authority_gate import H26DormantMaterializationPlan

class MaterializationOrchestratorTests(unittest.TestCase):
    def test_gate_then_one_fake_materializer(self):
        plan=H26DormantMaterializationPlan("id","a"*64,"/tmp/future","QUALIFIED")
        fake=mock.Mock(return_value={"fake":True})
        with mock.patch.object(orchestrator,"plan_h26_materialization",return_value=plan) as gate:
            trace=orchestrator.orchestrate_h26_materialization_with_injected_materializer(materializer=fake,materialization_authority={})
        gate.assert_called_once(); fake.assert_called_once_with(plan); self.assertEqual(trace.materializer_invocations,1)
    def test_gate_failure_prevents_materializer(self):
        fake=mock.Mock()
        with mock.patch.object(orchestrator,"plan_h26_materialization",side_effect=ValueError("terminal")):
            with self.assertRaises(ValueError): orchestrator.orchestrate_h26_materialization_with_injected_materializer(materializer=fake)
        fake.assert_not_called()
    def test_real_materializer_not_imported(self):
        self.assertNotIn("materialize_h26_population",Path(orchestrator.__file__).read_text())
if __name__=="__main__": unittest.main()
