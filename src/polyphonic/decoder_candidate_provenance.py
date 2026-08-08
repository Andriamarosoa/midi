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
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Mapping, Protocol, Sequence


DECODER_CANDIDATE_PARTITION_SCHEMA_VERSION = 1
DECODER_CANDIDATE_PARTITION_PURPOSE = "decoder_candidate_train_only_partition"
DECODER_CANDIDATE_PARTITION_POLICY = (
    "corpus_aware_leakage_group_hash_70_15_15"
)
DECODER_CANDIDATE_PARTITIONS = ("fit", "dev", "calibration")
_VALIDATED_PARTITION_TOKEN = object()


class ManifestItemLike(Protocol):
    """Metadata required for group-safe candidate provenance."""

    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    capture_id: str
    split: str


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
    train_items = train_items_only(items)
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
class ValidatedDecoderCandidatePartition:
    """A partition plan proven against one exact manifest before collection.

    The object is intentionally created only by
    :func:`validate_decoder_candidate_partition_plan_from_manifest`.  Future
    mining code must use :meth:`provenance_for_train_item` to construct each
    collector, which prevents it from inventing a partition or capture record.
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
