from __future__ import annotations

from dataclasses import fields, replace
import copy
import hashlib
import json
from pathlib import Path
import pickle
import unittest

from src.polyphonic.harmonic_censoring_h27_engine import (
    H27EngineResult, run_h27_engine,
)
from src.polyphonic.harmonic_censoring_h27_recomputer import (
    EXACT_RESULT_FIELDS, NUMERIC_RESULT_FIELDS, H27RecomputedResult,
    compare_h27_engine_and_recomputer, run_h27_independent_recomputer,
)
import src.polyphonic.harmonic_censoring_h27_scientific_capability_dormant as capability_module
from src.polyphonic.harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
    H27_SEALED_RECORD_BINDING_FIELDS, require_h27_sealed_record_binding,
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

    def test_rebinding_cannot_register_forged_capability_or_record_binding(self) -> None:
        forged_capability = object.__new__(H27ScientificCapability)
        forged_binding = object.__new__(H27SealedRecordBinding)
        capability_module._ISSUED_CAPABILITY_IDENTITIES = (id(forged_capability),)
        capability_module._ISSUED_RECORD_BINDING_IDENTITIES = (id(forged_binding),)
        try:
            for boundary in (run_h27_engine, run_h27_independent_recomputer):
                with self.assertRaisesRegex(PermissionError, "not issued"):
                    boundary(_Exploding(), forged_capability, _Exploding(), forged_binding)
            with self.assertRaisesRegex(PermissionError, "not issued"):
                require_h27_sealed_record_binding(forged_binding)
        finally:
            del capability_module._ISSUED_CAPABILITY_IDENTITIES
            del capability_module._ISSUED_RECORD_BINDING_IDENTITIES

    def test_both_public_boundaries_fail_before_numpy_invocation_or_filesystem(self) -> None:
        forged = object.__new__(H27ScientificCapability)
        for boundary in (run_h27_engine, run_h27_independent_recomputer):
            with self.assertRaisesRegex(PermissionError, "not issued"):
                boundary(_Exploding(), forged, _Exploding(), _Exploding())

    def test_record_binding_is_closed_unconstructible_and_matches_contract(self) -> None:
        with self.assertRaises(PermissionError):
            H27SealedRecordBinding()
        forged = object.__new__(H27SealedRecordBinding)
        with self.assertRaises(TypeError):
            copy.copy(forged)
        with self.assertRaises(TypeError):
            pickle.dumps(forged)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        expected = tuple(contract["future_record_contract"]["sealed_record_binding_field_order"])
        self.assertEqual(H27_SEALED_RECORD_BINDING_FIELDS, expected)
        forbidden = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["engine_contract"]["static_leakage_aliases"])
        self.assertFalse(set(expected) & forbidden)
        self.assertIn("population_index_sha256", expected)
        self.assertIn("population_index_record_sha256", expected)

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

    def test_result_schema_exactly_matches_both_results_and_comparator(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))["engine_contract"]
        expected = tuple(contract["result_field_order"])
        self.assertEqual(tuple(contract["result_schema"]), expected)
        self.assertEqual(tuple(field.name for field in fields(H27EngineResult)), expected)
        self.assertEqual(tuple(field.name for field in fields(H27RecomputedResult)), expected)
        compared = EXACT_RESULT_FIELDS + NUMERIC_RESULT_FIELDS
        self.assertEqual(len(compared), len(set(compared)))
        self.assertEqual(set(compared), set(expected))

    def test_no_source_contains_runtime_issuer_or_execution_at_import(self) -> None:
        capability = CAPABILITY.read_text(encoding="utf-8")
        self.assertNotIn("_ISSUED_CAPABILITY_IDENTITIES:", capability)
        self.assertIn('raise PermissionError("H27 scientific capability is not issued.")', capability)
        self.assertIn('raise PermissionError("H27 sealed record binding is not issued.")', capability)
        self.assertNotIn("def issue", capability)
        for path in (CAPABILITY, ENGINE, RECOMPUTER):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("locked_test", source)
            self.assertNotIn("tensorflow", source.lower())


if __name__ == "__main__":
    unittest.main()
