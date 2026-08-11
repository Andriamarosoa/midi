from dataclasses import FrozenInstanceError
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation as activation
from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner as planner

def candidate():
    fields, _, fixed = activation._activation_rules(); value = dict(fixed)
    value.update(activation_id="placeholder", activation_contract_commit=activation.ACTIVATION_CONTRACT_COMMIT, activation_contract_raw_sha256=activation.ACTIVATION_CONTRACT_RAW_SHA256, administrative_root="/var/tmp/h26", issued_at="2026-08-11T20:00:00Z", issuer_identity="codex.h26")
    assert set(value) == set(fields)
    value["activation_id"] = activation.derive_runtime_qualification_operational_activation_id(value)
    return value

class IssuancePlannerTests(unittest.TestCase):
    def test_plan_is_exact_and_immutable(self):
        result = planner.plan_runtime_qualification_operational_activation_issuance(candidate())
        self.assertEqual(result.final_path, "/var/tmp/h26/activation/activation.json")
        self.assertTrue(result.canonical_bytes.endswith(b"\n"))
        with self.assertRaises(FrozenInstanceError): result.final_path = "changed"

    def test_seal_loaders_and_validator_are_mandatory(self):
        with mock.patch.object(planner, "load_runtime_qualification_operational_activation_issuance_contract_external_seal", wraps=planner.load_runtime_qualification_operational_activation_issuance_contract_external_seal) as issuance, mock.patch.object(planner, "load_issuer_implementation_contract_external_seal", wraps=planner.load_issuer_implementation_contract_external_seal) as implementation, mock.patch.object(planner, "validate_artificial_runtime_qualification_operational_activation", wraps=planner.validate_artificial_runtime_qualification_operational_activation) as validator:
            planner.plan_runtime_qualification_operational_activation_issuance(candidate())
        issuance.assert_called_once(); implementation.assert_called_once(); validator.assert_called_once()

    def test_bad_issuer_time_or_id_fails(self):
        for field, value in (("issuer_identity", " bad"), ("issued_at", "2026-02-30T00:00:00Z"), ("activation_id", "bad")):
            item = candidate(); item[field] = value
            if field != "activation_id": item["activation_id"] = activation.derive_runtime_qualification_operational_activation_id(item)
            with self.subTest(field=field), self.assertRaises(ValueError): planner.plan_runtime_qualification_operational_activation_issuance(item)

if __name__ == "__main__": unittest.main()
