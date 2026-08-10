import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "configs/provisional_resolution_frame_fallback_h18_metadata_audit.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class FrameFallbackH18MetadataAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    def test_sources_and_frozen_bindings(self) -> None:
        audit = self.audit
        self.assertEqual(audit["schema_version"], 1)
        self.assertEqual(
            audit["status"], "fresh_discovery_population_established"
        )
        self.assertEqual(
            audit["h18a_provenance_resolution"]["status"],
            "checkpoint_fit_group_provenance_established",
        )
        self.assertFalse(
            audit["h18a_provenance_resolution"]["scientific_execution_authorized"]
        )
        self.assertEqual(
            audit["h17"]["commit"],
            "3a3e65ab532a4983fadae89c842b544228c3b028",
        )
        self.assertEqual(
            audit["grouping"]["git_blob"],
            "e43187b4e8ba0775a74114faf406703dd6c3187c",
        )
        for name in ("h8_cohort", "independent_v2_protocol"):
            source = audit["source_metadata"][name]
            path = ROOT / source["path"]
            self.assertEqual(path.stat().st_size, source["size_bytes"])
            self.assertEqual(_sha256(path), source["sha256"])
        h17 = ROOT / audit["h17"]["contract_path"]
        self.assertEqual(_sha256(h17), audit["h17"]["contract_sha256"])
        self.assertEqual(_git_blob(h17), audit["h17"]["contract_git_blob"])
        self.assertEqual(
            _git_blob(ROOT / "src/polyphonic/decoder_candidate_provenance.py"),
            audit["grouping"]["git_blob"],
        )

    def test_checkpoint_fit_provenance_is_exact_and_full_train(self) -> None:
        provenance = self.audit["checkpoint_fit_provenance"]
        self.assertEqual(
            provenance["checkpoint_sha256"],
            "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325",
        )
        self.assertTrue(provenance["exact_group_provenance_established"])
        self.assertEqual(provenance["fit_partition"], "train")
        self.assertEqual(provenance["fit_recording_count"], 572)
        self.assertEqual(provenance["fit_leakage_group_count"], 219)
        self.assertEqual(
            len(set(provenance["fit_leakage_group_keys"])), 219
        )
        evidence = provenance["evidence"]
        self.assertEqual(
            evidence["transaction_manifest_sha256"],
            "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7",
        )
        self.assertEqual(
            evidence["transaction_plan_sha256"],
            "d039ac2cfba31cc9560f80ed2da7230c1d039ef9dbaea38d56574d4c0b550714",
        )
        self.assertEqual(evidence["transaction_completed_epochs"], 7)
        self.assertEqual(evidence["union_unique_train_recording_indices"], 572)
        self.assertEqual(evidence["missing_train_recording_indices"], [])
        self.assertEqual(
            evidence["unique_train_recordings_per_epoch_1_through_7"],
            {str(epoch): 572 for epoch in range(1, 8)},
        )
        source_files = evidence["source_files"]
        self.assertEqual(
            source_files["epoch7_checkpoint"]["sha256"],
            provenance["checkpoint_sha256"],
        )
        self.assertEqual(
            source_files["epoch7_transaction"]["sha256"],
            "ff0e2c1aeadf551c2dcce200bd2617ac57c34cf0d363c0754e5517a3f89427ef",
        )

    def test_exact_set_subtraction_and_minimum(self) -> None:
        audit = self.audit
        candidate = audit["candidate_universe"]
        self.assertEqual(candidate["recording_count"], 754)
        self.assertEqual(candidate["leakage_group_count"], 285)
        self.assertEqual(candidate["missing_declared_asset_recording_count"], 0)

        memberships = audit["candidate_group_membership"]
        self.assertEqual(len(memberships), 285)
        self.assertEqual(
            len({row["leakage_group_key"] for row in memberships}), 285
        )
        for row in memberships:
            self.assertEqual(row["fresh"], not row["exclusion_reasons"])

        fresh = audit["fresh_discovery_population"]
        fresh_rows = [row for row in memberships if row["fresh"]]
        self.assertEqual(fresh["leakage_group_count"], 51)
        self.assertEqual(len(fresh_rows), 51)
        self.assertEqual(fresh["recording_count"], 146)
        self.assertTrue(fresh["minimum_met"])
        self.assertGreaterEqual(
            fresh["leakage_group_count"], fresh["minimum_required_leakage_groups"]
        )
        self.assertEqual(fresh["recordings_by_split"], {"validation": 146})
        self.assertEqual(
            sum(group["recording_count"] for group in fresh["groups"]), 146
        )
        self.assertEqual(
            {group["leakage_group_key"] for group in fresh["groups"]},
            {row["leakage_group_key"] for row in fresh_rows},
        )

    def test_forbidden_sets_match_sealed_h8_metadata(self) -> None:
        h8 = json.loads(
            (ROOT / "configs/provisional_resolution_age1_persistence_h8_selected_cohort.json")
            .read_text(encoding="utf-8")
        )
        forbidden = self.audit["forbidden_group_sets"]
        expected_h8 = {row["leakage_group_key"] for row in h8["recordings"]}
        expected_v2 = set(
            h8["forbidden_cohorts"]["consumed_v2"]["leakage_group_keys"]
        )
        expected_locked = set(
            h8["forbidden_cohorts"]["locked_test"]["leakage_group_keys"]
        )
        self.assertEqual(set(forbidden["h8_consumed"]["leakage_group_keys"]), expected_h8)
        self.assertEqual(
            set(forbidden["consumed_independent_v2"]["leakage_group_keys"]),
            expected_v2,
        )
        self.assertEqual(
            set(forbidden["locked_test"]["leakage_group_keys"]), expected_locked
        )

    def test_zero_scientific_execution_and_no_consumption(self) -> None:
        flags = self.audit["execution_flags"]
        self.assertTrue(flags)
        self.assertTrue(all(value is False for value in flags.values()))
        self.assertEqual(
            self.audit["next_action"],
            "external_review_before_any_h19_contract_or_scientific_execution",
        )


if __name__ == "__main__":
    unittest.main()
