from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest


class ProvisionalResolutionAge1PersistenceH8PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.preparation_path = (
            cls.root
            / "configs/provisional_resolution_age1_persistence_h8_preparation.json"
        )
        cls.cohort_path = (
            cls.root
            / "configs/provisional_resolution_age1_persistence_h8_selected_cohort.json"
        )
        cls.preparation_bytes = cls.preparation_path.read_bytes()
        cls.cohort_bytes = cls.cohort_path.read_bytes()
        cls.preparation = json.loads(cls.preparation_bytes)
        cls.cohort = json.loads(cls.cohort_bytes)

    def test_h7_prerequisite_and_terminal_status_are_exact(self) -> None:
        self.assertEqual(
            self.preparation["status"],
            "provisional_resolution_age1_persistence_h8_preparation_sealed",
        )
        self.assertEqual(
            self.preparation["h7_prerequisite"],
            {
                "commit": "e3e2be144282ecf0079ba22831abfb6439b16ac3",
                "contract_sha256": "2b03305444506430fc0458430730fd4f4bc04ca50b21b1fe321b9985ceaae296",
                "satisfied": True,
            },
        )
        h7 = self.root / "configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json"
        self.assertEqual(hashlib.sha256(h7.read_bytes()).hexdigest(), self.preparation["h7_prerequisite"]["contract_sha256"])

    def test_cohort_artifact_is_canonical_and_bound_by_raw_bytes(self) -> None:
        reference = self.preparation["selected_cohort"]
        self.assertEqual(reference["relative_path"], "configs/provisional_resolution_age1_persistence_h8_selected_cohort.json")
        self.assertEqual(reference["size_bytes"], len(self.cohort_bytes))
        self.assertEqual(hashlib.sha256(self.cohort_bytes).hexdigest(), reference["sha256"])
        canonical = (json.dumps(self.cohort, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(self.cohort_bytes, canonical)
        self.assertNotIn(b"\r\n", self.cohort_bytes)
        preparation_canonical = (json.dumps(self.preparation, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(self.preparation_bytes, preparation_canonical)
        self.assertEqual(
            hashlib.sha256(self.preparation_bytes).hexdigest(),
            "9bbe2b5558b6b5764415619260a6aba1e3daf1d3c22ce185f3b00a336f8e1639",
        )
        self.assertNotIn(b"\r\n", self.preparation_bytes)

    def test_all_and_only_eligible_dev_records_are_selected(self) -> None:
        recordings = self.cohort["recordings"]
        keys = [row["recording_key"] for row in recordings]
        groups = {row["leakage_group_key"] for row in recordings}
        self.assertEqual(len(recordings), 101)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(groups), 31)
        self.assertEqual({row["partition"] for row in recordings}, {"dev"})
        counts = self.cohort["counts"]
        self.assertEqual(counts["policy_a_dev_recordings_before_exclusion"], 102)
        self.assertEqual(counts["selected_recordings"], 101)
        self.assertEqual(counts["selected_leakage_groups"], 31)
        self.assertEqual(counts["selected_recordings_by_corpus"], {
            "gaps_poly_mix": 27,
            "guitar_techs_poly_directinput": 7,
            "guitar_techs_poly_micamp": 7,
            "guitarset_poly_mix": 60,
        })
        self.assertEqual(counts["selected_groups_by_corpus"], {
            "gaps_poly_mix": 23,
            "guitar_techs_poly_directinput": 7,
            "guitar_techs_poly_micamp": 7,
            "guitarset_poly_mix": 1,
        })
        self.assertEqual(counts["shared_capture_relationships"], 9)

    def test_forbidden_groups_are_excluded_whole_and_intersections_are_empty(self) -> None:
        groups = {row["leakage_group_key"] for row in self.cohort["recordings"]}
        forbidden = self.cohort["forbidden_cohorts"]
        v2_groups = set(forbidden["consumed_v2"]["leakage_group_keys"])
        locked_groups = set(forbidden["locked_test"]["leakage_group_keys"])
        self.assertFalse(groups & v2_groups)
        self.assertFalse(groups & locked_groups)
        self.assertEqual(self.cohort["intersection_proofs"], {
            "selected_with_consumed_v2_group_count": 0,
            "selected_with_locked_test_group_count": 0,
        })
        self.assertEqual(self.cohort["excluded_dev_records"], [{
            "leakage_group_key": "gaps:player:sanja_plohl",
            "reasons": ["locked_test_group"],
            "recording_key": "gaps_poly_mix|Sc1wc|054_Sc1wc|gaps_mixed_downmix",
        }])

    def test_every_record_has_complete_portable_byte_provenance(self) -> None:
        sha_pattern = re.compile(r"[0-9a-f]{64}")
        for row in self.cohort["recordings"]:
            for field in ("audio_path_identity", "labels_path_identity"):
                value = row[field]
                self.assertFalse(PurePosixPath(value).is_absolute())
                self.assertNotIn("..", PurePosixPath(value).parts)
                self.assertNotIn("\\", value)
            for field in ("audio_sha256", "labels_sha256", "source_manifest_sha256", "source_partition_plan_sha256"):
                self.assertRegex(row[field], sha_pattern)
            self.assertGreater(row["audio_size_bytes"], 0)
            self.assertGreater(row["labels_size_bytes"], 0)
            self.assertIn("audio_member_identity", row)
            self.assertEqual(row["labels_member_identity"], "")

    def test_fixed_execution_parameters_are_prepared_not_executed(self) -> None:
        parameters = self.preparation["execution_parameters_prepared_not_executed"]
        self.assertEqual(parameters["bootstrap_replicate_count"], 10000)
        self.assertEqual(parameters["bootstrap_seed_hex"], "2b033054")
        self.assertEqual(parameters["bootstrap_seed_decimal"], 721629268)
        self.assertEqual(parameters["minimum_valid_bootstrap_replicate_count"], 9500)
        self.assertEqual(parameters["minimum_valid_age1_observation_count"], 200)
        self.assertEqual(parameters["resampling_unit"], "leakage_group_key")
        self.assertEqual(parameters["minimum_class_count_beyond_h7"], None)
        self.assertEqual(set(self.preparation["implementation_state"].values()), {False})
        for name in (
            "scientific_execution_authorized", "metrics_computed", "targets_extracted",
            "signals_extracted", "locked_test_used", "consumed_v2_cohort_used",
        ):
            self.assertFalse(self.cohort[name])

    def test_checkout_is_forced_to_lf(self) -> None:
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for name in (
            "configs/provisional_resolution_age1_persistence_h8_preparation.json",
            "configs/provisional_resolution_age1_persistence_h8_selected_cohort.json",
        ):
            self.assertIn(f"{name} text eol=lf", attributes)


if __name__ == "__main__":
    unittest.main()
