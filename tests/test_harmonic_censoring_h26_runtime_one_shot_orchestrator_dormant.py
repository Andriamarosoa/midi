from pathlib import Path
import unittest
from unittest import mock
from src.polyphonic import harmonic_censoring_h26_runtime_one_shot_orchestrator as orchestrator

class RuntimeOrchestratorTests(unittest.TestCase):
    def test_exact_order_and_one_fake_observer_call(self):
        order=[]
        def mark(name, result=None):
            def fn(*args,**kwargs): order.append(name); return result
            return fn
        with mock.patch.object(orchestrator,"load_runtime_one_shot_orchestration_contract_external_seal",side_effect=mark("seal",{})), mock.patch.object(orchestrator,"validate_artificial_runtime_qualification_operational_activation",side_effect=mark("activation")), mock.patch.object(orchestrator.primitives,"validate_artificial_authority",side_effect=mark("authority")), mock.patch.object(orchestrator.primitives,"validate_artificial_claim",side_effect=mark("claim")), mock.patch.object(orchestrator.primitives,"validate_artificial_observer_entry_evidence",side_effect=mark("evidence")), mock.patch.object(orchestrator.primitives,"validate_artificial_terminal_execution_receipt",side_effect=mark("receipt")):
            result=orchestrator.orchestrate_h26_runtime_with_injected_observer(activation={},authority={},claim={},evidence={},receipt={},authority_raw_sha256="a"*64,claim_raw_sha256="b"*64,evidence_raw_sha256="c"*64,preflight=mark("preflight"),observer=mark("observer",None))
        self.assertEqual(order,["seal","activation","preflight","authority","claim","evidence","observer","receipt"])
        self.assertEqual(result.observer_invocations,1)

    def test_failure_stops_without_retry(self):
        observer=mock.Mock()
        with mock.patch.object(orchestrator,"load_runtime_one_shot_orchestration_contract_external_seal"), mock.patch.object(orchestrator,"validate_artificial_runtime_qualification_operational_activation",side_effect=ValueError("terminal")):
            with self.assertRaises(ValueError): orchestrator.orchestrate_h26_runtime_with_injected_observer(activation={},authority={},claim={},evidence={},receipt={},authority_raw_sha256="a"*64,claim_raw_sha256="b"*64,evidence_raw_sha256="c"*64,preflight=lambda:None,observer=observer)
        observer.assert_not_called()

    def test_real_observer_symbol_absent(self):
        source=Path(orchestrator.__file__).read_text()
        self.assertNotIn("observe_primary_runtime",source)
        self.assertNotIn("import numpy",source)

if __name__=="__main__": unittest.main()
