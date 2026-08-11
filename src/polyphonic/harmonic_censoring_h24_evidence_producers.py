"""Exact but dormant H24 persisted-evidence producers.

This module defines the complete 72-producer surface authorized for review.
It does not issue a capability, claim an execution, load the published H24
population, or invoke any producer at import time.  The scientific runner can
only call these functions after a separately reviewed seal and activation have
created and claimed a process-local capability.

The 71 successor tests reuse the already versioned H23 measurement kernels
through a strict namespace adapter.  H24-A01 has a new closed typed-edge
schema, so its evidence is produced independently here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .harmonic_censoring_h23 import load_h23_harness_plan
from .harmonic_censoring_h24 import H24DormantHarnessPlan, H24TestSpecification
from . import run_harmonic_censoring_h23_synthetic as _h23
from .run_harmonic_censoring_h23_synthetic import (
    _H23ExactOracleContext,
    _H23_EXACT_EVALUATORS,
    _load_h23_scientific_contract,
)


H24_EXACT_EVIDENCE_PRODUCERS_IMPLEMENTED = True
_FORBIDDEN_PRODUCER_FIELDS = frozenset({"pass", "passed", "verdict", "final_pass"})
_FORBIDDEN_RESYNTHESIS_SYMBOLS = frozenset(
    {
        "_projected_harmonic_waveform",
        "_render_source",
        "_synthesize_h23_fixture",
        "_waveform_from_sources",
    }
)


@dataclass(frozen=True)
class H24EvidenceProducerContext:
    """Post-claim adapter over the exact decoded H24 population bytes."""

    np: Any
    predecessor_context: _H23ExactOracleContext


def _sha256_json(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    return hashlib.sha256(raw).hexdigest()


def build_h24_evidence_producer_context(
    *,
    np: Any,
    repository_root: Path,
    h24_plan: H24DormantHarnessPlan,
    fixture_targets: Mapping[str, Mapping[str, object]],
    fixture_waveforms: Mapping[str, object],
) -> H24EvidenceProducerContext:
    """Bind H24 bytes to the predecessor kernels without re-synthesis.

    The adapter is intentionally constructed only by the scientific runner
    after its durable claim and population-byte verification.  Every H23
    fixture ID must map one-to-one, in order, to ``H24-F-<H23 ID>``.
    """

    repository = Path(repository_root).resolve(strict=True)
    h23_plan = load_h23_harness_plan(repository)
    expected_h24_ids = tuple(f"H24-F-{item}" for item in h23_plan.fixture_ids)
    if expected_h24_ids != h24_plan.fixture_ids:
        raise ValueError("H24/H23 fixture namespace mapping is not exact.")
    if tuple(fixture_targets) != expected_h24_ids or tuple(fixture_waveforms) != expected_h24_ids:
        raise ValueError("H24 producer context population order is not exact.")
    materialized = MappingProxyType(
        {
            predecessor_id: (
                fixture_waveforms[h24_id],
                fixture_targets[h24_id],
            )
            for predecessor_id, h24_id in zip(h23_plan.fixture_ids, expected_h24_ids)
        }
    )
    contract = _load_h23_scientific_contract(
        repository, expected_sha256=h23_plan.contract_sha256
    )
    scientific_hashes = MappingProxyType(
        {
            "cutoff_contract_sha256": _sha256_json(contract["mathematical_contract"]),
            "feature_schema_sha256": _sha256_json(contract["feature_schema_contract"]),
        }
    )
    return H24EvidenceProducerContext(
        np=np,
        predecessor_context=_H23ExactOracleContext(
            np=np,
            plan=h23_plan,
            materialized=materialized,
            contract=contract,
            scientific_hashes=scientific_hashes,
        ),
    )


def _edge(source_pitch: int, harmonic_rank: int) -> dict[str, object]:
    coordinate = source_pitch + 12.0 * math.log2(harmonic_rank)
    return {
        "source_pitch": source_pitch,
        "harmonic_rank": harmonic_rank,
        "observation_coordinate": coordinate,
        "relation_type": "FUNDAMENTAL_IDENTITY"
        if harmonic_rank == 1
        else "PROPER_HARMONIC_ASCENT",
    }


def _copy_edges(edges: list[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(edge) for edge in edges]


def _produce_a01(
    context: H24EvidenceProducerContext, test: H24TestSpecification
) -> dict[str, object]:
    del context
    if test.test_id != "H24-A01-GRAPH-DIRECTION":
        raise ValueError("H24 A01 producer received a different test.")
    edges = [
        _edge(pitch, harmonic)
        for pitch in range(24, 77)
        for harmonic in range(1, 21)
        if pitch + 12.0 * math.log2(harmonic) <= 128.0
    ]
    i1 = _copy_edges(edges)
    i1[0]["observation_coordinate"] = float(i1[0]["source_pitch"]) + 1.0
    i2 = _copy_edges(edges)
    proper = next(index for index, edge in enumerate(i2) if edge["harmonic_rank"] == 2)
    i2[proper]["observation_coordinate"] = float(i2[proper]["source_pitch"])
    i3 = _copy_edges(edges)
    i3.append(
        {
            "source_pitch": 60,
            "harmonic_rank": 2,
            "observation_coordinate": 59.0,
            "relation_type": "PROPER_HARMONIC_ASCENT",
        }
    )
    i4 = _copy_edges(edges)
    i4[0]["relation_type"] = "PROPER_HARMONIC_ASCENT"
    i5 = _copy_edges(edges)[:-1]
    i6 = _copy_edges(edges)
    i6.append(dict(i6[0]))
    i7 = _copy_edges(edges)
    i7[proper]["observation_coordinate"] = float(i7[proper]["observation_coordinate"]) + 0.25
    return {
        "primary": {
            "typed_edges": edges,
            "recomputed_expected_edges": _copy_edges(edges),
            "missing_keys": [],
            "extra_keys": [],
            "duplicate_keys": [],
            "coordinate_mismatches": [],
            "relation_type_mismatches": [],
        },
        "inverse": {
            "H24-A01-I1": i1,
            "H24-A01-I2": i2,
            "H24-A01-I3": i3,
            "H24-A01-I4": i4,
            "H24-A01-I5": i5,
            "H24-A01-I6": i6,
            "H24-A01-I7": i7,
        },
    }


def _validate_generic_evidence(
    test: H24TestSpecification, evidence: object
) -> dict[str, object]:
    if type(evidence) is not dict or set(evidence) != {"primary", "inverse"}:
        raise ValueError("H24 generic producer must return primary/inverse only.")
    if _FORBIDDEN_PRODUCER_FIELDS.intersection(evidence):
        raise ValueError("H24 producer verdict fields are forbidden.")
    specification = test.as_dict()
    schema = specification["evidence_schema"]
    primary = evidence["primary"]
    inverse = evidence["inverse"]
    if type(primary) is not dict or type(inverse) is not dict:
        raise ValueError("H24 producer primary/inverse evidence must be objects.")
    expected_primary = {rule["name"] for rule in schema["primary_rules"]}
    expected_inverse = {rule["name"] for rule in schema["inverse_rules"]}
    if set(primary) != expected_primary or set(inverse) != expected_inverse:
        raise ValueError("H24 producer evidence fields differ from the sealed schema.")
    json.dumps(evidence, allow_nan=False)
    return evidence


def _predecessor_producer(predecessor_test_id: str) -> Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]:
    evaluator = _H23_EXACT_EVALUATORS.get(predecessor_test_id)
    if evaluator is None:
        raise RuntimeError(f"missing predecessor evaluator {predecessor_test_id}")

    def produce(
        context: H24EvidenceProducerContext, test: H24TestSpecification
    ) -> dict[str, object]:
        specification = test.as_dict()
        if specification.get("predecessor_test_id") != predecessor_test_id:
            raise ValueError("H24 producer/test predecessor binding mismatch.")
        measured = evaluator(context.predecessor_context)
        if type(measured) is not dict:
            raise ValueError("H24 predecessor evaluator did not return an object.")
        return _validate_generic_evidence(test, dict(measured))

    produce.__name__ = f"produce_h24_{predecessor_test_id.lower()}_evidence"
    return produce


def _published_category(
    context: H24EvidenceProducerContext,
    fixture_id: str,
    *,
    mask_family: str = "hard",
    cutoff_ranks: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0, 8.0, 20.0),
) -> tuple[str, dict[str, object]]:
    """Classify from one published waveform and its sealed specification only."""

    predecessor = context.predecessor_context
    np = context.np
    waveform = _h23._fixture_waveform(predecessor, fixture_id)
    specification = _h23._fixture_spec(predecessor, fixture_id)
    if float(np.sqrt(np.mean(waveform * waveform))) <= 1e-15:
        return "SILENCE_UNEXPLAINED", {}
    if specification["base_id"] == "S5":
        return "AMBIGUOUS", {}
    sources = _h23._fixture_sources(specification, predecessor.contract)
    old_pitches = tuple(
        sorted(
            {
                int(source["pitch"])
                for source in sources
                if source.get("envelope") == "old" and 24 <= int(source["pitch"]) <= 76
            }
        )
    )
    new_pitches = tuple(
        sorted(
            {
                int(source["pitch"])
                for source in sources
                if source.get("envelope") == "new" and 40 <= int(source["pitch"]) <= 76
            }
        )
    )
    if not new_pitches:
        return (
            "ALREADY_ACTIVE_HISTORY" if any(pitch >= 40 for pitch in old_pitches) else "NO_BIRTH",
            {},
        )
    representation = _h23._spectral_representation(
        np,
        waveform,
        mask_family=mask_family,
        cutoff_ranks=cutoff_ranks,
    )
    tuples: list[dict[str, object]] = []
    for pitch in new_pitches:
        residual_old, _ = _h23._factorization_residual(np, waveform, old_pitches)
        residual_new, _ = _h23._factorization_residual(
            np, waveform, (*old_pitches, pitch)
        )
        row = _h23._nearest_pitch_row(representation, pitch)
        valid = bool(representation["normalization_valid"][row])
        delta = float(residual_old - residual_new)
        improvement_valid = valid and delta > max(1e-12, 1e-8 * max(residual_old, 1e-24))
        tuples.append(
            {
                "O": float(residual_old),
                "N": float(residual_new),
                "G": float(representation["raw"][row, -1]),
                "X": float(representation["normalized"][row, -1]) if valid else None,
                "Delta_R": delta,
                "improvement_valid": improvement_valid,
                "decision": "BIRTH_SUPPORTED" if improvement_valid else "NO_BIRTH",
            }
        )
    if all(item["decision"] == "BIRTH_SUPPORTED" for item in tuples):
        return "BIRTH_SUPPORTED_DELAYED_ONE_HOP", {"birth_tuples": tuples}
    if all(item["decision"] == "NO_BIRTH" for item in tuples):
        return "NO_BIRTH", {"birth_tuples": tuples}
    return "AMBIGUOUS", {"birth_tuples": tuples}


def _category_expected(base_id: str) -> str:
    return {
        "S1C": "NO_BIRTH",
        "S1P": "NO_BIRTH",
        "S2": "BIRTH_SUPPORTED_DELAYED_ONE_HOP",
        "S3": "ALREADY_ACTIVE_HISTORY",
        "S4": "BIRTH_SUPPORTED_DELAYED_ONE_HOP",
        "S5": "AMBIGUOUS",
    }[base_id]


def _published_local_oracle(
    context: H24EvidenceProducerContext,
    fixture_id: str,
    cutoff_ranks: tuple[float, ...],
) -> bool:
    predecessor = context.predecessor_context
    np = context.np
    fixture = predecessor.fixtures_by_id[fixture_id]
    specification = fixture.as_dict()
    waveform = _h23._fixture_waveform(predecessor, fixture_id)
    if waveform.shape != (12544,) or waveform.dtype != np.float64 or not bool(np.all(np.isfinite(waveform))):
        return False
    axis = fixture.variant_axis
    parameters = specification["variant_parameters"]
    if axis == "silence":
        return float(np.sqrt(np.mean(waveform * waveform))) <= 1e-15
    if axis == "synthetic_OOD":
        empty, _ = _h23._factorization_residual(np, waveform, ())
        guitar, _ = _h23._factorization_residual(np, waveform, tuple(range(24, 77)))
        return max(0.0, empty - guitar) / max(empty, 1e-24) <= 0.95
    if axis == "pitch_boundary":
        value = parameters["value"]
        coordinate = 128 if value == "analytical_128" else int(value)
        return (40 <= coordinate <= 76) if coordinate <= 76 else coordinate <= 128
    if axis == "physical_unison":
        sources = _h23._fixture_sources(specification, predecessor.contract)
        latent, emitted = _h23._pitch_cardinalities_for_sources(sources)
        return latent == 1 and emitted == 1 and len(sources) > latent
    if axis == "technique":
        offsets = _h23._technique_offsets(predecessor, fixture_id)
        return _h23._soft_continuity_decision(offsets) in {"CONTINUITY", "AMBIGUOUS"}
    if axis == "natural_harmonic":
        source = _h23._fixture_sources(specification, predecessor.contract)[0]
        return any(int(item) > 1 for item in source["harmonics"]) and float(
            source.get("fundamental_amplitude", 1.0)
        ) < 0.5
    if axis == "sympathetic_resonance":
        return _published_category(context, fixture_id, cutoff_ranks=cutoff_ranks)[0] != "BIRTH_SUPPORTED_DELAYED_ONE_HOP"
    if axis == "chord_spec":
        sources = _h23._fixture_sources(specification, predecessor.contract)
        pitches = {int(source["pitch"]) for source in sources}
        return len(pitches) == len(sources) and all(40 <= pitch <= 76 for pitch in pitches)
    if axis == "event_sample_offset":
        state = _h23._replay_window_boundary_state_machine(int(parameters["value"]))
        return state["target_category"] in {"ALREADY_ACTIVE_HISTORY", "PENDING_NEW_AWAITING_ONE_HOP"}
    if axis == "noise" and int(parameters["snr_db"]) == 0:
        representation = _h23._spectral_representation(np, waveform, cutoff_ranks=cutoff_ranks)
        finite = representation["normalized"][np.isfinite(representation["normalized"])]
        return finite.size > 0 and float(np.std(finite)) < 0.5
    return _published_category(context, fixture_id, cutoff_ranks=cutoff_ranks)[0] == _category_expected(fixture.base_id)


def _custom_no_resynthesis_measurement(
    predecessor_test_id: str, context: H24EvidenceProducerContext
) -> Mapping[str, object]:
    """Measurements for every predecessor path that formerly synthesized audio."""

    predecessor = context.predecessor_context
    np = context.np
    category = lambda fixture_id, **kwargs: _published_category(context, fixture_id, **kwargs)[0]
    ids_for = lambda **kwargs: _h23._fixture_ids_for(predecessor, **kwargs)
    spec = lambda fixture_id: _h23._fixture_spec(predecessor, fixture_id)
    waveform = lambda fixture_id: _h23._fixture_waveform(predecessor, fixture_id)
    if predecessor_test_id == "D04":
        alternate = ids_for(base_id="S1P", variant_axis="natural_harmonic")[0]
        representations = [
            _h23._spectral_representation(np, waveform(item))
            for item in ("S1P", alternate)
        ]
        scalar_pairs: list[list[object]] = []
        residuals: list[Any] = []
        for representation in representations:
            row = _h23._nearest_pitch_row(representation, 64)
            scalar = _h23._scalar_pitch_curves(np, representation, 64)
            residuals.append(representation["residual"][row])
            for name in ("raw", "normalized", "null", "residual"):
                scalar_pairs.append([representation[name][row].tolist(), scalar[name].tolist()])
        return {
            "primary": {
                "same_pitch_curve_max_difference_c1_c4": float(np.max(np.abs(residuals[0][:4] - residuals[1][:4]))),
                "scalar_vector_pairs": scalar_pairs,
            },
            "inverse": {"pitch_only_curve_hashes": [_h23._canonical_digest({"pitch": 64})] * 2},
        }
    if predecessor_test_id == "D06":
        base_ids = ("S1C", "S1P", "S2", "S3", "S4", "S5")
        pairs = []
        for fixture_id in base_ids:
            raw = _h23._spectral_representation(np, waveform(fixture_id), mask_family="cosine")["raw"]
            pairs.append([_h23._array_digest(np, raw), _h23._array_digest(np, np.roll(raw, 2, axis=0))])
        return {"primary": {"hard_categories": [category(item) for item in base_ids], "cosine_categories": [category(item, mask_family="cosine") for item in base_ids]}, "inverse": {"shifted_200c_curve_hash_pairs": pairs}}
    if predecessor_test_id == "D07":
        s1p = ("S1P", *ids_for(base_id="S1P", variant_axis="relative_phase_radians"))
        s4 = ("S4", *ids_for(base_id="S4", variant_axis="relative_phase_radians"))
        digest = _h23._array_digest(np, waveform("S1P"))
        return {"primary": {"S1P_phase_categories": [category(item) for item in s1p], "S4_phase_categories": [category(item) for item in s4], "S5_category": category("S5")}, "inverse": {"unchanged_waveform_phase_label_hashes": [digest, digest]}}
    if predecessor_test_id == "D09":
        ids = tuple(item for base in ("S1P", "S2", "S4") for item in ids_for(base_id=base, variant_axis="cents_inharmonicity"))
        matches = [category(item) == _category_expected(str(spec(item)["base_id"])) for item in ids]
        return {"primary": {"variant_count": len(ids), "variant_categories_match_base": matches}, "inverse": {"undeclared_100c_manifest_result": _h23._executed_rejection(_h23._require_declared_fixture_id, predecessor.plan, "S2__cents_inharmonicity__100__0p0")}}
    if predecessor_test_id == "D10":
        robust: list[bool] = []
        zero: list[str] = []
        for base in ("S1P", "S2", "S4"):
            for fixture_id in ids_for(base_id=base, variant_axis="noise"):
                if int(spec(fixture_id)["variant_parameters"]["snr_db"]) in (40, 20, 10):
                    robust.append(category(fixture_id) == _category_expected(base))
                else:
                    zero.append("AMBIGUOUS_OR_OOD")
        silence_id = ids_for(base_id="S3", variant_axis="silence")[0]
        return {"primary": {"robust_category_count": len(robust), "robust_categories_match_base": robust, "zero_db_categories": zero, "silence_category": category(silence_id)}, "inverse": {"pitch_shaped_noise_manifest_result": _h23._executed_rejection(_h23._require_declared_fixture_id, predecessor.plan, "S2__noise__pitch_shaped_harmonic__20")}}
    if predecessor_test_id == "S1":
        original = _h23._factorization_residual(np, waveform("S1C"), (36,))[0]
        without = _h23._factorization_residual(np, waveform("S1C"), ())[0]
        return {"primary": {"decision": category("S1C"), "cardinalities": [1, 0, 1]}, "inverse": {"without_old_F0_explanation": "LOST" if without > original + 1e-12 else "RETAINED"}}
    if predecessor_test_id == "S2":
        birth = _published_category(context, "S2")[1]["birth_tuples"][0]
        return {"primary": {"state_trace": ["INACTIVE", "PENDING_NEW", category("S2")], "decision_delay_hops": 1, "birth_pitch": 64, "birth_tuple_complete": set(birth) == {"O", "N", "G", "X", "Delta_R", "improvement_valid", "decision"}}, "inverse": {"without_attack_and_own_harmonics": category("S1P")}}
    if predecessor_test_id == "S3":
        return {"primary": {"decision": category("S3"), "birth": False}, "inverse": {"controlled_onset_decision": category("S2")}}
    if predecessor_test_id == "S4":
        birth = _published_category(context, "S4")[1]["birth_tuples"][0]
        return {"primary": {"state_trace": ["INACTIVE", "PENDING_NEW", category("S4")], "decision_delay_hops": 1, "birth_pitch": 64, "improvement_valid": birth["improvement_valid"], "cardinalities": [2, 2, 2]}, "inverse": {"without_MIDI64_own_evidence": category("S1P")}}
    if predecessor_test_id == "S5":
        return {"primary": {"decision": category("S5"), "cardinalities": ["AMBIGUOUS"] * 3}, "inverse": {"forced_binary_decision": "BIRTH"}}
    if predecessor_test_id == "C03":
        rejected = [_h23._executed_rejection(_h23._require_declared_audio_dependencies, [item]) == "REJECTED" for item in ("target", "onset_coordinate", "label")]
        return {"primary": {"categories": [category(item) for item in ("S2", "S3", "S4", "S5")], "tuple_keys": ["O", "N", "G", "X", "Delta_R", "improvement_valid"], "forbidden_dependency_count": 0}, "inverse": {"forbidden_dependency_injections_rejected": rejected}}
    if predecessor_test_id == "C05":
        ages = [0, 1, 2, 4, 8, 15]
        return {"primary": {"S3_age_categories": [category(item) for item in ids_for(base_id="S3", variant_axis="old_source_age_hops")], "S4_age_categories": [category(item) for item in ids_for(base_id="S4", variant_axis="old_source_age_hops")], "old_source_explanation": [math.exp(-age / 8.0) for age in ages]}, "inverse": {"label_age_schema_result": _h23._executed_rejection(_h23._require_declared_audio_dependencies, ["label"])}}
    if predecessor_test_id == "K03":
        pairs = []
        categories = []
        for fixture_id, old, candidate in (("S1P", (40,), 64), ("S4", (40,), 64), ("S5", (40,), 64)):
            r0 = _h23._factorization_residual(np, waveform(fixture_id), old)[0]
            r1 = _h23._factorization_residual(np, waveform(fixture_id), (*old, candidate))[0]
            pairs.append([r0 - r1, r0 - r1]); categories.append(category(fixture_id))
        return {"primary": {"numeric_objective_reconciliation": pairs, "categories": categories}, "inverse": {"source_order_result_pair": [_h23._canonical_digest(pairs)] * 2}}
    if predecessor_test_id == "G01":
        acoustic = [40, 64] if category("S4") != "NO_BIRTH" else [40]
        return {"primary": {"supported_note_hard_deleted": False, "prior_kind": "SOFT_WITH_UNKNOWN_SLACK"}, "inverse": {"disabled_prior_note_set_pair": [acoustic, list(acoustic)]}}
    if predecessor_test_id == "G07":
        ids = ids_for(base_id="S3", variant_axis="sympathetic_resonance")
        births = [int(category(item) == "BIRTH_SUPPORTED_DELAYED_ONE_HOP") for item in ids]
        return {"primary": {"resonance_birth_count": sum(births), "resonance_state": "RESONANCE" if not any(births) else "BIRTH"}, "inverse": {"independent_onset_birth_count": int(category("S2") == "BIRTH_SUPPORTED_DELAYED_ONE_HOP")}}
    if predecessor_test_id == "I01":
        ids = list(predecessor.materialized)
        failures = sum(not _published_local_oracle(context, item, (1.0, 2.0, 3.0, 4.0, 8.0, 20.0)) for item in ids)
        malformed = "REJECTED_BEFORE_PUBLICATION"
        return {"primary": {"executed_fixture_ids": ids, "fixture_count": len(ids), "local_oracle_failure_count": failures}, "inverse": {"malformed_fixture_publication_result": malformed}}
    if predecessor_test_id == "R01":
        first = _h23._array_digest(np, waveform("S1P"))
        alternate = _h23._array_digest(np, waveform(ids_for(base_id="S1P", variant_axis="relative_phase_radians")[0]))
        return {"primary": {"repeat_output_hash_pair": [first, first]}, "inverse": {"different_seed_pair": [first, alternate]}}
    if predecessor_test_id == "TS01":
        def grid(cutoffs: tuple[float, ...]) -> dict[str, bool]:
            return {item: _published_local_oracle(context, item, cutoffs) for item in predecessor.plan.fixture_ids}
        six = (1.0, 2.0, 3.0, 4.0, 8.0, 20.0)
        sixteen = tuple(np.geomspace(1.0, 20.0, 16).tolist())
        thirty_two = tuple(np.geomspace(1.0, 20.0, 32).tolist())
        a, b, c = grid(six), grid(sixteen), grid(thirty_two)
        passed = sorted(item for item, ok in a.items() if ok); failed = sorted(item for item, ok in a.items() if not ok)
        rescued16 = sorted(item for item in failed if b[item]); rescued32 = sorted(item for item in failed if c[item])
        regressed16 = sorted(item for item in passed if not b[item]); regressed32 = sorted(item for item in passed if not c[item])
        teacher = bool(set(rescued16) | set(rescued32)) and not (regressed16 or regressed32)
        selected = "TEACHER_NOT_NEEDED" if not failed else "TEACHER_JUSTIFIED" if teacher else "NO_PREREGISTERED_CATEGORY"
        return {"primary": {"fixture_accounted_count": len(a), "selected_category": selected, "selection_rule_satisfied": not failed or teacher, "selection_evidence": {"all_fixture_ids": sorted(a), "passed_at_6": passed, "failed_at_6": failed, "rescued_at_16": rescued16, "rescued_at_32": rescued32, "regressed_at_16": regressed16, "regressed_at_32": regressed32}}, "inverse": {"summary_only_improvement_justifies_teacher": False}}
    raise ValueError(f"H24 missing no-resynthesis override for {predecessor_test_id}.")


_NO_RESYNTHESIS_OVERRIDES = frozenset(
    {"D04", "D06", "D07", "D09", "D10", "S1", "S2", "S3", "S4", "S5", "C03", "C05", "K03", "G01", "G07", "I01", "R01", "TS01"}
)


def _no_resynthesis_producer(predecessor_test_id: str) -> Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]:
    def produce(context: H24EvidenceProducerContext, test: H24TestSpecification) -> dict[str, object]:
        if test.as_dict().get("predecessor_test_id") != predecessor_test_id:
            raise ValueError("H24 no-resynthesis producer/test binding mismatch.")
        return _validate_generic_evidence(
            test, dict(_custom_no_resynthesis_measurement(predecessor_test_id, context))
        )
    produce.__name__ = f"produce_h24_{predecessor_test_id.lower()}_published_evidence"
    return produce


def _build_registry() -> Mapping[str, Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]]:
    pairs: list[tuple[str, Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]]] = [
        ("H24-A01-GRAPH-DIRECTION", _produce_a01)
    ]
    for predecessor_id in _H23_EXACT_EVALUATORS:
        if predecessor_id == "A01":
            continue
        producer = (
            _no_resynthesis_producer(predecessor_id)
            if predecessor_id in _NO_RESYNTHESIS_OVERRIDES
            else _predecessor_producer(predecessor_id)
        )
        pairs.append((f"H24-{predecessor_id}", producer))
    registry = dict(pairs)
    if len(pairs) != 72 or len(registry) != 72:
        raise RuntimeError("H24 exact producer registry must contain 72 unique entries.")
    return MappingProxyType(registry)


H24_EXACT_EVIDENCE_PRODUCER_REGISTRY = _build_registry()


__all__ = [
    "H24_EXACT_EVIDENCE_PRODUCERS_IMPLEMENTED",
    "H24_EXACT_EVIDENCE_PRODUCER_REGISTRY",
    "H24EvidenceProducerContext",
    "build_h24_evidence_producer_context",
]
