from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from src.polyphonic.harmonic_censoring_h23 import (
    H23_CONTRACT_RELATIVE_PATH,
    H23_CONTRACT_SHA256,
    fixture_seed,
    load_h23_harness_plan,
    require_h23_synthetic_execution_authorized,
)


class HarmonicCensoringH23HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h23_harness_plan(cls.root)

    def test_canonical_contract_is_lf_hash_bound_and_implementation_only(self) -> None:
        raw = (self.root / H23_CONTRACT_RELATIVE_PATH).read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), H23_CONTRACT_SHA256)
        flags = self.plan.flags
        self.assertTrue(flags.implementation_authorized)
        self.assertFalse(flags.synthetic_execution_authorized)
        self.assertFalse(flags.reviewed_synthetic_execution_authorized)
        self.assertFalse(flags.scientific_execution_authorized)
        self.assertFalse(flags.real_data_access_authorized)
        self.assertFalse(flags.training_authorized)
        self.assertFalse(flags.locked_test_used)

    def test_fixture_manifest_resolves_exact_closed_universe(self) -> None:
        plan = self.plan
        self.assertEqual(len(plan.fixtures), 175)
        self.assertEqual(len(set(plan.fixture_ids)), 175)
        self.assertEqual(
            plan.fixture_ids[:6], ("S1C", "S1P", "S2", "S3", "S4", "S5")
        )
        by_axis: dict[str | None, int] = {}
        for fixture in plan.fixtures:
            by_axis[fixture.variant_axis] = by_axis.get(fixture.variant_axis, 0) + 1
        self.assertEqual(
            by_axis,
            {
                None: 6,
                "amplitude_gain": 9,
                "relative_phase_radians": 6,
                "envelope_attack_decay_hops": 18,
                "cents_inharmonicity": 42,
                "noise": 24,
                "neighbour_semitones": 8,
                "interval_semitones": 4,
                "chord_spec": 4,
                "physical_unison": 2,
                "technique": 12,
                "natural_harmonic": 3,
                "sympathetic_resonance": 3,
                "old_source_age_hops": 12,
                "event_sample_offset": 12,
                "pitch_boundary": 3,
                "silence": 1,
                "synthetic_OOD": 6,
            },
        )

    def test_fixture_ids_seeds_specs_and_targets_are_deterministic(self) -> None:
        by_id = {item.fixture_id: item for item in self.plan.fixtures}
        fixture_id = "S2__cents_inharmonicity__m35__0p0001"
        self.assertIn(fixture_id, by_id)
        self.assertEqual(by_id[fixture_id].synthesis_seed, fixture_seed(fixture_id))
        self.assertEqual(
            hashlib.sha256(by_id[fixture_id].canonical_spec).hexdigest(),
            by_id[fixture_id].spec_sha256,
        )
        pending = by_id["S4__event_sample_offset__4095"].as_dict()
        self.assertEqual(
            pending["expected_target"]["target_hop_category"],
            "PENDING_NEW_AWAITING_ONE_HOP",
        )
        self.assertEqual(
            pending["expected_target"]["resolution_hop_category"],
            "BIRTH_SUPPORTED_DELAYED_ONE_HOP",
        )
        analytical = by_id["S2__pitch_boundary__analytical_128"].as_dict()
        self.assertFalse(analytical["expected_target"]["emission_pitch_valid"])
        self.assertFalse(analytical["expected_target"]["source_or_candidate_at_128"])
        unison = by_id["S2__physical_unison__distinct_envelopes_two_sources"].as_dict()
        self.assertEqual(unison["expected_target"]["K_source"], "AMBIGUOUS")

    def test_manifest_is_zero_science_and_byte_deterministic(self) -> None:
        again = load_h23_harness_plan(self.root)
        self.assertEqual(self.plan.fixture_manifest, again.fixture_manifest)
        self.assertEqual(
            self.plan.fixture_manifest_sha256, again.fixture_manifest_sha256
        )
        self.assertEqual(
            self.plan.fixture_manifest_sha256,
            "acfa37b987deb19884c9f60cf3410717b68788eb466396402aaf992b3224e19c",
        )
        self.assertEqual(
            self.plan.resolved_test_manifest_sha256,
            "0d059d3f2540f2b08279bb8363e9036ae0f71b2bea11575bfebfce76b7fe7504",
        )
        manifest = json.loads(self.plan.fixture_manifest)
        self.assertEqual(manifest["fixture_count"], 175)
        self.assertEqual(manifest["fixture_ids"], list(self.plan.fixture_ids))
        self.assertFalse(manifest["waveforms_synthesized"])
        self.assertFalse(manifest["tests_executed"])
        self.assertFalse(manifest["real_data_used"])
        self.assertFalse(manifest["h17_population_used"])
        self.assertFalse(manifest["locked_test_used"])
        self.assertFalse(manifest["fit_performed"])

    def test_module_has_no_scientific_runtime_dependency_or_cli(self) -> None:
        source = (
            self.root / "src/polyphonic/harmonic_censoring_h23.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import numpy",
            "import tensorflow",
            "from .data import",
            "from .train import",
            "if __name__ == \"__main__\"",
        ):
            self.assertNotIn(forbidden, source)

    def test_all_72_test_records_are_fully_resolved_in_mandatory_order(self) -> None:
        plan = self.plan
        self.assertEqual(len(plan.tests), 72)
        self.assertEqual(len(set(plan.test_ids)), 72)
        self.assertEqual(plan.test_ids[:3], ("A01", "A02", "A03"))
        self.assertEqual(plan.test_ids[-3:], ("P05", "TS01", "TS02"))
        expected_keys = {
            "id", "phase", "objective", "exact_input", "procedure", "oracle",
            "metrics", "pass_rule", "fail_rule", "artifacts", "drawback",
            "inverse_check",
        }
        phases = {"P0": 0, "P1": 0, "P2": 0}
        for test in plan.tests:
            self.assertEqual(set(test.as_dict()), expected_keys)
            self.assertEqual(
                hashlib.sha256(test.canonical_record).hexdigest(),
                test.resolved_sha256,
            )
            phases[test.phase] += 1
        self.assertEqual(phases, {"P0": 27, "P1": 35, "P2": 10})
        manifest = json.loads(plan.resolved_test_manifest)
        self.assertEqual(manifest["test_count"], 72)
        self.assertFalse(manifest["tests_executed"])

    def test_synthetic_execution_remains_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            PermissionError, "synthetic execution is not authorized"
        ):
            require_h23_synthetic_execution_authorized(self.plan)
        with self.assertRaises(TypeError):
            require_h23_synthetic_execution_authorized(object())  # type: ignore[arg-type]

    def test_forged_true_flags_cannot_authorize_execution(self) -> None:
        forged_flags = replace(
            self.plan.flags,
            synthetic_execution_authorized=True,
            reviewed_synthetic_execution_authorized=True,
        )
        forged_plan = replace(self.plan, flags=forged_flags)
        with self.assertRaisesRegex(
            PermissionError, "synthetic execution is not authorized"
        ):
            require_h23_synthetic_execution_authorized(forged_plan)

    def test_modified_or_crlf_contract_is_rejected_before_resolution(self) -> None:
        original = (self.root / H23_CONTRACT_RELATIVE_PATH).read_bytes()
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            path = root / H23_CONTRACT_RELATIVE_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(original.replace(b"\n", b"\r\n"))
            with self.assertRaisesRegex(ValueError, "must use LF"):
                load_h23_harness_plan(root)
            path.write_bytes(original.replace(b"175", b"176", 1))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_h23_harness_plan(root)


if __name__ == "__main__":
    unittest.main()
