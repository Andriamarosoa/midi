from dataclasses import FrozenInstanceError
import unittest
from unittest import mock
from src.polyphonic import harmonic_censoring_h26_materialization_authority_gate as gate

class MaterializationGateTests(unittest.TestCase):
    def test_validators_order_and_immutable_plan(self):
        proof=mock.Mock(runtime_execution_terminal_status="QUALIFIED")
        authority=mock.Mock(authority_id="id",raw_sha256="a"*64)
        with mock.patch.object(gate,"load_materialization_operationalization_contract_external_seal"), mock.patch.object(gate,"validate_artificial_materialization_runtime_execution_proof",return_value=proof) as pv, mock.patch.object(gate,"validate_artificial_materialization_authority_artifact",return_value=authority) as av:
            result=gate.plan_h26_materialization(materialization_authority={"absolute_destination":"/tmp/future"},runtime_authority={},runtime_claim={},runtime_evidence={},runtime_receipt={},runtime_authority_raw_sha256="a"*64,runtime_claim_raw_sha256="b"*64,runtime_evidence_raw_sha256="c"*64,runtime_receipt_raw_sha256="d"*64,runtime_record=object())
        pv.assert_called_once(); av.assert_called_once(); self.assertEqual(result.runtime_terminal_status,"QUALIFIED")
        with self.assertRaises(FrozenInstanceError): result.destination="changed"

    def test_proof_failure_prevents_authority_validation(self):
        with mock.patch.object(gate,"load_materialization_operationalization_contract_external_seal"), mock.patch.object(gate,"validate_artificial_materialization_runtime_execution_proof",side_effect=ValueError("not qualified")), mock.patch.object(gate,"validate_artificial_materialization_authority_artifact") as av:
            with self.assertRaises(ValueError): gate.plan_h26_materialization(materialization_authority={},runtime_authority={},runtime_claim={},runtime_evidence={},runtime_receipt={},runtime_authority_raw_sha256="a"*64,runtime_claim_raw_sha256="b"*64,runtime_evidence_raw_sha256="c"*64,runtime_receipt_raw_sha256="d"*64,runtime_record=None)
        av.assert_not_called()

if __name__=="__main__": unittest.main()
