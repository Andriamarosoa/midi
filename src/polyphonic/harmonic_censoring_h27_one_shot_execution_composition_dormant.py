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
_COMPOSITION_INPUTS = (
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json", "2fc615a5f1c45245dd579891b42cfe12feb100aa", 9912, "230249ef9118d43d0d538f8b005178fd123852ddf6ed7ee69e1d76553949b622"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json", "d912a1ebd0fb6818147a0f07da1f6140d9434398", 2786, "9a698340046692eab0e415a6094cdffc7ce36c40ce38382cbe53425f10c6238e"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding.json", "1f41f92b60c541219013bb78d40d38d183b2b80c", 6092, "4621b87709ecf74ed5cb733d1a4470e576b8ea159b48256446b5dd539b0a70e0"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding_external_seal.json", "cfaf71d625e774cf7294b993b7ea6206b53adc43", 3184, "9e8b20928f233e0910c3bb3c583a4a4686681b91ab8049e89dfe4129c1a5e5e3"),
)
_HISTORICAL_INPUTS = (
    ("configs/harmonic_censoring_h27_materialization_activation_contract.json", "2df0e53637cc31d97c01e75b88cb47c2e866c187", 11131, "a1e679e4357552bd88640d3d67a6f17bd9feaad38e8f26e4ed68539f167980c4"),
    ("configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json", "0ef61aa7ada69b619a8e7acd7138151a36496089", 3122, "2174570372df3e8349a425d62ce8e1d084238757fb944968ad8539d9dcabac9d"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json", "e7ff1b71bdd62adf8341dbd824302f1eb57e69c6", 7358, "da96c338d4a99e848ab5fa63d717442c3af27fab6268bb9abae99c1f76321dab"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json", "d34da25095581694ce4ca928734bb9b01d2e357c", 1245, "8bb92ad437331528adf744388e77b445c8477a2e7dcbc87f4b84d602a147102b"),
)
_IDENTITY_INPUTS = (
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json", "e7191b7b27d9339b1f94fc89aec032dd9ad61062", 6032, "0f965e7bce28982d408dfd41054bde59f02c11a5016dc90af483dba6a14b6a1d"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json", "9e89d4d68013193582dee1062c61aaf8dd191ad3", 2848, "664ad640a623f3357226b83985665253b3c37b5c4fc10252223e25e0087def12"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_boundary_external_review_seal.json", "c33350b3712a179a0e5577e90763ec72f96fd165", 3864, "93b3d86633f979a9521cd93d0e7629956015e279ad61cbbfca579d2857185c6b"),
    ("src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py", "ec61eef88dce7591fd411af230568b1e1d44d62e", 18915, "d3d06f8c087845089094ff71f29d8745581d391784b9bbc40abeb57b0ba42f2f"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json", "a32721107c1ff65697661cfa7a2a235811884fc6", 4609, "a752721a022433ac1d9fddccb29b9e56cbd5c1bc0566762ca50acd2f9b01a9fc"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json", "be17bda1d7da5144758606ed4b4f1b56708ebf3d", 1760, "a7aa1f6d844fb25e2f633db8bd2817f6741bfe194418985c8419bda64573b3be"),
    ("configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json", "d5b852e63676b59a75b938ef17c51f9247dd5e68", 3057, "68751aede0f11ce04763eb7398f4c071db91310c62c9a58c11667b908b58f95f"),
    ("src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py", "79f399359e366781f9526098c98a93cca71b1b49", 32243, "02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70"),
)
_SEALED_ADMINISTRATIVE_INPUTS = _COMPOSITION_INPUTS + _HISTORICAL_INPUTS + _IDENTITY_INPUTS


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact_group(group: tuple[tuple[str, str, int, str], ...]) -> None:
    for relative, blob, size, sha256 in group:
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

    completed: list[str] = []
    adapters.verify_fixed_paths()
    completed.append("verify_fixed_paths")
    for name, group in (
        ("verify_contract_chain", _COMPOSITION_INPUTS),
        ("verify_historical_chain", _HISTORICAL_INPUTS),
        ("verify_module_identities", _IDENTITY_INPUTS),
    ):
        _verify_exact_group(group)
        getattr(adapters, name)()
        completed.append(name)
    for name in _STEPS[4:8]:
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
