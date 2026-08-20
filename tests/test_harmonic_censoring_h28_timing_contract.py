from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h28_timing_contract as h28


ROOT = Path(__file__).resolve().parents[1]


def _outcomes(*, p01_birth: str | None = None, n01_birth: str | None = None):
    values = OrderedDict((identity, "AMBIGUOUS") for identity in h28.RECORD_ORDER)
    if p01_birth is not None:
        values[f"H27-F-P01/{p01_birth}"] = "BIRTH_SUPPORTED"
    if n01_birth is not None:
        values[f"H27-F-N01/{n01_birth}"] = "BIRTH_SUPPORTED"
    return values


def _positive_diagnostic_record():
    return dict((
        ("record_identity", "H27-F-P01/N_PLUS_1"),
        ("fixture_id", "H27-F-P01"),
        ("horizon_id", "N_PLUS_1"),
        ("proposal_hop_end", 16639),
        ("maximum_sample_read", 16639),
        ("role_classifications", dict((
            ("current_short", "VALID_CURRENT_SHORT_ANALYSIS"),
            ("previous_short", "VALID_PREVIOUS_SHORT_ANALYSIS"),
            ("current_long", "VALID_CURRENT_LONG_ANALYSIS"),
            ("previous_long", "VALID_PREVIOUS_LONG_ANALYSIS"),
        ))),
        ("mask_counts", dict((
            ("current_short", 4096),
            ("previous_short", 4096),
            ("current_long", 8192),
            ("previous_long", 8192),
        ))),
        ("current_short_total_power", 2.0),
        ("previous_short_total_power", 1.0),
        ("current_long_total_power", 2.5),
        ("previous_long_total_power", 1.5),
        ("exclusive_ranks", [2, 3]),
        ("exclusive_band_energies", [0.06, 0.06]),
        ("harmonic_ratios", [0.03, 0.03]),
        ("ratios_at_or_above_positive_threshold", 2),
        ("onset_rise", 0.5),
        ("active_residual_before_candidate", 1.0),
        ("augmented_residual_after_candidate", 0.5),
        ("residual_improvement", 0.5),
        ("persistence", 0.4),
        ("bounded_claim_lower_bounds", [0.01, 0.01]),
        ("negative_margins", [0.3, 0.3]),
        ("positive_partial_condition", True),
        ("positive_onset_condition", True),
        ("positive_residual_condition", True),
        ("negative_partial_condition", False),
        ("negative_onset_condition", False),
        ("negative_residual_condition", False),
        ("outcome", "BIRTH_SUPPORTED"),
        ("certificate_kind", "POSITIVE"),
        ("certificate_complete", True),
        ("decision_reason", "complete_positive_certificate"),
        ("waveform_sha256", "a" * 64),
        ("mask_sha256", "b" * 64),
    ))


class H28TimingContractTests(unittest.TestCase):
    def test_repository_contract_is_dormant_complete_and_byte_bound(self):
        contract = h28.load_h28_timing_contract(ROOT)
        self.assertEqual(
            contract.raw_sha256,
            "7b42080ee96a40c23805c7eae946650b065ca8c252d6560f996ca4a61045bac2",
        )
        self.assertEqual(
            tuple(item.causal_samples_after_onset for item in contract.horizons),
            (256, 512, 768),
        )
        self.assertEqual(
            tuple(item.proposal_hop_end for item in contract.horizons),
            (16383, 16639, 16895),
        )
        self.assertEqual(contract.diagnostic_fields, h28.REQUIRED_DIAGNOSTIC_FIELDS)
        authorization = contract.document["authorization_boundary"]
        self.assertFalse(authorization["scientific_execution_authorized"])
        self.assertFalse(authorization["population_materialization_authorized"])
        self.assertFalse(authorization["locked_test_authorized"])

    def test_contract_preserves_h27_science_and_adds_inverse_safety(self):
        document = h28.load_h28_timing_contract(ROOT).document
        science = document["unchanged_science"]
        self.assertEqual(science["window"], "Hann")
        self.assertEqual(science["fft_zero_padding_multiplier"], 8)
        self.assertEqual(science["partial_band_half_width_cents"], 35.0)
        self.assertEqual(science["nnls_iterations"], 512)
        self.assertEqual(science["positive_minimum_exclusive_energy_ratio"], 0.02)
        self.assertEqual(science["positive_minimum_onset_rise"], 0.05)
        self.assertEqual(science["positive_minimum_residual_improvement"], 0.1)
        self.assertTrue(document["evaluation_contract"]["n01_birth_at_any_horizon_is_safety_failure"])

    def test_diagnostics_close_the_h27_forensic_gap(self):
        required = set(h28.REQUIRED_DIAGNOSTIC_FIELDS)
        self.assertTrue({
            "exclusive_ranks",
            "exclusive_band_energies",
            "harmonic_ratios",
            "onset_rise",
            "active_residual_before_candidate",
            "augmented_residual_after_candidate",
            "residual_improvement",
            "persistence",
            "positive_partial_condition",
            "positive_onset_condition",
            "positive_residual_condition",
            "maximum_sample_read",
        } <= required)

    def test_future_diagnostic_record_is_self_reconciling(self):
        contract = h28.load_h28_timing_contract(ROOT)
        record = _positive_diagnostic_record()
        validated = h28.validate_h28_diagnostic_record(contract, record)
        self.assertEqual(validated["outcome"], "BIRTH_SUPPORTED")
        corrupted = dict(record)
        corrupted["positive_residual_condition"] = False
        with self.assertRaisesRegex(ValueError, "derived condition inconsistent"):
            h28.validate_h28_diagnostic_record(contract, corrupted)

    def test_future_diagnostic_record_cannot_read_future(self):
        contract = h28.load_h28_timing_contract(ROOT)
        record = _positive_diagnostic_record()
        record["maximum_sample_read"] = 16640
        with self.assertRaisesRegex(ValueError, "must equal the causal horizon"):
            h28.validate_h28_diagnostic_record(contract, record)

    def test_first_positive_horizon_is_reported(self):
        self.assertEqual(
            h28.derive_h28_terminal_verdict(_outcomes(p01_birth="N_PLUS_1")),
            "H28_P01_FIRST_SUPPORTED_AT_N_PLUS_1",
        )
        values = _outcomes(p01_birth="N")
        values["H27-F-P01/N_PLUS_1"] = "BIRTH_SUPPORTED"
        values["H27-F-P01/N_PLUS_2"] = "BIRTH_SUPPORTED"
        self.assertEqual(
            h28.derive_h28_terminal_verdict(values),
            "H28_P01_FIRST_SUPPORTED_AT_N",
        )

    def test_negative_control_failure_has_precedence(self):
        values = _outcomes(p01_birth="N_PLUS_1", n01_birth="N_PLUS_2")
        self.assertEqual(
            h28.derive_h28_terminal_verdict(values),
            "H28_NEGATIVE_CONTROL_BECAME_BIRTH_SUPPORTED",
        )

    def test_no_positive_through_last_horizon_is_explicit(self):
        self.assertEqual(
            h28.derive_h28_terminal_verdict(_outcomes()),
            "H28_TIMING_INSUFFICIENT_THROUGH_N_PLUS_2",
        )

    def test_outcome_order_and_state_space_are_fail_closed(self):
        reversed_values = OrderedDict(reversed(tuple(_outcomes().items())))
        with self.assertRaisesRegex(ValueError, "exact sealed record order"):
            h28.derive_h28_terminal_verdict(reversed_values)
        invalid = _outcomes()
        invalid["H27-F-P01/N"] = "ALREADY_ACTIVE_HISTORY"
        with self.assertRaisesRegex(ValueError, "outside the timing-study state space"):
            h28.derive_h28_terminal_verdict(invalid)

    def test_mutated_threshold_is_rejected_without_population_access(self):
        source = json.loads((ROOT / h28.CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8"))
        source["unchanged_science"]["positive_minimum_residual_improvement"] = 0.099
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / h28.CONTRACT_RELATIVE_PATH
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(h28, "_require_dependency"):
                with self.assertRaisesRegex(ValueError, "inherited science changed"):
                    h28.load_h28_timing_contract(root)

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            h28._strict_json(b'{"schema_version":1,"schema_version":1}', label="test")


if __name__ == "__main__":
    unittest.main()
