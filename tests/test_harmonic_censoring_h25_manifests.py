from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class H25PopulationTestManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = Path(__file__).resolve().parents[1]
        cls.contract_path = (
            cls.repository
            / "configs/harmonic_censoring_h25_scientific_hypothesis_execution_contract.json"
        )
        cls.spec_path = (
            cls.repository / "configs/harmonic_censoring_h25_fixture_specifications.json"
        )
        cls.population_path = (
            cls.repository / "configs/harmonic_censoring_h25_population_manifest.json"
        )
        cls.test_path = (
            cls.repository / "configs/harmonic_censoring_h25_test_manifest.json"
        )
        cls.spec = json.loads(cls.spec_path.read_text(encoding="utf-8"))
        cls.population = json.loads(cls.population_path.read_text(encoding="utf-8"))
        cls.tests = json.loads(cls.test_path.read_text(encoding="utf-8"))

    def test_manifests_bind_exact_contract_and_specification_bytes(self) -> None:
        contract_sha = sha256(self.contract_path)
        spec_sha = sha256(self.spec_path)
        population_sha = sha256(self.population_path)
        self.assertEqual(
            contract_sha,
            "ae837a647792c56c02a7d96a4328f62c1ecac03d0c0a839d59488c420cfff911",
        )
        self.assertEqual(self.spec["contract_sha256"], contract_sha)
        self.assertEqual(self.population["contract_sha256"], contract_sha)
        self.assertEqual(self.population["fixture_specifications_sha256"], spec_sha)
        self.assertEqual(self.tests["contract_sha256"], contract_sha)
        self.assertEqual(self.tests["fixture_specifications_sha256"], spec_sha)
        self.assertEqual(self.tests["population_manifest_sha256"], population_sha)

    def test_fixture_ids_order_categories_families_and_bands_are_exact(self) -> None:
        fixtures = self.spec["fixtures"]
        ids = [item["id"] for item in fixtures]
        self.assertEqual(ids, self.population["ordered_fixture_ids"])
        self.assertEqual([item["order"] for item in fixtures], list(range(1, 37)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item.startswith("H25-F-") for item in ids))
        self.assertEqual(len(fixtures), 36)
        for key in ("category", "family", "pitch_band"):
            observed = Counter(item[key] for item in fixtures)
            self.assertEqual(dict(observed), self.spec["expected_counts"][key])
        self.assertEqual(
            self.spec["expected_counts"]["category"],
            self.population["exact_counts"]["category"],
        )
        self.assertEqual(
            self.spec["expected_counts"]["pitch_band"],
            self.population["exact_counts"]["pitch_band"],
        )

    def test_timeline_and_generation_parameters_are_deterministic_specs_only(self) -> None:
        timeline = self.spec["global_timeline"]
        formulas = self.spec["synthesis_formulas"]
        self.assertEqual(timeline["stream_samples"], 16640)
        self.assertEqual(timeline["target_short_window"], [12288, 16383])
        self.assertEqual(timeline["target_long_window"], [8192, 16383])
        self.assertEqual(timeline["resolution_hop_end"], 16639)
        self.assertTrue(timeline["padding_forbidden"])
        self.assertEqual(formulas["float_dtype"], "float64")
        self.assertIn("SHA256", formulas["noise_seed"])
        self.assertIn("Z[0]=complex128(0.0,0.0)", formulas["pink_noise"])
        noise = self.spec["noise_normalization_contract"]
        self.assertEqual(noise["active_support_start_inclusive"], 8192)
        self.assertEqual(noise["active_support_end_inclusive"], 16639)
        self.assertEqual(noise["active_support_count"], 8448)
        self.assertIn("same A={8192..16639}", noise["clean_reference_indices"])
        self.assertIn("direct assignment", noise["operation_4_unit_noise_and_exact_silence"])
        self.assertIn("bit-exact", noise["postcondition_pre_support"])
        self.assertEqual(
            noise["required_operation_order"],
            [
                "generate_ungated_u",
                "compute_mean_on_A_only",
                "subtract_mean_on_A_only",
                "compute_RMS_on_A_only",
                "normalize_on_A_and_directly_assign_positive_zero_outside_A",
                "compute_clean_RMS_on_exactly_A",
                "scale_to_SNR",
                "add_to_clean_mixture",
            ],
        )
        self.assertFalse(self.spec["generation_authorized"])
        self.assertEqual(
            formulas["WAV_cast_or_file_format"],
            "not_defined_and_not_authorized_in_this_specification_step",
        )
        bounds = self.spec["future_execution_operational_bounds"]
        self.assertEqual(bounds["wall_seconds_max"], 600)
        self.assertEqual(bounds["peak_RSS_bytes_max"], 4294967296)
        self.assertEqual(bounds["model_inference_call_count"], 0)

    def test_test_ids_phase_order_schema_and_counts_are_exact(self) -> None:
        tests = self.tests["tests"]
        expected_ids = [
            f"H25-T-{phase}-{index:03d}"
            for phase in ("P0", "P1", "P2")
            for index in range(1, 10)
        ]
        self.assertEqual([item["id"] for item in tests], expected_ids)
        self.assertEqual([item["order"] for item in tests], list(range(1, 28)))
        self.assertEqual(Counter(item["phase"] for item in tests), Counter(P0=9, P1=9, P2=9))
        schema = set(self.tests["test_record_schema"])
        for item in tests:
            self.assertEqual(set(item), schema)
        self.assertEqual(self.tests["fixed_phase_order"], ["P0", "P1", "P2"])
        self.assertTrue(self.tests["P1_requires_all_P0_pass"])
        self.assertTrue(self.tests["P2_requires_all_P1_pass"])

    def test_every_reference_is_unique_known_ordered_and_every_phase_is_exhaustive(self) -> None:
        population_ids = self.population["ordered_fixture_ids"]
        positions = {fixture_id: index for index, fixture_id in enumerate(population_ids)}
        phase_union = {phase: set() for phase in ("P0", "P1", "P2")}
        for item in self.tests["tests"]:
            refs = item["fixture_ids"]
            self.assertEqual(len(refs), len(set(refs)), item["id"])
            self.assertTrue(set(refs).issubset(positions), item["id"])
            self.assertEqual(
                [positions[fixture_id] for fixture_id in refs],
                sorted(positions[fixture_id] for fixture_id in refs),
                item["id"],
            )
            phase_union[item["phase"]].update(refs)
        for phase in ("P0", "P1", "P2"):
            self.assertEqual(phase_union[phase], set(population_ids), phase)

    def test_P1_covers_each_fixture_once_and_balances_oracle_categories(self) -> None:
        p1_refs = [
            fixture_id
            for item in self.tests["tests"]
            if item["phase"] == "P1"
            for fixture_id in item["fixture_ids"]
        ]
        self.assertEqual(p1_refs, self.population["ordered_fixture_ids"])
        category_by_id = {item["id"]: item["category"] for item in self.spec["fixtures"]}
        counts = Counter(category_by_id[fixture_id] for fixture_id in p1_refs)
        self.assertEqual(dict(counts), {"positive": 12, "negative": 12, "ambiguous": 12})
        self.assertEqual(
            dict(counts), self.tests["exact_counts"]["P1_fixture_category_coverage"]
        )

    def test_scope_remains_manifest_only_with_no_scientific_execution(self) -> None:
        self.assertFalse(self.population["materialized"])
        self.assertEqual(self.population["waveform_count"], 0)
        self.assertFalse(self.tests["executed"])
        self.assertIn("materialize_float_arrays_or_waveforms", self.spec["forbidden_now"])
        self.assertIn("execute_any_test", self.tests["forbidden_now"])
        self.assertIn(
            "H17_H23_H24_ID_or_byte_reuse_forbidden",
            self.population,
        )


if __name__ == "__main__":
    unittest.main()
