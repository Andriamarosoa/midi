from __future__ import annotations

import csv
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from src.polyphonic.data import ManifestSnapshot, load_manifest, load_manifest_snapshot
from src.polyphonic.decoder_candidate_miner import (
    DecoderCandidateMiningContext,
    create_decoder_candidate_mining_context,
    load_decoder_candidate_mining_context,
)
from src.polyphonic.decoder_candidate_asset_evidence import (
    build_decoder_candidate_asset_evidence,
    write_decoder_candidate_asset_evidence,
)
from src.polyphonic.decoder_candidate_mining import DecoderCandidateCollector
from src.polyphonic.decoder_candidate_labels import (
    label_emitted_decoder_candidates,
)
from src.polyphonic.decoder_candidate_provenance import (
    PersistedDecoderCandidatePartitionPlan,
    build_decoder_candidate_partition_plan_from_snapshot,
    load_decoder_candidate_partition_plan,
    validate_decoder_candidate_partition_plan_against_snapshot,
    write_decoder_candidate_partition_plan,
)


def _write_full_manifest(path: Path, *, path_suffix: str = "original") -> None:
    fields = (
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id",
        "license_id",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(3):
            writer.writerow({
                "source_id": f"source-{index}",
                "dataset_id": "unit-corpus",
                "player_id": f"player-{index}",
                "group_id": f"group-{index}",
                "split": "train",
                "audio_path": f"audio-{path_suffix}-{index}.wav",
                "audio_member": "" if index != 1 else "capture.wav",
                "labels_path": f"labels-{path_suffix}-{index}.npz",
                "capture_id": f"capture-{index}",
                "license_id": "unit-test",
            })
        writer.writerow({
            "source_id": "validation-source",
            "dataset_id": "unit-corpus",
            "player_id": "validation-player",
            "group_id": "validation-group",
            "split": "validation",
            "audio_path": f"audio-{path_suffix}-validation.wav",
            "audio_member": "",
            "labels_path": f"labels-{path_suffix}-validation.npz",
            "capture_id": "validation-capture",
            "license_id": "unit-test",
        })


class DecoderCandidateSnapshotProtocolTests(unittest.TestCase):
    def test_snapshot_hashes_the_same_bytes_that_build_full_manifest_items(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            _write_full_manifest(manifest_path)
            raw_bytes = manifest_path.read_bytes()

            snapshot = load_manifest_snapshot(manifest_path)

            self.assertEqual(snapshot.manifest_path, manifest_path.resolve())
            self.assertEqual(
                snapshot.manifest_sha256, hashlib.sha256(raw_bytes).hexdigest()
            )
            self.assertIsInstance(snapshot.items, tuple)
            self.assertEqual(snapshot.items[0].audio_path, root / "audio-original-0.wav")
            self.assertEqual(snapshot.items[1].audio_member, "capture.wav")
            self.assertEqual(snapshot.items[2].labels_path, root / "labels-original-2.npz")
            self.assertEqual(load_manifest(manifest_path), list(snapshot.items))

    def test_snapshot_capability_rejects_direct_construction_and_structural_lookalikes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            with self.assertRaisesRegex(ValueError, "created by load_manifest_snapshot"):
                ManifestSnapshot(
                    manifest_path=context.snapshot.manifest_path,
                    manifest_sha256=context.snapshot.manifest_sha256,
                    items=context.snapshot.items,
                    _decoder_candidate_snapshot_token=object(),
                )
            lookalike = SimpleNamespace(
                manifest_sha256=context.snapshot.manifest_sha256,
                items=context.snapshot.items,
            )
            with self.assertRaisesRegex(RuntimeError, "load_manifest_snapshot"):
                validate_decoder_candidate_partition_plan_against_snapshot(
                    context.persisted_plan, lookalike
                )
            copied_with_substituted_paths = replace(
                context.snapshot,
                items=tuple(
                    replace(
                        item,
                        audio_path=root / f"forged-{index}.wav",
                        labels_path=root / f"forged-{index}.npz",
                    )
                    for index, item in enumerate(context.snapshot.items)
                ),
            )
            with self.assertRaisesRegex(RuntimeError, "loader-attested"):
                validate_decoder_candidate_partition_plan_against_snapshot(
                    context.persisted_plan,
                    copied_with_substituted_paths,
                )
            with self.assertRaisesRegex(RuntimeError, "loader-attested"):
                DecoderCandidateMiningContext(
                    snapshot=copied_with_substituted_paths,
                    persisted_plan=context.persisted_plan,
                    validated_snapshot=context.validated_snapshot,
                )
            copied_validated_snapshot = replace(
                context.validated_snapshot,
                _items=tuple(
                    replace(
                        item,
                        audio_path=root / f"forged-validated-{index}.wav",
                        labels_path=root / f"forged-validated-{index}.npz",
                    )
                    for index, item in enumerate(context.snapshot.items)
                ),
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                DecoderCandidateCollector(
                    validated_snapshot=copied_validated_snapshot,
                    manifest_item=copied_validated_snapshot.items[0],
                )

    def test_snapshot_resolves_relative_paths_from_manifest_not_process_directory(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_directory = root / "manifest-directory"
            process_directory = root / "process-directory"
            manifest_directory.mkdir()
            process_directory.mkdir()
            manifest_path = manifest_directory / "manifest.csv"
            _write_full_manifest(manifest_path)
            (process_directory / "audio-original-0.wav").touch()
            previous_directory = Path.cwd()
            try:
                os.chdir(process_directory)
                snapshot = load_manifest_snapshot(manifest_path)
            finally:
                os.chdir(previous_directory)
            self.assertEqual(
                snapshot.items[0].audio_path,
                manifest_directory / "audio-original-0.wav",
            )

    def test_persisted_context_reuses_exact_snapshot_items_for_collector_and_corpus(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            evidence_path = root / "asset-evidence.json"
            _write_full_manifest(manifest_path)
            for index in range(3):
                (root / f"audio-original-{index}.wav").write_bytes(b"audio")
                (root / f"labels-original-{index}.npz").write_bytes(b"labels")

            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            write_decoder_candidate_asset_evidence(
                evidence_path,
                build_decoder_candidate_asset_evidence(context.validated_snapshot),
            )
            reloaded = load_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                asset_evidence_path=evidence_path,
            )

            self.assertEqual(context.persisted_plan, reloaded.persisted_plan)
            self.assertEqual(
                load_decoder_candidate_partition_plan(plan_path), context.persisted_plan
            )
            all_partition_items = tuple(
                item
                for partition in ("fit", "dev", "calibration")
                for item in reloaded.items_for_partition(partition)
            )
            self.assertEqual(len(all_partition_items), 3)
            for item in all_partition_items:
                self.assertTrue(any(item is original for original in reloaded.snapshot.items))
                collector = reloaded.collector_for_item(item, maximum_attempts=2)
                self.assertEqual(collector.source_id, item.source_id)

            item = all_partition_items[0]
            with mock.patch(
                "src.polyphonic.decoder_candidate_miner.PolyphonicCorpus"
            ) as corpus_type:
                corpus = corpus_type.return_value.__enter__.return_value
                corpus.items = [item]
                with reloaded.open_recording(item) as opened:
                    self.assertIs(opened, corpus)
                corpus_type.assert_called_once_with([item])

    def test_clone_with_identical_ids_but_substituted_paths_is_refused_before_collection(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            item = context.items_for_partition("fit")[0]
            clone = replace(
                item,
                audio_path=root / "substituted.wav",
                labels_path=root / "substituted.npz",
            )

            with self.assertRaisesRegex(RuntimeError, "not an object"):
                context.collector_for_item(clone)
            with self.assertRaisesRegex(RuntimeError, "not an object"):
                with context.open_recording(clone):
                    self.fail("a substituted item must be refused before opening data")
            validation_item = next(
                candidate
                for candidate in context.snapshot.items
                if candidate.split == "validation"
            )
            with self.assertRaisesRegex(RuntimeError, "requires split=train"):
                with context.open_recording(validation_item):
                    self.fail("validation data must never open through mining context")

    def test_changed_manifest_paths_fail_before_reusing_persisted_plan(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path, path_suffix="original")
            create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            _write_full_manifest(manifest_path, path_suffix="substituted")

            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                load_decoder_candidate_mining_context(
                    manifest_path=manifest_path,
                    partition_plan_path=plan_path,
                )

    def test_noncanonical_persisted_plan_is_refused(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            plan_path.write_bytes(plan_path.read_bytes() + b"\n")

            with self.assertRaisesRegex(ValueError, "canonical JSON"):
                load_decoder_candidate_partition_plan(plan_path)

    def test_persisted_plan_is_immutable_and_cannot_be_silently_replaced(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )

            with self.assertRaisesRegex(FileExistsError, "immutable"):
                create_decoder_candidate_mining_context(
                    manifest_path=manifest_path,
                    partition_plan_path=plan_path,
                    seed=48,
                )

    def test_collector_capability_cannot_be_created_from_an_in_memory_or_forged_plan(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            snapshot = load_manifest_snapshot(manifest_path)
            plan = build_decoder_candidate_partition_plan_from_snapshot(
                snapshot, seed=47
            )
            with self.assertRaisesRegex(ValueError, "PersistedDecoderCandidatePartitionPlan"):
                validate_decoder_candidate_partition_plan_against_snapshot(plan, snapshot)  # type: ignore[arg-type]

            persisted = write_decoder_candidate_partition_plan(plan_path, plan)
            forged = PersistedDecoderCandidatePartitionPlan(
                path=persisted.path,
                sha256=persisted.sha256,
                plan=persisted.plan,
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                validate_decoder_candidate_partition_plan_against_snapshot(
                    forged, snapshot
                )

    def test_direct_collector_refuses_to_drain_after_its_persisted_plan_changes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            collector = context.collector_for_item(
                context.items_for_partition("fit")[0]
            )
            collector.record_candidate(
                frame_index=0,
                pitch=60,
                candidate_reason="model_onset",
                candidate_score=0.9,
                frame_probability=0.9,
                onset_probability=0.9,
                harmonic_support=0.0,
                audio_onset_available=True,
                audio_onset_recent=True,
                active_polyphony=0,
                gate_eligible=True,
                post_gate_rank=0,
                post_gate_selected=True,
                emitted_noteon=True,
            )
            plan_path.write_bytes(plan_path.read_bytes() + b" ")
            with self.assertRaisesRegex(RuntimeError, "bytes changed"):
                collector.drain()

    def test_context_rejects_a_hand_constructed_nonpersisted_plan_wrapper(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            forged_persisted = PersistedDecoderCandidatePartitionPlan(
                path=root / "never-written.json",
                sha256=context.persisted_plan.sha256,
                plan=context.persisted_plan.plan,
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                DecoderCandidateMiningContext(
                    snapshot=context.snapshot,
                    persisted_plan=forged_persisted,
                    validated_snapshot=context.validated_snapshot,
                )

    def test_context_rechecks_persisted_plan_before_collection(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            plan_path.write_bytes(plan_path.read_bytes() + b" ")
            with self.assertRaisesRegex(RuntimeError, "bytes changed"):
                context.collector_for_item(context.items_for_partition("fit")[0])

    def test_context_aggregates_only_one_complete_preassigned_partition(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.csv"
            plan_path = root / "partition-plan.json"
            _write_full_manifest(manifest_path)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest_path,
                partition_plan_path=plan_path,
                seed=47,
            )
            item = context.items_for_partition("fit")[0]
            collector = context.collector_for_item(item)
            collector.record_candidate(
                frame_index=0,
                pitch=60,
                candidate_reason="model_onset",
                candidate_score=0.9,
                frame_probability=0.9,
                onset_probability=0.9,
                harmonic_support=0.0,
                audio_onset_available=True,
                audio_onset_recent=True,
                active_polyphony=0,
                gate_eligible=True,
                post_gate_rank=0,
                post_gate_selected=True,
                emitted_noteon=True,
            )
            labeled = label_emitted_decoder_candidates(
                collector.drain(),
                [],
                frame_valid=[True],
                sample_rate=100,
                hop_size=10,
                audio_frames=100,
                emitted_events=[SimpleNamespace(
                    kind="note_on",
                    frame_index=0,
                    pitch=60,
                    reason="model_onset",
                )],
                candidate_collection_error=None,
            )
            counters = context.aggregate_partition_label_batches("fit", (labeled,))
            self.assertEqual(counters.recording_identities, ((
                item.dataset_id,
                item.source_id,
                item.capture_id,
            ),))
            self.assertEqual(counters.negative_targets, 1)
            with self.assertRaisesRegex(RuntimeError, "duplicate a recording"):
                context.aggregate_partition_label_batches("fit", (labeled, labeled))


if __name__ == "__main__":
    unittest.main()
