from __future__ import annotations

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from src.polyphonic.decoder_candidate_provenance import (
    DECODER_CANDIDATE_PARTITION_POLICY,
    DecoderCandidatePartitionPlan,
    build_decoder_candidate_partition_plan_from_manifest,
    build_decoder_candidate_partition_plan,
    leakage_group_key,
    validate_decoder_candidate_partition_plan_from_manifest,
)


def _item(
    source_id: str,
    dataset_id: str,
    player_id: str,
    group_id: str,
    capture_id: str,
    split: str = "train",
) -> SimpleNamespace:
    return SimpleNamespace(
        source_id=source_id,
        dataset_id=dataset_id,
        player_id=player_id,
        group_id=group_id,
        capture_id=capture_id,
        split=split,
    )


def _complete_train_items() -> list[SimpleNamespace]:
    items: list[SimpleNamespace] = []
    for index in range(6):
        items.extend((
            _item(
                f"guitarset-{index}", "GuitarSet", f"player-{index}",
                f"guitarset-group-{index}", f"guitarset-capture-{index}",
            ),
            _item(
                f"gaps-{index}", "GAPS", f"performer-{index}",
                f"gaps-group-{index}", f"gaps-capture-{index}",
            ),
            _item(
                f"tech-direct-{index}", "Guitar-TECHS direct", "performer",
                f"tech-group-{index}", f"tech-direct-capture-{index}",
            ),
            _item(
                f"tech-mic-{index}", "Guitar-TECHS mic", "performer",
                f"tech-group-{index}", f"tech-mic-capture-{index}",
            ),
        ))
    return items


def _write_manifest(path: Path, items: list[SimpleNamespace]) -> None:
    fields = (
        "source_id", "dataset_id", "player_id", "group_id", "capture_id",
        "split",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({name: getattr(item, name) for name in fields})


class DecoderCandidateProvenanceTests(unittest.TestCase):
    MANIFEST_SHA256 = "a" * 64

    def test_plan_round_trip_is_deterministic_and_group_safe(self) -> None:
        items = _complete_train_items()
        first = build_decoder_candidate_partition_plan(
            items, manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        second = build_decoder_candidate_partition_plan(
            items, manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        shuffled = build_decoder_candidate_partition_plan(
            list(reversed(items)), manifest_sha256=self.MANIFEST_SHA256, seed=47
        )

        self.assertEqual(first, second)
        self.assertEqual(first.as_json(), shuffled.as_json())
        self.assertEqual(
            first.as_json()["partition_policy"],
            DECODER_CANDIDATE_PARTITION_POLICY,
        )
        restored = DecoderCandidatePartitionPlan.from_json(first.as_json())
        self.assertEqual(restored, first)
        restored.require_matches_manifest_items(
            items, expected_manifest_sha256=self.MANIFEST_SHA256
        )
        self.assertEqual(
            {
                (row.dataset_id, row.source_id, row.capture_id)
                for row in first.records
            },
            {
                (item.dataset_id, item.source_id, item.capture_id)
                for item in items
            },
        )

        partitions_by_group: dict[str, str] = {}
        for record in first.records:
            existing = partitions_by_group.setdefault(
                record.leakage_group_key, record.partition
            )
            self.assertEqual(existing, record.partition)
        for index in range(6):
            direct = next(
                record for record in first.records
                if record.source_id == f"tech-direct-{index}"
            )
            mic = next(
                record for record in first.records
                if record.source_id == f"tech-mic-{index}"
            )
            self.assertEqual(direct.leakage_group_key, mic.leakage_group_key)
            self.assertEqual(direct.partition, mic.partition)

    def test_plan_rejects_manifest_or_record_drift(self) -> None:
        items = _complete_train_items()
        plan = build_decoder_candidate_partition_plan(
            items, manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
            plan.require_matches_manifest_items(
                items, expected_manifest_sha256="b" * 64
            )

        tampered = plan.as_json()
        tampered["records"][0]["capture_id"] = "tampered-capture"
        changed = DecoderCandidatePartitionPlan.from_json(tampered)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            changed.require_matches_manifest_items(
                items, expected_manifest_sha256=self.MANIFEST_SHA256
            )

    def test_plan_excludes_validation_and_rejects_incomplete_identity(self) -> None:
        items = _complete_train_items()
        items[0].split = "validation"
        plan = build_decoder_candidate_partition_plan(
            items, manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        self.assertNotIn(
            (items[0].dataset_id, items[0].source_id, items[0].capture_id),
            {record.manifest_identity_key for record in plan.records},
        )

        items = _complete_train_items()
        items[0].capture_id = ""
        with self.assertRaisesRegex(ValueError, "capture_id"):
            build_decoder_candidate_partition_plan(
                items, manifest_sha256=self.MANIFEST_SHA256, seed=47
            )

    def test_plan_refuses_train_validation_leakage_group_overlap(self) -> None:
        items = _complete_train_items()
        train = items[0]
        items.append(_item(
            "validation-clone",
            train.dataset_id,
            train.player_id,
            train.group_id,
            "validation-capture",
            split="validation",
        ))
        with self.assertRaisesRegex(RuntimeError, "overlap by leakage group"):
            build_decoder_candidate_partition_plan(
                items, manifest_sha256=self.MANIFEST_SHA256, seed=47
            )

    def test_plan_rejects_inconsistent_leakage_partition_payload(self) -> None:
        plan = build_decoder_candidate_partition_plan(
            _complete_train_items(), manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        payload = plan.as_json()
        direct = next(
            row for row in payload["records"]
            if row["source_id"] == "tech-direct-0"
        )
        mic = next(
            row for row in payload["records"]
            if row["source_id"] == "tech-mic-0"
        )
        mic["partition"] = (
            "dev" if direct["partition"] != "dev" else "calibration"
        )
        with self.assertRaisesRegex(ValueError, "one leakage group"):
            DecoderCandidatePartitionPlan.from_json(payload)

    def test_plan_refuses_locked_test_or_missing_record(self) -> None:
        plan = build_decoder_candidate_partition_plan(
            _complete_train_items(), manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        payload = plan.as_json()
        payload["locked_test_used"] = True
        with self.assertRaisesRegex(ValueError, "locked test"):
            DecoderCandidatePartitionPlan.from_json(payload)

        payload = plan.as_json()
        payload["records"].pop()
        incomplete = DecoderCandidatePartitionPlan.from_json(payload)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            incomplete.require_matches_manifest_items(
                _complete_train_items(), expected_manifest_sha256=self.MANIFEST_SHA256
            )

    def test_plan_is_bound_to_the_complete_manifest_file_before_lookup(self) -> None:
        items = _complete_train_items()
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.csv"
            _write_manifest(path, items)
            plan = build_decoder_candidate_partition_plan_from_manifest(
                path, seed=47
            )
            validated = validate_decoder_candidate_partition_plan_from_manifest(
                plan, path
            )
            record = validated.provenance_for_train_item(items[0])
            self.assertIn(record, plan.records)
            self.assertEqual(record.capture_id, items[0].capture_id)

            wrong_capture = _item(
                items[0].source_id,
                items[0].dataset_id,
                items[0].player_id,
                items[0].group_id,
                "unplanned-capture",
            )
            with self.assertRaisesRegex(RuntimeError, "absent"):
                validated.provenance_for_train_item(wrong_capture)

            changed_group = _item(
                items[0].source_id,
                items[0].dataset_id,
                items[0].player_id,
                "tampered-group",
                items[0].capture_id,
            )
            with self.assertRaisesRegex(RuntimeError, "differs"):
                validated.provenance_for_train_item(changed_group)

            _write_manifest(path, list(reversed(items)))
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                validate_decoder_candidate_partition_plan_from_manifest(plan, path)

    def test_file_manifest_rejects_missing_cell_and_locked_test(self) -> None:
        items = _complete_train_items()
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.csv"
            path.write_text(
                "source_id,dataset_id,player_id,group_id,capture_id,split\n"
                "source,corpus,player,group,capture\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "split must be a CSV string"):
                build_decoder_candidate_partition_plan_from_manifest(path, seed=47)

            _write_manifest(path, items)
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("player-0", "", 1), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "GuitarSet"):
                build_decoder_candidate_partition_plan_from_manifest(path, seed=47)

            _write_manifest(path, items)
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("train", "test", 1), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "locked test"):
                build_decoder_candidate_partition_plan_from_manifest(path, seed=47)

    def test_plan_refuses_boolean_schema_version(self) -> None:
        plan = build_decoder_candidate_partition_plan(
            _complete_train_items(), manifest_sha256=self.MANIFEST_SHA256, seed=47
        )
        payload = plan.as_json()
        payload["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "schema"):
            DecoderCandidatePartitionPlan.from_json(payload)

    def test_existing_grouping_contract_is_preserved(self) -> None:
        direct = _item(
            "direct", "Guitar-TECHS direct", "performer", "song", "direct",
        )
        mic = _item(
            "mic", "Guitar-TECHS mic", "performer", "song", "mic",
        )
        self.assertEqual(leakage_group_key(direct), leakage_group_key(mic))


if __name__ == "__main__":
    unittest.main()
