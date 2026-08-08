"""Pure, fail-closed provenance contract for future train-only candidates.

This module deliberately creates no candidate artifact and imports neither
TensorFlow nor a decoder. It centralizes the leakage-safe partition logic
already used by the bounded independent-note smoke, then exposes a serializable
preassignment plan that a future miner must validate before collecting rows.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, field
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import weakref
from typing import Iterable, Mapping, Protocol, Sequence


DECODER_CANDIDATE_PARTITION_SCHEMA_VERSION = 1
DECODER_CANDIDATE_PARTITION_PURPOSE = "decoder_candidate_train_only_partition"
DECODER_CANDIDATE_PARTITION_POLICY = (
    "corpus_aware_leakage_group_hash_70_15_15"
)
DECODER_CANDIDATE_PARTITIONS = ("fit", "dev", "calibration")
_VALIDATED_PARTITION_TOKEN = object()
_VALIDATED_SNAPSHOT_TOKEN = object()
_LOADED_MANIFEST_SNAPSHOT_TOKEN = object()
_LOADED_MANIFEST_SNAPSHOTS: dict[int, weakref.ReferenceType[object]] = {}
_VALIDATED_MANIFEST_SNAPSHOTS: dict[int, weakref.ReferenceType[object]] = {}
_PERSISTED_PARTITION_PLANS: dict[int, weakref.ReferenceType[object]] = {}


def _manifest_snapshot_capability_token() -> object:
    """Return the private capability used only by ``data.load_manifest_snapshot``."""
    return _LOADED_MANIFEST_SNAPSHOT_TOKEN


def _register_identity(
    registry: dict[int, weakref.ReferenceType[object]],
    value: object,
) -> None:
    """Store a weak capability keyed by object identity, never equality.

    ``WeakKeyDictionary`` is intentionally not used: a separately loaded but
    equal plan may replace the weak value while retaining the first weak key,
    so garbage collection of that first object removes the new capability.
    """
    identity = id(value)

    def cleanup(reference: weakref.ReferenceType[object]) -> None:
        if registry.get(identity) is reference:
            registry.pop(identity, None)

    registry[identity] = weakref.ref(value, cleanup)


def _identity_is_registered(
    registry: Mapping[int, weakref.ReferenceType[object]],
    value: object,
) -> bool:
    reference = registry.get(id(value))
    return reference is not None and reference() is value


def _register_loaded_manifest_snapshot(snapshot: object) -> None:
    """Attest one exact loader-created snapshot object by identity.

    A frozen dataclass token alone is insufficient because
    :func:`dataclasses.replace` copies private fields.  The weak registry is
    intentionally process-local and stores the object itself as its value, so
    an equal-looking copy never gains this capability.
    """
    _register_identity(_LOADED_MANIFEST_SNAPSHOTS, snapshot)


def _register_validated_manifest_snapshot(snapshot: object) -> None:
    """Attest the exact validated capability returned by the factory."""
    _register_identity(_VALIDATED_MANIFEST_SNAPSHOTS, snapshot)


def _register_persisted_partition_plan(plan: object) -> None:
    """Attest a plan object that was actually written or reloaded from disk."""
    _register_identity(_PERSISTED_PARTITION_PLANS, plan)


class ManifestItemLike(Protocol):
    """Metadata required for group-safe candidate provenance."""

    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    capture_id: str
    split: str


class ManifestSnapshotLike(Protocol):
    """One loader-certified manifest parse whose items will open the recording."""

    manifest_sha256: str
    items: Sequence[ManifestItemLike]


def _require_loaded_manifest_snapshot(snapshot: ManifestSnapshotLike) -> None:
    """Reject a caller-made structural lookalike before candidate collection."""
    if (
        getattr(snapshot, "_decoder_candidate_snapshot_token", None)
        is not _LOADED_MANIFEST_SNAPSHOT_TOKEN
    ):
        raise RuntimeError(
            "Fail closed: candidate plan requires a snapshot created by "
            "load_manifest_snapshot()."
        )
    if not _identity_is_registered(_LOADED_MANIFEST_SNAPSHOTS, snapshot):
        raise RuntimeError(
            "Fail closed: candidate plan requires the exact loader-attested "
            "manifest snapshot object."
        )


def _require_validated_manifest_snapshot(snapshot: object) -> None:
    """Reject copied/forged validation capabilities before a collector sees them."""
    if not _identity_is_registered(_VALIDATED_MANIFEST_SNAPSHOTS, snapshot):
        raise RuntimeError(
            "Fail closed: candidate collector requires the exact factory-attested "
            "validated manifest snapshot object."
        )


def _require_persisted_partition_plan(persisted: object) -> None:
    """Require a factory-attested immutable on-disk plan before collection."""
    if not _identity_is_registered(_PERSISTED_PARTITION_PLANS, persisted):
        raise RuntimeError(
            "Fail closed: candidate context requires the exact factory-attested "
            "persisted plan object."
        )
    path = getattr(persisted, "path", None)
    sha256 = getattr(persisted, "sha256", None)
    plan = getattr(persisted, "plan", None)
    if not isinstance(path, Path) or not isinstance(sha256, str):
        raise RuntimeError("Fail closed: persisted partition plan shape is invalid.")
    resolved = path.resolve(strict=True)
    raw_bytes = resolved.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != sha256:
        raise RuntimeError("Fail closed: persisted partition plan bytes changed on disk.")
    if raw_bytes != _canonical_partition_plan_bytes(plan):
        raise RuntimeError("Fail closed: persisted partition plan no longer matches its plan.")


@dataclass(frozen=True)
class DecoderCandidateManifestItem:
    """Minimal metadata read directly from the exact candidate manifest file."""

    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    capture_id: str
    split: str


def _non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value


def _csv_string(
    row: Mapping[str, object],
    name: str,
    *,
    allow_empty: bool = False,
) -> str:
    """Read one CSV identity field without turning a missing cell into ``None``."""
    value = row.get(name)
    if not isinstance(value, str):
        raise ValueError(f"candidate manifest {name} must be a CSV string.")
    if not allow_empty:
        return _non_empty_string(value, f"candidate manifest {name}")
    return value


def load_decoder_candidate_manifest(
    path: Path,
) -> tuple[tuple[DecoderCandidateManifestItem, ...], str]:
    """Read the whole manifest and its digest without importing TensorFlow.

    Future candidate collection must use this entry point rather than handing a
    hand-filtered list to the partitioner.  That makes the persisted plan bind
    to the actual manifest bytes and lets :func:`train_items_only` reject a
    manifest that would expose the locked test split.
    """
    resolved = Path(path).resolve(strict=True)
    raw_bytes = resolved.read_bytes()
    manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("candidate manifest is not valid UTF-8.") from exc
    with io.StringIO(decoded, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        required = {
            "source_id", "dataset_id", "player_id", "group_id",
            "capture_id", "split",
        }
        missing = required - fieldnames
        if missing:
            raise ValueError(
                "candidate manifest columns missing: "
                f"{sorted(missing)!r}."
            )
        items = tuple(
            DecoderCandidateManifestItem(
                source_id=_csv_string(row, "source_id"),
                dataset_id=_csv_string(row, "dataset_id"),
                player_id=_csv_string(row, "player_id", allow_empty=True),
                group_id=_csv_string(row, "group_id"),
                capture_id=_csv_string(row, "capture_id"),
                split=_csv_string(row, "split"),
            )
            for row in reader
        )
    if not items:
        raise ValueError("candidate manifest is empty.")
    return items, manifest_sha256


def canonical_digest(values: Iterable[str]) -> str:
    """Return the stable digest already used in independent-note reports."""
    payload = ("\n".join(sorted(str(value) for value in values)) + "\n").encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def canonical_identifier(value: object) -> str:
    """Return a stable ASCII identifier for manifest grouping metadata."""
    normalized = unicodedata.normalize("NFKD", str(value).strip()).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")


def dataset_family(dataset_id: object) -> str:
    """Collapse capture variants only where the existing smoke does."""
    value = canonical_identifier(dataset_id)
    if value.startswith("guitarset"):
        return "guitarset"
    if value.startswith("gaps"):
        return "gaps"
    if "guitar" in value and "tech" in value:
        return "guitar_techs"
    if not value:
        raise RuntimeError("Fail closed: an item has an empty dataset_id.")
    return value


def leakage_group_key(item: ManifestItemLike) -> str:
    """Group related captures exactly as the existing smoke does."""
    family = dataset_family(item.dataset_id)
    group_id = canonical_identifier(item.group_id)
    player_id = canonical_identifier(item.player_id)
    if family == "guitarset":
        if not player_id:
            raise RuntimeError("Fail closed: GuitarSet item has no player_id.")
        return f"guitarset:player:{player_id}"
    if family == "gaps":
        unavailable = {
            "", "unknown", "gaps_unknown", "unknown_player", "na", "n_a",
            "none", "null",
        }
        if player_id not in unavailable:
            return f"gaps:player:{player_id}"
        if not group_id:
            raise RuntimeError(
                "Fail closed: GAPS item has neither a usable player_id nor group_id."
            )
        return f"gaps:group:{group_id}"
    if not group_id:
        raise RuntimeError(
            f"Fail closed: {item.dataset_id!r} item has no group_id."
        )
    return f"{family}:group:{group_id}"


def train_items_only(items: Sequence[ManifestItemLike]) -> list[ManifestItemLike]:
    """Return train rows while refusing a manifest that exposes test rows."""
    split_counts = Counter(str(item.split) for item in items)
    if split_counts.get("test", 0):
        raise RuntimeError(
            "Fail closed: the train-only manifest contains locked test rows."
        )
    unexpected = set(split_counts) - {"train", "validation"}
    if unexpected:
        raise RuntimeError(
            f"Fail closed: unexpected manifest splits {sorted(unexpected)}"
        )
    train = [item for item in items if str(item.split) == "train"]
    if not train:
        raise RuntimeError("Fail closed: the manifest has no train rows.")
    return train


def candidate_train_items_only(
    items: Sequence[ManifestItemLike],
) -> list[ManifestItemLike]:
    """Return candidate-train rows while refusing validation leakage groups.

    The historical smoke's generic :func:`train_items_only` deliberately only
    filters the split.  The future decoder-candidate miner has a stronger
    contract: its causal labels must not contain a player/group also used by
    official validation.  Keeping that stricter rule in a dedicated helper
    avoids silently changing the already-reviewed smoke semantics.
    """
    train = train_items_only(items)
    validation = [item for item in items if str(item.split) == "validation"]
    train_groups = {leakage_group_key(item) for item in train}
    validation_groups = {leakage_group_key(item) for item in validation}
    overlapping_groups = sorted(train_groups & validation_groups)
    if overlapping_groups:
        raise RuntimeError(
            "Fail closed: train and validation rows overlap by leakage group: "
            f"{overlapping_groups!r}."
        )
    return train


def partition_train_groups(
    items: Sequence[ManifestItemLike],
    *,
    seed: int,
) -> tuple[dict[str, list[ManifestItemLike]], dict[str, object]]:
    """Create deterministic 70/15/15 partitions without leakage."""
    by_group: dict[str, list[ManifestItemLike]] = defaultdict(list)
    for item in items:
        if str(item.split) != "train":
            raise RuntimeError("Non-train item reached the group partitioner.")
        by_group[leakage_group_key(item)].append(item)
    group_stratum: dict[str, str] = {}
    for group_key, members in by_group.items():
        strata = {dataset_family(item.dataset_id) for item in members}
        if len(strata) != 1:
            raise RuntimeError(
                f"Fail closed: leakage group {group_key!r} spans unrelated corpora."
            )
        group_stratum[group_key] = next(iter(strata))

    groups_by_stratum: dict[str, list[str]] = defaultdict(list)
    for group_key, stratum in group_stratum.items():
        groups_by_stratum[stratum].append(group_key)

    assignments: dict[str, str] = {}
    for stratum, group_keys in sorted(groups_by_stratum.items()):
        ordered = sorted(
            group_keys,
            key=lambda group_key: hashlib.sha256(
                f"independent-note-v2:{int(seed)}:{stratum}:{group_key}".encode(
                    "utf-8"
                )
            ).hexdigest(),
        )
        if len(ordered) < 3:
            raise RuntimeError(
                f"Fail closed: {stratum} needs at least three leakage groups."
            )
        dev_count = max(1, int(round(len(ordered) * 0.15)))
        calibration_count = max(1, int(round(len(ordered) * 0.15)))
        if dev_count + calibration_count >= len(ordered):
            dev_count = calibration_count = 1
        fit_end = len(ordered) - dev_count - calibration_count
        for group_key in ordered[:fit_end]:
            assignments[group_key] = "fit"
        for group_key in ordered[fit_end : fit_end + dev_count]:
            assignments[group_key] = "dev"
        for group_key in ordered[fit_end + dev_count :]:
            assignments[group_key] = "calibration"

    partitions = {name: [] for name in DECODER_CANDIDATE_PARTITIONS}
    for item in items:
        partitions[assignments[leakage_group_key(item)]].append(item)
    group_sets = {
        name: {leakage_group_key(item) for item in selected}
        for name, selected in partitions.items()
    }
    if any(
        group_sets[left] & group_sets[right]
        for left, right in (
            ("fit", "dev"),
            ("fit", "calibration"),
            ("dev", "calibration"),
        )
    ):
        raise RuntimeError("Fail closed: train partitions overlap by leakage group.")

    datasets = {str(item.dataset_id) for item in items}
    for name, selected in partitions.items():
        if {str(item.dataset_id) for item in selected} != datasets:
            raise RuntimeError(f"Fail closed: {name} does not cover every corpus.")
    report = {
        "seed": int(seed),
        "strategy": DECODER_CANDIDATE_PARTITION_POLICY,
        "partitions": {
            name: {
                "rows": len(selected),
                "groups": len(group_sets[name]),
                "group_digest": canonical_digest(group_sets[name]),
                "source_digest": canonical_digest(
                    str(item.source_id) for item in selected
                ),
                "by_corpus": dict(sorted(Counter(
                    str(item.dataset_id) for item in selected
                ).items())),
            }
            for name, selected in partitions.items()
        },
    }
    return partitions, report


@dataclass(frozen=True)
class DecoderCandidateProvenance:
    """One immutable, persisted identity for a future candidate recording."""

    source_id: str
    dataset_id: str
    group_id: str
    capture_id: str
    leakage_group_key: str
    partition: str

    def __post_init__(self) -> None:
        for name in (
            "source_id", "dataset_id", "group_id", "capture_id",
            "leakage_group_key",
        ):
            _non_empty_string(getattr(self, name), name)
        if (
            not isinstance(self.partition, str)
            or self.partition not in DECODER_CANDIDATE_PARTITIONS
        ):
            raise ValueError(
                "partition must be one of "
                f"{list(DECODER_CANDIDATE_PARTITIONS)!r}."
            )

    @property
    def manifest_identity_key(self) -> tuple[str, str, str]:
        """Return the complete physical recording identity in the manifest."""
        return (self.dataset_id, self.source_id, self.capture_id)

    def as_json(self) -> dict[str, str]:
        return {
            "dataset_id": self.dataset_id,
            "source_id": self.source_id,
            "group_id": self.group_id,
            "capture_id": self.capture_id,
            "leakage_group_key": self.leakage_group_key,
            "partition": self.partition,
        }

    @classmethod
    def from_train_item(
        cls,
        item: ManifestItemLike,
        *,
        partition: str,
    ) -> "DecoderCandidateProvenance":
        if str(item.split) != "train":
            raise RuntimeError("Fail closed: candidate provenance requires split=train.")
        return cls(
            source_id=_non_empty_string(item.source_id, "source_id"),
            dataset_id=_non_empty_string(item.dataset_id, "dataset_id"),
            group_id=_non_empty_string(item.group_id, "group_id"),
            capture_id=_non_empty_string(item.capture_id, "capture_id"),
            leakage_group_key=leakage_group_key(item),
            partition=partition,
        )


def _manifest_sha256(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("manifest_sha256 must be a lowercase SHA-256 digest.")
    return value


@dataclass(frozen=True)
class DecoderCandidatePartitionPlan:
    """Versioned preassignment which must match the exact train manifest."""

    manifest_sha256: str
    seed: int
    records: tuple[DecoderCandidateProvenance, ...]

    def __post_init__(self) -> None:
        _manifest_sha256(self.manifest_sha256)
        if type(self.seed) is not int:
            raise ValueError("seed must be a JSON-native integer.")
        if type(self.records) is not tuple or not self.records:
            raise ValueError("records must be a non-empty immutable tuple.")
        expected = tuple(sorted(
            self.records,
            key=lambda record: (
                record.dataset_id,
                record.source_id,
                record.capture_id,
            ),
        ))
        if self.records != expected:
            raise ValueError("partition-plan records must be canonically sorted.")
        keys = [record.manifest_identity_key for record in self.records]
        if len(set(keys)) != len(keys):
            raise ValueError(
                "partition-plan records have duplicate "
                "dataset/source/capture identities."
            )
        group_assignments: dict[str, str] = {}
        for record in self.records:
            assigned = group_assignments.setdefault(
                record.leakage_group_key, record.partition
            )
            if assigned != record.partition:
                raise ValueError(
                    "one leakage group cannot span candidate partitions."
                )

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": DECODER_CANDIDATE_PARTITION_SCHEMA_VERSION,
            "purpose": DECODER_CANDIDATE_PARTITION_PURPOSE,
            "locked_test_used": False,
            "manifest_sha256": self.manifest_sha256,
            "partition_policy": DECODER_CANDIDATE_PARTITION_POLICY,
            "seed": self.seed,
            "records": [record.as_json() for record in self.records],
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> "DecoderCandidatePartitionPlan":
        required = {
            "schema_version", "purpose", "locked_test_used", "manifest_sha256",
            "partition_policy", "seed", "records",
        }
        if not isinstance(payload, Mapping) or set(payload) != required:
            raise ValueError("partition plan has unexpected or missing top-level fields.")
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"]
            != DECODER_CANDIDATE_PARTITION_SCHEMA_VERSION
        ):
            raise ValueError("Unsupported decoder candidate partition schema.")
        if payload["purpose"] != DECODER_CANDIDATE_PARTITION_PURPOSE:
            raise ValueError("Invalid decoder candidate partition purpose.")
        if payload["locked_test_used"] is not False:
            raise ValueError("Fail closed: candidate partition plan touches locked test.")
        if payload["partition_policy"] != DECODER_CANDIDATE_PARTITION_POLICY:
            raise ValueError("Unsupported decoder candidate partition policy.")
        records_payload = payload["records"]
        if not isinstance(records_payload, list):
            raise ValueError("partition-plan records must be a JSON list.")
        record_keys = {
            "dataset_id", "source_id", "group_id", "capture_id",
            "leakage_group_key", "partition",
        }
        records: list[DecoderCandidateProvenance] = []
        for value in records_payload:
            if not isinstance(value, dict) or set(value) != record_keys:
                raise ValueError("partition-plan record schema is invalid.")
            records.append(DecoderCandidateProvenance(**value))
        return cls(
            manifest_sha256=_manifest_sha256(payload["manifest_sha256"]),
            seed=payload["seed"],
            records=tuple(records),
        )

    def require_matches_manifest_items(
        self,
        items: Sequence[ManifestItemLike],
        *,
        expected_manifest_sha256: str,
    ) -> None:
        if self.manifest_sha256 != _manifest_sha256(expected_manifest_sha256):
            raise RuntimeError("Fail closed: candidate partition manifest SHA-256 mismatch.")
        expected = build_decoder_candidate_partition_plan(
            items,
            manifest_sha256=expected_manifest_sha256,
            seed=self.seed,
        )
        if self.records != expected.records:
            raise RuntimeError(
                "Fail closed: candidate partition plan does not match train manifest."
            )

    def provenance_for_train_item(
        self,
        item: ManifestItemLike,
    ) -> DecoderCandidateProvenance:
        """Resolve one train item only through this preassigned plan.

        A collector must receive the returned record, never a caller-created
        partition value.  The full identity is re-derived from the manifest
        item, so a changed group, capture, source, dataset, or leakage key is
        rejected before the decoder can record a row.
        """
        if str(item.split) != "train":
            raise RuntimeError("Fail closed: candidate collection requires split=train.")
        identity = (
            _non_empty_string(item.dataset_id, "dataset_id"),
            _non_empty_string(item.source_id, "source_id"),
            _non_empty_string(item.capture_id, "capture_id"),
        )
        matching = [
            record for record in self.records
            if record.manifest_identity_key == identity
        ]
        if len(matching) != 1:
            raise RuntimeError(
                "Fail closed: train item is absent from the candidate partition plan."
            )
        record = matching[0]
        observed = DecoderCandidateProvenance.from_train_item(
            item, partition=record.partition
        )
        if observed != record:
            raise RuntimeError(
                "Fail closed: train item provenance differs from the partition plan."
            )
        return record


def build_decoder_candidate_partition_plan(
    items: Sequence[ManifestItemLike],
    *,
    manifest_sha256: str,
    seed: int,
) -> DecoderCandidatePartitionPlan:
    """Build but do not persist a deterministic plan from a complete manifest.

    This function deliberately applies :func:`train_items_only` itself.  A
    future miner should prefer :func:`build_decoder_candidate_partition_plan_from_manifest`
    so the SHA-256 comes from the file actually read, rather than from a
    caller-supplied declaration.
    """
    _manifest_sha256(manifest_sha256)
    if not items:
        raise RuntimeError("Fail closed: candidate manifest has no items.")
    train_items = candidate_train_items_only(items)
    partitions, _ = partition_train_groups(train_items, seed=seed)
    records = tuple(sorted(
        (
            DecoderCandidateProvenance.from_train_item(item, partition=partition)
            for partition, partition_items in partitions.items()
            for item in partition_items
        ),
        key=lambda record: (
            record.dataset_id,
            record.source_id,
            record.capture_id,
        ),
    ))
    return DecoderCandidatePartitionPlan(
        manifest_sha256=manifest_sha256,
        seed=seed,
        records=records,
    )


@dataclass(frozen=True)
class PersistedDecoderCandidatePartitionPlan:
    """A strict plan loaded from or atomically written to one JSON file."""

    path: Path
    sha256: str
    plan: DecoderCandidatePartitionPlan

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise ValueError("path must be a pathlib.Path.")
        _manifest_sha256(self.sha256)
        if not isinstance(self.plan, DecoderCandidatePartitionPlan):
            raise ValueError("plan must be DecoderCandidatePartitionPlan.")


def _canonical_partition_plan_bytes(
    plan: DecoderCandidatePartitionPlan,
) -> bytes:
    if not isinstance(plan, DecoderCandidatePartitionPlan):
        raise ValueError("plan must be DecoderCandidatePartitionPlan.")
    return (
        json.dumps(
            plan.as_json(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def decoder_candidate_partition_plan_sha256(
    plan: DecoderCandidatePartitionPlan,
) -> str:
    """Return the SHA-256 of the canonical immutable plan representation."""
    return hashlib.sha256(_canonical_partition_plan_bytes(plan)).hexdigest()


def write_decoder_candidate_partition_plan(
    path: Path,
    plan: DecoderCandidatePartitionPlan,
) -> PersistedDecoderCandidatePartitionPlan:
    """Persist one canonical plan atomically, without generating any rows.

    The caller is responsible for deciding when a real plan may be created.
    This helper only makes its JSON serialization reproducible and ensures that
    a partially written plan can never be mistaken for a valid preassignment.
    """
    target = Path(path).expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError(
            "Fail closed: candidate partition plan already exists and is immutable."
        )
    if not target.parent.is_dir():
        raise ValueError("partition-plan parent directory does not exist.")
    target = target.resolve(strict=False)
    payload = _canonical_partition_plan_bytes(plan)
    temporary_path: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Link creation is exclusive: unlike os.replace(), it cannot
            # silently replace a reviewed preassignment if a second invocation
            # races or merely reuses the same output path.
            os.link(temporary_path, target)
        except FileExistsError as exc:
            raise FileExistsError(
                "Fail closed: candidate partition plan already exists and is immutable."
            ) from exc
        temporary_path.unlink()
        temporary_path = None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    # Return only a fresh parse of the bytes that reached their immutable
    # destination.  An in-memory plan is never a collector capability.
    return load_decoder_candidate_partition_plan(target)


def load_decoder_candidate_partition_plan(
    path: Path,
) -> PersistedDecoderCandidatePartitionPlan:
    """Load only a complete canonical candidate partition plan file."""
    resolved = Path(path).resolve(strict=True)
    raw_bytes = resolved.read_bytes()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate partition plan is not valid UTF-8 JSON.") from exc
    plan = DecoderCandidatePartitionPlan.from_json(payload)
    if raw_bytes != _canonical_partition_plan_bytes(plan):
        raise ValueError("candidate partition plan is not canonical JSON.")
    persisted = PersistedDecoderCandidatePartitionPlan(
        path=resolved,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        plan=plan,
    )
    _register_persisted_partition_plan(persisted)
    return persisted


@dataclass(frozen=True)
class ValidatedDecoderCandidatePartition:
    """Legacy identity-only validation for plan preparation and inspection.

    It remains useful to inspect a plan without importing the data stack.  It
    intentionally cannot construct a collector: that requires
    :class:`ValidatedDecoderCandidateManifestSnapshot`, which retains the exact
    full manifest items holding audio and label paths.
    """

    plan: DecoderCandidatePartitionPlan
    manifest_sha256: str
    _validation_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._validation_token is not _VALIDATED_PARTITION_TOKEN:
            raise ValueError(
                "validated candidate partition must come from exact manifest validation."
            )
        if self.plan.manifest_sha256 != _manifest_sha256(self.manifest_sha256):
            raise ValueError("validated candidate partition manifest mismatch.")

    def provenance_for_train_item(
        self,
        item: ManifestItemLike,
    ) -> DecoderCandidateProvenance:
        return self.plan.provenance_for_train_item(item)


@dataclass(frozen=True)
class ValidatedDecoderCandidateManifestSnapshot:
    """A plan bound to the exact full item objects which will open data.

    Object identity is intentional.  A clone with the same source/capture IDs
    but substituted ``audio_path`` or ``labels_path`` is not an item from the
    hash-validated snapshot and is refused before a collector or corpus can be
    created.
    """

    plan: DecoderCandidatePartitionPlan
    persisted_plan: PersistedDecoderCandidatePartitionPlan = field(
        repr=False, compare=False
    )
    manifest_sha256: str
    _items: tuple[ManifestItemLike, ...] = field(repr=False, compare=False)
    _validation_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._validation_token is not _VALIDATED_SNAPSHOT_TOKEN:
            raise ValueError(
                "validated candidate snapshot must come from exact snapshot validation."
            )
        if self.plan.manifest_sha256 != _manifest_sha256(self.manifest_sha256):
            raise ValueError("validated candidate snapshot manifest mismatch.")
        if not isinstance(self.persisted_plan, PersistedDecoderCandidatePartitionPlan):
            raise ValueError(
                "validated candidate snapshot requires a persisted partition plan."
            )
        _require_persisted_partition_plan(self.persisted_plan)
        if self.persisted_plan.plan != self.plan:
            raise ValueError("validated candidate snapshot plan differs from persisted plan.")
        if self.persisted_plan.sha256 != decoder_candidate_partition_plan_sha256(
            self.plan
        ):
            raise ValueError("validated candidate snapshot partition-plan digest mismatch.")
        if type(self._items) is not tuple or not self._items:
            raise ValueError("validated candidate snapshot must retain immutable items.")

    @property
    def items(self) -> tuple[ManifestItemLike, ...]:
        """Return the exact objects parsed from the hash-validated CSV bytes."""
        return self._items

    @property
    def partition_plan_sha256(self) -> str:
        """Digest which every drained recording batch must carry."""
        return self.persisted_plan.sha256

    @property
    def train_items(self) -> tuple[ManifestItemLike, ...]:
        """Return only snapshot objects that the train-only plan covers."""
        return tuple(item for item in self._items if str(item.split) == "train")

    def require_snapshot_item(self, item: ManifestItemLike) -> ManifestItemLike:
        """Refuse every object which is not literally from this snapshot."""
        if not any(item is snapshot_item for snapshot_item in self._items):
            raise RuntimeError(
                "Fail closed: candidate item is not an object from the validated "
                "manifest snapshot."
            )
        return item

    def provenance_for_snapshot_item(
        self,
        item: ManifestItemLike,
    ) -> DecoderCandidateProvenance:
        """Resolve a train item only after its snapshot object identity is proven."""
        snapshot_item = self.require_snapshot_item(item)
        return self.plan.provenance_for_train_item(snapshot_item)


def build_decoder_candidate_partition_plan_from_snapshot(
    snapshot: ManifestSnapshotLike,
    *,
    seed: int,
) -> DecoderCandidatePartitionPlan:
    """Build a plan from one already byte-hashed full manifest snapshot."""
    _require_loaded_manifest_snapshot(snapshot)
    manifest_sha256 = _manifest_sha256(snapshot.manifest_sha256)
    return build_decoder_candidate_partition_plan(
        tuple(snapshot.items), manifest_sha256=manifest_sha256, seed=seed
    )


def validate_decoder_candidate_partition_plan_against_snapshot(
    persisted_plan: PersistedDecoderCandidatePartitionPlan,
    snapshot: ManifestSnapshotLike,
) -> ValidatedDecoderCandidateManifestSnapshot:
    """Bind an immutable persisted plan to exact full manifest objects.

    This is intentionally the only factory which creates a collector-capable
    validation.  A caller may inspect or construct an in-memory plan, but it
    cannot bind that plan to decoder collection until the canonical bytes have
    been written without overwrite and loaded back from disk.
    """
    if not isinstance(persisted_plan, PersistedDecoderCandidatePartitionPlan):
        raise ValueError(
            "persisted_plan must be PersistedDecoderCandidatePartitionPlan."
        )
    _require_persisted_partition_plan(persisted_plan)
    plan = persisted_plan.plan
    _require_loaded_manifest_snapshot(snapshot)
    manifest_sha256 = _manifest_sha256(snapshot.manifest_sha256)
    items = tuple(snapshot.items)
    if not items:
        raise RuntimeError("Fail closed: candidate manifest snapshot has no items.")
    plan.require_matches_manifest_items(
        items, expected_manifest_sha256=manifest_sha256
    )
    validated = ValidatedDecoderCandidateManifestSnapshot(
        plan=plan,
        persisted_plan=persisted_plan,
        manifest_sha256=manifest_sha256,
        _items=items,
        _validation_token=_VALIDATED_SNAPSHOT_TOKEN,
    )
    _register_validated_manifest_snapshot(validated)
    return validated


def build_decoder_candidate_partition_plan_from_manifest(
    path: Path,
    *,
    seed: int,
) -> DecoderCandidatePartitionPlan:
    """Build a plan from all rows and the real byte digest of one manifest."""
    items, manifest_sha256 = load_decoder_candidate_manifest(path)
    return build_decoder_candidate_partition_plan(
        items,
        manifest_sha256=manifest_sha256,
        seed=seed,
    )


def validate_decoder_candidate_partition_plan_from_manifest(
    plan: DecoderCandidatePartitionPlan,
    path: Path,
) -> ValidatedDecoderCandidatePartition:
    """Fail closed unless a plan covers the exact on-disk train manifest."""
    if not isinstance(plan, DecoderCandidatePartitionPlan):
        raise ValueError("plan must be DecoderCandidatePartitionPlan.")
    items, manifest_sha256 = load_decoder_candidate_manifest(path)
    plan.require_matches_manifest_items(
        items,
        expected_manifest_sha256=manifest_sha256,
    )
    return ValidatedDecoderCandidatePartition(
        plan=plan,
        manifest_sha256=manifest_sha256,
        _validation_token=_VALIDATED_PARTITION_TOKEN,
    )
