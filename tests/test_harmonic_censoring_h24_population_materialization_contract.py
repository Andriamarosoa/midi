import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "configs/harmonic_censoring_h24_population_materialization_one_shot_contract.json"


def _load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _validate_corrected_closure(contract):
    algorithm = contract["deterministic_waveform_algorithm_v1"]
    expected_defaults = {
        "gain": 1.0,
        "cents": 0.0,
        "inharmonicity_B": 0.0,
        "fundamental_amplitude": 1.0,
        "h1_phase": 0.0,
        "phase": 0.0,
        "old_source_age_hops": 0,
        "onset": 12032,
        "attack_hops": 0,
        "decay_tau_hops": 8,
        "technique": None,
        "instantaneous_pitch_offset": 0.0,
    }
    if algorithm.get("source_defaults_exact") != expected_defaults:
        raise ValueError("source defaults are not exact")
    numeric = contract["numpy_numeric_execution_trace_v1"]
    pink = numeric["noise_rng_call_order"]["pink"]
    if pink[2:5] != [
        "real = generator.standard_normal(bins)",
        "imag = generator.standard_normal(bins)",
        "values = real + 1j * imag",
    ]:
        raise ValueError("pink RNG draw order is not exact")
    if not numeric["source_and_harmonic_order"]["pairwise_tree_reduction_vectorization_fma_or_fastmath_forbidden"]:
        raise ValueError("numeric accumulation is not closed")
    trajectories = numeric.get("technique_trajectory_trace", {})
    if trajectories.get("common_prefix") != [
        "elapsed = np.maximum(samples - int(resolved onset), 0).astype(np.float64)",
        "trajectory = technique['trajectory']",
    ]:
        raise ValueError("technique trajectory common prefix is not exact")
    if trajectories.get("linear_cents") != [
        "duration = max(1, int(technique['duration_hops']) * 256)",
        "fraction = np.minimum(elapsed / duration, 1.0)",
        "pitch_offset = (float(technique.get('start', 0.0)) + (float(technique['end']) - float(technique.get('start', 0.0))) * fraction) * 0.01",
    ]:
        raise ValueError("linear cents trajectory trace is not exact")
    if trajectories.get("linear_semitones") != [
        "duration = max(1, int(technique['duration_hops']) * 256)",
        "fraction = np.minimum(elapsed / duration, 1.0)",
        "pitch_offset = (float(technique.get('start', 0.0)) + (float(technique['end']) - float(technique.get('start', 0.0))) * fraction) * 1.0",
    ]:
        raise ValueError("linear semitones trajectory trace is not exact")
    if trajectories.get("sinusoidal_cents") != [
        "pitch_offset = float(technique['depth']) / 100.0 * np.sin(2.0 * np.pi * float(technique['rate_hz']) * elapsed / 44100.0)"
    ]:
        raise ValueError("sinusoidal trajectory trace is not exact")
    if trajectories.get("linear_endpoint_rule") != (
        "the first sample equal to end is samples == resolved onset + duration; "
        "samples == resolved onset + duration - 1 remains start + (end-start)*(duration-1)/duration; "
        "np.linspace and any duration-1 denominator are forbidden"
    ):
        raise ValueError("linear endpoint convention is not exact")
    ood = numeric.get("OOD_exact_trace", {})
    if ood.get("linear_chirp") != [
        "local = np.arange(4096, dtype=np.float64)",
        "duration = 4095.0 / 44100.0",
        "phase = 2.0 * np.pi * (80.0 * local / 44100.0 + 0.5 * (8000.0 - 80.0) * (local / 44100.0) ** 2 / duration)",
        "waveform[8192:12288] = 0.4 * np.sin(phase)",
    ]:
        raise ValueError("linear chirp trace is not exact")
    if ood.get("log_chirp") != [
        "local = np.arange(4096, dtype=np.float64)",
        "frequency = 80.0 * np.power(100.0, local / 4095.0)",
        "phase = 2.0 * np.pi * np.cumsum(frequency) / 44100.0",
        "waveform[8192:12288] = 0.4 * np.sin(phase)",
    ]:
        raise ValueError("log chirp trace is not exact")
    if ood.get("impulse") != ["waveform[12032] = 0.4"]:
        raise ValueError("impulse trace is not exact")
    if ood.get("nonharmonic_stack") != [
        "local = np.arange(4096, dtype=np.float64)",
        "for frequency in (233, 377, 611, 997, 1597): waveform[8192:12288] += 0.08 * np.sin(2.0 * np.pi * frequency * local / 44100.0)",
    ]:
        raise ValueError("nonharmonic stack trace is not exact")
    if ood.get("pink_noise_burst") != [
        "waveform = execute noise_rng_call_order.pink with seed=synthesis_seed and length=12544",
        "waveform *= 0.4 * execute envelope_primitives.new with source defaults onset=12032 attack_hops=0 decay_tau_hops=8",
    ]:
        raise ValueError("pink noise burst trace is not exact")
    if ood.get("inharmonic_bell") != [
        "valid = samples >= 12032",
        "elapsed = samples[valid] - 12032",
        "for harmonic in range(1, 9): waveform[valid] += 0.3 / harmonic * np.exp(-elapsed / (512.0 * harmonic)) * np.sin(2.0 * np.pi * 220.0 * math.pow(harmonic, 1.08) * elapsed / 44100.0)",
    ]:
        raise ValueError("inharmonic bell trace is not exact")
    required_ood = {"impulse", "linear_chirp", "log_chirp", "nonharmonic_stack", "pink_noise_burst", "inharmonic_bell"}
    if set(ood.get("branch_dispatch_order", [])) != required_ood or not required_ood.issubset(ood):
        raise ValueError("OOD branch traces are not exhaustive")
    line = contract["population_index_line_value_contract"]["for_line_i"]
    if set(line) != set(contract["population_index_contract"]["exact_fields"]):
        raise ValueError("index line values do not cover exact fields")
    if line.get("dtype") != "<f8" or line.get("waveform_byte_count") != 100352:
        raise ValueError("index line constants are not exact")
    ordered = contract["ordered_fixture_ids_sha256_contract"]
    if "population_manifest.fixture_ids" not in ordered.get("canonical_bytes", ""):
        raise ValueError("ordered fixture ID hash input is not exact")
    capability = contract["future_identity_attested_capability_contract"]
    marker = contract["future_claim_marker_contract"]
    marker_authority = set(marker["exact_fields"]) - {
        "schema_version", "purpose", "population_consumed"
    }
    if marker_authority != set(capability["exact_immutable_fields"]):
        raise ValueError("marker does not preserve every capability authority field")
    runtime = contract["future_runtime_identity"]["receipt_and_marker_exact_object"]
    if set(runtime) != {
        "implementation", "python_version", "numpy_version", "architecture",
        "execution_device", "thread_count", "sample_rate_hz", "hop_samples",
    }:
        raise ValueError("runtime identity key set is not exact")


class H24PopulationMaterializationContractTests(unittest.TestCase):
    def test_contract_is_definition_only_and_binds_approved_harness(self):
        contract = _load_contract()
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["status"], "contract_only_corrected_external_review_required")
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

    def test_source_defaults_and_numpy_trace_are_normatively_closed(self):
        contract = _load_contract()
        _validate_corrected_closure(contract)
        trace = contract["numpy_numeric_execution_trace_v1"]
        self.assertTrue(trace["reference_runtime_only_byte_identity"])
        self.assertFalse(trace["cross_runtime_byte_identity_claimed"])
        self.assertEqual(trace["OOD_accumulation_order"]["inharmonic_bell_harmonic_order"], list(range(1, 9)))

    def test_missing_default_or_changed_rng_order_is_rejected(self):
        contract = _load_contract()
        missing = deepcopy(contract)
        del missing["deterministic_waveform_algorithm_v1"]["source_defaults_exact"]["gain"]
        with self.assertRaisesRegex(ValueError, "source defaults"):
            _validate_corrected_closure(missing)
        changed_rng = deepcopy(contract)
        pink = changed_rng["numpy_numeric_execution_trace_v1"]["noise_rng_call_order"]["pink"]
        pink[2], pink[3] = pink[3], pink[2]
        with self.assertRaisesRegex(ValueError, "RNG draw order"):
            _validate_corrected_closure(changed_rng)

    def test_alternative_trajectory_endpoint_or_chirp_trace_is_rejected(self):
        contract = _load_contract()
        endpoint = deepcopy(contract)
        endpoint["numpy_numeric_execution_trace_v1"]["technique_trajectory_trace"]["linear_cents"][1] = (
            "fraction = np.linspace(0.0, 1.0, duration, endpoint=True)"
        )
        with self.assertRaisesRegex(ValueError, "linear cents trajectory"):
            _validate_corrected_closure(endpoint)
        chirp = deepcopy(contract)
        chirp["numpy_numeric_execution_trace_v1"]["OOD_exact_trace"]["log_chirp"][2] = (
            "phase = scipy.signal.chirp(local, method='logarithmic')"
        )
        with self.assertRaisesRegex(ValueError, "log chirp trace"):
            _validate_corrected_closure(chirp)

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

    def test_each_index_field_and_ordered_id_hash_are_normative(self):
        contract = _load_contract()
        _validate_corrected_closure(contract)
        line = contract["population_index_line_value_contract"]["for_line_i"]
        self.assertEqual(line["fixture_id"], "population_manifest.fixture_ids[i]")
        self.assertEqual(line["sample_count"], 12544)
        self.assertEqual(line["sample_rate_hz"], 44100)
        self.assertIn("source_specification_sha256", line["specification_sha256"])
        self.assertIn("format(i,'06d')", line["waveform_path"])
        ids_hash = contract["ordered_fixture_ids_sha256_contract"]
        self.assertTrue(ids_hash["alternative_join_delimiter_or_missing_trailing_LF_forbidden"])

    def test_bad_index_metadata_or_ambiguous_id_hash_is_rejected(self):
        contract = _load_contract()
        bad_dtype = deepcopy(contract)
        bad_dtype["population_index_line_value_contract"]["for_line_i"]["dtype"] = "float64"
        with self.assertRaisesRegex(ValueError, "index line constants"):
            _validate_corrected_closure(bad_dtype)
        bad_hash = deepcopy(contract)
        bad_hash["ordered_fixture_ids_sha256_contract"]["canonical_bytes"] = "LF-joined IDs"
        with self.assertRaisesRegex(ValueError, "ordered fixture ID"):
            _validate_corrected_closure(bad_hash)

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

    def test_capability_marker_and_receipt_runtime_are_closed(self):
        contract = _load_contract()
        _validate_corrected_closure(contract)
        capability = contract["future_identity_attested_capability_contract"]
        marker = contract["future_claim_marker_contract"]
        self.assertFalse(capability["constructor_publicly_callable"])
        self.assertTrue(capability["identity_only_private_registry_with_weak_reference_or_equivalent"])
        self.assertTrue(marker["timestamp_random_nonce_hostname_pid_or_caller_metadata_forbidden"])
        self.assertTrue(marker["runtime_identity_must_equal_future_runtime_identity_receipt_and_marker_exact_object"])

    def test_missing_marker_authority_or_extra_runtime_field_is_rejected(self):
        contract = _load_contract()
        missing = deepcopy(contract)
        missing["future_claim_marker_contract"]["exact_fields"].remove("authorization_seal_raw_sha256")
        with self.assertRaisesRegex(ValueError, "marker"):
            _validate_corrected_closure(missing)
        extra = deepcopy(contract)
        extra["future_runtime_identity"]["receipt_and_marker_exact_object"]["hostname"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "runtime identity"):
            _validate_corrected_closure(extra)

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
