"""Byte-level provenance for the sealed independent V2 validation cohort.

This module is deliberately narrower than the train-only candidate evidence:
it can attest only the 30 independently derived validation recordings.  It
never loads a waveform, an NPZ payload, TensorFlow, a checkpoint, or a
decoder.  Building the registry reads the bytes of the declared audio and
label *files* solely to record size and SHA-256, but is impossible while the
sealed protocol leaves builder authorization disabled.  A future reviewed
runner must re-hash them at their actual open boundaries before it can use
them.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from typing import Protocol, Sequence
import weakref

from .decoder_candidate_provenance import _require_loaded_manifest_snapshot, leakage_group_key
from .run_causal_candidate_v2_independent_validation import (
    IndependentV2ValidationCohort,
    IndependentV2ValidationAssetEvidenceRequirement,
    require_independent_v2_validation_asset_evidence_requirement,
    require_sealed_independent_v2_validation_cohort,
)
from .causal_candidate_v2_independent_validation_execution_contract import (
    IndependentV2ExecutionContract,
    INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256,
    INDEPENDENT_V2_ASSET_EVIDENCE_SHA256,
    INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256,
    INDEPENDENT_V2_MANIFEST_SHA256,
    require_sealed_independent_v2_execution_contract,
)


INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION = 1
INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE = (
    "causal_candidate_v2_independent_validation_asset_evidence"
)
_BUILT_EVIDENCE: dict[int, weakref.ReferenceType[object]] = {}
_VALIDATED_EVIDENCE: dict[int, weakref.ReferenceType[object]] = {}
_EXECUTION_REQUIREMENTS: dict[int, weakref.ReferenceType[object]] = {}


class IndependentValidationManifestItemLike(Protocol):
    """The exact manifest fields needed to bind one validation capture."""

    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    capture_id: str
    split: str
    audio_path: Path
    audio_member: str
    labels_path: Path


class IndependentValidationManifestSnapshotLike(Protocol):
    manifest_sha256: str
    items: Sequence[IndependentValidationManifestItemLike]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> tuple[int, str]:
    """Hash one regular file without parsing it as audio or labels."""
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"independent validation asset is not a regular file: {resolved}")
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _require_digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string.")
    return value


def _require_size(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative JSON-native integer.")
    return value


def canonical_recording_key(item: IndependentValidationManifestItemLike) -> str:
    """Use the independent V2 contract's canonical recording identity."""
    return "|".join((
        item.dataset_id,
        item.group_id,
        item.source_id,
        item.capture_id,
    ))


def ordered_recording_keys_sha256(recording_keys: Sequence[str]) -> str:
    return _sha256(("\n".join(recording_keys) + "\n").encode("utf-8"))


@dataclass(frozen=True)
class IndependentV2ValidationAssetEvidenceEntry:
    """Portable byte evidence for the two files opened for one validation row."""

    recording_key: str
    leakage_group_key: str
    dataset_id: str
    source_id: str
    capture_id: str
    audio_member: str
    audio_size_bytes: int
    audio_sha256: str
    labels_size_bytes: int
    labels_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "recording_key",
            "leakage_group_key",
            "dataset_id",
            "source_id",
            "capture_id",
        ):
            _require_text(getattr(self, field), field=field)
        if not isinstance(self.audio_member, str):
            raise ValueError("audio_member must be a string.")
        _require_size(self.audio_size_bytes, field="audio_size_bytes")
        _require_digest(self.audio_sha256, field="audio_sha256")
        _require_size(self.labels_size_bytes, field="labels_size_bytes")
        _require_digest(self.labels_sha256, field="labels_sha256")

    def as_json(self) -> dict[str, object]:
        return {
            "recording_key": self.recording_key,
            "leakage_group_key": self.leakage_group_key,
            "dataset_id": self.dataset_id,
            "source_id": self.source_id,
            "capture_id": self.capture_id,
            "audio_member": self.audio_member,
            "audio_size_bytes": self.audio_size_bytes,
            "audio_sha256": self.audio_sha256,
            "labels_size_bytes": self.labels_size_bytes,
            "labels_sha256": self.labels_sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "IndependentV2ValidationAssetEvidenceEntry":
        required = {
            "recording_key",
            "leakage_group_key",
            "dataset_id",
            "source_id",
            "capture_id",
            "audio_member",
            "audio_size_bytes",
            "audio_sha256",
            "labels_size_bytes",
            "labels_sha256",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("independent validation asset-evidence entry has an invalid schema.")
        return cls(**value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class IndependentV2ValidationAssetEvidence:
    """Canonical evidence bound to one exact independent validation cohort."""

    schema_version: int
    purpose: str
    independent_validation_protocol_sha256: str
    manifest_sha256: str
    ordered_recording_keys_sha256: str
    recording_keys: tuple[str, ...]
    asset_types: tuple[str, ...]
    entries: tuple[IndependentV2ValidationAssetEvidenceEntry, ...]

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not int
            or self.schema_version != INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION
        ):
            raise ValueError("unsupported independent validation asset-evidence schema version.")
        if self.purpose != INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE:
            raise ValueError("independent validation asset-evidence purpose is invalid.")
        for field in (
            "independent_validation_protocol_sha256",
            "manifest_sha256",
            "ordered_recording_keys_sha256",
        ):
            _require_digest(getattr(self, field), field=field)
        if (
            type(self.recording_keys) is not tuple
            or len(self.recording_keys) != 30
            or len(set(self.recording_keys)) != 30
            or any(not isinstance(key, str) or not key for key in self.recording_keys)
        ):
            raise ValueError("independent validation asset evidence must bind 30 unique keys.")
        if self.ordered_recording_keys_sha256 != ordered_recording_keys_sha256(
            self.recording_keys
        ):
            raise ValueError("independent validation asset-evidence key digest is invalid.")
        if self.asset_types != ("audio", "labels"):
            raise ValueError("independent validation asset evidence must bind audio and labels only.")
        if (
            type(self.entries) is not tuple
            or len(self.entries) != len(self.recording_keys)
            or not all(
                isinstance(entry, IndependentV2ValidationAssetEvidenceEntry)
                for entry in self.entries
            )
            or tuple(entry.recording_key for entry in self.entries) != self.recording_keys
        ):
            raise ValueError("independent validation asset-evidence entries must match key order.")
        for key, entry in zip(self.recording_keys, self.entries):
            key_fields = key.split("|")
            if (
                len(key_fields) != 4
                or entry.recording_key != key
                or key_fields[0] != entry.dataset_id
                or key_fields[2] != entry.source_id
                or key_fields[3] != entry.capture_id
            ):
                raise ValueError("independent validation evidence entry identity differs from its key.")

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "purpose": self.purpose,
            "independent_validation_protocol_sha256": self.independent_validation_protocol_sha256,
            "manifest_sha256": self.manifest_sha256,
            "ordered_recording_keys_sha256": self.ordered_recording_keys_sha256,
            "recording_keys": list(self.recording_keys),
            "asset_types": list(self.asset_types),
            "entries": [entry.as_json() for entry in self.entries],
        }

    @classmethod
    def from_json(cls, value: object) -> "IndependentV2ValidationAssetEvidence":
        required = {
            "schema_version",
            "purpose",
            "independent_validation_protocol_sha256",
            "manifest_sha256",
            "ordered_recording_keys_sha256",
            "recording_keys",
            "asset_types",
            "entries",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("independent validation asset evidence has an invalid schema.")
        keys = value["recording_keys"]
        asset_types = value["asset_types"]
        entries = value["entries"]
        if (
            not isinstance(keys, list)
            or not isinstance(asset_types, list)
            or not isinstance(entries, list)
        ):
            raise ValueError("independent validation asset evidence has invalid JSON arrays.")
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            purpose=value["purpose"],  # type: ignore[arg-type]
            independent_validation_protocol_sha256=value[
                "independent_validation_protocol_sha256"
            ],  # type: ignore[arg-type]
            manifest_sha256=value["manifest_sha256"],  # type: ignore[arg-type]
            ordered_recording_keys_sha256=value[
                "ordered_recording_keys_sha256"
            ],  # type: ignore[arg-type]
            recording_keys=tuple(keys),
            asset_types=tuple(asset_types),
            entries=tuple(
                IndependentV2ValidationAssetEvidenceEntry.from_json(entry)
                for entry in entries
            ),
        )


def _canonical_bytes(evidence: IndependentV2ValidationAssetEvidence) -> bytes:
    return (
        json.dumps(evidence.as_json(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


@dataclass(frozen=True)
class PersistedIndependentV2ValidationAssetEvidence:
    """A canonical on-disk registry which is not trusted until validated."""

    path: Path
    sha256: str
    evidence: IndependentV2ValidationAssetEvidence


@dataclass(frozen=True)
class BuiltIndependentV2ValidationAssetEvidence:
    """A builder capability bound to one sealed cohort and exact snapshot."""

    cohort: IndependentV2ValidationCohort
    snapshot: IndependentValidationManifestSnapshotLike
    requirement: IndependentV2ValidationAssetEvidenceRequirement
    evidence: IndependentV2ValidationAssetEvidence


@dataclass(frozen=True)
class ValidatedIndependentV2ValidationAssetEvidence:
    """One full re-hash of an immutable registry against its exact assets."""

    persisted: PersistedIndependentV2ValidationAssetEvidence
    cohort: IndependentV2ValidationCohort
    snapshot: IndependentValidationManifestSnapshotLike
    requirement: object


@dataclass(frozen=True)
class IndependentV2ExecutionAssetEvidenceRequirement:
    """Execution-only evidence capability derived from two sealed objects."""

    execution_contract: IndependentV2ExecutionContract
    cohort: IndependentV2ValidationCohort
    protocol_sha256: str
    manifest_sha256: str
    ordered_recording_keys_sha256: str
    recording_keys: tuple[str, ...]
    source_evidence_protocol_sha256: str
    expected_evidence_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "protocol_sha256", "manifest_sha256", "ordered_recording_keys_sha256",
            "source_evidence_protocol_sha256", "expected_evidence_sha256",
        ):
            _require_digest(getattr(self, field), field=field)
        if (
            type(self.recording_keys) is not tuple
            or len(self.recording_keys) != 30
            or len(set(self.recording_keys)) != 30
            or self.ordered_recording_keys_sha256
            != ordered_recording_keys_sha256(self.recording_keys)
        ):
            raise ValueError("execution evidence requirement recording keys are invalid")


def _register(
    registry: dict[int, weakref.ReferenceType[object]], value: object
) -> None:
    identifier = id(value)

    def cleanup(reference: weakref.ReferenceType[object]) -> None:
        if registry.get(identifier) is reference:
            registry.pop(identifier, None)

    registry[identifier] = weakref.ref(value, cleanup)


def _require_registered(
    registry: dict[int, weakref.ReferenceType[object]], value: object, *, name: str
) -> None:
    reference = registry.get(id(value))
    if reference is None or reference() is not value:
        raise RuntimeError(f"Fail closed: {name} must be factory-attested.")


def _require_built(
    value: object,
) -> BuiltIndependentV2ValidationAssetEvidence:
    if not isinstance(value, BuiltIndependentV2ValidationAssetEvidence):
        raise ValueError(
            "independent validation evidence must be "
            "BuiltIndependentV2ValidationAssetEvidence."
        )
    _require_registered(_BUILT_EVIDENCE, value, name="independent validation evidence build")
    return value


def _require_validated(
    value: object,
) -> ValidatedIndependentV2ValidationAssetEvidence:
    if not isinstance(value, ValidatedIndependentV2ValidationAssetEvidence):
        raise ValueError(
            "independent validation evidence must be "
            "ValidatedIndependentV2ValidationAssetEvidence."
        )
    _require_registered(
        _VALIDATED_EVIDENCE,
        value,
        name="independent validation asset evidence validation",
    )
    checked = _read_persisted_bytes(value.persisted)
    if checked.sha256 != value.requirement.expected_evidence_sha256:
        raise RuntimeError("Fail closed: independent validation evidence SHA-256 differs from protocol.")
    return value


def execution_asset_evidence_requirement(
    execution_contract: IndependentV2ExecutionContract,
    cohort: IndependentV2ValidationCohort,
) -> IndependentV2ExecutionAssetEvidenceRequirement:
    """Create the sole execution-specific route to the prebuilt registry."""

    contract = require_sealed_independent_v2_execution_contract(execution_contract)
    sealed = require_sealed_independent_v2_validation_cohort(cohort)
    if (
        contract.closed_independent_protocol_sha256 != INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256
        or contract.closed_independent_protocol_sha256 != sealed.protocol_sha256
        or sealed.manifest_sha256 != INDEPENDENT_V2_MANIFEST_SHA256
        or contract.asset_evidence_sha256 != INDEPENDENT_V2_ASSET_EVIDENCE_SHA256
        or contract.asset_evidence_builder_protocol_sha256
        != INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256
        or contract.recording_count != 30
        or contract.independent_group_count != 20
        or len(sealed.recording_keys) != 30
        or len(sealed.leakage_groups) != 20
        or sealed.asset_evidence_builder_authorized
        or sealed.asset_evidence_reader_authorized
    ):
        raise RuntimeError("Fail closed: execution evidence requirement differs from sealed contracts")
    requirement = IndependentV2ExecutionAssetEvidenceRequirement(
        execution_contract=contract,
        cohort=sealed,
        protocol_sha256=sealed.protocol_sha256,
        manifest_sha256=sealed.manifest_sha256,
        ordered_recording_keys_sha256=ordered_recording_keys_sha256(sealed.recording_keys),
        recording_keys=sealed.recording_keys,
        source_evidence_protocol_sha256=contract.asset_evidence_builder_protocol_sha256,
        expected_evidence_sha256=contract.asset_evidence_sha256,
    )
    _register(_EXECUTION_REQUIREMENTS, requirement)
    return requirement


def _require_execution_requirement(
    cohort: IndependentV2ValidationCohort,
    value: object,
) -> IndependentV2ExecutionAssetEvidenceRequirement:
    sealed = require_sealed_independent_v2_validation_cohort(cohort)
    if not isinstance(value, IndependentV2ExecutionAssetEvidenceRequirement):
        raise ValueError("execution evidence requirement has an invalid type")
    _require_registered(
        _EXECUTION_REQUIREMENTS,
        value,
        name="independent V2 execution asset-evidence requirement",
    )
    require_sealed_independent_v2_execution_contract(value.execution_contract)
    if (
        value.cohort is not sealed
        or value.protocol_sha256 != sealed.protocol_sha256
        or value.manifest_sha256 != sealed.manifest_sha256
        or value.recording_keys != sealed.recording_keys
        or value.ordered_recording_keys_sha256
        != ordered_recording_keys_sha256(sealed.recording_keys)
        or value.source_evidence_protocol_sha256
        != value.execution_contract.asset_evidence_builder_protocol_sha256
        or value.expected_evidence_sha256 != value.execution_contract.asset_evidence_sha256
    ):
        raise RuntimeError("Fail closed: execution evidence requirement identity changed")
    return value


def _read_persisted_bytes(
    value: object,
) -> PersistedIndependentV2ValidationAssetEvidence:
    if not isinstance(value, PersistedIndependentV2ValidationAssetEvidence):
        raise ValueError(
            "independent validation asset evidence must be "
            "PersistedIndependentV2ValidationAssetEvidence."
        )
    resolved = value.path.resolve(strict=True)
    raw = resolved.read_bytes()
    if _sha256(raw) != value.sha256:
        raise RuntimeError("Fail closed: independent validation evidence bytes changed.")
    if raw != _canonical_bytes(value.evidence):
        raise RuntimeError("Fail closed: independent validation evidence is no longer canonical.")
    return value


def _require_requirement(
    cohort: IndependentV2ValidationCohort,
    requirement: object,
    *,
    operation: str,
) -> IndependentV2ValidationAssetEvidenceRequirement:
    sealed = require_sealed_independent_v2_validation_cohort(cohort)
    checked = require_independent_v2_validation_asset_evidence_requirement(requirement)
    if (
        checked.protocol_sha256 != sealed.protocol_sha256
        or checked.manifest_sha256 != sealed.manifest_sha256
        or checked.recording_keys != sealed.recording_keys
        or checked.ordered_recording_keys_sha256
        != ordered_recording_keys_sha256(sealed.recording_keys)
        or checked.builder_authorized_now
        != sealed.asset_evidence_builder_authorized
        or checked.reader_authorized_now
        != sealed.asset_evidence_reader_authorized
        or checked.source_evidence_protocol_sha256
        != (
            sealed.protocol_sha256
            if sealed.asset_evidence_builder_authorized
            else sealed.asset_evidence_source_protocol_sha256
        )
        or checked.expected_evidence_sha256
        != sealed.asset_evidence_expected_sha256
    ):
        raise RuntimeError("Fail closed: asset-evidence requirement differs from sealed cohort.")
    allowed = (
        checked.builder_authorized_now
        if operation == "build"
        else checked.reader_authorized_now
    )
    if not allowed:
        raise RuntimeError(
            f"Fail closed: independent validation asset-evidence {operation} is not authorized."
        )
    return checked


def _cohort_items(
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
) -> tuple[IndependentValidationManifestItemLike, ...]:
    """Select exact full-snapshot objects only after all identities agree."""
    require_sealed_independent_v2_validation_cohort(cohort)
    _require_loaded_manifest_snapshot(snapshot)
    if snapshot.manifest_sha256 != cohort.manifest_sha256:
        raise RuntimeError("Fail closed: validation snapshot uses another manifest digest.")
    by_key = {canonical_recording_key(item): item for item in snapshot.items}
    if len(by_key) != len(snapshot.items):
        raise RuntimeError("Fail closed: validation snapshot has duplicate recording keys.")
    selected: list[IndependentValidationManifestItemLike] = []
    for key in cohort.recording_keys:
        item = by_key.get(key)
        if item is None or item.split != "validation":
            raise RuntimeError(
                "Fail closed: independent validation evidence selected a missing "
                "or non-validation manifest item."
            )
        selected.append(item)
    groups = tuple(sorted({leakage_group_key(item) for item in selected}))
    if groups != cohort.leakage_groups:
        raise RuntimeError("Fail closed: validation snapshot leakage groups differ from cohort.")
    return tuple(selected)


def _verify_evidence_against_selected(
    evidence: IndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    requirement: IndependentV2ValidationAssetEvidenceRequirement,
    selected: Sequence[IndependentValidationManifestItemLike],
) -> None:
    """Re-hash every declared file before a registry becomes usable/published."""

    if (
        evidence.independent_validation_protocol_sha256
        != requirement.source_evidence_protocol_sha256
        or evidence.manifest_sha256 != cohort.manifest_sha256
        or evidence.recording_keys != cohort.recording_keys
        or evidence.ordered_recording_keys_sha256
        != ordered_recording_keys_sha256(cohort.recording_keys)
    ):
        raise RuntimeError("Fail closed: validation asset evidence differs from the sealed cohort.")
    if len(evidence.entries) != len(selected):
        raise RuntimeError("Fail closed: validation asset evidence entry count differs from cohort.")
    for item, entry in zip(selected, evidence.entries):
        expected_metadata = (
            canonical_recording_key(item),
            leakage_group_key(item),
            item.dataset_id,
            item.source_id,
            item.capture_id,
            item.audio_member,
        )
        actual_metadata = (
            entry.recording_key,
            entry.leakage_group_key,
            entry.dataset_id,
            entry.source_id,
            entry.capture_id,
            entry.audio_member,
        )
        if actual_metadata != expected_metadata:
            raise RuntimeError(
                "Fail closed: validation asset evidence entry metadata differs from snapshot."
            )
        if _digest_file(item.audio_path) != (
            entry.audio_size_bytes,
            entry.audio_sha256,
        ):
            raise RuntimeError("Fail closed: validation asset evidence audio bytes differ.")
        if _digest_file(item.labels_path) != (
            entry.labels_size_bytes,
            entry.labels_sha256,
        ):
            raise RuntimeError("Fail closed: validation asset evidence label bytes differ.")


def build_independent_v2_validation_asset_evidence(
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    requirement: IndependentV2ValidationAssetEvidenceRequirement,
) -> BuiltIndependentV2ValidationAssetEvidence:
    """Hash exactly the 30 selected files without decoding either asset type."""
    checked_requirement = _require_requirement(cohort, requirement, operation="build")
    selected = _cohort_items(cohort, snapshot)
    digest_cache: dict[Path, tuple[int, str]] = {}

    def cached_digest(path: Path) -> tuple[int, str]:
        resolved = Path(path).resolve(strict=True)
        if resolved not in digest_cache:
            digest_cache[resolved] = _digest_file(resolved)
        return digest_cache[resolved]

    entries = tuple(
        IndependentV2ValidationAssetEvidenceEntry(
            recording_key=canonical_recording_key(item),
            leakage_group_key=leakage_group_key(item),
            dataset_id=item.dataset_id,
            source_id=item.source_id,
            capture_id=item.capture_id,
            audio_member=item.audio_member,
            audio_size_bytes=cached_digest(item.audio_path)[0],
            audio_sha256=cached_digest(item.audio_path)[1],
            labels_size_bytes=cached_digest(item.labels_path)[0],
            labels_sha256=cached_digest(item.labels_path)[1],
        )
        for item in selected
    )
    evidence = IndependentV2ValidationAssetEvidence(
        schema_version=INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION,
        purpose=INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE,
        independent_validation_protocol_sha256=cohort.protocol_sha256,
        manifest_sha256=cohort.manifest_sha256,
        ordered_recording_keys_sha256=ordered_recording_keys_sha256(
            cohort.recording_keys
        ),
        recording_keys=cohort.recording_keys,
        asset_types=("audio", "labels"),
        entries=entries,
    )
    built = BuiltIndependentV2ValidationAssetEvidence(
        cohort=cohort,
        snapshot=snapshot,
        requirement=checked_requirement,
        evidence=evidence,
    )
    _register(_BUILT_EVIDENCE, built)
    return built


def write_independent_v2_validation_asset_evidence(
    path: Path,
    built: BuiltIndependentV2ValidationAssetEvidence,
) -> PersistedIndependentV2ValidationAssetEvidence:
    """Publish immutable canonical evidence without overwriting an existing file."""
    checked = _require_built(built)
    _require_requirement(checked.cohort, checked.requirement, operation="build")
    selected = _cohort_items(checked.cohort, checked.snapshot)
    # Close the build -> write race: nothing is published unless the bytes just
    # re-hashed now still equal the builder's evidence.
    _verify_evidence_against_selected(
        checked.evidence,
        checked.cohort,
        checked.requirement,
        selected,
    )
    target = Path(path).expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError(
            "Fail closed: independent validation asset evidence already exists and is immutable."
        )
    if not target.parent.is_dir():
        raise ValueError("independent validation evidence parent directory does not exist.")
    raw = _canonical_bytes(checked.evidence)
    temporary = target.with_name(
        f".{target.name}.{os.getpid()}.{secrets.token_hex(8)}.part"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # ``link`` is an atomic no-replace publication on the same filesystem.
        # A concurrent existing target therefore fails closed rather than being
        # silently replaced by a second evidence build.
        os.link(temporary, target)
    except Exception:
        raise
    finally:
        temporary.unlink(missing_ok=True)
    return PersistedIndependentV2ValidationAssetEvidence(
        path=target.resolve(strict=True),
        sha256=_sha256(raw),
        evidence=checked.evidence,
    )


def load_independent_v2_validation_asset_evidence(
    path: Path,
    cohort: IndependentV2ValidationCohort,
    requirement: IndependentV2ValidationAssetEvidenceRequirement,
) -> PersistedIndependentV2ValidationAssetEvidence:
    """Parse canonical JSON only; it remains untrusted until full validation."""
    _require_requirement(cohort, requirement, operation="read")
    resolved = Path(path).resolve(strict=True)
    raw = resolved.read_bytes()
    try:
        evidence = IndependentV2ValidationAssetEvidence.from_json(
            json.loads(raw.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("independent validation asset evidence is not valid UTF-8 JSON.") from exc
    if raw != _canonical_bytes(evidence):
        raise ValueError("independent validation asset evidence is not canonical JSON.")
    if _sha256(raw) != requirement.expected_evidence_sha256:
        raise RuntimeError("Fail closed: independent validation evidence SHA-256 differs from protocol.")
    return PersistedIndependentV2ValidationAssetEvidence(
        path=resolved,
        sha256=_sha256(raw),
        evidence=evidence,
    )


def validate_independent_v2_validation_asset_evidence(
    persisted: PersistedIndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    requirement: IndependentV2ValidationAssetEvidenceRequirement,
) -> ValidatedIndependentV2ValidationAssetEvidence:
    """Re-hash all 60 declared files before returning a usable capability."""
    checked_requirement = _require_requirement(cohort, requirement, operation="read")
    checked = _read_persisted_bytes(persisted)
    selected = _cohort_items(cohort, snapshot)
    _verify_evidence_against_selected(
        checked.evidence,
        cohort,
        checked_requirement,
        selected,
    )
    validated = ValidatedIndependentV2ValidationAssetEvidence(
        persisted=checked,
        cohort=cohort,
        snapshot=snapshot,
        requirement=checked_requirement,
    )
    _register(_VALIDATED_EVIDENCE, validated)
    return validated


def load_and_validate_independent_v2_validation_asset_evidence_for_execution(
    path: Path,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    requirement: IndependentV2ExecutionAssetEvidenceRequirement,
) -> ValidatedIndependentV2ValidationAssetEvidence:
    """Execution-only load plus complete 60-asset revalidation.

    This intentionally does not call the historically closed generic reader.
    Authority comes exclusively from the factory-attested execution contract
    and cohort pair.
    """

    checked_requirement = _require_execution_requirement(cohort, requirement)
    candidate = Path(path)
    if candidate.is_symlink() or tuple(candidate.parts[-3:]) != (
        "tmp", "local", "causal_candidate_v2_independent_validation_asset_evidence_20260810.json",
    ):
        raise ValueError("independent V2 execution evidence path is not canonical")
    resolved = candidate.resolve(strict=True)
    raw = resolved.read_bytes()
    if _sha256(raw) != checked_requirement.expected_evidence_sha256:
        raise RuntimeError("Fail closed: execution evidence SHA-256 differs from contract")
    try:
        evidence = IndependentV2ValidationAssetEvidence.from_json(
            json.loads(raw.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("independent V2 execution evidence is not valid UTF-8 JSON") from exc
    if raw != _canonical_bytes(evidence):
        raise ValueError("independent V2 execution evidence is not canonical JSON")
    persisted = PersistedIndependentV2ValidationAssetEvidence(
        path=resolved,
        sha256=_sha256(raw),
        evidence=evidence,
    )
    selected = _cohort_items(cohort, snapshot)
    _verify_evidence_against_selected(
        evidence,
        cohort,
        checked_requirement,  # type: ignore[arg-type]
        selected,
    )
    validated = ValidatedIndependentV2ValidationAssetEvidence(
        persisted=persisted,
        cohort=cohort,
        snapshot=snapshot,
        requirement=checked_requirement,
    )
    _register(_VALIDATED_EVIDENCE, validated)
    return validated


def _entry_for_item(
    validated: ValidatedIndependentV2ValidationAssetEvidence,
    item: IndependentValidationManifestItemLike,
) -> IndependentV2ValidationAssetEvidenceEntry:
    checked = _require_validated(validated)
    selected = _cohort_items(checked.cohort, checked.snapshot)
    if not any(item is snapshot_item for snapshot_item in selected):
        raise RuntimeError("Fail closed: validation asset item is not an exact selected snapshot object.")
    key = canonical_recording_key(item)
    index = checked.cohort.recording_keys.index(key)
    return checked.persisted.evidence.entries[index]


def verify_independent_v2_validation_label_asset_for_item(
    validated: ValidatedIndependentV2ValidationAssetEvidence,
    item: IndependentValidationManifestItemLike,
) -> None:
    """Re-hash labels immediately before a future runner opens them."""
    entry = _entry_for_item(validated, item)
    if _digest_file(item.labels_path) != (
        entry.labels_size_bytes,
        entry.labels_sha256,
    ):
        raise RuntimeError("Fail closed: independent validation label asset bytes differ.")


def verify_independent_v2_validation_audio_asset_for_item(
    validated: ValidatedIndependentV2ValidationAssetEvidence,
    item: IndependentValidationManifestItemLike,
) -> None:
    """Re-hash audio immediately before a future runner opens it."""
    entry = _entry_for_item(validated, item)
    if _digest_file(item.audio_path) != (
        entry.audio_size_bytes,
        entry.audio_sha256,
    ):
        raise RuntimeError("Fail closed: independent validation audio asset bytes differ.")


__all__ = [
    "INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE",
    "INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION",
    "BuiltIndependentV2ValidationAssetEvidence",
    "IndependentV2ValidationAssetEvidence",
    "IndependentV2ValidationAssetEvidenceEntry",
    "IndependentV2ExecutionAssetEvidenceRequirement",
    "PersistedIndependentV2ValidationAssetEvidence",
    "ValidatedIndependentV2ValidationAssetEvidence",
    "build_independent_v2_validation_asset_evidence",
    "canonical_recording_key",
    "execution_asset_evidence_requirement",
    "load_and_validate_independent_v2_validation_asset_evidence_for_execution",
    "load_independent_v2_validation_asset_evidence",
    "ordered_recording_keys_sha256",
    "validate_independent_v2_validation_asset_evidence",
    "verify_independent_v2_validation_audio_asset_for_item",
    "verify_independent_v2_validation_label_asset_for_item",
    "write_independent_v2_validation_asset_evidence",
]
