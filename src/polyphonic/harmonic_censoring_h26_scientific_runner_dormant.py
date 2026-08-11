"""Dormant H26 scientific sequence runner for injected fakes only."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .harmonic_censoring_h26_scientific_execution_contract_seal import load_scientific_execution_contract_external_seal

@dataclass(frozen=True)
class H26DormantScientificTrace:
    stages: tuple[str,...]
    fake_population_identity: str
    locked_test_used: bool
    real_science_executed: bool
    results: tuple[Any,...]

def exercise_h26_scientific_sequence_with_fakes(*, fake_population_identity: str, fake_p0: Callable[[],Any], fake_p1: Callable[[Any],Any], fake_p2: Callable[[Any],Any]) -> H26DormantScientificTrace:
    """Exercise control flow only; no real engine or population is reachable."""
    load_scientific_execution_contract_external_seal()
    if type(fake_population_identity) is not str or not fake_population_identity.startswith("fake:"):
        raise ValueError("explicit fake population identity required")
    p0=fake_p0(); p1=fake_p1(p0); p2=fake_p2(p1)
    return H26DormantScientificTrace(("P0_FAKE","P1_FAKE","P2_FAKE"),fake_population_identity,False,False,(p0,p1,p2))

__all__=["H26DormantScientificTrace","exercise_h26_scientific_sequence_with_fakes"]
