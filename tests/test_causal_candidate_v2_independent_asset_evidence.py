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
from unittest import mock

from src.polyphonic import run_causal_candidate_v2_independent_validation as runner
from src.polyphonic.causal_candidate_v2_independent_asset_evidence import (
    IndependentV2ValidationAssetEvidence,
    IndependentV2ValidationAssetEvidenceEntry,
    PersistedIndependentV2ValidationAssetEvidence,
    build_independent_v2_validation_asset_evidence,
    canonical_recording_key,
    load_independent_v2_validation_asset_evidence,
    validate_independent_v2_validation_asset_evidence,
    verify_independent_v2_validation_audio_asset_for_item,
    verify_independent_v2_validation_label_asset_for_item,
    write_independent_v2_validation_asset_evidence,
)
from src.polyphonic.decoder_candidate_provenance import load_decoder_candidate_manifest
from src.polyphonic.manifest_snapshot import load_manifest_snapshot


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _recording_key(row: dict[str, str]) -> str:
    return "|".join(
        (row["dataset_id"], row["group_id"], row["source_id"], row["capture_id"])
    )


def _row(
    dataset_id: str,
    source_id: str,
    group_id: str,
    capture_id: str,
    *,
    player_id: str = "",
    split: str = "validation",
    asset_root: Path,
) -> dict[str, str]:
    stem = f"{dataset_id}-{source_id}-{capture_id}"
    audio = asset_root / f"{stem}.wav"
    labels = asset_root / f"{stem}.npz"
    if split == "validation":
        audio.write_bytes(f"audio:{stem}".encode("utf-8"))
        labels.write_bytes(f"labels:{stem}".encode("utf-8"))
    return {
        "source_id": source_id,
        "dataset_id": dataset_id,
        "player_id": player_id,
        "group_id": group_id,
        "split": split,
        "audio_path": audio.name,
        "audio_member": capture_id,
        "labels_path": labels.name,
        "capture_id": capture_id,
        "license_id": "unit-test",
    }


def _write_sealed_fixture(
    root: Path,
    *,
    mode: str,
    source_evidence_protocol_sha256: str | None = None,
    expected_evidence_sha256: str | None = None,
):
    """Create a full fake manifest and a loader-attested sealed cohort.

    Only fake byte files belonging to the selected validation rows are ever
    opened.  The production protocol is read only as a JSON template; no
    project audio, labels, model or checkpoint participates in this fixture.
    """

    rows: list[dict[str, str]] = []
    historical: list[str] = []
    for index in range(5):
        row = _row(
            "gaps_poly_mix", f"historic-gaps-{index}", f"historic-gaps-{index}",
            "gaps_mixed_downmix", player_id=f"Historic {index}", asset_root=root,
        )
        rows.append(row)
        historical.append(_recording_key(row))
    for capture in ("directinput", "micamp"):
        for index in range(2):
            row = _row(
                f"guitar_techs_poly_{capture}",
                f"historic-{capture}-{index}",
                f"historic-{capture}-{index}",
                capture,
                asset_root=root,
            )
            rows.append(row)
            historical.append(_recording_key(row))
    for index in range(3):
        guitarset = _row(
            "guitarset_poly_mix", f"historic-guitarset-{index}",
            f"historic-guitarset-{index}", "mono_pickup_mix",
            player_id="04", asset_root=root,
        )
        rows.append(guitarset)
        historical.append(_recording_key(guitarset))

    for index in range(10):
        rows.append(_row(
            "gaps_poly_mix", f"gaps-{index}", f"gaps-{index}",
            "gaps_mixed_downmix", player_id=f"Fresh {index}", asset_root=root,
        ))
    for index in range(10):
        group = f"gtech-{index}"
        rows.extend((
            _row(
                "guitar_techs_poly_directinput", f"{group}-direct", group,
                "directinput", asset_root=root,
            ),
            _row(
                "guitar_techs_poly_micamp", f"{group}-mic", group,
                "micamp", asset_root=root,
            ),
        ))
    # Policy A only needs metadata here; these train paths are never opened.
    rows.extend((
        _row(
            "gaps_poly_mix", "train-gaps", "train-gaps", "gaps_mixed_downmix",
            player_id="Fresh 0", split="train", asset_root=root,
        ),
        _row(
            "guitar_techs_poly_directinput", "train-gtech", "gtech-0",
            "directinput", split="train", asset_root=root,
        ),
        _row(
            "gaps_poly_mix", "train-safe", "train-safe", "gaps_mixed_downmix",
            player_id="Train only", split="train", asset_root=root,
        ),
    ))

    manifest = root / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata_items, manifest_sha256 = load_decoder_candidate_manifest(manifest)
    derived_keys, _ = runner._derive_expected_recording_keys(
        metadata_items, historical_recording_keys=historical
    )

    if mode not in {"disabled", "builder", "reader"}:
        raise ValueError("unsupported synthetic authorization mode")
    repository = root / f"repository-{mode}"
    protocol_path = repository / runner.INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH
    history_path = repository / runner.HISTORICAL_V1_SELECTION_RELATIVE_PATH
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps({
            "schema_version": 1,
            "locked_test_used": False,
            "recording_keys": historical,
        }) + "\n",
        encoding="utf-8",
    )
    template_path = Path(__file__).resolve().parents[1] / runner.INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH
    protocol = json.loads(template_path.read_text(encoding="utf-8"))
    protocol["independence_boundary"]["manifest_sha256"] = manifest_sha256
    protocol["independence_boundary"]["historical_v1_validation_selection_sha256"] = _sha256_bytes(history_path.read_bytes())
    protocol["cohort_rule"]["recording_keys"] = list(derived_keys)
    evidence_contract = protocol["validation_asset_evidence_contract"]
    evidence_contract["builder_authorized_now"] = mode == "builder"
    evidence_contract["reader_authorized_now"] = mode == "reader"
    evidence_contract["source_evidence_protocol_sha256"] = source_evidence_protocol_sha256
    evidence_contract["expected_evidence_sha256"] = expected_evidence_sha256
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    snapshot = load_manifest_snapshot(manifest)
    with mock.patch.object(runner, "INDEPENDENT_V2_PROTOCOL_SHA256", _sha256_bytes(protocol_path.read_bytes())):
        cohort = runner.load_sealed_independent_v2_validation_cohort(repository, manifest)
    requirement = runner.validation_asset_evidence_requirement(cohort)
    return snapshot, cohort, requirement


class IndependentV2ValidationAssetEvidenceTests(unittest.TestCase):
    def test_unauthorized_protocol_refuses_builder_and_reader_before_any_asset_read(self) -> None:
        with TemporaryDirectory() as temporary:
            snapshot, cohort, requirement = _write_sealed_fixture(
                Path(temporary), mode="disabled"
            )
            with mock.patch(
                "src.polyphonic.causal_candidate_v2_independent_asset_evidence._digest_file"
            ) as digest:
                with self.assertRaisesRegex(RuntimeError, "build is not authorized"):
                    build_independent_v2_validation_asset_evidence(
                        cohort, snapshot, requirement
                    )
                self.assertFalse(digest.called)
            with self.assertRaisesRegex(RuntimeError, "read is not authorized"):
                load_independent_v2_validation_asset_evidence(
                    Path(temporary) / "does-not-matter.json", cohort, requirement
                )

    def test_build_write_load_validate_and_open_boundary_rehash(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort, requirement = _write_sealed_fixture(root, mode="builder")
            built = build_independent_v2_validation_asset_evidence(cohort, snapshot, requirement)
            persisted = write_independent_v2_validation_asset_evidence(
                root / "independent-assets.json", built
            )
            _, reader_cohort, reader_requirement = _write_sealed_fixture(
                root,
                mode="reader",
                source_evidence_protocol_sha256=cohort.protocol_sha256,
                expected_evidence_sha256=persisted.sha256,
            )
            loaded = load_independent_v2_validation_asset_evidence(
                persisted.path, reader_cohort, reader_requirement
            )
            validated = validate_independent_v2_validation_asset_evidence(
                loaded, reader_cohort, snapshot, reader_requirement
            )
            self.assertEqual(len(validated.persisted.evidence.entries), 30)
            raw = persisted.path.read_text(encoding="utf-8")
            self.assertNotIn(str(root), raw)
            self.assertNotIn("audio_path", raw)
            self.assertNotIn("labels_path", raw)
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                write_independent_v2_validation_asset_evidence(persisted.path, built)
            item = next(
                item
                for item in snapshot.items
                if canonical_recording_key(item) == reader_cohort.recording_keys[0]
            )
            verify_independent_v2_validation_label_asset_for_item(validated, item)
            item.labels_path.write_bytes(b"changed labels")
            with self.assertRaisesRegex(RuntimeError, "label asset bytes differ"):
                verify_independent_v2_validation_label_asset_for_item(validated, item)

    def test_rejects_forged_or_cloned_cohorts_and_capabilities(self) -> None:
        with TemporaryDirectory() as temporary:
            snapshot, cohort, requirement = _write_sealed_fixture(
                Path(temporary), mode="builder"
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested by the sealed loader"):
                build_independent_v2_validation_asset_evidence(
                    replace(cohort), snapshot, requirement
                )
            with self.assertRaisesRegex(RuntimeError, "factory-attested by the sealed loader"):
                build_independent_v2_validation_asset_evidence(
                    replace(cohort, protocol_sha256="0" * 64), snapshot, requirement
                )
            with self.assertRaisesRegex(RuntimeError, "factory-attested by the sealed loader"):
                build_independent_v2_validation_asset_evidence(
                    cohort, snapshot, replace(requirement)
                )

    def test_forged_canonical_registry_is_not_usable_until_all_assets_match(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort, requirement = _write_sealed_fixture(root, mode="builder")
            built = build_independent_v2_validation_asset_evidence(cohort, snapshot, requirement)
            persisted = write_independent_v2_validation_asset_evidence(root / "good.json", built)
            payload = persisted.evidence.as_json()
            payload["entries"][0]["audio_sha256"] = "0" * 64  # type: ignore[index]
            forged_path = root / "forged.json"
            forged_path.write_bytes(
                (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            )
            _, reader_cohort, reader_requirement = _write_sealed_fixture(
                root,
                mode="reader",
                source_evidence_protocol_sha256=cohort.protocol_sha256,
                expected_evidence_sha256=_sha256_bytes(forged_path.read_bytes()),
            )
            forged = load_independent_v2_validation_asset_evidence(
                forged_path, reader_cohort, reader_requirement
            )
            with self.assertRaisesRegex(RuntimeError, "audio bytes differ"):
                validate_independent_v2_validation_asset_evidence(
                    forged, reader_cohort, snapshot, reader_requirement
                )
            direct_wrapper = PersistedIndependentV2ValidationAssetEvidence(
                path=persisted.path,
                sha256=persisted.sha256,
                evidence=persisted.evidence,
            )
            _, good_reader_cohort, good_reader_requirement = _write_sealed_fixture(
                root,
                mode="reader",
                source_evidence_protocol_sha256=cohort.protocol_sha256,
                expected_evidence_sha256=persisted.sha256,
            )
            validated = validate_independent_v2_validation_asset_evidence(
                direct_wrapper, good_reader_cohort, snapshot, good_reader_requirement
            )
            with self.assertRaisesRegex(RuntimeError, "factory-attested"):
                verify_independent_v2_validation_audio_asset_for_item(
                    replace(validated), snapshot.items[0]
                )
            persisted.path.write_bytes(persisted.path.read_bytes() + b" ")
            with self.assertRaisesRegex(RuntimeError, "evidence bytes changed"):
                verify_independent_v2_validation_audio_asset_for_item(
                    validated,
                    next(
                        item
                        for item in snapshot.items
                        if canonical_recording_key(item)
                        == good_reader_cohort.recording_keys[0]
                    ),
                )

    def test_mutation_between_build_and_write_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort, requirement = _write_sealed_fixture(root, mode="builder")
            built = build_independent_v2_validation_asset_evidence(cohort, snapshot, requirement)
            selected = next(
                item
                for item in snapshot.items
                if canonical_recording_key(item) == cohort.recording_keys[0]
            )
            selected.audio_path.write_bytes(b"changed after build")
            destination = root / "must-not-exist.json"
            with self.assertRaisesRegex(RuntimeError, "audio bytes differ"):
                write_independent_v2_validation_asset_evidence(destination, built)
            self.assertFalse(destination.exists())

    def test_reader_rejects_semantically_identical_noncanonical_bytes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, cohort, requirement = _write_sealed_fixture(root, mode="builder")
            built = build_independent_v2_validation_asset_evidence(cohort, snapshot, requirement)
            persisted = write_independent_v2_validation_asset_evidence(root / "good.json", built)
            noncanonical = root / "noncanonical.json"
            noncanonical.write_bytes(b" \n" + persisted.path.read_bytes())
            _, reader_cohort, reader_requirement = _write_sealed_fixture(
                root,
                mode="reader",
                source_evidence_protocol_sha256=cohort.protocol_sha256,
                expected_evidence_sha256=_sha256_bytes(noncanonical.read_bytes()),
            )
            with self.assertRaisesRegex(ValueError, "not canonical JSON"):
                load_independent_v2_validation_asset_evidence(
                    noncanonical, reader_cohort, reader_requirement
                )

    def test_synthetic_snapshot_and_evidence_imports_do_not_load_tensorflow_or_cli(self) -> None:
        code = (
            "import sys; "
            "import src.polyphonic.manifest_snapshot as snapshot; "
            "import src.polyphonic.causal_candidate_v2_independent_asset_evidence as evidence; "
            "raise SystemExit(int('tensorflow' in sys.modules or hasattr(evidence, 'main')))"
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
