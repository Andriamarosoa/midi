"""Strictly dormant H27 one-shot composition harness.

Only the private dependency-injected harness is testable. The public production
edge is an immutable native barrier and cannot invoke the reviewed materializer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_SEALED_ADMINISTRATIVE_INPUTS = (
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json", "2fc615a5f1c45245dd579891b42cfe12feb100aa", 9912, "230249ef9118d43d0d538f8b005178fd123852ddf6ed7ee69e1d76553949b622"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json", "d912a1ebd0fb6818147a0f07da1f6140d9434398", 2786, "9a698340046692eab0e415a6094cdffc7ce36c40ce38382cbe53425f10c6238e"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding.json", "1f41f92b60c541219013bb78d40d38d183b2b80c", 6092, "4621b87709ecf74ed5cb733d1a4470e576b8ea159b48256446b5dd539b0a70e0"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding_external_seal.json", "cfaf71d625e774cf7294b993b7ea6206b53adc43", 3184, "9e8b20928f233e0910c3bb3c583a4a4686681b91ab8049e89dfe4129c1a5e5e3"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json", "e7191b7b27d9339b1f94fc89aec032dd9ad61062", 6032, "0f965e7bce28982d408dfd41054bde59f02c11a5016dc90af483dba6a14b6a1d"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json", "a32721107c1ff65697661cfa7a2a235811884fc6", 4609, "a752721a022433ac1d9fddccb29b9e56cbd5c1bc0566762ca50acd2f9b01a9fc"),
)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_reviewed_administrative_bytes() -> None:
    for relative, blob, size, sha256 in _SEALED_ADMINISTRATIVE_INPUTS:
        raw = (_ROOT / relative).resolve(strict=True).read_bytes()
        if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
            raise PermissionError(f"H27 composition administrative binding drift: {relative}.")


class H27DormantCompositionAdapters(NamedTuple):
    verify_fixed_paths: Callable[[], None]
    verify_contract_chain: Callable[[], None]
    verify_historical_chain: Callable[[], None]
    verify_module_identities: Callable[[], None]
    verify_git_state: Callable[[], None]
    verify_runtime_environment: Callable[[], None]
    verify_path_preconditions: Callable[[], None]
    verify_activation_authority: Callable[[], None]
    create_durable_claim: Callable[[], object]
    construct_capability: Callable[[object], tuple[object, object]]
    consume_attested: Callable[[tuple[object, object]], object]


@dataclass(frozen=True)
class H27DormantCompositionTrace:
    steps: tuple[str, ...]
    claim_created: bool
    capability_consumed: bool
    science_invocations: int
    terminal: bool


_STEPS = (
    "verify_fixed_paths",
    "verify_contract_chain",
    "verify_historical_chain",
    "verify_module_identities",
    "verify_git_state",
    "verify_runtime_environment",
    "verify_path_preconditions",
    "verify_activation_authority",
    "create_durable_claim",
    "construct_capability",
    "consume_attested",
)


def _exercise_dormant_composition(adapters: H27DormantCompositionAdapters) -> H27DormantCompositionTrace:
    """Exercise steps 1-11 with fake adapters; step 12 is unconditionally shut."""

    _verify_reviewed_administrative_bytes()
    completed: list[str] = []
    for name in _STEPS[:8]:
        getattr(adapters, name)()
        completed.append(name)
    claim = adapters.create_durable_claim()
    completed.append("create_durable_claim")
    pair = adapters.construct_capability(claim)
    if type(pair) is not tuple or len(pair) != 2:
        raise PermissionError("H27 dormant capability adapter must return one exact pair.")
    completed.append("construct_capability")
    consumed = adapters.consume_attested(pair)
    if consumed is not pair[1]:
        raise PermissionError("H27 dormant atomic consumption returned a foreign binding.")
    completed.append("consume_attested")
    return H27DormantCompositionTrace(
        steps=tuple(completed),
        claim_created=True,
        capability_consumed=True,
        science_invocations=0,
        terminal=True,
    )


_DORMANT_NATIVE_BARRIER = ().__getitem__
execute_h27_one_shot_composition = _DORMANT_NATIVE_BARRIER


__all__ = ["execute_h27_one_shot_composition"]
