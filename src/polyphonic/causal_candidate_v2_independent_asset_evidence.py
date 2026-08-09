"""Byte-level provenance for the sealed independent V2 validation cohort.

This module is deliberately narrower than the train-only candidate evidence:
it can attest only the 30 independently derived validation recordings.  It
never loads a waveform, an NPZ payload, TensorFlow, a checkpoint, or a
decoder.  Building the registry reads the bytes of the declared audio and
label *files* solely to record size and SHA-256; a future reviewed runner must
re-hash them at their actual open boundaries before it can use them.
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
)


INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION = 1
INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE = (
    "causal_candidate_v2_independent_validation_asset_evidence"
)
_PERSISTED_EVIDENCE: dict[int, weakref.ReferenceType[object]] = {}


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
    """One factory-attested canonical parse of immutable evidence bytes."""

    path: Path
    sha256: str
    evidence: IndependentV2ValidationAssetEvidence


def _register(persisted: PersistedIndependentV2ValidationAssetEvidence) -> None:
    identifier = id(persisted)

    def cleanup(reference: weakref.ReferenceType[object]) -> None:
        if _PERSISTED_EVIDENCE.get(identifier) is reference:
            _PERSISTED_EVIDENCE.pop(identifier, None)

    _PERSISTED_EVIDENCE[identifier] = weakref.ref(persisted, cleanup)


def _require_persisted(value: object) -> PersistedIndependentV2ValidationAssetEvidence:
    if not isinstance(value, PersistedIndependentV2ValidationAssetEvidence):
        raise ValueError(
            "independent validation asset evidence must be "
            "PersistedIndependentV2ValidationAssetEvidence."
        )
    reference = _PERSISTED_EVIDENCE.get(id(value))
    if reference is None or reference() is not value:
        raise RuntimeError("Fail closed: independent validation evidence must be factory-attested.")
    raw = value.path.read_bytes()
    if _sha256(raw) != value.sha256:
        raise RuntimeError("Fail closed: independent validation evidence bytes changed.")
    if raw != _canonical_bytes(value.evidence):
        raise RuntimeError("Fail closed: independent validation evidence is no longer canonical.")
    return value


def _cohort_items(
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
) -> tuple[IndependentValidationManifestItemLike, ...]:
    """Select exact full-snapshot objects only after all identities agree."""
    if not isinstance(cohort, IndependentV2ValidationCohort):
        raise ValueError("cohort must be IndependentV2ValidationCohort.")
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


def build_independent_v2_validation_asset_evidence(
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
) -> IndependentV2ValidationAssetEvidence:
    """Hash exactly the 30 selected files without decoding either asset type."""
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
    return IndependentV2ValidationAssetEvidence(
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


def write_independent_v2_validation_asset_evidence(
    path: Path,
    evidence: IndependentV2ValidationAssetEvidence,
) -> PersistedIndependentV2ValidationAssetEvidence:
    """Publish immutable canonical evidence without overwriting an existing file."""
    target = Path(path).expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError(
            "Fail closed: independent validation asset evidence already exists and is immutable."
        )
    if not target.parent.is_dir():
        raise ValueError("independent validation evidence parent directory does not exist.")
    raw = _canonical_bytes(evidence)
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
    return load_independent_v2_validation_asset_evidence(target)


def load_independent_v2_validation_asset_evidence(
    path: Path,
) -> PersistedIndependentV2ValidationAssetEvidence:
    """Read only the canonical evidence JSON; never open its declared assets."""
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
    persisted = PersistedIndependentV2ValidationAssetEvidence(
        path=resolved,
        sha256=_sha256(raw),
        evidence=evidence,
    )
    _register(persisted)
    return persisted


def validate_independent_v2_validation_asset_evidence(
    persisted: PersistedIndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
) -> None:
    """Require the persisted registry to bind the exact sealed 30-item cohort."""
    checked = _require_persisted(persisted)
    selected = _cohort_items(cohort, snapshot)
    evidence = checked.evidence
    if (
        evidence.independent_validation_protocol_sha256 != cohort.protocol_sha256
        or evidence.manifest_sha256 != cohort.manifest_sha256
        or evidence.recording_keys != cohort.recording_keys
        or evidence.ordered_recording_keys_sha256
        != ordered_recording_keys_sha256(cohort.recording_keys)
    ):
        raise RuntimeError("Fail closed: validation asset evidence differs from the sealed cohort.")
    expected = tuple(
        (
            canonical_recording_key(item),
            leakage_group_key(item),
            item.dataset_id,
            item.source_id,
            item.capture_id,
            item.audio_member,
        )
        for item in selected
    )
    actual = tuple(
        (
            entry.recording_key,
            entry.leakage_group_key,
            entry.dataset_id,
            entry.source_id,
            entry.capture_id,
            entry.audio_member,
        )
        for entry in evidence.entries
    )
    if actual != expected:
        raise RuntimeError("Fail closed: validation asset evidence entry metadata differs from snapshot.")


def _entry_for_item(
    persisted: PersistedIndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    item: IndependentValidationManifestItemLike,
) -> IndependentV2ValidationAssetEvidenceEntry:
    validate_independent_v2_validation_asset_evidence(persisted, cohort, snapshot)
    selected = _cohort_items(cohort, snapshot)
    if not any(item is snapshot_item for snapshot_item in selected):
        raise RuntimeError("Fail closed: validation asset item is not an exact selected snapshot object.")
    key = canonical_recording_key(item)
    index = cohort.recording_keys.index(key)
    return persisted.evidence.entries[index]


def verify_independent_v2_validation_label_asset_for_item(
    persisted: PersistedIndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    item: IndependentValidationManifestItemLike,
) -> None:
    """Re-hash labels immediately before a future runner opens them."""
    entry = _entry_for_item(persisted, cohort, snapshot, item)
    if _digest_file(item.labels_path) != (
        entry.labels_size_bytes,
        entry.labels_sha256,
    ):
        raise RuntimeError("Fail closed: independent validation label asset bytes differ.")


def verify_independent_v2_validation_audio_asset_for_item(
    persisted: PersistedIndependentV2ValidationAssetEvidence,
    cohort: IndependentV2ValidationCohort,
    snapshot: IndependentValidationManifestSnapshotLike,
    item: IndependentValidationManifestItemLike,
) -> None:
    """Re-hash audio immediately before a future runner opens it."""
    entry = _entry_for_item(persisted, cohort, snapshot, item)
    if _digest_file(item.audio_path) != (
        entry.audio_size_bytes,
        entry.audio_sha256,
    ):
        raise RuntimeError("Fail closed: independent validation audio asset bytes differ.")


__all__ = [
    "INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_PURPOSE",
    "INDEPENDENT_V2_VALIDATION_ASSET_EVIDENCE_SCHEMA_VERSION",
    "IndependentV2ValidationAssetEvidence",
    "IndependentV2ValidationAssetEvidenceEntry",
    "PersistedIndependentV2ValidationAssetEvidence",
    "build_independent_v2_validation_asset_evidence",
    "canonical_recording_key",
    "load_independent_v2_validation_asset_evidence",
    "ordered_recording_keys_sha256",
    "validate_independent_v2_validation_asset_evidence",
    "verify_independent_v2_validation_audio_asset_for_item",
    "verify_independent_v2_validation_label_asset_for_item",
    "write_independent_v2_validation_asset_evidence",
]
