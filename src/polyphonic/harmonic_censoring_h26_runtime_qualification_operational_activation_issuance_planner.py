"""Pure dormant planner for one future H26 activation issuance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Mapping

from .harmonic_censoring_h26_runtime_qualification_operational_activation import validate_artificial_runtime_qualification_operational_activation
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract_seal import load_runtime_qualification_operational_activation_issuance_contract_external_seal
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_implementation_contract_seal import load_issuer_implementation_contract_external_seal

_ISSUER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_ISSUED_AT = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$")

@dataclass(frozen=True)
class H26ActivationIssuancePlan:
    activation_id: str
    activation_raw_sha256: str
    canonical_bytes: bytes
    administrative_root: str
    final_path: str
    staging_path: str
    issuer_identity: str
    issued_at: str

def plan_runtime_qualification_operational_activation_issuance(activation: Mapping[str, Any]) -> H26ActivationIssuancePlan:
    """Validate caller-supplied values and return a side-effect-free plan."""
    load_runtime_qualification_operational_activation_issuance_contract_external_seal()
    load_issuer_implementation_contract_external_seal()
    issuer = activation.get("issuer_identity")
    issued_at = activation.get("issued_at")
    if type(issuer) is not str or _ISSUER.fullmatch(issuer) is None or not issuer.isascii():
        raise ValueError("issuer_identity contract mismatch")
    if type(issued_at) is not str or _ISSUED_AT.fullmatch(issued_at) is None:
        raise ValueError("issued_at contract mismatch")
    try:
        datetime.strptime(issued_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("issued_at is not valid Gregorian UTC") from exc
    validated = validate_artificial_runtime_qualification_operational_activation(activation)
    root = activation["administrative_root"]
    return H26ActivationIssuancePlan(
        activation_id=validated.activation_id,
        activation_raw_sha256=validated.raw_sha256,
        canonical_bytes=validated.canonical_bytes,
        administrative_root=root,
        final_path=f"{root}/activation/activation.json",
        staging_path=f"{root}/activation/.activation.json.staging",
        issuer_identity=issuer,
        issued_at=issued_at,
    )

__all__ = ["H26ActivationIssuancePlan", "plan_runtime_qualification_operational_activation_issuance"]
