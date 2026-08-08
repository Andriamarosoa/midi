"""Immutable byte evidence required before a candidate miner opens assets.

This module deliberately hashes only files referenced by a manifest snapshot. It
does not load audio, labels, TensorFlow, a decoder, or candidate rows.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import weakref

from .data import ManifestItem
from .decoder_candidate_provenance import ValidatedDecoderCandidateManifestSnapshot


DECODER_CANDIDATE_ASSET_EVIDENCE_SCHEMA_VERSION = 1
_PERSISTED_EVIDENCE: dict[int, weakref.ReferenceType[object]] = {}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> tuple[int, str]:
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"candidate asset is not a regular file: {resolved}")
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


def _identity(item: ManifestItem) -> tuple[str, str, str]:
    return item.dataset_id, item.source_id, item.capture_id


@dataclass(frozen=True)
class DecoderCandidateAssetEvidenceEntry:
    """Portable byte evidence for the two files opened for one train capture."""

    dataset_id: str
    source_id: str
    capture_id: str
    partition: str
    audio_member: str
    audio_size_bytes: int
    audio_sha256: str
    labels_size_bytes: int
    labels_sha256: str

    def __post_init__(self) -> None:
        for field in ("dataset_id", "source_id", "capture_id", "partition"):
            _require_text(getattr(self, field), field=field)
        if not isinstance(self.audio_member, str):
            raise ValueError("audio_member must be a string.")
        _require_size(self.audio_size_bytes, field="audio_size_bytes")
        _require_digest(self.audio_sha256, field="audio_sha256")
        _require_size(self.labels_size_bytes, field="labels_size_bytes")
        _require_digest(self.labels_sha256, field="labels_sha256")

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.dataset_id, self.source_id, self.capture_id

    def as_json(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "source_id": self.source_id,
            "capture_id": self.capture_id,
            "partition": self.partition,
            "audio_member": self.audio_member,
            "audio_size_bytes": self.audio_size_bytes,
            "audio_sha256": self.audio_sha256,
            "labels_size_bytes": self.labels_size_bytes,
            "labels_sha256": self.labels_sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "DecoderCandidateAssetEvidenceEntry":
        if not isinstance(value, dict) or set(value) != {
            "dataset_id", "source_id", "capture_id", "partition", "audio_member",
            "audio_size_bytes", "audio_sha256", "labels_size_bytes", "labels_sha256",
        }:
            raise ValueError("candidate asset evidence entry has an invalid schema.")
        return cls(**value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class DecoderCandidateAssetEvidence:
    """Canonical, train-only asset proof bound to a manifest and plan digest."""

    schema_version: int
    manifest_sha256: str
    partition_plan_sha256: str
    entries: tuple[DecoderCandidateAssetEvidenceEntry, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != DECODER_CANDIDATE_ASSET_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("unsupported candidate asset-evidence schema version.")
        _require_digest(self.manifest_sha256, field="manifest_sha256")
        _require_digest(self.partition_plan_sha256, field="partition_plan_sha256")
        if type(self.entries) is not tuple or not self.entries:
            raise ValueError("candidate asset evidence must contain immutable entries.")
        if not all(isinstance(entry, DecoderCandidateAssetEvidenceEntry) for entry in self.entries):
            raise ValueError("candidate asset evidence contains an invalid entry.")
        identities = tuple(entry.identity for entry in self.entries)
        if len(set(identities)) != len(identities):
            raise ValueError("candidate asset evidence contains duplicate recording identities.")
        if tuple(sorted(identities)) != identities:
            raise ValueError("candidate asset evidence entries must be canonically sorted.")

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "partition_plan_sha256": self.partition_plan_sha256,
            "entries": [entry.as_json() for entry in self.entries],
        }

    @classmethod
    def from_json(cls, value: object) -> "DecoderCandidateAssetEvidence":
        if not isinstance(value, dict) or set(value) != {
            "schema_version", "manifest_sha256", "partition_plan_sha256", "entries",
        }:
            raise ValueError("candidate asset evidence has an invalid schema.")
        entries = value["entries"]
        if not isinstance(entries, list):
            raise ValueError("candidate asset evidence entries must be a JSON array.")
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            manifest_sha256=value["manifest_sha256"],  # type: ignore[arg-type]
            partition_plan_sha256=value["partition_plan_sha256"],  # type: ignore[arg-type]
            entries=tuple(DecoderCandidateAssetEvidenceEntry.from_json(entry) for entry in entries),
        )


def _canonical_bytes(evidence: DecoderCandidateAssetEvidence) -> bytes:
    return (json.dumps(evidence.as_json(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(frozen=True)
class PersistedDecoderCandidateAssetEvidence:
    """A fresh canonical parse of the asset-evidence file on disk."""

    path: Path
    sha256: str
    evidence: DecoderCandidateAssetEvidence


def _register(persisted: PersistedDecoderCandidateAssetEvidence) -> None:
    identifier = id(persisted)
    _PERSISTED_EVIDENCE[identifier] = weakref.ref(
        persisted, lambda _ref, key=identifier: _PERSISTED_EVIDENCE.pop(key, None)
    )


def _require_persisted_asset_evidence(value: object) -> None:
    if not isinstance(value, PersistedDecoderCandidateAssetEvidence):
        raise ValueError("asset evidence must be PersistedDecoderCandidateAssetEvidence.")
    reference = _PERSISTED_EVIDENCE.get(id(value))
    if reference is None or reference() is not value:
        raise RuntimeError("Fail closed: asset evidence must be factory-attested.")
    raw = value.path.read_bytes()
    if _sha256(raw) != value.sha256:
        raise RuntimeError("Fail closed: candidate asset-evidence bytes changed.")
    if raw != _canonical_bytes(value.evidence):
        raise RuntimeError("Fail closed: candidate asset-evidence is no longer canonical.")


def build_decoder_candidate_asset_evidence(
    validated_snapshot: ValidatedDecoderCandidateManifestSnapshot,
) -> DecoderCandidateAssetEvidence:
    """Hash only train assets referenced by one already validated snapshot."""
    items: list[DecoderCandidateAssetEvidenceEntry] = []
    digest_cache: dict[Path, tuple[int, str]] = {}

    def cached_digest(path: Path) -> tuple[int, str]:
        # A zip/container can legitimately back several ``audio_member`` rows.
        # Hash its bytes once during pre-registration, while retaining one
        # member-bound evidence entry per capture.
        resolved = Path(path).resolve(strict=True)
        if resolved not in digest_cache:
            digest_cache[resolved] = _digest_file(resolved)
        return digest_cache[resolved]

    for item in validated_snapshot.train_items:
        if not isinstance(item, ManifestItem):
            raise AssertionError("validated snapshot retained a non-ManifestItem.")
        provenance = validated_snapshot.provenance_for_snapshot_item(item)
        audio_size, audio_sha = cached_digest(item.audio_path)
        labels_size, labels_sha = cached_digest(item.labels_path)
        items.append(DecoderCandidateAssetEvidenceEntry(
            dataset_id=item.dataset_id,
            source_id=item.source_id,
            capture_id=item.capture_id,
            partition=provenance.partition,
            audio_member=item.audio_member,
            audio_size_bytes=audio_size,
            audio_sha256=audio_sha,
            labels_size_bytes=labels_size,
            labels_sha256=labels_sha,
        ))
    return DecoderCandidateAssetEvidence(
        schema_version=DECODER_CANDIDATE_ASSET_EVIDENCE_SCHEMA_VERSION,
        manifest_sha256=validated_snapshot.manifest_sha256,
        partition_plan_sha256=validated_snapshot.partition_plan_sha256,
        entries=tuple(sorted(items, key=lambda entry: entry.identity)),
    )


def write_decoder_candidate_asset_evidence(
    path: Path,
    evidence: DecoderCandidateAssetEvidence,
) -> PersistedDecoderCandidateAssetEvidence:
    """Write one immutable canonical evidence file, then reload it."""
    target = Path(path).expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError("Fail closed: candidate asset-evidence already exists and is immutable.")
    if not target.parent.is_dir():
        raise ValueError("asset-evidence parent directory does not exist.")
    raw = _canonical_bytes(evidence)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return load_decoder_candidate_asset_evidence(target)


def load_decoder_candidate_asset_evidence(path: Path) -> PersistedDecoderCandidateAssetEvidence:
    """Load only strict canonical asset evidence, without opening its assets."""
    resolved = Path(path).resolve(strict=True)
    raw = resolved.read_bytes()
    try:
        evidence = DecoderCandidateAssetEvidence.from_json(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate asset evidence is not valid UTF-8 JSON.") from exc
    if raw != _canonical_bytes(evidence):
        raise ValueError("candidate asset evidence is not canonical JSON.")
    persisted = PersistedDecoderCandidateAssetEvidence(resolved, _sha256(raw), evidence)
    _register(persisted)
    return persisted


def validate_decoder_candidate_asset_evidence(
    persisted: PersistedDecoderCandidateAssetEvidence,
    validated_snapshot: ValidatedDecoderCandidateManifestSnapshot,
) -> None:
    """Require exact train coverage before an approved context can open data."""
    _require_persisted_asset_evidence(persisted)
    evidence = persisted.evidence
    if evidence.manifest_sha256 != validated_snapshot.manifest_sha256:
        raise RuntimeError("Fail closed: asset evidence uses another manifest snapshot.")
    if evidence.partition_plan_sha256 != validated_snapshot.partition_plan_sha256:
        raise RuntimeError("Fail closed: asset evidence uses another partition plan.")
    expected = tuple(sorted(
        (item.dataset_id, item.source_id, item.capture_id,
         validated_snapshot.provenance_for_snapshot_item(item).partition, item.audio_member)
        for item in validated_snapshot.train_items
    ))
    actual = tuple(sorted(
        (entry.dataset_id, entry.source_id, entry.capture_id, entry.partition, entry.audio_member)
        for entry in evidence.entries
    ))
    if actual != expected:
        raise RuntimeError("Fail closed: asset evidence does not cover exact train snapshot items.")


def verify_decoder_candidate_assets_for_item(
    persisted: PersistedDecoderCandidateAssetEvidence,
    validated_snapshot: ValidatedDecoderCandidateManifestSnapshot,
    item: ManifestItem,
) -> None:
    """Re-hash one exact item immediately before its corpus opens the paths."""
    validate_decoder_candidate_asset_evidence(persisted, validated_snapshot)
    identity = _identity(item)
    matching = [entry for entry in persisted.evidence.entries if entry.identity == identity]
    if len(matching) != 1:
        raise RuntimeError("Fail closed: no unique asset evidence entry for snapshot item.")
    entry = matching[0]
    provenance = validated_snapshot.provenance_for_snapshot_item(item)
    if entry.partition != provenance.partition or entry.audio_member != item.audio_member:
        raise RuntimeError("Fail closed: asset evidence identity metadata differs from snapshot item.")
    audio_size, audio_sha = _digest_file(item.audio_path)
    labels_size, labels_sha = _digest_file(item.labels_path)
    if (audio_size, audio_sha) != (entry.audio_size_bytes, entry.audio_sha256):
        raise RuntimeError("Fail closed: candidate audio asset bytes differ from pre-registration.")
    if (labels_size, labels_sha) != (entry.labels_size_bytes, entry.labels_sha256):
        raise RuntimeError("Fail closed: candidate label asset bytes differ from pre-registration.")


__all__ = [
    "DecoderCandidateAssetEvidence",
    "DecoderCandidateAssetEvidenceEntry",
    "PersistedDecoderCandidateAssetEvidence",
    "build_decoder_candidate_asset_evidence",
    "load_decoder_candidate_asset_evidence",
    "validate_decoder_candidate_asset_evidence",
    "verify_decoder_candidate_assets_for_item",
    "write_decoder_candidate_asset_evidence",
]
