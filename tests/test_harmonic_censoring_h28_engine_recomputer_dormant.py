from __future__ import annotations

import ast
import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import pickle
from types import MappingProxyType, SimpleNamespace
import unittest

from src.polyphonic import harmonic_censoring_h28_engine as engine
from src.polyphonic import harmonic_censoring_h28_recomputer as recomputer
from src.polyphonic.harmonic_censoring_h28_diagnostics import (
    serialize_h28_reconciled_diagnostic,
)
from src.polyphonic.harmonic_censoring_h28_scientific_capability_dormant import (
    H28ScientificCapability,
    H28SealedRecordBinding,
)
from src.polyphonic.harmonic_censoring_h28_timing_contract import (
    load_h28_timing_contract,
)
from src.polyphonic import harmonic_censoring_h28_timing_contract as timing


ROOT = Path(__file__).resolve().parents[1]


def _result_kwargs() -> dict[str, object]:
    return {
        "record_identity": "H27-F-P01/N_PLUS_1",
        "validated_payload_sha256": MappingProxyType({
            "waveform.f64le": "a" * 64,
            "sample-valid-mask.u8": "b" * 64,
        }),
        "role_classifications": MappingProxyType({
            "current_short": "VALID_CURRENT_SHORT_ANALYSIS",
            "previous_short": "VALID_PREVIOUS_SHORT_ANALYSIS",
            "current_long": "VALID_CURRENT_LONG_ANALYSIS",
            "previous_long": "VALID_PREVIOUS_LONG_ANALYSIS",
        }),
        "mask_counts": MappingProxyType({
            "current_short": 4096,
            "previous_short": 4096,
            "current_long": 8192,
            "previous_long": 8192,
        }),
        "current_short_total_power": 2.0,
        "previous_short_total_power": 1.0,
        "current_long_total_power": 2.5,
        "previous_long_total_power": 1.5,
        "outcome": "BIRTH_SUPPORTED",
        "certificate_kind": "POSITIVE",
        "certificate_complete": True,
        "exclusive_ranks": (2, 3),
        "exclusive_band_energies": (0.06, 0.06),
        "harmonic_ratios": (0.03, 0.03),
        "ratios_at_or_above_positive_threshold": 2,
        "onset_rise": 0.5,
        "active_residual_before_candidate": 1.0,
        "augmented_residual_after_candidate": 0.5,
        "residual_improvement": 0.5,
        "persistence": 0.4,
        "bounded_claim_lower_bounds": (0.01, 0.01),
        "negative_margins": (1.0 / 3.0, 1.0 / 3.0),
        "pitch_dilution_curve": tuple(
            (pitch, 0.5 if pitch == 40 else 0.0) for pitch in range(24, 97)
        ),
        "positive_partial_condition": True,
        "positive_onset_condition": True,
        "positive_residual_condition": True,
        "negative_partial_condition": False,
        "negative_onset_condition": False,
        "negative_residual_condition": False,
        "decision_reason": "complete_positive_certificate",
        "maximum_sample_read": 16639,
    }


def _function_ast(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    return ast.dump(node, include_attributes=False)


class _ExplodingScientificDependency:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"scientific dependency was touched: {name}")


class H28DormantEngineRecomputerTests(unittest.TestCase):
    def test_byte_exact_dormant_implementation_contract(self):
        contract_path = ROOT / "configs/harmonic_censoring_h28_engine_recomputer_dormant_contract.json"
        raw = contract_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "784100a20890a7ba15d1d43e79009b39469e7b60e5132efa78e7934878a35ed8",
        )
        document = timing._strict_json(raw, label="H28 dormant implementation contract")
        self.assertIs(type(document), dict)
        self.assertEqual(document["schema_identity"], "H28_DORMANT_ENGINE_RECOMPUTER_DESIGN_V1")
        self.assertEqual(document["status"], "IMPLEMENTED_DORMANT_NO_POPULATION_NO_SCIENCE")
        for item in document["dormant_implementation_bindings"]:
            path = ROOT / item["path"]
            payload = path.read_bytes()
            blob = hashlib.sha1(
                b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
            ).hexdigest()
            self.assertEqual(len(payload), item["size_bytes"], item["path"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"], item["path"])
            self.assertEqual(blob, item["git_blob"], item["path"])
        authorization = document["authorization_boundary"]
        self.assertTrue(all(value is False for value in authorization.values()))

    def test_capability_and_binding_have_no_public_issuer_or_copy_path(self):
        for nominal_type in (H28ScientificCapability, H28SealedRecordBinding):
            with self.assertRaisesRegex(PermissionError, "no (issuer|loader)"):
                nominal_type()
            forged = object.__new__(nominal_type)
            with self.assertRaises(TypeError):
                copy.copy(forged)
            with self.assertRaises(TypeError):
                copy.deepcopy(forged)
            with self.assertRaises(TypeError):
                pickle.dumps(forged)

    def test_public_engine_fails_before_numpy_contract_or_filesystem(self):
        exploding = _ExplodingScientificDependency()
        with self.assertRaisesRegex(PermissionError, "not issued"):
            engine.run_h28_engine(exploding, object(), exploding, exploding)

    def test_public_recomputer_fails_before_numpy_contract_or_filesystem(self):
        exploding = _ExplodingScientificDependency()
        with self.assertRaisesRegex(PermissionError, "not issued"):
            recomputer.run_h28_independent_recomputer(exploding, object(), exploding, exploding)

    def test_engine_and_recomputer_use_extended_geometry_only(self):
        self.assertEqual(engine.WAVEFORM_SAMPLES, 17152)
        self.assertEqual(engine.ROLE_MAJOR_MASK_VALUES, 68608)
        self.assertEqual(engine.MAXIMUM_PROPOSAL_HOP_END, 16895)
        self.assertEqual(recomputer._WAVEFORM_SAMPLES, 17152)
        self.assertEqual(recomputer._ROLE_MAJOR_MASK_VALUES, 68608)
        self.assertEqual(recomputer._MAXIMUM_PROPOSAL_HOP_END, 16895)

    def test_record_identity_cannot_be_rebound_to_another_horizon(self):
        contract = load_h28_timing_contract(ROOT)
        mismatched = SimpleNamespace(
            record_identity="H27-F-P01/N_PLUS_1",
            proposal_hop_end=16895,
            resolution_hop_end=17151,
        )
        with self.assertRaisesRegex(ValueError, "identity and causal coordinates differ"):
            engine._require_record_geometry(contract, mismatched)
        with self.assertRaisesRegex(ValueError, "identity and causal coordinates differ"):
            recomputer._require_record_geometry(contract, mismatched)

    def test_scientific_primitives_are_ast_identical_to_h27(self):
        pairs = (
            ("engine", (
                "_spectrum", "_f0", "_center", "_kernel", "_band",
                "_exclusive_ranks", "_basis", "_residual",
            )),
            ("recomputer", (
                "_independent_spectrum", "_frequency", "_weights", "_energy",
                "_exclusive", "_independent_residual",
            )),
        )
        for suffix, function_names in pairs:
            h27_source = (ROOT / f"src/polyphonic/harmonic_censoring_h27_{suffix}.py").read_text(
                encoding="utf-8"
            )
            h28_source = (ROOT / f"src/polyphonic/harmonic_censoring_h28_{suffix}.py").read_text(
                encoding="utf-8"
            ).replace("H28", "H27").replace("h28", "h27")
            for function_name in function_names:
                with self.subTest(suffix=suffix, function=function_name):
                    self.assertEqual(
                        _function_ast(h28_source, function_name),
                        _function_ast(h27_source, function_name),
                    )

    def test_recomputer_compares_every_raw_and_derived_diagnostic(self):
        values = _result_kwargs()
        primary = engine.H28EngineResult(**values)
        independent = recomputer.H28RecomputedResult(**values)
        recomputer.compare_h28_engine_and_recomputer(primary, independent)
        with self.assertRaisesRegex(RuntimeError, "current_short_total_power"):
            recomputer.compare_h28_engine_and_recomputer(
                primary,
                replace(independent, current_short_total_power=2.1),
            )
        with self.assertRaisesRegex(RuntimeError, "positive_partial_condition"):
            recomputer.compare_h28_engine_and_recomputer(
                primary,
                replace(independent, positive_partial_condition=False),
            )

    def test_serializer_emits_and_revalidates_complete_closed_schema(self):
        values = _result_kwargs()
        primary = engine.H28EngineResult(**values)
        independent = recomputer.H28RecomputedResult(**values)
        row = serialize_h28_reconciled_diagnostic(
            load_h28_timing_contract(ROOT), primary, independent
        )
        self.assertEqual(row["record_identity"], "H27-F-P01/N_PLUS_1")
        self.assertEqual(row["pitch_dilution_curve"][0], [24, 0.0])
        self.assertEqual(dict(row["pitch_dilution_curve"])[40], 0.5)
        self.assertEqual(row["pitch_dilution_curve"][-1], [96, 0.0])

    def test_serializer_refuses_missing_diagnostic_even_when_results_agree(self):
        values = _result_kwargs()
        values["pitch_dilution_curve"] = None
        primary = engine.H28EngineResult(**values)
        independent = recomputer.H28RecomputedResult(**values)
        with self.assertRaisesRegex(ValueError, "pitch_dilution_curve"):
            serialize_h28_reconciled_diagnostic(
                load_h28_timing_contract(ROOT), primary, independent
            )


if __name__ == "__main__":
    unittest.main()
