from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import numpy as np

from src.polyphonic import decoder_candidate_asset_evidence as asset_evidence
from src.polyphonic.decoder_candidate_asset_evidence import (
    PersistedDecoderCandidateAssetEvidence,
    build_decoder_candidate_asset_evidence,
    load_decoder_candidate_asset_evidence,
    validate_decoder_candidate_asset_evidence,
    verify_decoder_candidate_assets_for_item,
    write_decoder_candidate_asset_evidence,
)
from src.polyphonic.decoder_candidate_miner import (
    create_decoder_candidate_mining_context,
    load_decoder_candidate_mining_context,
    pre_register_decoder_candidate_asset_evidence,
)


def _write_manifest_and_assets(root: Path, *, shared_audio: bool = False) -> Path:
    manifest = root / "manifest.csv"
    fields = (
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id", "license_id",
    )
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(3):
            audio = root / f"audio-{index}.wav"
            labels = root / f"labels-{index}.npz"
            audio.write_bytes(f"synthetic audio {index}".encode("utf-8"))
            labels.write_bytes(f"synthetic labels {index}".encode("utf-8"))
            writer.writerow({
                "source_id": f"source-{index}", "dataset_id": "unit-corpus",
                "player_id": f"player-{index}", "group_id": f"group-{index}",
                "split": "train", "audio_path": "audio-0.wav" if shared_audio and index == 1 else audio.name,
                "audio_member": "" if index != 1 else "capture.wav",
                "labels_path": labels.name, "capture_id": f"capture-{index}",
                "license_id": "unit-test",
            })
        writer.writerow({
            "source_id": "validation-source", "dataset_id": "unit-corpus",
            "player_id": "validation-player", "group_id": "validation-group",
            "split": "validation", "audio_path": "validation.wav", "audio_member": "",
            "labels_path": "validation.npz", "capture_id": "validation-capture",
            "license_id": "unit-test",
        })
    return manifest


def _write_runnable_manifest_and_assets(root: Path) -> Path:
    """Create the smallest real NumPy/NPZ corpus accepted by PolyphonicCorpus."""
    manifest = root / "runnable-manifest.csv"
    fields = (
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id", "license_id",
    )
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(3):
            audio = root / f"runnable-audio-{index}.npy"
            labels = root / f"runnable-labels-{index}.npz"
            waveform = np.linspace(-0.25, 0.25, 16, dtype=np.float32)
            np.save(audio, waveform, allow_pickle=False)
            np.savez_compressed(
                labels,
                active_bits=np.zeros(4, dtype=np.uint64),
                onset_bits=np.zeros(4, dtype=np.uint64),
                polyphony=np.zeros(4, dtype=np.uint8),
                valid=np.ones(4, dtype=np.uint8),
                slot_pitch=np.full((4, 1), -1, dtype=np.int8),
                slot_note_id=np.full((4, 1), -1, dtype=np.int32),
                note_harmonic_present=np.ones((1, 1), dtype=np.uint8),
                note_harmonic_amplitude=np.ones((1, 1), dtype=np.float16),
                note_harmonic_offset_cents=np.zeros((1, 1), dtype=np.float16),
                note_harmonic_valid=np.ones(1, dtype=np.uint8),
                sample_rate=np.int32(8),
                hop_size=np.int32(4),
                audio_frames=np.int64(len(waveform)),
                midi_min=np.int16(40),
                midi_max=np.int16(40),
            )
            writer.writerow({
                "source_id": f"runnable-source-{index}",
                "dataset_id": "unit-corpus",
                "player_id": f"runnable-player-{index}",
                "group_id": f"runnable-group-{index}",
                "split": "train",
                "audio_path": audio.name,
                "audio_member": "",
                "labels_path": labels.name,
                "capture_id": f"runnable-capture-{index}",
                "license_id": "unit-test",
            })
    return manifest


class DecoderCandidateAssetEvidenceTests(unittest.TestCase):
    def test_pre_registration_reload_and_open_rehash_at_actual_lazy_audio_load(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _write_runnable_manifest_and_assets(root)
            create_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                seed=47,
            )
            context = pre_register_decoder_candidate_asset_evidence(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                asset_evidence_path=root / "assets.json",
            )
            item = context.items_for_partition("fit")[0]

            # Labels are loaded by the constructor, so their verifier must
            # reject a change immediately before context.open_recording().
            original_labels = item.labels_path.read_bytes()
            item.labels_path.write_bytes(b"mutated before labels load")
            with self.assertRaisesRegex(RuntimeError, "label asset bytes differ"):
                with context.open_recording(item):
                    self.fail("changed labels must fail before the corpus opens")
            item.labels_path.write_bytes(original_labels)

            # The corpus is now really constructed from the pre-registered
            # synthetic files. Audio is intentionally mutated afterwards: the
            # verifier attached to PolyphonicCorpus.audio() must reject it at
            # the genuine lazy-load boundary, before np.load() reads it.
            with context.open_recording(item) as corpus:
                self.assertIs(corpus.items[0], item)
                item.audio_path.write_bytes(b"mutated after corpus construction")
                with self.assertRaisesRegex(RuntimeError, "audio asset bytes differ"):
                    corpus.audio(0)

    def test_shared_audio_container_is_hashed_once_during_pre_registration(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _write_manifest_and_assets(root, shared_audio=True)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                seed=47,
            )
            with mock.patch(
                "src.polyphonic.decoder_candidate_asset_evidence._digest_file",
                wraps=asset_evidence._digest_file,
            ) as digest_file:
                build_decoder_candidate_asset_evidence(context.validated_snapshot)
            digested_names = [Path(call.args[0]).name for call in digest_file.call_args_list]
            self.assertEqual(digested_names.count("audio-0.wav"), 1)
            self.assertEqual(len(digested_names), 5)

    def test_canonical_evidence_covers_train_only_and_rechecks_opened_bytes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _write_manifest_and_assets(root)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                seed=47,
            )
            evidence = build_decoder_candidate_asset_evidence(context.validated_snapshot)
            persisted = write_decoder_candidate_asset_evidence(root / "assets.json", evidence)
            self.assertEqual(len(persisted.evidence.entries), 3)
            self.assertEqual(
                {entry.partition for entry in persisted.evidence.entries},
                {"fit", "dev", "calibration"},
            )
            validate_decoder_candidate_asset_evidence(
                persisted, context.validated_snapshot
            )
            item = context.items_for_partition("fit")[0]
            verify_decoder_candidate_assets_for_item(
                persisted, context.validated_snapshot, item
            )
            loaded_context = load_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                asset_evidence_path=root / "assets.json",
            )
            self.assertEqual(loaded_context.persisted_asset_evidence, persisted)
            item.labels_path.write_bytes(b"modified labels")
            with self.assertRaisesRegex(RuntimeError, "label asset bytes differ"):
                verify_decoder_candidate_assets_for_item(
                    persisted, context.validated_snapshot, item
                )

    def test_evidence_rejects_forged_wrapper_changed_bytes_and_wrong_snapshot_coverage(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _write_manifest_and_assets(root)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                seed=47,
            )
            persisted = write_decoder_candidate_asset_evidence(
                root / "assets.json",
                build_decoder_candidate_asset_evidence(context.validated_snapshot),
            )
            forged = PersistedDecoderCandidateAssetEvidence(
                path=persisted.path, sha256=persisted.sha256, evidence=persisted.evidence
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                validate_decoder_candidate_asset_evidence(
                    forged, context.validated_snapshot
                )
            persisted.path.write_bytes(persisted.path.read_bytes() + b" ")
            with self.assertRaisesRegex(RuntimeError, "bytes changed"):
                validate_decoder_candidate_asset_evidence(
                    persisted, context.validated_snapshot
                )

            # A new valid file that omits one capture is rejected against the
            # original snapshot before any corpus can open an asset.
            reduced = replace(
                persisted.evidence,
                entries=persisted.evidence.entries[:-1],
            )
            replacement = write_decoder_candidate_asset_evidence(root / "reduced.json", reduced)
            with self.assertRaisesRegex(RuntimeError, "does not cover exact train"):
                validate_decoder_candidate_asset_evidence(
                    replacement, context.validated_snapshot
                )

    def test_context_refuses_to_open_without_evidence(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _write_manifest_and_assets(root)
            context = create_decoder_candidate_mining_context(
                manifest_path=manifest,
                partition_plan_path=root / "plan.json",
                seed=47,
            )
            with self.assertRaisesRegex(RuntimeError, "requires persisted audio/label"):
                with context.open_recording(context.items_for_partition("fit")[0]):
                    self.fail("opening without evidence must fail closed")


if __name__ == "__main__":
    unittest.main()
