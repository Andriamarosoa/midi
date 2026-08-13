from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json"
ACTIVATION_CONTRACT = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json"
ACTIVATION_SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class H27ActivationCapableMaterializerAuthorityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_seal_binds_exact_contract_without_self_hash(self) -> None:
        self.assertNotIn(b"\r", self.raw + self.seal_raw)
        self.assertNotIn("seal_sha256", self.seal)
        binding = self.seal["contract"]
        self.assertEqual(binding["git_blob_sha1"], _blob(self.raw))
        self.assertEqual(binding["size_bytes"], len(self.raw))
        self.assertEqual(binding["raw_sha256"], hashlib.sha256(self.raw).hexdigest())

    def test_future_target_is_distinct_absent_and_non_authorized(self) -> None:
        future = self.contract["future_activation_capable_materializer"]
        self.assertFalse(future["exists"])
        self.assertFalse(future["implementation_authorized"])
        for field in ("path", "reviewed_commit", "git_blob_sha1", "raw_sha256", "external_seal_path", "external_seal_sha256"):
            self.assertIsNone(future[field])
        self.assertTrue(future["must_be_distinct_module"])
        self.assertEqual(future["allowed_difference_from_dormant_logic"], "authority boundary plumbing only")

    def test_normative_activation_contract_and_seal_are_exactly_bound(self) -> None:
        source = self.contract["normative_activation_binding_source"]
        for binding, path in ((source["contract"], ACTIVATION_CONTRACT), (source["external_seal"], ACTIVATION_SEAL)):
            raw = path.read_bytes()
            self.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(binding["git_blob_sha1"], _blob(raw))
            self.assertEqual(binding["size_bytes"], len(raw))
            self.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())

    def test_all_scientific_bindings_are_derived_without_override(self) -> None:
        source = self.contract["normative_activation_binding_source"]
        activation = json.loads(ACTIVATION_CONTRACT.read_bytes())
        derivations = source["required_exact_derivations"]
        self.assertEqual(
            set(derivations),
            {"sealed_runtime_source", "runtime_exact", "process_environment_exact", "sealed_h27_inputs", "population_namespace", "expected_counts", "fixed_destinations"},
        )
        self.assertEqual(activation["population_namespace"], self.contract["population_namespace"])
        self.assertEqual(activation["atomic_publication"]["expected_record_count"], 124)
        self.assertEqual(activation["atomic_publication"]["expected_baseline_record_count"], 17)
        self.assertEqual(activation["atomic_publication"]["expected_p2_record_count"], 107)
        self.assertEqual(activation["atomic_publication"]["final_destination"], "/Users/amcarene/h27-admin/population/h27-synthetic-v1")
        self.assertEqual(activation["atomic_publication"]["staging_destination"], "/Users/amcarene/h27-admin/population/.h27-synthetic-v1.staging")
        self.assertEqual(len(activation["sealed_h27_inputs"]), 5)
        self.assertTrue(source["all_derived_values_must_equal_the_linked_contract_exactly"])
        self.assertTrue(source["caller_file_environment_or_runtime_override_forbidden"])
        self.assertTrue(source["missing_mismatched_or_unsealed_source_is_terminal_before_claim"])

    def test_fail_closed_order_places_claim_before_science(self) -> None:
        order = self.contract["fail_closed_order"]
        claim = order.index("create durable claim with O_EXCL and fsync")
        capability = order.index("construct process-local noncopyable capability")
        science = order.index("only then import or receive NumPy and inspect H27 plan for production")
        self.assertLess(claim, capability)
        self.assertLess(capability, science)
        self.assertTrue(self.contract["claim_contract"]["created_before_numpy_import_or_first_scientific_filesystem_access"])
        self.assertFalse(self.contract["claim_contract"]["retry_allowed"])

    def test_direct_calls_forge_and_rebinding_are_contractually_closed(self) -> None:
        defence = self.contract["direct_call_and_rebinding_defence"]
        self.assertTrue(defence["all_waveform_payload_index_and_publish_helpers_require_capability_first"])
        self.assertTrue(defence["capability_guard_must_validate_external_identity_attestation"])
        self.assertTrue(defence["monkeypatch_rebinding_or_replacement_of_guard_helpers_or_publisher_forbidden"])
        required = self.contract["required_adversarial_tests"]
        for value in ("forged capability via object.__new__", "module registry rebinding", "guard helper monkeypatch", "direct call of every production helper", "post-claim code identity drift"):
            self.assertIn(value, required)

    def test_every_operational_state_remains_false(self) -> None:
        for field, value in self.contract["current_state"].items():
            self.assertIs(value, False, field)
        for field, value in self.seal.items():
            if field.endswith("_exists") or field.endswith("_authorized") or field in {"materialization_authorized", "scientific_execution_authorized", "locked_test_used"}:
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
