from __future__ import annotations

from dataclasses import fields, replace
import copy
import hashlib
import json
from pathlib import Path
import pickle
import unittest

from src.polyphonic.harmonic_censoring_h27_engine import (
    H27EngineResult, H27RecordInvocation, run_h27_engine,
)
from src.polyphonic.harmonic_censoring_h27_recomputer import (
    H27RecomputedResult, H27RecomputerInvocation,
    compare_h27_engine_and_recomputer, run_h27_independent_recomputer,
)
from src.polyphonic.harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_engine_recomputer_contract.json"
ENGINE = ROOT / "src/polyphonic/harmonic_censoring_h27_engine.py"
RECOMPUTER = ROOT / "src/polyphonic/harmonic_censoring_h27_recomputer.py"
CAPABILITY = ROOT / "src/polyphonic/harmonic_censoring_h27_scientific_capability_dormant.py"


class _Exploding:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"unexpected access before capability: {name}")


class H27DormantEngineRecomputerTests(unittest.TestCase):
    def test_contract_binds_exact_dormant_source_blobs(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for binding in contract["dormant_implementation_bindings"].values():
            path = ROOT / binding["path"]
            raw = path.read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            self.assertEqual(actual, binding["git_blob_sha1"])

    def test_capability_has_no_constructor_copy_pickle_or_replace_path(self) -> None:
        with self.assertRaises(PermissionError):
            H27ScientificCapability()
        forged = object.__new__(H27ScientificCapability)
        with self.assertRaises(TypeError):
            copy.copy(forged)
        with self.assertRaises(TypeError):
            copy.deepcopy(forged)
        with self.assertRaises(TypeError):
            pickle.dumps(forged)
        with self.assertRaises(TypeError):
            replace(forged)  # type: ignore[arg-type]

    def test_both_public_boundaries_fail_before_numpy_invocation_or_filesystem(self) -> None:
        forged = object.__new__(H27ScientificCapability)
        for boundary in (run_h27_engine, run_h27_independent_recomputer):
            with self.assertRaisesRegex(PermissionError, "not issued"):
                boundary(_Exploding(), forged, _Exploding(), _Exploding())

    def test_engine_and_recomputer_descriptors_expose_only_scientific_inputs(self) -> None:
        expected = {
            "population_root", "record_directory", "record_identity",
            "population_namespace", "payload_sha256", "candidate_pitch",
            "active_pitches", "proposal_hop_end", "resolution_hop_end",
            "cents", "inharmonicity",
        }
        self.assertEqual({field.name for field in fields(H27RecordInvocation)}, expected)
        self.assertEqual({field.name for field in fields(H27RecomputerInvocation)}, expected)
        forbidden = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["engine_contract"]["static_leakage_aliases"])
        self.assertFalse(expected & forbidden)

    def test_recomputer_does_not_import_or_delegate_to_engine_or_historical_science(self) -> None:
        source = RECOMPUTER.read_text(encoding="utf-8")
        self.assertNotIn("harmonic_censoring_h27_engine", source)
        self.assertNotIn("harmonic_censoring_h26", source)
        self.assertNotIn("harmonic_censoring_h25", source)
        self.assertNotIn("run_h27_engine", source)
        self.assertIn("np.fft.rfft", source)
        self.assertIn("range(512)", source)

    def test_engine_is_self_contained_and_numpy_is_injected(self) -> None:
        source = ENGINE.read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("harmonic_censoring_h26", source)
        self.assertNotIn("harmonic_censoring_h25", source)
        for token in ("np.fft.rfft", "range(512)", "range(24, 97)", "/ 35.0", "0.8 * shared"):
            self.assertIn(token, source)

    def test_contract_marks_only_dormant_implementation_present(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertTrue(contract["engine_exists"])
        self.assertTrue(contract["recomputer_exists"])
        self.assertTrue(contract["engine_implementation_authorized"])
        self.assertTrue(contract["recomputer_implementation_authorized"])
        for field in (
            "materialization_authorized", "science_authorized", "execution_authorized",
            "authority_exists", "claim_exists", "capability_exists",
            "locked_test_authorized", "training_calibration_authorized",
        ):
            self.assertIs(contract[field], False)
        bindings = contract["dormant_implementation_bindings"]
        self.assertEqual(set(bindings), {"capability", "engine", "independent_recomputer", "tests"})

    def test_comparison_is_exact_for_discrete_fields_and_tolerant_only_for_finite_values(self) -> None:
        base = dict(
            record_identity="baseline/H27-F-P01",
            validated_payload_sha256={"waveform.f64le": "a" * 64},
            role_classifications={role: "VALID" for role in ("current_short", "previous_short", "current_long", "previous_long")},
            mask_counts={role: 1 for role in ("current_short", "previous_short", "current_long", "previous_long")},
            outcome="AMBIGUOUS", certificate_kind="NONE", certificate_complete=False,
            exclusive_partial_membership=(2, 3), exclusive_energy_ratios=(0.1, 0.2),
            onset_rise=0.1, residual_improvement=0.2, persistence=0.3,
            bounded_claim_lower_bounds=(0.4, 0.5), negative_margins=(4.0, 5.0),
            pitch_dilution_curve=((24, 0.1),), early_resolution_reason="certificate_gap_or_conflict",
            maximum_sample_read=16383,
        )
        engine = H27EngineResult(**base)
        recomputed = H27RecomputedResult(**base)
        compare_h27_engine_and_recomputer(engine, recomputed)
        close = replace(recomputed, onset_rise=0.1 + 1e-12)
        compare_h27_engine_and_recomputer(engine, close)
        with self.assertRaisesRegex(RuntimeError, "outcome"):
            compare_h27_engine_and_recomputer(engine, replace(recomputed, outcome="NO_BIRTH"))
        with self.assertRaisesRegex(RuntimeError, "onset_rise"):
            compare_h27_engine_and_recomputer(engine, replace(recomputed, onset_rise=0.2))

    def test_no_source_contains_runtime_issuer_or_execution_at_import(self) -> None:
        capability = CAPABILITY.read_text(encoding="utf-8")
        self.assertIn("_ISSUED_CAPABILITY_IDENTITIES: tuple[int, ...] = ()", capability)
        self.assertNotIn("def issue", capability)
        for path in (CAPABILITY, ENGINE, RECOMPUTER):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("locked_test", source)
            self.assertNotIn("tensorflow", source.lower())


if __name__ == "__main__":
    unittest.main()
