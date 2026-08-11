"""Dormant H26 scientific sequence runner for structural fakes only."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .harmonic_censoring_h26_scientific_execution_contract_seal import load_scientific_execution_contract_external_seal


@dataclass(frozen=True)
class H26FakeOnlySequence:
    """Non-executable input for the fixed dormant P0/P1/P2 demonstration."""

    fake_population_identity: str

    def __post_init__(self) -> None:
        if (
            type(self.fake_population_identity) is not str
            or not self.fake_population_identity.startswith("fake:")
        ):
            raise ValueError("explicit fake population identity required")

@dataclass(frozen=True)
class H26DormantScientificTrace:
    stages: tuple[str,...]
    fake_population_identity: str
    locked_test_used: bool
    real_science_executed: bool
    results: tuple[Any,...]


def make_h26_fake_only_sequence(*, fake_population_identity: str) -> H26FakeOnlySequence:
    """Create inert fake-only input; it cannot carry executable callbacks."""

    return H26FakeOnlySequence(fake_population_identity=fake_population_identity)


def exercise_h26_scientific_sequence_with_fakes(
    *, fake_sequence: H26FakeOnlySequence
) -> H26DormantScientificTrace:
    """Exercise fixed fake control flow; no caller-provided code is invoked."""
    load_scientific_execution_contract_external_seal()
    if type(fake_sequence) is not H26FakeOnlySequence:
        raise TypeError("exact H26FakeOnlySequence required")
    p0 = "P0_FAKE_COMPLETE"
    p1 = ("P1_FAKE_COMPLETE", p0)
    p2 = ("P2_FAKE_COMPLETE", p1)
    return H26DormantScientificTrace(
        ("P0_FAKE", "P1_FAKE", "P2_FAKE"),
        fake_sequence.fake_population_identity,
        False,
        False,
        (p0, p1, p2),
    )

__all__ = [
    "H26DormantScientificTrace",
    "H26FakeOnlySequence",
    "exercise_h26_scientific_sequence_with_fakes",
    "make_h26_fake_only_sequence",
]
