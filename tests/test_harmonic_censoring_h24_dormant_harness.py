from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest

from src.polyphonic.harmonic_censoring_h24 import (
    H24_BINDING_SHA256,
    H24_HARNESS_CONTRACT_SHA256,
    H24_POPULATION_SHA256,
    H24_SUCCESSOR_SHA256,
    H24_TEST_SHA256,
    load_h24_dormant_harness_plan,
    require_h24_population_materialization_authorized,
    require_h24_scientific_execution_authorized,
    translate_all_h24_fixture_specifications,
    translate_h24_fixture_specification,
)
from src.polyphonic.harmonic_censoring_h24_operators import (
    require_h24_evidence_production_authorized,
)


class HarmonicCensoringH24DormantHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h24_dormant_harness_plan(cls.root)

    def test_loader_binds_exact_approved_artifacts(self) -> None:
        self.assertEqual(
            dict(self.plan.raw_sha256),
            {
                "successor": H24_SUCCESSOR_SHA256,
                "population": H24_POPULATION_SHA256,
                "test_manifest": H24_TEST_SHA256,
                "binding": H24_BINDING_SHA256,
                "harness_contract": H24_HARNESS_CONTRACT_SHA256,
            },
        )
        self.assertEqual(
            H24_HARNESS_CONTRACT_SHA256,
            hashlib.sha256(
                    (
                        self.root
                        / "configs/harmonic_censoring_h24_dormant_harness_contract.json"
                    ).read_bytes()
                ).hexdigest(),
        )
        self.assertEqual(len(self.plan.fixtures), 175)
        self.assertEqual(len(self.plan.tests), 72)
        self.assertEqual(len(self.plan.operator_registry), 27)
        self.assertEqual(set(self.plan.sentinel_registry), {"__PLAN_FIXTURE_IDS__"})

    def test_registry_is_exactly_one_dormant_entry_per_test(self) -> None:
        self.assertEqual(set(self.plan.evaluator_registry), set(self.plan.test_ids))
        self.assertEqual(len(self.plan.evaluator_registry), 72)
        for test_id, registration in self.plan.evaluator_registry.items():
            self.assertEqual(registration.test_id, test_id)
            self.assertFalse(registration.producer_callable)
            self.assertFalse(registration.scientific_evaluator_callable)
            self.assertIn("DORMANT", registration.producer_id)

    def test_all_175_specs_translate_to_immutable_recipes_without_waveforms(self) -> None:
        recipes = translate_all_h24_fixture_specifications(self.plan)
        self.assertEqual(len(recipes), 175)
        self.assertEqual(tuple(item.fixture_id for item in recipes), self.plan.fixture_ids)
        first = recipes[0]
        self.assertEqual(first.fixture_id, "H24-F-S1C")
        self.assertEqual(first.synthesis_seed, 4877250027711485546)
        with self.assertRaises(TypeError):
            first.variant_parameters["forbidden"] = 1  # type: ignore[index]
        self.assertEqual(
            first,
            translate_h24_fixture_specification(self.plan, first.fixture_id),
        )

    def test_every_execution_boundary_remains_unconditionally_closed(self) -> None:
        forged = replace(
            self.plan,
            flags=replace(
                self.plan.flags,
                population_materialization_authorized=True,
                waveform_synthesis_authorized=True,
                scientific_test_execution_authorized=True,
            ),
        )
        for boundary in (
            require_h24_population_materialization_authorized,
            require_h24_scientific_execution_authorized,
            require_h24_evidence_production_authorized,
        ):
            with self.assertRaises(PermissionError):
                boundary(forged)

    def test_replaced_or_directly_constructed_plan_is_not_attested(self) -> None:
        forged = replace(self.plan, tests=tuple(reversed(self.plan.tests)))
        with self.assertRaisesRegex(PermissionError, "not factory-attested"):
            translate_all_h24_fixture_specifications(forged)

    def test_sealed_artifact_byte_drift_fails_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            for relative in (
                "configs/harmonic_censoring_h24_dormant_harness_contract.json",
                "configs/harmonic_censoring_h24_successor_contract.json",
                "configs/harmonic_censoring_h24_population_manifest.json",
                "configs/harmonic_censoring_h24_test_manifest.json",
                "configs/harmonic_censoring_h24_manifest_binding_contract.json",
            ):
                source = self.root / relative
                target = temp / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            contract_path = (
                temp / "configs/harmonic_censoring_h24_dormant_harness_contract.json"
            )
            original_contract = contract_path.read_bytes()
            contract_path.write_bytes(original_contract + b" ")
            with self.assertRaisesRegex(
                ValueError, "dormant harness contract SHA-256 mismatch"
            ):
                load_h24_dormant_harness_plan(temp)
            contract_path.write_bytes(original_contract)
            path = temp / "configs/harmonic_censoring_h24_test_manifest.json"
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "test manifest SHA-256 mismatch"):
                load_h24_dormant_harness_plan(temp)

    def test_harness_has_no_scientific_dependency_or_cli(self) -> None:
        for relative in (
            "src/polyphonic/harmonic_censoring_h24.py",
            "src/polyphonic/harmonic_censoring_h24_operators.py",
        ):
            source = (self.root / relative).read_text(encoding="utf-8")
            for forbidden in (
                "import numpy",
                "import tensorflow",
                "from .data import",
                "from .train import",
                "if __name__ == \"__main__\"",
                "soundfile",
                "librosa",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
