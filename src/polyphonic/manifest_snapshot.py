"""TensorFlow-free, capability-attested polyphonic manifest snapshots.

This module owns the byte-for-byte manifest reader used by provenance-only
workflows.  Keeping it separate from :mod:`src.polyphonic.data` lets a
preflight prove identities and resolved asset paths without importing the
TensorFlow-backed corpus implementation.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path
import re
from typing import Mapping

from .decoder_candidate_provenance import (
    _manifest_snapshot_capability_token,
    _register_loaded_manifest_snapshot,
)


@dataclass(frozen=True)
class ManifestItem:
    """One fully resolved recording row from the exact manifest bytes."""

    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    split: str
    audio_path: Path
    audio_member: str
    labels_path: Path
    capture_id: str
    license_id: str


@dataclass(frozen=True)
class ManifestSnapshot:
    """One immutable parse of the exact bytes used to create its items."""

    manifest_path: Path
    manifest_sha256: str
    items: tuple[ManifestItem, ...]
    _decoder_candidate_snapshot_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._decoder_candidate_snapshot_token
            is not _manifest_snapshot_capability_token()
        ):
            raise ValueError(
                "ManifestSnapshot must be created by load_manifest_snapshot()."
            )
        if not isinstance(self.manifest_path, Path):
            raise ValueError("manifest_path must be a pathlib.Path.")
        if not isinstance(self.manifest_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.manifest_sha256
        ):
            raise ValueError("manifest_sha256 must be a lowercase SHA-256 digest.")
        if type(self.items) is not tuple or not self.items:
            raise ValueError("items must be a non-empty immutable tuple.")
        if not all(isinstance(item, ManifestItem) for item in self.items):
            raise ValueError("items must contain only ManifestItem values.")


def _manifest_path(value: str, *, manifest_directory: Path) -> Path:
    """Resolve one manifest path against its manifest, never the CWD."""

    normalized = value.replace("\\", "/")
    candidate = Path(normalized)
    foreign_absolute = bool(
        re.match(r"^[A-Za-z]:/", normalized) or normalized.startswith("/")
    )
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()
    marker = "/data/"
    marker_index = normalized.lower().find(marker)
    if foreign_absolute and marker_index >= 0:
        configured_root = os.environ.get("MIDI_DATA_ROOT")
        data_root = (
            Path(configured_root).expanduser().resolve()
            if configured_root
            else Path(__file__).resolve().parents[2] / "data"
        )
        return (data_root / normalized[marker_index + len(marker):]).resolve()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (manifest_directory / candidate).resolve()


def _manifest_cell(
    row: Mapping[str, object], name: str, *, allow_empty: bool = False
) -> str:
    value = row.get(name)
    if not isinstance(value, str):
        raise ValueError(f"Manifest {name} must be a CSV string.")
    if not allow_empty and not value.strip():
        raise ValueError(f"Manifest {name} must be non-empty.")
    return value


def load_manifest_snapshot(path: Path) -> ManifestSnapshot:
    """Read, hash and parse one CSV buffer before any asset is opened."""

    resolved_manifest = Path(path).resolve(strict=True)
    raw_bytes = resolved_manifest.read_bytes()
    manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Manifest is not valid UTF-8: {path}") from exc
    with io.StringIO(decoded, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        rows = list(reader)
    required = {
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id",
        "license_id",
    }
    if not rows:
        raise ValueError(f"Empty polyphonic manifest: {path}")
    missing = required - fieldnames
    if missing:
        raise ValueError(f"Manifest columns missing: {sorted(missing)}")
    snapshot = ManifestSnapshot(
        manifest_path=resolved_manifest,
        manifest_sha256=manifest_sha256,
        items=tuple(
            ManifestItem(
                source_id=_manifest_cell(row, "source_id"),
                dataset_id=_manifest_cell(row, "dataset_id"),
                player_id=_manifest_cell(row, "player_id", allow_empty=True),
                group_id=_manifest_cell(row, "group_id"),
                split=_manifest_cell(row, "split"),
                audio_path=_manifest_path(
                    _manifest_cell(row, "audio_path"),
                    manifest_directory=resolved_manifest.parent,
                ),
                audio_member=_manifest_cell(row, "audio_member", allow_empty=True),
                labels_path=_manifest_path(
                    _manifest_cell(row, "labels_path"),
                    manifest_directory=resolved_manifest.parent,
                ),
                capture_id=_manifest_cell(row, "capture_id"),
                license_id=_manifest_cell(row, "license_id"),
            )
            for row in rows
        ),
        _decoder_candidate_snapshot_token=_manifest_snapshot_capability_token(),
    )
    _register_loaded_manifest_snapshot(snapshot)
    return snapshot


def load_manifest(path: Path) -> list[ManifestItem]:
    """Historical list-returning API backed by the same one-shot reader."""

    return list(load_manifest_snapshot(path).items)


__all__ = ["ManifestItem", "ManifestSnapshot", "load_manifest", "load_manifest_snapshot"]
