from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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
)


def _write_manifest_and_assets(root: Path) -> Path:
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
                "split": "train", "audio_path": audio.name,
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


class DecoderCandidateAssetEvidenceTests(unittest.TestCase):
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
