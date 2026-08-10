"""Pure, closed H23 oracle recomputation from persisted measurements.

This module deliberately imports no NumPy and performs no synthesis.  The
scientific executor persists operands, categories, counts and hashes; this
module owns the corresponding comparisons.  Producer booleans are never an
input to the decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .harmonic_censoring_h23 import H23ResolvedTest


@dataclass(frozen=True)
class H23MeasurementRule:
    name: str
    operator: str
    expected: object = None
    rtol: float = 0.0
    atol: float = 0.0


@dataclass(frozen=True)
class H23ExactOracleSpec:
    primary: tuple[H23MeasurementRule, ...]
    inverse: tuple[H23MeasurementRule, ...]


@dataclass(frozen=True)
class H23RecomputedOracle:
    primary_pass: bool
    inverse_pass: bool

    @property
    def final_pass(self) -> bool:
        return self.primary_pass and self.inverse_pass


def _r(name: str, operator: str, expected: object = None, *, rtol: float = 0.0, atol: float = 0.0) -> H23MeasurementRule:
    return H23MeasurementRule(name, operator, expected, rtol, atol)


def _spec(
    primary: Sequence[H23MeasurementRule], inverse: Sequence[H23MeasurementRule]
) -> H23ExactOracleSpec:
    return H23ExactOracleSpec(tuple(primary), tuple(inverse))


# Every entry describes raw persisted operands, never a producer PASS bit.
# Dynamic comparisons use two-element ``[left, right]`` operands.  Tolerances
# and categorical expectations live here, outside the transcript.
EXACT_H23_ORACLE_REGISTRY: Mapping[str, H23ExactOracleSpec] = {
    "A01": _spec([_r("edges", "all_edges_ascending")], [_r("mutated_edges", "any_edge_descending")]),
    "A02": _spec([_r("analytic_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12)], [_r("cosine_semantics", "eq", "APPROXIMATION_NOT_ANALYTIC")]),
    "A03": _spec([_r("feature_class", "eq", "TRIVIAL_FEATURE"), _r("disappearance_indices", "all_equal")], [_r("shuffled_disappearance_indices", "all_equal")]),
    "A04": _spec([_r("latent_feature_hashes", "all_equal"), _r("decision", "eq", "AMBIGUOUS")], [_r("target_conditioned_feature_hashes", "all_equal")]),
    "A05": _spec([_r("cardinality_triplets", "eq", [[1, 0, 1], [1, 1, 1], [1, 1, "AMBIGUOUS"]])], [_r("collapsed_cardinality_triplets", "ne", [[1, 0, 1], [1, 1, 1], [1, 1, "AMBIGUOUS"]])]),
    "A06": _spec([_r("domain_counts", "eq", [37, 53, 89]), _r("domain_endpoints", "eq", [[40, 76], [24, 76], [40, 128]]), _r("maximum_h20_coordinate", "close", 127.86313713864834, rtol=1e-12, atol=1e-12)], [_r("forbidden_emit_coordinates", "none_in", [40, 76])]),
    "A07": _spec([_r("relative_geometry_hashes", "all_equal")], [_r("absolute_geometry_hashes", "not_all_equal")]),
    "A08": _spec([_r("maximum_future_sample_offset", "eq", 0)], [_r("injected_future_sample_offset", "gt", 0)]),
    "D01": _spec([_r("scalar_vector_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12), _r("mask_pairs", "all_exact_pairs")], [_r("permuted_then_canonical_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12)]),
    "D02": _spec([_r("normalized_gain_curves", "allclose_all", rtol=1e-10, atol=1e-12), _r("raw_gain_levels", "strictly_gain_ordered")], [_r("zero_energy_validity", "eq", "INVALID_MASKED")]),
    "D03": _spec([_r("supported_residual_abs_max", "le", 1e-12), _r("unsupported_term_counted", "eq", 0)], [_r("empty_kernel_denominator_result", "eq", "REJECTED")]),
    "D04": _spec([_r("same_pitch_curve_max_difference_c1_c4", "gt", 1e-12), _r("scalar_vector_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12)], [_r("pitch_only_curve_hashes", "all_equal")]),
    "D05": _spec([_r("normalized_gain_curves", "allclose_all", rtol=1e-10, atol=1e-12), _r("raw_gain_levels", "not_all_equal")], [_r("raw_only_claim", "eq", "INSUFFICIENT")]),
    "D06": _spec([_r("hard_categories", "eq", ["NO_BIRTH", "NO_BIRTH", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "ALREADY_ACTIVE_HISTORY", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "AMBIGUOUS"]), _r("cosine_categories", "eq", ["NO_BIRTH", "NO_BIRTH", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "ALREADY_ACTIVE_HISTORY", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "AMBIGUOUS"])], [_r("shifted_200c_curve_hash_pairs", "any_different_pair")]),
    "D07": _spec([_r("S1P_phase_categories", "all_eq", "NO_BIRTH"), _r("S4_phase_categories", "all_eq", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"), _r("S5_category", "eq", "AMBIGUOUS")], [_r("unchanged_waveform_phase_label_hashes", "all_equal")]),
    "D08": _spec([_r("target_hop_categories", "eq", ["ALREADY_ACTIVE_HISTORY", "ALREADY_ACTIVE_HISTORY", "ALREADY_ACTIVE_HISTORY", "ALREADY_ACTIVE_HISTORY", "PENDING_NEW_AWAITING_ONE_HOP", "PENDING_NEW_AWAITING_ONE_HOP"]), _r("resolved_categories", "eq", ["BIRTH_SUPPORTED_DELAYED_ONE_HOP", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"]), _r("pending_lifetimes", "all_eq", 1), _r("runtime_fields", "eq", ["pitch", "state", "first_seen_hop"])], [_r("forbidden_runtime_fields_result", "eq", "REJECTED")]),
    "D09": _spec([_r("variant_count", "eq", 42), _r("variant_categories_match_base", "all_true")], [_r("undeclared_100c_manifest_result", "eq", "REJECTED")]),
    "D10": _spec([_r("robust_category_count", "eq", 18), _r("robust_categories_match_base", "all_true"), _r("zero_db_categories", "all_in", ["AMBIGUOUS_OR_OOD"]), _r("silence_category", "eq", "SILENCE_UNEXPLAINED")], [_r("pitch_shaped_noise_manifest_result", "eq", "REJECTED")]),
    "D11": _spec([_r("primary_curve_retained", "eq", True), _r("same_summary_curve_hashes", "any_different_pair"), _r("raw_auc_gain_values", "not_all_equal"), _r("normalized_auc_gain_values", "allclose_all", rtol=1e-10, atol=1e-12)], [_r("duplicated_auc_channel_hashes", "all_equal")]),
    "D12": _spec([_r("monotone_rebound", "eq", False), _r("two_regime_flag", "eq", True)], [_r("mutated_monotone_rebound", "eq", True)]),
    "D13": _spec([_r("validity_bits", "support_formula_exact"), _r("unsupported_value_representation", "eq", "MASKED_NOT_ZERO")], [_r("negative_coercion_result", "eq", "REJECTED")]),
    "D14": _spec([_r("unmasked_nonfinite_count", "eq", 0), _r("invalidity_explicit", "eq", True)], [_r("silent_divide_result", "eq", "REJECTED")]),
    "S1": _spec([_r("decision", "eq", "NO_BIRTH"), _r("cardinalities", "eq", [1, 0, 1])], [_r("without_old_F0_explanation", "eq", "LOST")]),
    "S2": _spec([_r("state_trace", "eq", ["INACTIVE", "PENDING_NEW", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"]), _r("decision_delay_hops", "eq", 1), _r("birth_pitch", "eq", 64), _r("birth_tuple_complete", "eq", True)], [_r("without_attack_and_own_harmonics", "in", ["AMBIGUOUS", "NO_BIRTH"])]),
    "S3": _spec([_r("decision", "eq", "ALREADY_ACTIVE_HISTORY"), _r("birth", "eq", False)], [_r("controlled_onset_decision", "in", ["PENDING_NEW_AWAITING_ONE_HOP", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"])]),
    "S4": _spec([_r("state_trace", "eq", ["INACTIVE", "PENDING_NEW", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"]), _r("decision_delay_hops", "eq", 1), _r("birth_pitch", "eq", 64), _r("improvement_valid", "eq", True), _r("cardinalities", "eq", [2, 2, 2])], [_r("without_MIDI64_own_evidence", "in", ["AMBIGUOUS", "NO_BIRTH"])]),
    "S5": _spec([_r("decision", "eq", "AMBIGUOUS"), _r("cardinalities", "eq", ["AMBIGUOUS", "AMBIGUOUS", "AMBIGUOUS"])], [_r("forced_binary_decision", "in", ["BIRTH", "NO_BIRTH"])]),
    "C01": _spec([_r("causal_feature_hash_pair", "pair_equal"), _r("causal_decision_pair", "pair_equal")], [_r("future_sensitive_feature_hash_pair", "pair_different")]),
    "C02": _spec([_r("translated_state_traces", "all_equal"), _r("translated_delays", "all_eq", 1), _r("translations_hops", "eq", [0, 1, 2, 4])], [_r("unshifted_index_trace_pair", "pair_different")]),
    "C03": _spec([_r("categories", "eq", ["BIRTH_SUPPORTED_DELAYED_ONE_HOP", "ALREADY_ACTIVE_HISTORY", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "AMBIGUOUS"]), _r("tuple_keys", "eq", ["O", "N", "G", "X", "Delta_R", "improvement_valid"]), _r("forbidden_dependency_count", "eq", 0)], [_r("forbidden_dependency_injections_rejected", "all_true")]),
    "C04": _spec([_r("decisions", "eq", ["RETRIGGER_SUPPORTED", "ALREADY_ACTIVE_HISTORY"]), _r("retrigger_noteon_counts", "eq", [1, 0]), _r("cardinality_deltas", "all_eq", 0)], [_r("new_pitch_route_result", "eq", "REJECTED")]),
    "C05": _spec([_r("S3_age_categories", "all_eq", "ALREADY_ACTIVE_HISTORY"), _r("S4_age_categories", "all_eq", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"), _r("old_source_explanation", "nonincreasing", None, atol=1e-12)], [_r("label_age_schema_result", "eq", "REJECTED")]),
    "C06": _spec([_r("additional_lookahead_samples", "eq", 0)], [_r("hidden_stability_vote_lookahead", "gt", 0)]),
    "F01": _spec([_r("additive_reconstruction_pair", "allclose_pair", rtol=1e-10, atol=1e-12), _r("column_order_residual_pair", "close_pair", rtol=1e-10, atol=1e-12), _r("exclusive_ownership_flag_present", "eq", False)], [_r("exclusive_residual_minus_additive", "ge", 0.0), _r("exclusive_contract_result", "eq", "REJECTED")]),
    "F02": _spec([_r("unexplained_residual", "gt", 1e-12), _r("residual_vector_scalar_pair", "close_pair", rtol=1e-10, atol=1e-12)], [_r("matching_column_delta_R", "gt", 0.0)]),
    "F03": _spec([_r("permutation_residuals", "allclose_all", rtol=1e-10, atol=1e-12), _r("permutation_amplitude_maps", "all_equal")], [_r("tie_winner_indices", "all_eq", 0)]),
    "F04": _spec([_r("graph_traversal_residuals", "allclose_all", rtol=1e-10, atol=1e-12), _r("graph_traversal_amplitude_maps", "all_equal")], [_r("shared_partial_stress_parity", "eq", True)]),
    "K01": _spec([_r("K_latent_pitch", "eq", [0, 1, 1, 2, 3, 1]), _r("K_emit_pitch", "eq", [0, 0, 1, 2, 3, 1]), _r("forbidden_K_pitch_alias_present", "eq", False)], [_r("S1C_MIDI36_emit_count", "eq", 1)]),
    "K02": _spec([_r("physical_unison_K_source", "all_eq", "AMBIGUOUS")], [_r("forced_unison_K_source", "all_eq", 2)]),
    "K03": _spec([_r("numeric_objective_reconciliation", "allclose_pairs", rtol=1e-10, atol=1e-12), _r("categories", "eq", ["NO_BIRTH", "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "AMBIGUOUS"])], [_r("source_order_result_pair", "pair_equal")]),
    "K04": _spec([_r("set_permutation_results", "all_equal")], [_r("duplicate_handling", "eq", "EXPLICIT_DEDUPLICATION")]),
    "AC01": _spec([_r("channel_state", "eq", "CONFLICT_RETAINED"), _r("self_confirmation", "eq", False)], [_r("without_independent_observation_state", "in", ["INCOMPLETE", "AMBIGUOUS"])]),
    "AC02": _spec([_r("disagreement_retained", "eq", True), _r("channels_erased", "eq", False)], [_r("swapped_channel_state", "eq", "DISAGREEMENT_RETAINED")]),
    "AC03": _spec([_r("head_only_state", "in", ["INCOMPLETE", "AMBIGUOUS"])], [_r("with_independent_structure_state", "eq", "CONFIRMED")]),
    "AC04": _spec([_r("residual_curve_hash_pair", "pair_different")], [_r("forced_equal_residual_hash_pair", "pair_equal")]),
    "G01": _spec([_r("supported_note_hard_deleted", "eq", False), _r("prior_kind", "eq", "SOFT_WITH_UNKNOWN_SLACK")], [_r("disabled_prior_note_set_pair", "pair_equal")]),
    "G02": _spec([_r("bend_decisions", "all_in", ["CONTINUITY", "AMBIGUOUS"]), _r("forced_semitone_birth_count", "eq", 0)], [_r("quantized_control_birth_count", "gt", 0)]),
    "G03": _spec([_r("slide_state", "eq", "SOFTLY_PLAUSIBLE"), _r("hard_string_owner_present", "eq", False)], [_r("cross_string_alternative_retained", "eq", True)]),
    "G04": _spec([_r("decisions", "eq", ["ALREADY_ACTIVE_HISTORY", "RETRIGGER_SUPPORTED"]), _r("retrigger_counts", "eq", [0, 1]), _r("cardinality_deltas", "all_eq", 0)], [_r("K_plus_one_route_result", "eq", "REJECTED")]),
    "G05": _spec([_r("K_latent_pitch", "all_eq", 1), _r("K_emit_pitch", "all_eq", 1), _r("K_source", "all_eq", "AMBIGUOUS"), _r("temporal_evidence_serialized", "eq", True)], [_r("envelope_forced_K_source", "all_eq", 2)]),
    "G06": _spec([_r("natural_harmonic_states", "all_in", ["NATURAL_HARMONIC", "UNKNOWN"])], [_r("normal_fretted_state", "eq", "NORMAL_FRETTED")]),
    "G07": _spec([_r("resonance_birth_count", "eq", 0), _r("resonance_state", "in", ["RESONANCE", "OBSERVATION_ONLY"])], [_r("independent_onset_birth_count", "eq", 1)]),
    "G08": _spec([_r("hypothesis_count", "gt", 6), _r("tension_reported", "eq", True), _r("silently_removed_count", "eq", 0)], [_r("six_source_boundary_preserved", "eq", True)]),
    "V01": _spec([_r("retained_observation_coordinates", "eq", list(range(77, 129))), _r("emissions_above_76", "eq", 0)], [_r("pitch76_emit_capable", "eq", True)]),
    "V02": _spec([_r("endpoint_categories", "eq", {"40": "EMIT", "76": "EMIT", "77": "EVIDENCE_ONLY", "127": "EVIDENCE_ONLY", "128": "EVIDENCE_ONLY", "129": "INVALID"})], [_r("forbidden_endpoint_emission_count", "gt", 0)]),
    "V03": _spec([_r("low_F0_explained", "eq", True), _r("high_MIDI_emission_count", "eq", 0)], [_r("without_low_F0_explained", "eq", False)]),
    "O01": _spec([_r("silence_states", "all_in", ["SILENCE", "UNEXPLAINED"]), _r("confident_pitch_count", "eq", 0)], [_r("structured_source_state", "eq", "EXPLAINED_HARMONIC_SOURCE")]),
    "O02": _spec([_r("OOD_states", "all_in", ["OOD", "UNEXPLAINED"]), _r("forced_guitar_factorization_count", "eq", 0)], [_r("matched_harmonic_stack_state", "eq", "EXPLAINED_HARMONIC_SOURCE")]),
    "O03": _spec([_r("trace_required_fields_present", "eq", True), _r("label_dependency_count", "eq", 0)], [_r("redacted_target_trace_hash_pair", "pair_equal")]),
    "O04": _spec([_r("raw_score_count", "gt", 0), _r("selected_threshold", "eq", None)], [_r("hardcoded_cutoff_result", "eq", "REJECTED")]),
    "I01": _spec([_r("executed_fixture_ids", "eq", "__PLAN_FIXTURE_IDS__"), _r("fixture_count", "eq", 175), _r("local_oracle_failure_count", "eq", 0)], [_r("malformed_fixture_publication_result", "eq", "REJECTED_BEFORE_PUBLICATION")]),
    "I02": _spec([_r("success_final_exists", "eq", True), _r("success_staging_exists", "eq", False), _r("partial_final_observed", "eq", False)], [_r("pre_rename_interrupt_final_exists", "eq", False)]),
    "R01": _spec([_r("repeat_output_hash_pair", "pair_equal")], [_r("different_seed_pair", "pair_different")]),
    "R02": _spec([_r("same_runtime_output_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12)], [_r("thread_variation_measurement_count", "gt", 0)]),
    "R03": _spec([_r("batch_output_pairs", "allclose_pairs", rtol=1e-10, atol=1e-12), _r("batch_ID_sets", "all_equal")], [_r("dropped_partial_batch_ID_set_equal", "eq", False)]),
    "P01": _spec([_r("spectral_encodings_per_frame", "all_eq", 1)], [_r("encoding_counts_by_candidate_count", "all_eq", 1)]),
    "P02": _spec([_r("live_censoring_shape", "eq", [37, 6]), _r("observation_shape", "eq", [89]), _r("spectral_encodings", "eq", 1), _r("emit_capable_above_76", "eq", 0)], [_r("invalid_89x6_candidate_matrix_result", "eq", "REJECTED")]),
    "P03": _spec([_r("maximum_retained_frames", "le", 16), _r("maximum_tracked_array_bytes", "le", 67108864), _r("post_warmup_RSS_range_bytes", "le", 33554432), _r("final_retained_frames", "le", 16)], [_r("retain_every_frame_count", "gt", 16)]),
    "P04": _spec([_r("hop_count", "eq", 10336), _r("p95_ms", "le", 5.804988662131519), _r("p99_ms", "le", 5.804988662131519), _r("max_ms", "le", 11.609977324263038), _r("maximum_backlog_hops", "le", 1), _r("final_backlog_hops", "eq", 0), _r("added_lookahead_samples", "eq", 0)], [_r("stress_cutoff_count", "eq", 12), _r("stress_replaced_primary", "eq", False)]),
    "P05": _spec([_r("reported_components", "eq", ["window", "hop", "feature", "inference", "decoder", "MIDI"]), _r("algorithmic_lookahead_samples", "eq", 0)], [_r("hidden_buffering_samples", "gt", 0)]),
    "TS01": _spec([_r("fixture_accounted_count", "eq", 175), _r("selected_category", "in", ["TEACHER_NOT_NEEDED", "TEACHER_JUSTIFIED"]), _r("selection_rule_satisfied", "eq", True)], [_r("summary_only_improvement_justifies_teacher", "eq", False)]),
    "TS02": _spec([_r("forbidden_dependency_count", "eq", 0), _r("maximum_future_sample_offset", "eq", 0)], [_r("future_t_plus_1_dependency_result", "eq", "REJECTED_BEFORE_FIT")]),
}


def _as_sequence(value: object, label: str) -> Sequence[object]:
    if type(value) is not list:
        raise ValueError(f"H23 {label} must be an array.")
    return value


def _strict_equal(left: object, right: object) -> bool:
    """JSON-native equality without Python's bool/int aliasing."""

    if type(left) is not type(right):
        return False
    if type(left) is list:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            _strict_equal(a, b) for a, b in zip(left, right)  # type: ignore[arg-type]
        )
    if type(left) is dict:
        return set(left) == set(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index]
        )
    return bool(left == right)


def _allclose(left: object, right: object, rtol: float, atol: float) -> bool:
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        left_items = _as_sequence(left, "allclose left")
        right_items = _as_sequence(right, "allclose right")
        return len(left_items) == len(right_items) and all(
            _allclose(a, b, rtol, atol) for a, b in zip(left_items, right_items)
        )
    if type(left) not in (int, float) or type(right) not in (int, float):
        return False
    return math.isfinite(float(left)) and math.isfinite(float(right)) and math.isclose(
        float(left), float(right), rel_tol=rtol, abs_tol=atol
    )


def _pair(value: object, label: str) -> tuple[object, object]:
    items = _as_sequence(value, label)
    if len(items) != 2:
        raise ValueError(f"H23 {label} must contain exactly two operands.")
    return items[0], items[1]


def _evaluate_rule(rule: H23MeasurementRule, value: object, plan_fixture_ids: Sequence[str]) -> bool:
    expected = list(plan_fixture_ids) if rule.expected == "__PLAN_FIXTURE_IDS__" else rule.expected
    op = rule.operator
    if op == "eq":
        return _strict_equal(value, expected)
    if op == "ne":
        return not _strict_equal(value, expected)
    if op == "in":
        return any(
            _strict_equal(value, item)
            for item in _as_sequence(expected, f"{rule.name} expected values")
        )
    if op == "gt":
        return type(value) in (int, float) and float(value) > float(expected)
    if op == "ge":
        return type(value) in (int, float) and float(value) >= float(expected)
    if op == "le":
        return type(value) in (int, float) and float(value) <= float(expected)
    if op == "close":
        return _allclose(value, expected, rule.rtol, rule.atol)
    if op in {"pair_equal", "pair_different", "close_pair", "allclose_pair"}:
        left, right = _pair(value, rule.name)
        equal = (
            _allclose(left, right, rule.rtol, rule.atol)
            if "close" in op
            else _strict_equal(left, right)
        )
        return equal if op in {"pair_equal", "close_pair", "allclose_pair"} else not equal
    if op == "all_equal":
        items = _as_sequence(value, rule.name)
        return bool(items) and all(_strict_equal(item, items[0]) for item in items[1:])
    if op == "not_all_equal":
        items = _as_sequence(value, rule.name)
        return len(items) >= 2 and any(not _strict_equal(item, items[0]) for item in items[1:])
    if op == "all_eq":
        return all(_strict_equal(item, expected) for item in _as_sequence(value, rule.name))
    if op == "all_in":
        allowed = _as_sequence(expected, f"{rule.name} allowed values")
        return all(
            any(_strict_equal(item, option) for option in allowed)
            for item in _as_sequence(value, rule.name)
        )
    if op == "all_true":
        items = _as_sequence(value, rule.name)
        return bool(items) and all(item is True for item in items)
    if op == "none_in":
        low, high = _as_sequence(expected, f"{rule.name} interval")
        return all(not (int(low) <= int(item) <= int(high)) for item in _as_sequence(value, rule.name))
    if op == "contains_any":
        return any(item in value for item in _as_sequence(expected, rule.name)) if isinstance(value, (list, tuple, dict, set)) else False
    if op == "all_exact_pairs":
        return all(_strict_equal(left, right) for left, right in (_pair(item, rule.name) for item in _as_sequence(value, rule.name)))
    if op == "allclose_pairs":
        return all(_allclose(*_pair(item, rule.name), rule.rtol, rule.atol) for item in _as_sequence(value, rule.name))
    if op == "allclose_all":
        items = _as_sequence(value, rule.name)
        return bool(items) and all(_allclose(items[0], item, rule.rtol, rule.atol) for item in items[1:])
    if op == "any_different_pair":
        return any(not _strict_equal(left, right) for left, right in (_pair(item, rule.name) for item in _as_sequence(value, rule.name)))
    if op == "strictly_gain_ordered":
        items = _as_sequence(value, rule.name)
        return len(items) >= 2 and all(float(a) < float(b) for a, b in zip(items, items[1:]))
    if op == "nonincreasing":
        items = _as_sequence(value, rule.name)
        return len(items) >= 2 and all(float(b) - float(a) <= rule.atol for a, b in zip(items, items[1:]))
    if op == "all_edges_ascending":
        return all(float(edge[1]) > float(edge[0]) for edge in _as_sequence(value, rule.name))
    if op == "any_edge_descending":
        return any(float(edge[1]) < float(edge[0]) for edge in _as_sequence(value, rule.name))
    if op == "support_formula_exact":
        return all(bool(item[0]) is (float(item[1]) <= 22050.0 and bool(item[2])) for item in _as_sequence(value, rule.name))
    raise ValueError(f"H23 unknown sealed measurement operator {op!r}.")


def recompute_h23_exact_oracle(
    test: H23ResolvedTest,
    persisted_measurements: object,
    *,
    plan_fixture_ids: Sequence[str],
) -> H23RecomputedOracle:
    """Recompute one exact test without consulting producer booleans."""

    if test.test_id not in EXACT_H23_ORACLE_REGISTRY:
        raise ValueError(f"H23 test {test.test_id} has no exact oracle registry entry.")
    if not isinstance(persisted_measurements, Mapping):
        raise ValueError("H23 persisted oracle measurements must be an object.")
    if set(persisted_measurements) != {"primary", "inverse"}:
        raise ValueError("H23 persisted oracle measurements require primary/inverse only.")
    primary = persisted_measurements["primary"]
    inverse = persisted_measurements["inverse"]
    if not isinstance(primary, Mapping) or not isinstance(inverse, Mapping):
        raise ValueError("H23 primary/inverse measurements must be objects.")
    spec = EXACT_H23_ORACLE_REGISTRY[test.test_id]
    if set(primary) != {rule.name for rule in spec.primary}:
        raise ValueError(f"H23 {test.test_id} primary measurement keys mismatch.")
    if set(inverse) != {rule.name for rule in spec.inverse}:
        raise ValueError(f"H23 {test.test_id} inverse measurement keys mismatch.")
    primary_pass = all(
        _evaluate_rule(rule, primary[rule.name], plan_fixture_ids)
        for rule in spec.primary
    )
    inverse_pass = all(
        _evaluate_rule(rule, inverse[rule.name], plan_fixture_ids)
        for rule in spec.inverse
    )
    return H23RecomputedOracle(primary_pass=primary_pass, inverse_pass=inverse_pass)


__all__ = [
    "EXACT_H23_ORACLE_REGISTRY",
    "H23ExactOracleSpec",
    "H23MeasurementRule",
    "H23RecomputedOracle",
    "recompute_h23_exact_oracle",
]
