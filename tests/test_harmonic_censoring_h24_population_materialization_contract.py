import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "configs/harmonic_censoring_h24_population_materialization_one_shot_contract.json"


def _load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


class H24PopulationMaterializationContractTests(unittest.TestCase):
    def test_contract_is_definition_only_and_binds_approved_harness(self):
        contract = _load_contract()
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["status"], "contract_only_external_review_required")
        self.assertEqual(
            contract["authorization_basis"]["reviewed_harness_commit"],
            "1b6aa27536dd5bfceba62d6bc5c9a499b4c11f18",
        )
        scope = contract["scope"]
        self.assertTrue(scope["contract_only"])
        for key, value in scope.items():
            if key != "contract_only":
                self.assertFalse(value, key)

    def test_all_sealed_input_hashes_match_exact_bytes(self):
        contract = _load_contract()
        for name, binding in contract["sealed_inputs"].items():
            if "raw_sha256" not in binding:
                continue
            raw = (ROOT / binding["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), binding["raw_sha256"], name)

    def test_population_resolution_is_exact_and_nonselectable(self):
        contract = _load_contract()["population_resolution"]
        self.assertEqual(contract["required_namespace"], "H24_SYNTHETIC_V1")
        self.assertEqual(contract["required_fixture_count"], 175)
        self.assertEqual(contract["recipe_count"], 175)
        self.assertTrue(contract["omission_addition_duplicate_or_reordering_forbidden"])
        self.assertTrue(contract["caller_fixture_selection_forbidden"])
        self.assertTrue(contract["predecessor_waveform_seed_or_outcome_reuse_forbidden"])

    def test_waveform_algorithm_closes_all_17_variant_axes(self):
        contract = _load_contract()["deterministic_waveform_algorithm_v1"]
        population = json.loads(
            (ROOT / "configs/harmonic_censoring_h24_population_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        axes = {item["variant_axis"] for item in population["fixture_specifications"] if item["variant_axis"]}
        self.assertEqual(set(contract["variant_dispatch_order"]), axes)
        self.assertEqual(set(contract["variant_semantics"]), axes)
        self.assertEqual(contract["sample_count"], 12544)
        self.assertEqual(contract["array_dtype_during_synthesis"], "numpy.float64")
        self.assertTrue(contract["seed_must_equal_manifest_value"])
        self.assertTrue(contract["nonfinite_output_forbidden"])

    def test_seed_rule_recomputes_every_manifest_seed(self):
        contract = _load_contract()["deterministic_waveform_algorithm_v1"]
        population = json.loads(
            (ROOT / "configs/harmonic_censoring_h24_population_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            contract["seed_rule"],
            "unsigned_little_endian_uint64(first_8_bytes(SHA256(UTF8('H24|'+fixture_id))))",
        )
        for fixture in population["fixture_specifications"]:
            digest = hashlib.sha256(("H24|" + fixture["fixture_id"]).encode("utf-8")).digest()
            self.assertEqual(int.from_bytes(digest[:8], "little", signed=False), fixture["synthesis_seed"])

    def test_materialized_bytes_and_index_are_exactly_closed(self):
        contract = _load_contract()
        materialized = contract["materialized_fixture_bytes"]
        self.assertEqual(materialized["waveform_extension"], ".f64le")
        self.assertEqual(materialized["waveform_byte_count"], 12544 * 8)
        self.assertEqual(materialized["expected_files_per_fixture"], 3)
        self.assertTrue(materialized["additional_per_fixture_files_forbidden"])
        index = contract["population_index_contract"]
        self.assertEqual(index["line_count"], 175)
        self.assertEqual(len(index["exact_fields"]), 13)
        self.assertTrue(index["additional_fields_forbidden"])
        self.assertTrue(index["all_referenced_files_must_be_reopened_and_rehashed_before_publication"])

    def test_receipt_is_non_scientific_and_exact(self):
        contract = _load_contract()
        receipt = contract["population_receipt_contract"]
        self.assertEqual(receipt["fixed_values"]["fixture_count"], 175)
        self.assertEqual(receipt["fixed_values"]["scientific_tests_executed"], 0)
        self.assertFalse(receipt["fixed_values"]["real_data_used"])
        self.assertFalse(receipt["fixed_values"]["H17_population_used"])
        self.assertFalse(receipt["fixed_values"]["locked_test_used"])
        separation = contract["separation_from_scientific_execution"]
        self.assertTrue(separation["materialization_receipt_is_not_scientific_evidence"])
        self.assertTrue(separation["P0_P1_P2_remain_forbidden_after_materialization"])

    def test_claim_is_durable_before_numpy_and_is_irrevocably_one_shot(self):
        contract = _load_contract()
        boundary = contract["one_shot_consumption_boundary"]
        self.assertEqual(boundary["population_id"], "H24_SYNTHETIC_V1")
        self.assertTrue(boundary["claim_must_be_durable_before_numpy_import"])
        self.assertTrue(boundary["claim_must_be_durable_before_first_waveform_allocation_or_synthesis"])
        self.assertTrue(boundary["marker_existence_alone_means_consumed_even_if_partial_or_corrupt"])
        self.assertTrue(boundary["failure_after_O_EXCL_keeps_population_consumed"])
        self.assertFalse(boundary["automatic_retry_allowed"])
        self.assertFalse(boundary["manual_same_population_retry_allowed"])
        self.assertTrue(boundary["claim_or_marker_is_not_implemented_or_created_by_this_contract"])

    def test_partial_output_can_never_become_authoritative(self):
        contract = _load_contract()
        partial = contract["interruption_and_partial_output"]
        self.assertTrue(partial["staging_is_private_non_authoritative"])
        self.assertTrue(partial["partial_staging_must_never_be_renamed_to_success"])
        self.assertTrue(partial["success_directory_must_be_absent_on_failure"])
        self.assertTrue(partial["repair_resume_or_retry_forbidden"])
        sequence = contract["future_materialization_sequence"]["exact_order"]
        self.assertLess(sequence.index("durable_exclusive_claim"), sequence.index("materialize_175_fixtures_in_manifest_order"))
        self.assertEqual(sequence[-1], "stop_without_scientific_execution")

    def test_contract_does_not_add_an_operational_or_scientific_source(self):
        contract = _load_contract()
        allowed = set(contract["contract_definition_allowed_files"])
        self.assertFalse(any(path.startswith("src/") for path in allowed))
        self.assertIn("src/polyphonic/harmonic_censoring_h24.py", contract["contract_definition_forbidden_files"])
        self.assertIn("src/polyphonic/harmonic_censoring_h24_operators.py", contract["contract_definition_forbidden_files"])
        self.assertIn("separate authorization seal binding exact implementation commit source blob contract SHA and fixed paths", contract["future_authorization_sequence"])


if __name__ == "__main__":
    unittest.main()
