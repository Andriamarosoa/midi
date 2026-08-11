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
from .run_harmonic_censoring_h23_synthetic import (
    _H23ExactOracleContext,
    _H23_EXACT_EVALUATORS,
    _load_h23_scientific_contract,
)


H24_EXACT_EVIDENCE_PRODUCERS_IMPLEMENTED = True
_FORBIDDEN_PRODUCER_FIELDS = frozenset({"pass", "passed", "verdict", "final_pass"})


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


def _build_registry() -> Mapping[str, Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]]:
    pairs: list[tuple[str, Callable[[H24EvidenceProducerContext, H24TestSpecification], dict[str, object]]]] = [
        ("H24-A01-GRAPH-DIRECTION", _produce_a01)
    ]
    for predecessor_id in _H23_EXACT_EVALUATORS:
        if predecessor_id == "A01":
            continue
        pairs.append((f"H24-{predecessor_id}", _predecessor_producer(predecessor_id)))
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
