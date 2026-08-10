from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import src.polyphonic.provisional_resolution_age1_h12 as h12
import src.polyphonic.provisional_resolution_age1_h13 as h13


ROOT = Path(__file__).resolve().parents[1]


def _hash_object(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


class H13ExecutionSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_path = ROOT / h13.H13_CONTRACT_RELATIVE
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))

    def test_contract_seals_reviewed_h12_and_corrected_sources(self) -> None:
        self.assertEqual(
            self.contract["accepted_h12"]["contract_raw_sha256"],
            "d1f9e80227776c8d6c81fc91d7a2df8982425eaadf786b7406ca54f33fa41fce",
        )
        self.assertEqual(
            self.contract["accepted_h12"]["reviewed_concrete_runner_blob"],
            "4aba24acc1d3a435285e7260485f1bd4a358bf61",
        )
        bindings = self.contract["source_bindings"]
        self.assertEqual(
            bindings["corrected_metric_blob"],
            _hash_object(ROOT / "src/polyphonic/provisional_resolution_age1_metrics.py"),
        )
        self.assertEqual(
            bindings["corrected_h12_binding_blob"],
            _hash_object(ROOT / "src/polyphonic/provisional_resolution_age1_h12.py"),
        )
        self.assertEqual(
            bindings["final_h13_runner_blob"],
            _hash_object(ROOT / "src/polyphonic/provisional_resolution_age1_h13.py"),
        )

    def test_h8_metadata_derives_exact_canonical_31_group_universe(self) -> None:
        records, _forbidden = h12._load_h8_metadata(ROOT / h12.H8_COHORT_RELATIVE)
        universe = h12.h8_group_universe(records)
        self.assertEqual(len(universe), 31)
        self.assertEqual(universe, tuple(sorted(universe)))
        self.assertEqual(len(set(universe)), 31)

    def test_real_entrypoint_has_no_scientific_parameters_and_binds_h13_marker(self) -> None:
        self.assertEqual(tuple(inspect.signature(h13.run_real_h7_discovery).parameters), ())
        source = inspect.getsource(h13.run_real_h7_discovery)
        self.assertIn("expected_contract_sha256=sha256_file(contract_path)", source)
        self.assertIn("group_universe = h12.h8_group_universe(records)", source)
        self.assertNotIn("cohort_group_universe=", inspect.signature(h13.run_real_h7_discovery).parameters)
        self.assertIn("provisional_resolution_age1_h13", inspect.getsource(h12.run_real_h7_discovery))

    def test_zero_science_preflight_uses_metadata_universe_only(self) -> None:
        records, forbidden = h12._load_h8_metadata(ROOT / h12.H8_COHORT_RELATIVE)
        base = {
            "status": "h7_real_execution_preflight_ready",
            "leakage_groups": 31,
            "scientific_execution_authorized": False,
            "execution_marker_created": False,
            "h8_scientific_assets_opened": False,
            "h8_discovery_consumed": False,
            "real_targets_extracted": False,
            "real_signals_extracted": False,
            "real_metrics_computed": False,
        }
        paths = type("Paths", (), {"h8_cohort": ROOT / h12.H8_COHORT_RELATIVE})()
        with patch.object(h12, "run_h12_preflight", return_value=base), \
             patch.object(h13, "require_h13_source_bindings", return_value=self.contract), \
             patch.object(h12, "sealed_h12_paths", return_value=paths), \
             patch.object(h12, "_load_h8_metadata", return_value=(records, forbidden)), \
             patch.object(h12.ConcreteH7ScientificAdapter, "open_recording") as opened, \
             patch.object(h12.ConcreteH7ScientificAdapter, "infer_once") as inferred, \
             patch.object(h12.ConcreteH7ScientificAdapter, "decode_once") as decoded, \
             patch.object(h12.ConcreteH7ScientificAdapter, "extract_targets") as targeted:
            result = h13.run_h13_preflight(ROOT, ROOT.parent)
        self.assertEqual(result["sealed_cohort_group_universe_count"], 31)
        self.assertFalse(result["h8_discovery_consumed"])
        self.assertFalse(result["scientific_execution_authorized"])
        for operation in (opened, inferred, decoded, targeted):
            operation.assert_not_called()

    def test_contract_is_nonexecuting_and_preserves_frozen_bootstrap(self) -> None:
        bootstrap = self.contract["bootstrap_conformance"]
        self.assertEqual(bootstrap["replicate_count"], 10000)
        self.assertEqual(bootstrap["seed"], 721629268)
        self.assertEqual(bootstrap["minimum_valid_replicates"], 9500)
        self.assertEqual(self.contract["sealed_group_universe"]["count"], 31)
        self.assertFalse(self.contract["sealed_group_universe"]["eligible_row_requirement_per_group"])
        self.assertTrue(all(value is False for value in self.contract["terminal_flags"].values()))


if __name__ == "__main__":
    unittest.main()
