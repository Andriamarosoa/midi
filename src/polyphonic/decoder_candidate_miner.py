"""Fail-closed preflight context for a future decoder-candidate miner.

This is deliberately not an executable miner: it contains no model loading,
inference, decoding loop, artifact export, or command-line entry point.  It
only binds the persisted train-only plan to the one full manifest snapshot
which yields the exact ``ManifestItem`` objects later used to open audio and
labels.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .data import ManifestItem, ManifestSnapshot, PolyphonicCorpus, load_manifest_snapshot
from .decoder_candidate_asset_evidence import (
    PersistedDecoderCandidateAssetEvidence,
    build_decoder_candidate_asset_evidence,
    load_decoder_candidate_asset_evidence,
    validate_decoder_candidate_asset_evidence,
    verify_decoder_candidate_audio_asset_for_item,
    verify_decoder_candidate_label_asset_for_item,
    write_decoder_candidate_asset_evidence,
)
from .decoder_candidate_mining import DecoderCandidateCollector
from .decoder_candidate_labels import (
    CausalCandidateLabelBatch,
    DecoderCandidateMiningCounters,
)
from .decoder_candidate_provenance import (
    DECODER_CANDIDATE_PARTITIONS,
    DecoderCandidatePartitionPlan,
    PersistedDecoderCandidatePartitionPlan,
    ValidatedDecoderCandidateManifestSnapshot,
    build_decoder_candidate_partition_plan_from_snapshot,
    load_decoder_candidate_partition_plan,
    _require_loaded_manifest_snapshot,
    _require_persisted_partition_plan,
    _require_validated_manifest_snapshot,
    validate_decoder_candidate_partition_plan_against_snapshot,
    write_decoder_candidate_partition_plan,
)


@dataclass(frozen=True)
class DecoderCandidateMiningContext:
    """The only object a future train-only miner may use to open recordings."""

    snapshot: ManifestSnapshot
    persisted_plan: PersistedDecoderCandidatePartitionPlan
    validated_snapshot: ValidatedDecoderCandidateManifestSnapshot
    persisted_asset_evidence: PersistedDecoderCandidateAssetEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ManifestSnapshot):
            raise ValueError("snapshot must be ManifestSnapshot.")
        _require_loaded_manifest_snapshot(self.snapshot)
        if not isinstance(self.persisted_plan, PersistedDecoderCandidatePartitionPlan):
            raise ValueError("persisted_plan must be PersistedDecoderCandidatePartitionPlan.")
        _require_persisted_partition_plan(self.persisted_plan)
        if not isinstance(
            self.validated_snapshot, ValidatedDecoderCandidateManifestSnapshot
        ):
            raise ValueError(
                "validated_snapshot must be ValidatedDecoderCandidateManifestSnapshot."
            )
        _require_validated_manifest_snapshot(self.validated_snapshot)
        if self.persisted_plan.plan != self.validated_snapshot.plan:
            raise ValueError("persisted plan and validated snapshot plan differ.")
        if (
            self.persisted_plan.sha256
            != self.validated_snapshot.partition_plan_sha256
        ):
            raise ValueError("persisted plan digest and validated snapshot differ.")
        if self.snapshot.manifest_sha256 != self.validated_snapshot.manifest_sha256:
            raise ValueError("snapshot and validated plan manifest digests differ.")
        if len(self.snapshot.items) != len(self.validated_snapshot.items):
            raise ValueError("snapshot and validated item counts differ.")
        if any(
            snapshot_item is not validated_item
            for snapshot_item, validated_item in zip(
                self.snapshot.items, self.validated_snapshot.items
            )
        ):
            raise ValueError(
                "validated items must be the exact objects from the manifest snapshot."
            )
        if self.persisted_asset_evidence is not None:
            validate_decoder_candidate_asset_evidence(
                self.persisted_asset_evidence, self.validated_snapshot
            )

    def items_for_partition(self, partition: str) -> tuple[ManifestItem, ...]:
        """Return only exact train snapshot objects preassigned to one partition."""
        if partition not in DECODER_CANDIDATE_PARTITIONS:
            raise ValueError(
                "partition must be one of "
                f"{list(DECODER_CANDIDATE_PARTITIONS)!r}."
            )
        selected: list[ManifestItem] = []
        for item in self.snapshot.items:
            if item.split != "train":
                continue
            record = self.validated_snapshot.provenance_for_snapshot_item(item)
            if record.partition == partition:
                selected.append(item)
        return tuple(selected)

    def collector_for_item(
        self,
        item: ManifestItem,
        *,
        maximum_attempts: int = 4096,
    ) -> DecoderCandidateCollector:
        """Build a bounded collector only for an exact train snapshot item."""
        _require_persisted_partition_plan(self.persisted_plan)
        snapshot_item = self.validated_snapshot.require_snapshot_item(item)
        if not isinstance(snapshot_item, ManifestItem):
            raise AssertionError("full mining context retained a non-ManifestItem.")
        return DecoderCandidateCollector(
            validated_snapshot=self.validated_snapshot,
            manifest_item=snapshot_item,
            maximum_attempts=maximum_attempts,
        )

    def aggregate_partition_label_batches(
        self,
        partition: str,
        batches: Iterable[CausalCandidateLabelBatch],
    ) -> DecoderCandidateMiningCounters:
        """Verify one complete preassigned partition before any future artifact.

        A caller cannot combine a convenient subset of recordings, replay one
        capture twice, or mix batches from another plan/manifest.  This method
        only produces in-memory counters; it intentionally does not write a
        candidate artifact or authorize training.
        """
        if partition not in DECODER_CANDIDATE_PARTITIONS:
            raise ValueError(
                "partition must be one of "
                f"{list(DECODER_CANDIDATE_PARTITIONS)!r}."
            )
        _require_persisted_partition_plan(self.persisted_plan)
        values = tuple(batches)
        counters = DecoderCandidateMiningCounters.from_batches(values)
        if counters.manifest_sha256 != self.snapshot.manifest_sha256:
            raise RuntimeError("Fail closed: label batches use another manifest snapshot.")
        if counters.partition_plan_sha256 != self.persisted_plan.sha256:
            raise RuntimeError("Fail closed: label batches use another partition plan.")
        if any(batch.partition != partition for batch in values):
            raise RuntimeError("Fail closed: label batches mix candidate partitions.")
        expected_identities = tuple(sorted(
            (
                item.dataset_id,
                item.source_id,
                item.capture_id,
            )
            for item in self.items_for_partition(partition)
        ))
        if counters.recording_identities != expected_identities:
            raise RuntimeError(
                "Fail closed: label batches do not cover exactly the preassigned "
                "snapshot recordings for this partition."
            )
        return counters

    @contextmanager
    def open_recording(self, item: ManifestItem) -> Iterator[PolyphonicCorpus]:
        """Open audio and labels through the same snapshot object as the collector.

        A future decoder loop must obtain both its corpus and collector from this
        context for the same ``item``.  This is intentionally a context manager
        so archive/mmap resources still close deterministically after a replay.
        """
        snapshot_item = self.validated_snapshot.require_snapshot_item(item)
        _require_persisted_partition_plan(self.persisted_plan)
        if not isinstance(snapshot_item, ManifestItem):
            raise AssertionError("full mining context retained a non-ManifestItem.")
        # Keep this opening path train-only as well: a future caller cannot
        # inspect an official validation item through the same context and then
        # accidentally pair it with an unrelated collector.
        self.validated_snapshot.provenance_for_snapshot_item(snapshot_item)
        if self.persisted_asset_evidence is None:
            raise RuntimeError(
                "Fail closed: opening a candidate recording requires persisted "
                "audio/label asset evidence."
            )
        def verify_labels_at_load(lazy_item: ManifestItem) -> None:
            if lazy_item is not snapshot_item:
                raise RuntimeError(
                    "Fail closed: corpus requested labels for another manifest item."
                )
            verify_decoder_candidate_label_asset_for_item(
                self.persisted_asset_evidence,
                self.validated_snapshot,
                lazy_item,
            )

        def verify_audio_at_load(lazy_item: ManifestItem) -> None:
            if lazy_item is not snapshot_item:
                raise RuntimeError(
                    "Fail closed: corpus requested audio for another manifest item."
                )
            verify_decoder_candidate_audio_asset_for_item(
                self.persisted_asset_evidence,
                self.validated_snapshot,
                lazy_item,
            )

        with PolyphonicCorpus(
            [snapshot_item],
            label_verifier=verify_labels_at_load,
            asset_verifier=verify_audio_at_load,
        ) as corpus:
            if corpus.items[0] is not snapshot_item:
                raise AssertionError("corpus did not retain the validated snapshot item.")
            yield corpus


def load_decoder_candidate_mining_context(
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    asset_evidence_path: Path | None = None,
) -> DecoderCandidateMiningContext:
    """Load a persisted plan and validate it before any future decode can start."""
    snapshot = load_manifest_snapshot(manifest_path)
    persisted_plan = load_decoder_candidate_partition_plan(partition_plan_path)
    validated_snapshot = validate_decoder_candidate_partition_plan_against_snapshot(
        persisted_plan, snapshot
    )
    persisted_asset_evidence = (
        load_decoder_candidate_asset_evidence(asset_evidence_path)
        if asset_evidence_path is not None
        else None
    )
    return DecoderCandidateMiningContext(
        snapshot=snapshot,
        persisted_plan=persisted_plan,
        validated_snapshot=validated_snapshot,
        persisted_asset_evidence=persisted_asset_evidence,
    )


def create_decoder_candidate_mining_context(
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    seed: int,
) -> DecoderCandidateMiningContext:
    """Create, persist, reload, and revalidate a plan without mining anything.

    This future-only preflight is the required first action before a proposed
    train-only replay.  It never opens an audio or label path; callers must
    separately obtain approval before invoking it on the real manifest.
    """
    snapshot = load_manifest_snapshot(manifest_path)
    plan: DecoderCandidatePartitionPlan = (
        build_decoder_candidate_partition_plan_from_snapshot(snapshot, seed=seed)
    )
    persisted_plan = write_decoder_candidate_partition_plan(
        partition_plan_path, plan
    )
    # Re-read the bytes that were actually persisted; never trust an in-memory
    # plan as a substitute for the future miner's file-backed preassignment.
    reloaded_plan = load_decoder_candidate_partition_plan(persisted_plan.path)
    validated_snapshot = validate_decoder_candidate_partition_plan_against_snapshot(
        reloaded_plan, snapshot
    )
    return DecoderCandidateMiningContext(
        snapshot=snapshot,
        persisted_plan=reloaded_plan,
        validated_snapshot=validated_snapshot,
    )


def pre_register_decoder_candidate_asset_evidence(
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    asset_evidence_path: Path,
) -> DecoderCandidateMiningContext:
    """Hash train assets once and persist their proof without decoding them.

    This is intentionally distinct from a candidate-mining run: it only hashes
    manifest-referenced files, writes immutable evidence, then returns a
    context which will re-hash an item immediately before any future open.
    """
    context = load_decoder_candidate_mining_context(
        manifest_path=manifest_path,
        partition_plan_path=partition_plan_path,
    )
    evidence = build_decoder_candidate_asset_evidence(context.validated_snapshot)
    persisted = write_decoder_candidate_asset_evidence(asset_evidence_path, evidence)
    return DecoderCandidateMiningContext(
        snapshot=context.snapshot,
        persisted_plan=context.persisted_plan,
        validated_snapshot=context.validated_snapshot,
        persisted_asset_evidence=persisted,
    )


__all__ = [
    "DecoderCandidateMiningContext",
    "create_decoder_candidate_mining_context",
    "load_decoder_candidate_mining_context",
    "pre_register_decoder_candidate_asset_evidence",
]
