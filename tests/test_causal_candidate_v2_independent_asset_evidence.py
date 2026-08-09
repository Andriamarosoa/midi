from __future__ import annotations

import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from src.polyphonic.causal_candidate_v2_independent_asset_evidence import (
    PersistedIndependentV2ValidationAssetEvidence,
    build_independent_v2_validation_asset_evidence,
    canonical_recording_key,
    load_independent_v2_validation_asset_evidence,
    ordered_recording_keys_sha256,
    validate_independent_v2_validation_asset_evidence,
    verify_independent_v2_validation_audio_asset_for_item,
    verify_independent_v2_validation_label_asset_for_item,
    write_independent_v2_validation_asset_evidence,
)
from src.polyphonic.data import load_manifest_snapshot
from src.polyphonic.decoder_candidate_provenance import leakage_group_key
from src.polyphonic.run_causal_candidate_v2_independent_validation import (
    IndependentV2ValidationCohort,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_snapshot_with_selected_assets(root: Path):
    """Create the V2-required 30 recordings, without audio/NPZ decoding."""
    manifest = root / "manifest.csv"
    fields = (
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id", "license_id",
    )
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(10):
            audio = root / f"gaps-{index}.wav"
            labels = root / f"gaps-{index}.npz"
            audio.write_bytes(f"gaps audio {index}".encode("utf-8"))
            labels.write_bytes(f"gaps labels {index}".encode("utf-8"))
            writer.writerow({
                "source_id": f"gaps-source-{index}",
                "dataset_id": "gaps_poly_mix",
                "player_id": f"fresh-player-{index}",
                "group_id": f"gaps-group-{index}",
                "split": "validation",
                "audio_path": audio.name,
                "audio_member": "gaps_mixed_downmix",
                "labels_path": labels.name,
                "capture_id": "gaps_mixed_downmix",
                "license_id": "unit-test",
            })
        for index in range(10):
            group = f"gtech-group-{index}"
            for capture, dataset in (
                ("directinput", "guitar_techs_poly_directinput"),
                ("micamp", "guitar_techs_poly_micamp"),
            ):
                audio = root / f"{group}-{capture}.wav"
                labels = root / f"{group}-{capture}.npz"
                audio.write_bytes(f"{capture} audio {index}".encode("utf-8"))
                labels.write_bytes(f"{capture} labels {index}".encode("utf-8"))
                writer.writerow({
                    "source_id": f"{group}-{capture}",
                    "dataset_id": dataset,
                    "player_id": "",
                    "group_id": group,
                    "split": "validation",
                    "audio_path": audio.name,
                    "audio_member": capture,
                    "labels_path": labels.name,
                    "capture_id": capture,
                    "license_id": "unit-test",
                })
    snapshot = load_manifest_snapshot(manifest)
    keys = tuple(canonical_recording_key(item) for item in snapshot.items)
    groups = tuple(sorted({leakage_group_key(item) for item in snapshot.items}))
    cohort = IndependentV2ValidationCohort(
        protocol_sha256="a" * 64,
        manifest_sha256=snapshot.manifest_sha256,
        historical_selection_sha256="b" * 64,
        recording_keys=keys,
        leakage_groups=groups,
        recordings_per_dataset=(
            ("gaps_poly_mix", 10),
            ("guitar_techs_poly_directinput", 10),
            ("guitar_techs_poly_micamp", 10),
        ),
        independent_group_count=20,
    )
    return snapshot, cohort


class IndependentV2ValidationAssetEvidenceTests(unittest.TestCase):
    def test_build_write_reload_and_validate_exact_selected_snapshot(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort = _write_snapshot_with_selected_assets(root)
            evidence = build_independent_v2_validation_asset_evidence(cohort, snapshot)
            persisted = write_independent_v2_validation_asset_evidence(
                root / "independent-assets.json", evidence
            )
            validate_independent_v2_validation_asset_evidence(
                persisted, cohort, snapshot
            )
            self.assertEqual(len(persisted.evidence.entries), 30)
            self.assertEqual(
                persisted.evidence.ordered_recording_keys_sha256,
                ordered_recording_keys_sha256(cohort.recording_keys),
            )
            raw = persisted.path.read_text(encoding="utf-8")
            self.assertNotIn(str(root), raw)
            self.assertNotIn("audio_path", raw)
            self.assertNotIn("labels_path", raw)
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                write_independent_v2_validation_asset_evidence(
                    persisted.path, persisted.evidence
                )
            self.assertEqual(persisted.path.read_text(encoding="utf-8"), raw)

    def test_verification_rejects_mutated_selected_assets_and_unselected_item(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort = _write_snapshot_with_selected_assets(root)
            persisted = write_independent_v2_validation_asset_evidence(
                root / "independent-assets.json",
                build_independent_v2_validation_asset_evidence(cohort, snapshot),
            )
            item = snapshot.items[0]
            cloned_item = replace(item, audio_path=root / "substituted.wav")
            with self.assertRaisesRegex(RuntimeError, "exact selected snapshot object"):
                verify_independent_v2_validation_audio_asset_for_item(
                    persisted, cohort, snapshot, cloned_item
                )
            verify_independent_v2_validation_label_asset_for_item(
                persisted, cohort, snapshot, item
            )
            item.labels_path.write_bytes(b"changed labels")
            with self.assertRaisesRegex(RuntimeError, "label asset bytes differ"):
                verify_independent_v2_validation_label_asset_for_item(
                    persisted, cohort, snapshot, item
                )

            item.audio_path.write_bytes(b"changed audio")
            with self.assertRaisesRegex(RuntimeError, "audio asset bytes differ"):
                verify_independent_v2_validation_audio_asset_for_item(
                    persisted, cohort, snapshot, item
                )

    def test_rejects_forged_evidence_and_cohort_snapshot_mismatch(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort = _write_snapshot_with_selected_assets(root)
            persisted = write_independent_v2_validation_asset_evidence(
                root / "independent-assets.json",
                build_independent_v2_validation_asset_evidence(cohort, snapshot),
            )
            forged = PersistedIndependentV2ValidationAssetEvidence(
                path=persisted.path,
                sha256=persisted.sha256,
                evidence=persisted.evidence,
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                validate_independent_v2_validation_asset_evidence(
                    forged, cohort, snapshot
                )
            mismatched = replace(cohort, recording_keys=tuple(reversed(cohort.recording_keys)))
            with self.assertRaisesRegex(RuntimeError, "differs from the sealed cohort"):
                validate_independent_v2_validation_asset_evidence(
                    persisted, mismatched, snapshot
                )

    def test_reader_is_canonical_and_import_has_no_tensorflow_or_cli(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort = _write_snapshot_with_selected_assets(root)
            persisted = write_independent_v2_validation_asset_evidence(
                root / "independent-assets.json",
                build_independent_v2_validation_asset_evidence(cohort, snapshot),
            )
            self.assertEqual(
                load_independent_v2_validation_asset_evidence(persisted.path).sha256,
                _sha256(persisted.path),
            )
            payload = json.loads(persisted.path.read_text(encoding="utf-8"))
            payload["entries"] = list(reversed(payload["entries"]))
            noncanonical = root / "noncanonical.json"
            noncanonical.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "entries must match key order"
            ):
                load_independent_v2_validation_asset_evidence(noncanonical)

        code = (
            "import sys; "
            "import src.polyphonic.causal_candidate_v2_independent_asset_evidence as module; "
            "raise SystemExit(int('tensorflow' in sys.modules or hasattr(module, 'main')))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
