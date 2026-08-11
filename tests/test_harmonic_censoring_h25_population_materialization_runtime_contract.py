import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "configs/harmonic_censoring_h25_population_materialization_runtime_provenance_encoding_contract.json"


def _load():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


class H25PopulationMaterializationRuntimeContractTests(unittest.TestCase):
    def test_contract_is_definition_only(self):
        contract = _load()
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(
            contract["status"],
            "contract_only_population_not_materialized_external_review_required",
        )
        scope = contract["scope"]
        self.assertTrue(scope["contract_only"])
        for key, value in scope.items():
            if key != "contract_only":
                self.assertFalse(value, key)
        self.assertFalse(any(path.startswith("src/") for path in contract["contract_definition_allowed_files"]))

    def test_all_sealed_inputs_match_exact_bytes(self):
        for name, binding in _load()["sealed_inputs"].items():
            raw = (ROOT / binding["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), binding["raw_sha256"], name)
            if "size_bytes" in binding:
                self.assertEqual(len(raw), binding["size_bytes"], name)

    def test_population_identity_and_counts_are_closed(self):
        contract = _load()["population_resolution"]
        population = json.loads(
            (ROOT / "configs/harmonic_censoring_h25_population_manifest.json").read_text(encoding="utf-8")
        )
        fixtures = json.loads(
            (ROOT / "configs/harmonic_censoring_h25_fixture_specifications.json").read_text(encoding="utf-8")
        )["fixtures"]
        ids = population["ordered_fixture_ids"]
        self.assertEqual(contract["population_namespace"], "H25_SYNTHETIC_V1")
        self.assertEqual(contract["fixture_count"], len(ids), 36)
        self.assertEqual([item["id"] for item in fixtures], ids)
        self.assertEqual(len(set(ids)), 36)
        self.assertTrue(contract["omission_addition_duplicate_reordering_or_caller_selection_forbidden"])

    def test_runtime_identity_is_exact_and_binds_openblas_not_accelerate(self):
        runtime = _load()["reference_runtime_identity"]
        self.assertEqual(runtime["platform"], {
            "os_system": "Darwin", "os_release": "24.5.0", "macos_version": "15.5",
            "machine": "arm64", "execution_device": "CPU", "gpu_count": 0,
        })
        self.assertEqual(runtime["python"]["version"], "3.11.9")
        self.assertEqual(runtime["numpy"]["distribution_version"], "1.26.4")
        backend = runtime["linear_algebra_backend"]
        self.assertEqual(backend["provider"], "OpenBLAS ILP64")
        self.assertFalse(backend["accelerate_framework_loaded"])
        self.assertRegex(backend["loaded_library_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(backend["loaded_library_size_bytes"], 23198400)
        expected_env = {
            "MIDI_FORCE_CPU": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
            "PYTHONHASHSEED": "0", "LC_ALL": "C", "LANG": "C", "TZ": "UTC",
        }
        self.assertEqual(runtime["process_environment_exact"], expected_env)

    def test_waveform_encoding_is_exact(self):
        encoding = _load()["fixture_artifact_encoding"]
        waveform = encoding["waveform"]
        self.assertEqual(waveform["sample_count"], 16640)
        self.assertEqual(waveform["serialized_dtype"], "<f8")
        self.assertEqual(waveform["byte_count"], 16640 * 8)
        self.assertEqual(waveform["header_bytes"], 0)
        self.assertTrue(waveform["pre_support_samples_0_through_8191_are_bit_exact_positive_zero"])
        self.assertTrue(waveform["negative_zero_nan_inf_or_trailing_bytes_forbidden"])
        self.assertEqual(encoding["files_per_fixture"], 3)
        self.assertTrue(encoding["additional_per_fixture_files_forbidden"])

    def test_fixture_and_target_json_schemas_are_closed(self):
        encoding = _load()["fixture_artifact_encoding"]
        self.assertEqual(
            encoding["fixture_record"]["exact_fields"],
            ["schema_version", "fixture_id", "ordinal", "population_namespace", "source_fixture_record", "source_fixture_record_sha256"],
        )
        self.assertEqual(
            encoding["target_record"]["exact_fields"],
            ["schema_version", "fixture_id", "category", "family", "oracle"],
        )
        self.assertTrue(encoding["target_record"]["target_is_fixture_oracle_only_not_a_scientific_result"])
        canonical = _load()["canonical_json_encoding"]
        self.assertIn("sort_keys=True", canonical["algorithm"])
        self.assertEqual(canonical["line_ending"], "LF")
        self.assertTrue(canonical["nonfinite_float_forbidden"])

    def test_index_receipts_and_totals_are_exact(self):
        contract = _load()
        index = contract["population_index_contract"]
        self.assertEqual(index["line_count"], 36)
        self.assertEqual(index["waveform_size_bytes"], 133120)
        self.assertEqual(len(index["exact_fields"]), 13)
        self.assertTrue(index["all_108_referenced_files_reopened_rehashed_and_size_checked_before_publication"])
        fixed = contract["population_receipt_contract"]["fixed_values"]
        self.assertEqual(fixed["total_fixture_files"], 108)
        self.assertEqual(fixed["total_waveform_bytes"], 36 * 16640 * 8)
        self.assertEqual(fixed["P0_P1_P2_executed_counts"], [0, 0, 0])
        self.assertFalse(fixed["locked_test_used"])

    def test_preflight_precedes_numpy_and_publication_is_atomic(self):
        contract = _load()
        preflight = contract["zero_science_preflight"]
        self.assertTrue(preflight["must_complete_before_numpy_scientific_import_or_waveform_allocation"])
        self.assertTrue(preflight["any_mismatch_is_preclaim_non_consuming_and_creates_no_population_file"])
        sequence = contract["future_materialization_and_publication_sequence"]
        self.assertTrue(sequence["defined_for_future_review_not_authorized_now"])
        self.assertEqual(sequence["exact_order"][0], "complete zero_science_preflight")
        self.assertEqual(sequence["exact_order"][-1], "stop before P0 P1 P2")
        self.assertTrue(sequence["success_root_absent_on_any_failure"])
        self.assertTrue(sequence["staging_is_never_authoritative"])

    def test_recomputation_is_independent_and_byte_exact(self):
        recompute = _load()["deterministic_recomputation_contract"]
        self.assertTrue(recompute["same_process_second_generation_from_fresh_PCG64_generators_required"])
        self.assertEqual(
            recompute["exact_second_generation_RNG_constructor"],
            "numpy.random.Generator(numpy.random.PCG64(seed))",
        )
        self.assertIn("no generator state cloning", recompute["second_generation_seed_rule"])
        self.assertTrue(recompute["recomputer_must_read_only_sealed_contracts_not_first_pass_arrays_or_files"])
        self.assertTrue(recompute["waveform_fixture_target_bytes_must_be_byte_identical_for_every_fixture"])
        self.assertIn("cross-runtime materialized byte identity is not claimed", recompute["cross_runtime_claim"])

    def test_scientific_boundary_remains_closed(self):
        separation = _load()["separation_from_scientific_execution"]
        self.assertTrue(separation["materialization_receipt_is_not_P0_P1_P2_evidence"])
        self.assertTrue(separation["population_success_does_not_authorize_tests_or_training"])
        forbidden = set(_load()["forbidden_now"])
        self.assertIn("execute_P0_P1_P2", forbidden)
        self.assertIn("create_population_staging_receipt_index_or_fixture_file", forbidden)
        self.assertIn("add_or_modify_any_src_file", forbidden)


if __name__ == "__main__":
    unittest.main()
