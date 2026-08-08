"""Compact corpus and Keras sequences for continuous polyphonic frames."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence
from zipfile import ZipFile

import numpy as np
import soundfile as sf
import tensorflow as tf

from src.polyphonic.independent_note_targets import (
    build_independent_note_targets,
)
from src.polyphonic.decoder_candidate_provenance import (
    _manifest_snapshot_capability_token,
    _register_loaded_manifest_snapshot,
)


NUMPY_MAGIC = b"\x93NUMPY"
EPOCH_PLAN_SCHEMA_VERSION = 1


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class ManifestItem:
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
    """One immutable parse of the exact manifest bytes used by a workflow.

    ``items`` deliberately contains the fully resolved :class:`ManifestItem`
    objects which later open audio and labels.  A caller that has validated the
    SHA-256 can therefore keep using these exact objects instead of reparsing a
    manifest and accidentally binding an otherwise-identical recording to
    different paths.
    """

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


@dataclass(frozen=True)
class CachedLabels:
    item: ManifestItem
    arrays: Mapping[str, np.ndarray]


FundamentalOffsetMap = Mapping[tuple[str, str], np.ndarray]


def load_independent_note_fundamental_offsets(
    path: Path,
    *,
    expected_sha256: str,
    expected_manifest_sha256: str,
) -> dict[tuple[str, str], np.ndarray]:
    """Load the small train/validation sidecar used by the independent head.

    The sidecar exists because schema-3 label archives do not yet carry the
    fractional fundamental tuning.  It is fail-closed against tampering,
    manifest drift, duplicate rows, malformed arrays, and any indication that
    the locked test split was used.
    """

    resolved = path.resolve(strict=True)
    actual_sha256 = _sha256_file(resolved)
    if actual_sha256 != str(expected_sha256):
        raise ValueError("Independent-note offset sidecar SHA-256 mismatch.")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Independent-note offset sidecar is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Independent-note offset sidecar must be an object.")
    if int(payload.get("schema_version", -1)) != 1:
        raise ValueError("Unsupported independent-note offset sidecar schema.")
    if payload.get("locked_test_used") is not False:
        raise ValueError("Fail closed: offset sidecar does not exclude locked test.")
    if payload.get("manifest_sha256") != str(expected_manifest_sha256):
        raise ValueError("Independent-note offset sidecar manifest mismatch.")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Independent-note offset sidecar has no records.")
    result: dict[tuple[str, str], np.ndarray] = {}
    ordered_keys: list[tuple[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Independent-note offset sidecar record is invalid.")
        dataset_id = str(record.get("dataset_id", ""))
        source_id = str(record.get("source_id", ""))
        key = (dataset_id, source_id)
        if not dataset_id or not source_id or key in result:
            raise ValueError("Independent-note offset sidecar keys are invalid.")
        values = np.asarray(record.get("note_fundamental_offset_cents"), dtype=np.float32)
        if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
            raise ValueError("Independent-note offset sidecar values are invalid.")
        result[key] = values
        ordered_keys.append(key)
    if ordered_keys != sorted(ordered_keys):
        raise ValueError("Independent-note offset sidecar records are not sorted.")
    return result


def _manifest_path(
    value: str,
    *,
    manifest_directory: Path | None = None,
) -> Path:
    """Load Windows/POSIX manifests from the current project checkout.

    Materialized manifests intentionally preserve source provenance and may
    contain absolute paths from the machine that built them. When such a path
    is foreign to the current OS, rebase its ``data/...`` tail onto this
    checkout (or ``MIDI_DATA_ROOT``) instead of treating a Windows drive path
    as a relative POSIX path.
    """
    normalized = value.replace("\\", "/")
    candidate = Path(normalized)
    foreign_absolute = bool(
        re.match(r"^[A-Za-z]:/", normalized) or normalized.startswith("/")
    )
    # A native absolute path remains native.  Relative manifest entries must
    # never be captured opportunistically from the process working directory:
    # the manifest directory is the sole coordinate system for a snapshot.
    if candidate.is_absolute() and candidate.exists():
        return candidate
    data_marker = "/data/"
    marker_index = normalized.lower().find(data_marker)
    if foreign_absolute and marker_index >= 0:
        configured_root = os.environ.get("MIDI_DATA_ROOT")
        data_root = (
            Path(configured_root).expanduser().resolve()
            if configured_root
            else Path(__file__).resolve().parents[2] / "data"
        )
        relative_to_data = normalized[marker_index + len(data_marker):]
        return (data_root / Path(relative_to_data)).resolve()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    if manifest_directory is not None:
        return (manifest_directory / candidate).resolve()
    return candidate


def _is_numpy_audio(path: Path) -> bool:
    """Recognize NPY audio even when Kaggle truncates the file extension."""
    if path.suffix.lower() == ".npy":
        return True
    with path.open("rb") as handle:
        return handle.read(len(NUMPY_MAGIC)) == NUMPY_MAGIC


def _manifest_cell(
    row: Mapping[str, object],
    name: str,
    *,
    allow_empty: bool = False,
) -> str:
    """Read one manifest cell without silently coercing a missing value."""
    value = row.get(name)
    if not isinstance(value, str):
        raise ValueError(f"Manifest {name} must be a CSV string.")
    if not allow_empty and not value.strip():
        raise ValueError(f"Manifest {name} must be non-empty.")
    return value


def load_manifest_snapshot(path: Path) -> ManifestSnapshot:
    """Read, hash, and parse a complete manifest from the same byte buffer.

    The digest is intentionally computed before the CSV is decoded, from the
    precise bytes which yielded the returned fully-resolved item objects.  This
    is the manifest entry point required by future decoder-candidate mining;
    it closes the parse/hash and path-binding gap that an independent reload
    would leave open.
    """
    resolved_manifest = path.resolve(strict=True)
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
        items=tuple(ManifestItem(
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
        ) for row in rows),
        _decoder_candidate_snapshot_token=_manifest_snapshot_capability_token(),
    )
    _register_loaded_manifest_snapshot(snapshot)
    return snapshot


def load_manifest(path: Path) -> list[ManifestItem]:
    """Load manifest items while preserving the historical list-returning API."""
    return list(load_manifest_snapshot(path).items)


class PolyphonicCorpus:
    """Keep compact labels in RAM and load each waveform at most once."""

    REQUIRED_LABELS = {
        "active_bits", "onset_bits", "polyphony", "valid", "slot_pitch",
        "slot_note_id", "note_harmonic_present", "note_harmonic_amplitude",
        "note_harmonic_offset_cents", "note_harmonic_valid", "sample_rate",
        "hop_size", "audio_frames", "midi_min", "midi_max",
    }

    def __init__(
        self,
        items: Sequence[ManifestItem],
        *,
        fundamental_offsets: FundamentalOffsetMap | None = None,
        required_fundamental_offset_datasets: Sequence[str] = (),
    ) -> None:
        if not items:
            raise ValueError("The corpus split is empty.")
        self.items = list(items)
        offsets = dict(fundamental_offsets or {})
        required_datasets = {str(value) for value in required_fundamental_offset_datasets}
        self.labels: list[CachedLabels] = []
        for item in self.items:
            with np.load(item.labels_path, allow_pickle=False) as source:
                missing = self.REQUIRED_LABELS - set(source.files)
                if missing:
                    raise ValueError(
                        f"{item.source_id}: label arrays missing {sorted(missing)}"
                    )
                arrays = {name: np.asarray(source[name]) for name in source.files}
            key = (str(item.dataset_id), str(item.source_id))
            offset_values = offsets.get(key)
            if offset_values is None:
                if item.dataset_id in required_datasets:
                    raise ValueError(
                        f"{item.source_id}: required fundamental offset is missing"
                    )
            else:
                offset_values = np.asarray(offset_values, dtype=np.float32)
                expected_rows = int(arrays["note_harmonic_present"].shape[0])
                if offset_values.shape != (expected_rows,):
                    raise ValueError(
                        f"{item.source_id}: fundamental offset rows do not match labels"
                    )
                existing = arrays.get("note_fundamental_offset_cents")
                if existing is not None and not np.allclose(
                    np.asarray(existing, dtype=np.float32), offset_values,
                    rtol=0.0, atol=1e-4,
                ):
                    raise ValueError(
                        f"{item.source_id}: embedded and sidecar fundamental offsets disagree"
                    )
                arrays["note_fundamental_offset_cents"] = offset_values
            frame_count = len(arrays["active_bits"])
            for name in ("onset_bits", "polyphony", "valid"):
                if len(arrays[name]) != frame_count:
                    raise ValueError(f"{item.source_id}: inconsistent {name} length")
            if arrays["slot_pitch"].shape[0] != frame_count:
                raise ValueError(f"{item.source_id}: inconsistent slot arrays")
            self.labels.append(CachedLabels(item, arrays))

        first = self.labels[0].arrays
        self.sample_rate = int(first["sample_rate"])
        self.hop_size = int(first["hop_size"])
        self.midi_min = int(first["midi_min"])
        self.midi_max = int(first["midi_max"])
        self.pitch_classes = self.midi_max - self.midi_min + 1
        self.harmonic_count = int(first["note_harmonic_present"].shape[1])
        self._audio: dict[int, np.ndarray] = {}
        self._archives: dict[Path, ZipFile] = {}

        for cached in self.labels[1:]:
            arrays = cached.arrays
            contract = (
                int(arrays["sample_rate"]), int(arrays["hop_size"]),
                int(arrays["midi_min"]), int(arrays["midi_max"]),
                int(arrays["note_harmonic_present"].shape[1]),
            )
            expected = (
                self.sample_rate, self.hop_size, self.midi_min,
                self.midi_max, self.harmonic_count,
            )
            if contract != expected:
                raise ValueError(f"{cached.item.source_id}: mixed label contract")

    def close(self) -> None:
        for archive in self._archives.values():
            archive.close()
        self._archives.clear()
        for waveform in self._audio.values():
            mapping = getattr(waveform, "_mmap", None)
            if mapping is not None:
                mapping.close()
        self._audio.clear()

    def __enter__(self) -> "PolyphonicCorpus":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @property
    def audio_gib(self) -> float:
        return sum(value.nbytes for value in self._audio.values()) / 1024**3

    def audio(self, recording_index: int) -> np.ndarray:
        recording_index = int(recording_index)
        cached = self._audio.get(recording_index)
        if cached is not None:
            return cached
        item = self.items[recording_index]
        if not item.audio_member and _is_numpy_audio(item.audio_path):
            waveform = np.load(item.audio_path, mmap_mode="r", allow_pickle=False)
            rate = self.sample_rate
            if waveform.ndim == 1:
                waveform = waveform[:, None]
        elif item.audio_member:
            archive = self._archives.get(item.audio_path)
            if archive is None:
                archive = ZipFile(item.audio_path)
                self._archives[item.audio_path] = archive
            source = io.BytesIO(archive.read(item.audio_member))
            waveform, rate = sf.read(source, dtype="float32", always_2d=True)
        else:
            waveform, rate = sf.read(
                item.audio_path, dtype="float32", always_2d=True
            )
        if int(rate) != self.sample_rate or waveform.shape[1] != 1:
            raise ValueError(
                f"{item.source_id}: expected mono {self.sample_rate} Hz audio"
            )
        mono = (
            waveform[:, 0]
            if isinstance(waveform, np.memmap)
            else np.ascontiguousarray(waveform[:, 0], dtype=np.float32)
        )
        expected_frames = int(self.labels[recording_index].arrays["audio_frames"])
        if len(mono) != expected_frames:
            raise ValueError(
                f"{item.source_id}: audio length {len(mono)} != {expected_frames}"
            )
        self._audio[recording_index] = mono
        return mono

    def preload_audio(self) -> None:
        for index in range(len(self.items)):
            self.audio(index)


@dataclass(frozen=True)
class FramePools:
    onset: np.ndarray
    polyphonic: np.ndarray
    monophonic: np.ndarray
    silence: np.ndarray

    @property
    def sizes(self) -> dict[str, int]:
        return {
            "onset": len(self.onset),
            "polyphonic": len(self.polyphonic),
            "monophonic": len(self.monophonic),
            "silence": len(self.silence),
        }


def _refs(recording_index: int, frame_indices: np.ndarray) -> np.ndarray:
    return np.column_stack((
        np.full(len(frame_indices), recording_index, dtype=np.int32),
        np.asarray(frame_indices, dtype=np.int32),
    ))


def build_frame_pools(corpus: PolyphonicCorpus) -> FramePools:
    return _build_frame_pools(corpus, range(len(corpus.labels)))


def _build_frame_pools(
    corpus: PolyphonicCorpus,
    recording_indices: Sequence[int],
) -> FramePools:
    categories: dict[str, list[np.ndarray]] = {
        "onset": [], "polyphonic": [], "monophonic": [], "silence": [],
    }
    for recording_index in recording_indices:
        cached = corpus.labels[int(recording_index)]
        arrays = cached.arrays
        valid = np.asarray(arrays["valid"] > 0)
        active = np.asarray(arrays["active_bits"] != 0)
        onset = np.asarray(arrays["onset_bits"] != 0)
        polyphonic = np.asarray(arrays["polyphony"] > 1)
        masks = {
            "onset": valid & onset,
            "polyphonic": valid & active & polyphonic & ~onset,
            "monophonic": valid & active & ~polyphonic & ~onset,
            "silence": valid & ~active,
        }
        for name, mask in masks.items():
            categories[name].append(_refs(recording_index, np.flatnonzero(mask)))
    pools = {
        name: np.concatenate(parts, axis=0)
        for name, parts in categories.items()
    }
    if any(len(pool) == 0 for pool in pools.values()):
        raise ValueError(f"One or more frame pools are empty: {pools.keys()}")
    return FramePools(**pools)


def build_dataset_frame_pools(
    corpus: PolyphonicCorpus,
) -> dict[str, FramePools]:
    indices: dict[str, list[int]] = {}
    for index, item in enumerate(corpus.items):
        indices.setdefault(item.dataset_id, []).append(index)
    return {
        dataset_id: _build_frame_pools(corpus, recording_indices)
        for dataset_id, recording_indices in sorted(indices.items())
    }


def natural_validation_refs(
    corpus: PolyphonicCorpus,
    maximum_examples: int | None,
    seed: int,
) -> np.ndarray:
    parts: list[np.ndarray] = []
    for recording_index, cached in enumerate(corpus.labels):
        valid = np.flatnonzero(cached.arrays["valid"] > 0)
        parts.append(_refs(recording_index, valid))
    refs = np.concatenate(parts, axis=0)
    if maximum_examples is not None and len(refs) > maximum_examples:
        rng = np.random.default_rng(seed)
        refs = refs[rng.choice(len(refs), size=maximum_examples, replace=False)]
    return refs


def dataset_balanced_validation_refs(
    corpus: PolyphonicCorpus,
    maximum_examples: int,
    dataset_fractions: Mapping[str, float],
    seed: int,
) -> np.ndarray:
    if set(dataset_fractions) != {item.dataset_id for item in corpus.items}:
        raise ValueError("Validation dataset fractions do not match the corpus.")
    if abs(sum(dataset_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Validation dataset fractions must sum to 1.0.")
    by_dataset: dict[str, list[np.ndarray]] = {
        dataset: [] for dataset in dataset_fractions
    }
    for recording_index, cached in enumerate(corpus.labels):
        valid = np.flatnonzero(cached.arrays["valid"] > 0)
        by_dataset[cached.item.dataset_id].append(_refs(recording_index, valid))
    rng = np.random.default_rng(seed)
    selected: list[np.ndarray] = []
    assigned = 0
    datasets = list(dataset_fractions)
    for index, dataset in enumerate(datasets):
        pool = np.concatenate(by_dataset[dataset], axis=0)
        count = (
            maximum_examples - assigned
            if index == len(datasets) - 1
            else int(round(maximum_examples * float(dataset_fractions[dataset])))
        )
        choices = rng.choice(len(pool), size=count, replace=count > len(pool))
        selected.append(pool[choices])
        assigned += count
    refs = np.concatenate(selected, axis=0)
    rng.shuffle(refs)
    return refs


def class_counts(
    corpus: PolyphonicCorpus,
    target: str,
) -> tuple[np.ndarray, int]:
    if target not in {"active_bits", "onset_bits"}:
        raise ValueError(target)
    positives = np.zeros(corpus.pitch_classes, dtype=np.int64)
    total = 0
    for cached in corpus.labels:
        arrays = cached.arrays
        valid = arrays["valid"] > 0
        bits = np.asarray(arrays[target][valid], dtype=np.uint64)
        total += len(bits)
        for class_index in range(corpus.pitch_classes):
            mask = np.uint64(1) << np.uint64(class_index)
            positives[class_index] += int(np.count_nonzero(bits & mask))
    return positives, total


def dataset_balanced_class_counts(
    corpus: PolyphonicCorpus,
    target: str,
    dataset_fractions: Mapping[str, float],
    effective_total: int = 1_000_000,
) -> tuple[np.ndarray, int]:
    """Estimate class counts under the configured dataset sampling mixture."""
    datasets = {item.dataset_id for item in corpus.items}
    if set(dataset_fractions) != datasets:
        raise ValueError("Class-weight dataset fractions do not match the corpus.")
    if abs(sum(dataset_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Class-weight dataset fractions must sum to 1.0.")
    if effective_total < 1:
        raise ValueError("effective_total must be positive.")
    positive_by_dataset = {
        dataset: np.zeros(corpus.pitch_classes, dtype=np.int64)
        for dataset in datasets
    }
    total_by_dataset = {dataset: 0 for dataset in datasets}
    for cached in corpus.labels:
        arrays = cached.arrays
        valid = arrays["valid"] > 0
        bits = np.asarray(arrays[target][valid], dtype=np.uint64)
        dataset = cached.item.dataset_id
        total_by_dataset[dataset] += len(bits)
        for class_index in range(corpus.pitch_classes):
            mask = np.uint64(1) << np.uint64(class_index)
            positive_by_dataset[dataset][class_index] += int(
                np.count_nonzero(bits & mask)
            )
    rate = np.zeros(corpus.pitch_classes, dtype=np.float64)
    for dataset, fraction in dataset_fractions.items():
        total = total_by_dataset[dataset]
        if total < 1:
            raise ValueError(f"Dataset {dataset!r} has no valid frames.")
        rate += (
            float(fraction)
            * positive_by_dataset[dataset].astype(np.float64)
            / float(total)
        )
    return rate * float(effective_total), int(effective_total)


def _class_counts_for_refs(
    corpus: PolyphonicCorpus,
    target: str,
    refs: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Count per-pitch positives in an explicit set of frame references."""
    if target not in {"active_bits", "onset_bits"}:
        raise ValueError(target)
    refs = np.asarray(refs, dtype=np.int32)
    if refs.ndim != 2 or refs.shape[1] != 2:
        raise ValueError("Frame references must have shape (N, 2).")
    positives = np.zeros(corpus.pitch_classes, dtype=np.int64)
    if len(refs) == 0:
        return positives, 0

    recording_indices = refs[:, 0]
    starts = np.concatenate((
        np.asarray([0], dtype=np.int64),
        np.flatnonzero(recording_indices[1:] != recording_indices[:-1]) + 1,
    ))
    ends = np.concatenate((starts[1:], np.asarray([len(refs)])))
    for start, end in zip(starts, ends):
        recording_index = int(recording_indices[start])
        frame_indices = refs[start:end, 1]
        bits = np.asarray(
            corpus.labels[recording_index].arrays[target][frame_indices],
            dtype=np.uint64,
        )
        for class_index in range(corpus.pitch_classes):
            mask = np.uint64(1) << np.uint64(class_index)
            positives[class_index] += int(np.count_nonzero(bits & mask))
    return positives, len(refs)


def sampler_effective_class_counts(
    corpus: PolyphonicCorpus,
    target: str,
    dataset_pools: Mapping[str, FramePools],
    dataset_fractions: Mapping[str, float],
    sampling_fractions: Mapping[str, float],
    effective_total: int = 1_000_000,
) -> tuple[np.ndarray, int]:
    """Estimate counts under the sampler's dataset/category mixture.

    The training sampler first chooses a dataset according to
    ``dataset_fractions``, then a disjoint frame pool according to
    ``sampling_fractions``. Class weights must follow that effective mixture,
    rather than the natural frequency inside each complete dataset.
    """
    if target not in {"active_bits", "onset_bits"}:
        raise ValueError(target)
    if set(dataset_fractions) != set(dataset_pools):
        raise ValueError("Class-weight dataset fractions do not match pools.")
    pool_names = {"onset", "polyphonic", "monophonic", "silence"}
    if set(sampling_fractions) != pool_names:
        raise ValueError(
            "Class-weight sampling fractions must define "
            f"{sorted(pool_names)}."
        )
    if any(float(value) < 0.0 for value in dataset_fractions.values()):
        raise ValueError("Class-weight dataset fractions must be non-negative.")
    if any(float(value) < 0.0 for value in sampling_fractions.values()):
        raise ValueError("Class-weight sampling fractions must be non-negative.")
    if abs(sum(dataset_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Class-weight dataset fractions must sum to 1.0.")
    if abs(sum(sampling_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Class-weight sampling fractions must sum to 1.0.")
    if effective_total < 1:
        raise ValueError("effective_total must be positive.")

    rate = np.zeros(corpus.pitch_classes, dtype=np.float64)
    for dataset, dataset_fraction in dataset_fractions.items():
        pools = dataset_pools[dataset]
        for pool_name, sampling_fraction in sampling_fractions.items():
            mixture_fraction = (
                float(dataset_fraction) * float(sampling_fraction)
            )
            if mixture_fraction == 0.0:
                continue
            positives, total = _class_counts_for_refs(
                corpus, target, getattr(pools, pool_name)
            )
            if total < 1:
                raise ValueError(
                    f"Dataset {dataset!r} pool {pool_name!r} is empty."
                )
            rate += mixture_fraction * positives.astype(np.float64) / total
    return rate * float(effective_total), int(effective_total)


@dataclass(frozen=True)
class PolyphonicEpochPlan:
    """Canonical, immutable sampling and augmentation plan for one epoch.

    The arrays use explicit little-endian dtypes so the digest is stable
    across operating systems.  ``export`` produces values accepted directly
    by ``numpy.savez``; ``from_export`` validates the stored digest before
    returning a plan.
    """

    epoch: int
    order: np.ndarray
    augmentation_gains: np.ndarray
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        epoch = _plan_integer("epoch", self.epoch)
        order = _canonical_plan_order(self.order)
        gains = _canonical_plan_gains(self.augmentation_gains, len(order))
        digest = _plan_sha256(epoch, order, gains)
        object.__setattr__(self, "epoch", epoch)
        object.__setattr__(self, "order", order)
        object.__setattr__(self, "augmentation_gains", gains)
        object.__setattr__(self, "sha256", digest)

    def export(self) -> dict[str, np.ndarray]:
        """Return a read-only mapping suitable for ``numpy.savez``."""

        values = {
            "schema_version": np.asarray(
                EPOCH_PLAN_SCHEMA_VERSION, dtype="<i4"
            ),
            "epoch": np.asarray(self.epoch, dtype="<i8"),
            "order": self.order.copy(),
            "augmentation_gains": self.augmentation_gains.copy(),
            "sha256": np.asarray(self.sha256, dtype="<U64"),
        }
        for value in values.values():
            value.setflags(write=False)
        return values

    @classmethod
    def from_export(
        cls, payload: Mapping[str, object]
    ) -> "PolyphonicEpochPlan":
        """Restore and authenticate a plan exported by :meth:`export`."""

        required = {
            "schema_version",
            "epoch",
            "order",
            "augmentation_gains",
            "sha256",
        }
        try:
            missing = required - set(payload)
        except TypeError as error:
            raise TypeError("The epoch plan export must be a mapping.") from error
        if missing:
            raise ValueError(
                f"Epoch plan export fields missing: {sorted(missing)}"
            )
        schema_version = _plan_scalar_integer(
            "schema_version", payload["schema_version"]
        )
        if schema_version != EPOCH_PLAN_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported epoch plan schema: {schema_version}"
            )
        epoch = _plan_scalar_integer("epoch", payload["epoch"])
        expected_sha256 = _plan_scalar_text("sha256", payload["sha256"])
        plan = cls(
            epoch=epoch,
            order=np.asarray(payload["order"]),
            augmentation_gains=np.asarray(payload["augmentation_gains"]),
        )
        if expected_sha256 != plan.sha256:
            raise ValueError(
                "Epoch plan SHA-256 mismatch; the persisted plan is corrupt."
            )
        return plan


def _plan_integer(name: str, value: object) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a non-negative integer.")
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            f"{name} must be a non-negative integer."
        ) from error
    if result != value or result < 0 or result > np.iinfo(np.int64).max:
        raise ValueError(f"{name} must be a non-negative integer.")
    return result


def _plan_scalar_integer(name: str, value: object) -> int:
    array = np.asarray(value)
    if array.shape != ():
        raise ValueError(f"{name} must be a scalar.")
    return _plan_integer(name, array.item())


def _plan_scalar_text(name: str, value: object) -> str:
    array = np.asarray(value)
    if array.shape != ():
        raise ValueError(f"{name} must be a scalar.")
    result = array.item()
    if isinstance(result, bytes):
        try:
            result = result.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError(f"{name} must contain ASCII text.") from error
    if not isinstance(result, str):
        raise ValueError(f"{name} must be text.")
    return result


def _canonical_plan_order(value: object) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 2 or raw.shape[1] != 2:
        raise ValueError("Epoch plan order must have shape (N, 2).")
    if raw.dtype.kind not in {"i", "u"}:
        raise ValueError("Epoch plan order must contain integers.")
    if raw.size:
        minimum = int(np.min(raw))
        maximum = int(np.max(raw))
        if minimum < 0 or maximum > np.iinfo(np.int32).max:
            raise ValueError(
                "Epoch plan references must fit non-negative int32 values."
            )
    order = np.array(raw, dtype="<i4", order="C", copy=True)
    order.setflags(write=False)
    return order


def _canonical_plan_gains(value: object, expected: int) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (expected,):
        raise ValueError(
            "Epoch plan augmentation gains must have shape (N,)."
        )
    if raw.dtype.kind not in {"f", "i", "u"}:
        raise ValueError("Epoch plan augmentation gains must be numeric.")
    gains = np.array(raw, dtype="<f4", order="C", copy=True)
    if not np.all(np.isfinite(gains)) or np.any(gains <= 0.0):
        raise ValueError(
            "Epoch plan augmentation gains must be finite and positive."
        )
    gains.setflags(write=False)
    return gains


def _plan_sha256(
    epoch: int, order: np.ndarray, augmentation_gains: np.ndarray
) -> str:
    digest = hashlib.sha256()
    digest.update(b"guitar-midi-polyphonic-epoch-plan\x00")
    digest.update(struct.pack("<I", EPOCH_PLAN_SCHEMA_VERSION))
    digest.update(struct.pack("<q", epoch))
    digest.update(struct.pack("<Q", len(order)))
    digest.update(order.tobytes(order="C"))
    digest.update(augmentation_gains.tobytes(order="C"))
    return digest.hexdigest()


class PolyphonicSequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        corpus: PolyphonicCorpus,
        batch_size: int,
        input_samples: int,
        normalization_gain: float,
        seed: int,
        refs: np.ndarray | None = None,
        pools: FramePools | None = None,
        dataset_pools: Mapping[str, FramePools] | None = None,
        dataset_fractions: Mapping[str, float] | None = None,
        examples_per_epoch: int | None = None,
        sampling_fractions: Mapping[str, float] | None = None,
        augmentation_gain_db: float = 0.0,
        input_gain_by_frame: Sequence[np.ndarray] | None = None,
        full_context_from_start: bool = False,
        harmonic_presence_target: bool = False,
        independent_note_target: bool = False,
        shuffle: bool = False,
        workers: int = 1,
        max_queue_size: int = 2,
    ) -> None:
        # Keras 3 removed the queue options from ``Model.fit``. They now
        # belong to ``PyDataset``/``Sequence`` itself. Keep multiprocessing
        # disabled because each process would duplicate the multi-gigabyte
        # audio cache.
        try:
            super().__init__(
                workers=int(workers),
                use_multiprocessing=False,
                max_queue_size=int(max_queue_size),
            )
        except TypeError as error:
            # TensorFlow/Keras 2 exposes ``Sequence`` as a legacy base whose
            # initializer is effectively ``object.__init__``. Its queue
            # options are still passed to ``Model.fit`` by train.py.
            if "object.__init__()" not in str(error):
                raise
            super().__init__()
        self.corpus = corpus
        self.batch_size = int(batch_size)
        self.input_samples = int(input_samples)
        self.normalization_gain = float(normalization_gain)
        self.seed = _plan_integer("seed", seed)
        self.pools = pools
        self.dataset_pools = None if dataset_pools is None else dict(dataset_pools)
        self.dataset_fractions = None if dataset_fractions is None else dict(dataset_fractions)
        self.examples_per_epoch = examples_per_epoch
        self.sampling_fractions = dict(sampling_fractions or {
            "onset": 0.30,
            "polyphonic": 0.30,
            "monophonic": 0.25,
            "silence": 0.15,
        })
        self.shuffle = bool(shuffle)
        self.augmentation_gain_db = float(augmentation_gain_db)
        self.input_gain_by_frame = (
            None
            if input_gain_by_frame is None
            else tuple(
                np.asarray(values, dtype=np.float32)
                for values in input_gain_by_frame
            )
        )
        self.full_context_from_start = bool(full_context_from_start)
        self.harmonic_presence_target = bool(harmonic_presence_target)
        self.independent_note_target = bool(independent_note_target)
        self.workers = int(workers)
        self.max_queue_size = int(max_queue_size)
        if (
            self.batch_size < 1
            or self.input_samples < 1
            or self.workers < 1
            or self.max_queue_size < 1
        ):
            raise ValueError("Invalid sequence dimensions.")
        if pools is None and self.dataset_pools is None and refs is None:
            raise ValueError("Either fixed refs or balanced pools are required.")
        if (pools is not None or self.dataset_pools is not None) and examples_per_epoch is None:
            raise ValueError("examples_per_epoch is required with pools.")
        if self.dataset_pools is not None:
            if not self.dataset_fractions:
                raise ValueError("dataset_fractions are required with dataset_pools.")
            if set(self.dataset_fractions) != set(self.dataset_pools):
                raise ValueError("dataset_fractions must match dataset_pools.")
            if abs(sum(self.dataset_fractions.values()) - 1.0) > 1e-6:
                raise ValueError("dataset_fractions must sum to 1.0.")
        if abs(sum(self.sampling_fractions.values()) - 1.0) > 1e-6:
            raise ValueError("sampling_fractions must sum to 1.0.")
        if self.input_gain_by_frame is not None:
            if len(self.input_gain_by_frame) != len(self.corpus.labels):
                raise ValueError(
                    "input_gain_by_frame must contain one array per recording."
                )
            for cached, values in zip(
                self.corpus.labels, self.input_gain_by_frame
            ):
                expected = len(cached.arrays["active_bits"])
                if values.shape != (expected,):
                    raise ValueError(
                        "Each input gain array must contain one value per frame."
                    )
                if (
                    not np.all(np.isfinite(values))
                    or np.any(values <= 0.0)
                ):
                    raise ValueError(
                        "Per-frame input gains must be finite and positive."
                    )
        self.fixed_refs = (
            None if refs is None else _canonical_plan_order(refs)
        )
        self._epoch_plan: PolyphonicEpochPlan | None = None
        self.install_plan(self.plan_for_epoch(0))

    @property
    def epoch(self) -> int:
        assert self._epoch_plan is not None
        return self._epoch_plan.epoch

    @property
    def plan_sha256(self) -> str:
        assert self._epoch_plan is not None
        return self._epoch_plan.sha256

    def plan_for_epoch(self, epoch: int) -> PolyphonicEpochPlan:
        """Build an epoch plan without depending on prior RNG calls."""

        epoch = _plan_integer("epoch", epoch)
        rng = self._rng_for_epoch(epoch)
        if self.pools is None and self.dataset_pools is None:
            assert self.fixed_refs is not None
            order = self.fixed_refs.copy()
            if self.shuffle:
                rng.shuffle(order)
        else:
            assert self.examples_per_epoch is not None
            if self.dataset_pools is not None:
                assert self.dataset_fractions is not None
                dataset_parts: list[np.ndarray] = []
                assigned = 0
                datasets = list(self.dataset_fractions)
                for index, dataset_id in enumerate(datasets):
                    count = (
                        self.examples_per_epoch - assigned
                        if index == len(datasets) - 1
                        else int(round(
                            self.examples_per_epoch
                            * float(self.dataset_fractions[dataset_id])
                        ))
                    )
                    dataset_parts.append(self._sample_pools(
                        self.dataset_pools[dataset_id], count, rng
                    ))
                    assigned += count
                order = np.concatenate(dataset_parts, axis=0)
            else:
                assert self.pools is not None
                order = self._sample_pools(
                    self.pools, self.examples_per_epoch, rng
                )
            rng.shuffle(order)

        if self.augmentation_gain_db > 0.0:
            gains = np.power(
                np.float32(10.0),
                rng.uniform(
                    -self.augmentation_gain_db,
                    self.augmentation_gain_db,
                    size=len(order),
                ).astype(np.float32)
                / np.float32(20.0),
            ).astype(np.float32)
        else:
            gains = np.ones(len(order), dtype=np.float32)
        return PolyphonicEpochPlan(
            epoch=epoch,
            order=order,
            augmentation_gains=gains,
        )

    def export_plan(self) -> dict[str, np.ndarray]:
        """Export the currently installed plan for durable persistence."""

        assert self._epoch_plan is not None
        return self._epoch_plan.export()

    def install_plan(
        self,
        plan: PolyphonicEpochPlan | Mapping[str, object],
    ) -> PolyphonicEpochPlan:
        """Validate and install an immutable plan without sampling again."""

        if not isinstance(plan, PolyphonicEpochPlan):
            plan = PolyphonicEpochPlan.from_export(plan)
        expected = (
            len(self.fixed_refs)
            if self.pools is None and self.dataset_pools is None
            else int(self.examples_per_epoch or 0)
        )
        if len(plan.order) != expected:
            raise ValueError(
                "Epoch plan example count does not match the sequence: "
                f"{len(plan.order)} != {expected}."
            )
        self._validate_plan_references(plan.order)
        self._epoch_plan = plan
        self.order = plan.order
        self.augmentation_gains = plan.augmentation_gains
        return plan

    def _rng_for_epoch(self, epoch: int) -> np.random.Generator:
        seed_material = (
            "guitar-midi-polyphonic-sequence-plan-v1:"
            f"{self.seed}:{epoch}"
        ).encode("ascii")
        entropy = np.frombuffer(
            hashlib.sha256(seed_material).digest(), dtype="<u4"
        )
        return np.random.default_rng(np.random.SeedSequence(entropy))

    def _sample_pools(
        self,
        pools: FramePools,
        total: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        sampled: list[np.ndarray] = []
        assigned = 0
        names = list(self.sampling_fractions)
        for index, name in enumerate(names):
            fraction = float(self.sampling_fractions[name])
            count = (
                total - assigned
                if index == len(names) - 1
                else int(round(total * fraction))
            )
            pool = getattr(pools, name)
            selection = rng.choice(
                len(pool), size=count, replace=count > len(pool)
            )
            sampled.append(pool[selection])
            assigned += count
        return np.concatenate(sampled, axis=0)

    def _validate_plan_references(self, order: np.ndarray) -> None:
        labels = getattr(self.corpus, "labels", None)
        if labels is None or len(order) == 0:
            return
        recording_indices = order[:, 0]
        if np.any(recording_indices >= len(labels)):
            raise ValueError(
                "Epoch plan contains an out-of-range recording reference."
            )
        for recording_index in np.unique(recording_indices):
            frame_indices = order[
                recording_indices == recording_index, 1
            ]
            frame_count = len(
                labels[int(recording_index)].arrays["active_bits"]
            )
            if np.any(frame_indices >= frame_count):
                raise ValueError(
                    "Epoch plan contains an out-of-range frame reference."
                )

    def __len__(self) -> int:
        return max(1, math.ceil(len(self.order) / self.batch_size))

    def __getitem__(self, batch_index: int):
        start = batch_index * self.batch_size
        end = (batch_index + 1) * self.batch_size
        selected = self.order[start:end]
        selected_augmentation_gains = self.augmentation_gains[start:end]
        if len(selected) == 0:
            raise IndexError(batch_index)
        size = len(selected)
        classes = self.corpus.pitch_classes
        harmonics = self.corpus.harmonic_count
        audio = np.zeros((size, self.input_samples, 1), dtype=np.float32)
        time_mask = np.zeros((size, self.input_samples), dtype=np.float32)
        frame_target = np.zeros((size, classes), dtype=np.float32)
        onset_target = np.zeros((size, classes), dtype=np.float32)
        independent_note = np.zeros((size, classes), dtype=np.float32)
        independent_note_weight = np.zeros((size, classes), dtype=np.float32)
        harmonic_amplitude = np.zeros((size, classes, harmonics), np.float32)
        harmonic_offset = np.zeros((size, classes, harmonics), np.float32)
        harmonic_valid = np.zeros((size, classes, harmonics), np.float32)
        harmonic_presence = np.zeros(
            (size, classes, harmonics), np.float32
        )
        harmonic_supervision_weight = np.zeros(
            (size, classes, harmonics), np.float32
        )
        class_bits = np.arange(classes, dtype=np.uint64)

        for row, (recording_index, frame_index) in enumerate(selected):
            recording_index = int(recording_index)
            frame_index = int(frame_index)
            cached = self.corpus.labels[recording_index]
            arrays = cached.arrays
            waveform = self.corpus.audio(recording_index)
            end_sample = min(
                len(waveform), (frame_index + 1) * self.corpus.hop_size
            )
            start_sample = max(0, end_sample - self.input_samples)
            visible = end_sample - start_sample
            segment = np.asarray(
                waveform[start_sample:end_sample], dtype=np.float32
            )
            if np.issubdtype(waveform.dtype, np.integer):
                segment /= max(abs(np.iinfo(waveform.dtype).min), 1)
            audio[row, -visible:, 0] = segment
            gain = self.normalization_gain
            if self.input_gain_by_frame is not None:
                gain *= float(
                    self.input_gain_by_frame[recording_index][frame_index]
                )
            gain *= float(selected_augmentation_gains[row])
            audio[row, :, 0] *= gain
            np.clip(audio[row, :, 0], -1.0, 1.0, out=audio[row, :, 0])
            if self.full_context_from_start:
                time_mask[row, :] = 1.0
            else:
                time_mask[row, -visible:] = 1.0

            active_bits = np.uint64(arrays["active_bits"][frame_index])
            onset_bits = np.uint64(arrays["onset_bits"][frame_index])
            frame_target[row] = ((active_bits >> class_bits) & 1).astype(np.float32)
            onset_target[row] = ((onset_bits >> class_bits) & 1).astype(np.float32)
            if self.independent_note_target:
                independent = build_independent_note_targets(
                    arrays,
                    frame_index,
                    pitch_classes=classes,
                )
                independent_note[row] = independent.target
                independent_note_weight[row] = independent.weight

            for pitch_index, note_id in zip(
                arrays["slot_pitch"][frame_index],
                arrays["slot_note_id"][frame_index],
            ):
                pitch_index = int(pitch_index)
                note_id = int(note_id)
                if pitch_index < 0 or note_id < 0:
                    continue
                if not arrays["note_harmonic_valid"][note_id]:
                    continue
                present = np.asarray(
                    arrays["note_harmonic_present"][note_id], np.float32
                )
                if self.harmonic_presence_target:
                    supervised_source = arrays.get(
                        "note_harmonic_supervised"
                    )
                    reliability_source = arrays.get(
                        "note_harmonic_reliability"
                    )
                    if (
                        supervised_source is None
                        or reliability_source is None
                    ):
                        # Old or non-harmonic labels mean supervision is
                        # unavailable, never an observed absent harmonic.
                        continue
                    supervised = np.asarray(
                        supervised_source[note_id], np.float32
                    )
                    reliability = np.asarray(
                        reliability_source[note_id], np.float32
                    )
                    supervision_weight = supervised * reliability
                    harmonic_presence[row, pitch_index] = present
                    harmonic_supervision_weight[
                        row, pitch_index
                    ] = supervision_weight
                    harmonic_valid[row, pitch_index] = (
                        supervision_weight * present
                    )
                else:
                    harmonic_valid[row, pitch_index] = present
                harmonic_amplitude[row, pitch_index] = np.asarray(
                    arrays["note_harmonic_amplitude"][note_id], np.float32
                )
                harmonic_offset[row, pitch_index] = np.asarray(
                    arrays["note_harmonic_offset_cents"][note_id], np.float32
                )

        inputs = {"audio": audio, "time_mask": time_mask}
        targets = {
            "frame": frame_target,
            "onset": onset_target,
            "harmonic_amplitude": np.concatenate(
                [
                    harmonic_amplitude,
                    (
                        harmonic_supervision_weight
                        if self.harmonic_presence_target
                        else harmonic_valid
                    ),
                ],
                axis=-1,
            ),
            "harmonic_offset_cents": np.concatenate(
                [harmonic_offset, harmonic_valid, harmonic_amplitude], axis=-1
            ),
        }
        if self.harmonic_presence_target:
            targets["harmonic_presence"] = np.concatenate(
                [harmonic_presence, harmonic_supervision_weight], axis=-1
            )
        if self.independent_note_target:
            targets["independent_note"] = np.concatenate(
                [independent_note, independent_note_weight], axis=-1
            )
        return inputs, targets

    def on_epoch_end(self) -> None:
        self.install_plan(self.plan_for_epoch(self.epoch + 1))


class PlanBatchSlice(tf.keras.utils.Sequence):
    """Expose a fixed batch interval without advancing its parent plan."""

    def __init__(
        self,
        sequence: PolyphonicSequence,
        start_batch: int,
        end_batch: int,
    ) -> None:
        if not isinstance(sequence, PolyphonicSequence):
            raise TypeError("sequence must be a PolyphonicSequence.")
        start_batch = _plan_integer("start_batch", start_batch)
        end_batch = _plan_integer("end_batch", end_batch)
        if start_batch >= end_batch:
            raise ValueError("A plan batch slice must contain at least one batch.")
        if end_batch > len(sequence):
            raise ValueError(
                f"end_batch {end_batch} exceeds sequence length {len(sequence)}."
            )

        try:
            super().__init__(
                workers=sequence.workers,
                use_multiprocessing=False,
                max_queue_size=sequence.max_queue_size,
            )
        except TypeError as error:
            if "object.__init__()" not in str(error):
                raise
            super().__init__()

        self.sequence = sequence
        self.start_batch = start_batch
        self.end_batch = end_batch
        self.batch_size = sequence.batch_size
        self.workers = sequence.workers
        self.max_queue_size = sequence.max_queue_size
        self.epoch = sequence.epoch
        self.plan_sha256 = sequence.plan_sha256

    def __len__(self) -> int:
        return self.end_batch - self.start_batch

    def __getitem__(self, batch_index: int):
        batch_index = _plan_integer("batch_index", batch_index)
        if batch_index >= len(self):
            raise IndexError(batch_index)
        self._assert_parent_plan()
        return self.sequence[self.start_batch + batch_index]

    def on_epoch_end(self) -> None:
        """Intentionally keep the parent on the exact installed plan."""

    def _assert_parent_plan(self) -> None:
        if (
            self.sequence.epoch != self.epoch
            or self.sequence.plan_sha256 != self.plan_sha256
        ):
            raise RuntimeError(
                "The parent epoch plan changed while a batch slice was active."
            )
