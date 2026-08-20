"""Fail-closed loader for the exact H27 Review-4 population index."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Mapping

from .harmonic_censoring_h27_contract import (
    H27DormantPlan, canonical_h27_record_identities, parse_strict_json,
)
from .harmonic_censoring_h27_scientific_authority import (
    register_h27_sealed_record_binding, require_h27_capability_population_index,
    require_operational_h27_capability,
)
from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
    H27_SEALED_RECORD_BINDING_FIELDS,
)


INDEX_FIELDS = ("population_namespace", "record_count", "records", "schema_version")
RECORD_FIELDS = (
    "record_identity", "record_directory", "population_namespace", "payload_sha256",
    "candidate_pitch", "active_pitches", "proposal_hop_end", "resolution_hop_end",
    "cents", "inharmonicity",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _regular_no_symlink(path: Path, label: str) -> Path:
    value = Path(path)
    info = os.lstat(value)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"H27 {label} must be a regular non-symlink file.")
    return value


def _record_sha(record: Mapping[str, object]) -> str:
    raw = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    return _sha(raw)


def load_h27_sealed_population_bindings(
    *, capability: H27ScientificCapability, plan: H27DormantPlan,
    population_root: Path, expected_index_sha256: str,
) -> tuple[H27SealedRecordBinding, ...]:
    """Read the sealed index only after capability issuance; never read payload bytes."""

    require_operational_h27_capability(capability)
    require_h27_capability_population_index(capability, expected_index_sha256)
    lexical_root = Path(population_root).absolute()
    root = lexical_root.resolve(strict=True)
    if lexical_root != root or lexical_root.is_symlink() or not root.is_dir():
        raise ValueError("H27 population root invalid.")
    index_path = _regular_no_symlink(root / "population_index.json", "population index")
    raw = index_path.read_bytes()
    if _sha(raw) != expected_index_sha256:
        raise ValueError("H27 population index SHA mismatch.")
    value = parse_strict_json(raw, "H27 population index")
    if tuple(value) != INDEX_FIELDS or value["schema_version"] != 1:
        raise ValueError("H27 population index schema/order mismatch.")
    if value["population_namespace"] != "H27_SYNTHETIC_V1" or value["record_count"] != 124:
        raise ValueError("H27 population index identity/count mismatch.")
    records = value["records"]
    if type(records) is not list or len(records) != 124:
        raise ValueError("H27 population records invalid.")
    expected_identities = canonical_h27_record_identities(plan)
    if tuple(record.get("record_identity") for record in records) != expected_identities:
        raise ValueError("H27 population record identity/order mismatch.")
    result = []
    for record in records:
        if type(record) is not dict or tuple(record) != RECORD_FIELDS:
            raise ValueError("H27 population record schema/order mismatch.")
        identity = str(record["record_identity"])
        relative = Path(str(record["record_directory"]))
        if relative.as_posix() != identity or relative.is_absolute() or ".." in relative.parts:
            raise ValueError("H27 record path mismatch or escape.")
        directory = root / relative
        resolved = directory.resolve(strict=True)
        if (directory.absolute() != resolved or resolved.parent == resolved
                or root not in resolved.parents or directory.is_symlink()):
            raise ValueError("H27 record directory containment mismatch.")
        payloads = record["payload_sha256"]
        expected_names = {"waveform.f64le", "sample-valid-mask.u8"}
        if identity in {"baseline/H27-F-A01", "baseline/H27-F-A02"} or "/H27-F-A01/" in identity or "/H27-F-A02/" in identity:
            expected_names.add("alternate-waveform.f64le")
        if type(payloads) is not dict or set(payloads) != expected_names:
            raise ValueError("H27 payload topology mismatch.")
        for name, digest in payloads.items():
            if type(digest) is not str or len(digest) != 64:
                raise ValueError("H27 payload digest invalid.")
            _regular_no_symlink(resolved / name, f"payload {name}")
        binding = object.__new__(H27SealedRecordBinding)
        values = {
            "population_root": root,
            "population_index_path": index_path,
            "population_index_sha256": expected_index_sha256,
            "population_index_record_sha256": _record_sha(record),
            "record_directory": resolved,
            "record_identity": identity,
            "population_namespace": record["population_namespace"],
            "payload_sha256": dict(payloads),
            "candidate_pitch": record["candidate_pitch"],
            "active_pitches": tuple(record["active_pitches"]),
            "proposal_hop_end": record["proposal_hop_end"],
            "resolution_hop_end": record["resolution_hop_end"],
            "cents": record["cents"],
            "inharmonicity": record["inharmonicity"],
        }
        if tuple(values) != H27_SEALED_RECORD_BINDING_FIELDS:
            raise RuntimeError("H27 sealed binding field order drift.")
        for field, item in values.items():
            object.__setattr__(binding, field, item)
        result.append(register_h27_sealed_record_binding(capability, binding))
    return tuple(result)


__all__ = ["INDEX_FIELDS", "RECORD_FIELDS", "load_h27_sealed_population_bindings"]
