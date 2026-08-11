from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import src.polyphonic.harmonic_censoring_h26_engine as h26_engine_module
import src.polyphonic.harmonic_censoring_h26_materializer as h26_materializer_module

from src.polyphonic.harmonic_censoring_h26_contract import (
    FIXTURE_SPECIFICATIONS_SHA256,
    SCIENTIFIC_CONTRACT_SHA256,
    TEST_MANIFEST_SHA256,
    _validate_recipe,
    deep_thaw_json,
    load_h26_dormant_plan,
)
from src.polyphonic.harmonic_censoring_h26_engine import (
    H26Measurements,
    H26NumericalPolicy,
    H26RawOperands,
    H26ScientificCapability,
    produce_h26_fixture_evidence,
    causal_spectrum,
    extract_causal_view,
    fixed_nnls_v1,
    measurements_from_raw_operands,
    nonzero_observations_are_byte_equivalent,
    begin_h26_causal_proposal,
    finish_h26_causal_proposal,
    p2_cells,
    partial_center_hz,
    pitch_dilution_pitch_order,
    required_support_is_valid,
    require_h26_scientific_execution_authorized,
    resolve_h26,
)
from src.polyphonic.harmonic_censoring_h26_materializer import (
    H26BoundObservation,
    H26MaterializationCapability,
    bind_h26_population_observation,
    build_h26_p2_transform,
    materialize_h26_population,
)
from src.polyphonic.harmonic_censoring_h26_recomputer import (
    H26TranscriptRecord,
    recompute_h26_evidence_from_raw_operands,
    recompute_h26_resolution,
    validate_transcript_prefix,
)


class H26DormantStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h26_dormant_plan(cls.root)
        cls.policy = H26NumericalPolicy.from_plan(cls.plan)

    def test_plan_binds_three_blobs_and_exact_34_plus_6_population(self) -> None:
        self.assertEqual(len(SCIENTIFIC_CONTRACT_SHA256), 64)
        self.assertEqual(len(FIXTURE_SPECIFICATIONS_SHA256), 64)
        self.assertEqual(len(TEST_MANIFEST_SHA256), 64)
        self.assertEqual(len(self.plan.fixture_ids), 40)
        self.assertEqual(len(self.plan.recipes), 34)
        self.assertEqual(len(self.plan.collision_fixture_ids), 6)
        self.assertEqual(set(self.plan.recipes) | set(self.plan.collision_fixture_ids), set(self.plan.fixture_ids))
        self.assertFalse(set(self.plan.recipes) & set(self.plan.collision_fixture_ids))
        self.assertEqual(len(self.plan.test_ids), 27)
        self.assertEqual([test.phase for test in self.plan.tests], ["P0"] * 9 + ["P1"] * 9 + ["P2"] * 9)
        self.assertTrue(all(value is False for value in self.plan.contract["authorization_boundary"].values()))

    def test_recipe_validation_fails_before_allocation_on_missing_or_divergent_fields(self) -> None:
        fixture = dict(self.plan.fixture("H26-F-P01"))
        recipe = deep_thaw_json(self.plan.recipes["H26-F-P01"])
        del recipe["sources"][0]["phase_radians"]
        with self.assertRaisesRegex(ValueError, "source schema"):
            _validate_recipe(fixture, recipe)
        recipe = deep_thaw_json(self.plan.recipes["H26-F-P01"])
        recipe["sources"][0]["gain"] = 0.75
        with self.assertRaisesRegex(ValueError, "candidate candidate_gain divergence"):
            _validate_recipe(fixture, recipe)

    def test_masked_fundamental_and_noise_namespace_are_exact(self) -> None:
        for fixture_id in ("H26-F-P07", "H26-F-P08"):
            recipe = self.plan.recipes[fixture_id]
            candidate = next(item for item in recipe["sources"] if item["source_id"] == "candidate")
            self.assertEqual(candidate["partial_ranks"], tuple(range(1, 9)))
            self.assertIn("old-source H2", recipe["fundamental_masked_physical_definition"])
        expected = {
            "H26-F-N05": "489426142522370829",
            "H26-F-N06": "10432360115859685675",
            "H26-F-N07": "13039863101835106650",
        }
        for fixture_id, seed in expected.items():
            noise = self.plan.recipes[fixture_id]["noise"]
            self.assertIn("|BASELINE_DECAY_NOISE_V1|", noise["seed_preimage"])
            self.assertEqual(noise["seed_uint64_decimal"], seed)

    def test_loaded_plan_is_recursively_immutable(self) -> None:
        with self.assertRaises(TypeError):
            self.plan.contract["causal_contract"]["hop_samples"] = 1
        with self.assertRaises(TypeError):
            self.plan.recipes["H26-F-P01"]["sources"][0]["gain"] = 99.0
        with self.assertRaises(TypeError):
            self.plan.fixtures[0]["parameters"]["candidate_gain"] = 99.0

    def test_capabilities_and_execution_are_unissuable(self) -> None:
        with self.assertRaises(PermissionError):
            H26MaterializationCapability(self.plan, "0" * 40)
        with self.assertRaises(PermissionError):
            H26ScientificCapability(self.plan, "0" * 64)
        with self.assertRaises(PermissionError):
            materialize_h26_population(np, object(), self.root / "must-not-exist")
        with self.assertRaises(PermissionError):
            require_h26_scientific_execution_authorized()
        self.assertFalse((self.root / "must-not-exist").exists())
        self.assertFalse(hasattr(h26_materializer_module, "_CAPABILITY_TOKEN"))
        self.assertFalse(hasattr(h26_engine_module, "_SCIENTIFIC_TOKEN"))

    def test_p2_cents_and_inharmonicity_move_every_candidate_band_center(self) -> None:
        baseline = partial_center_hz(52, 3, cents=0.0, inharmonicity=0.0)
        perturbed = partial_center_hz(52, 3, cents=25.0, inharmonicity=0.004)
        self.assertNotEqual(baseline, perturbed)
        self.assertGreater(perturbed, baseline)
        self.assertEqual(pitch_dilution_pitch_order("ascending")[:2], (24, 25))
        self.assertEqual(pitch_dilution_pitch_order("descending")[:2], (96, 95))

    def test_equivalence_is_derived_from_nonzero_bytes_not_fixture_identity(self) -> None:
        left = np.array([0.0, 0.25, -0.5], dtype=np.float64)
        self.assertTrue(nonzero_observations_are_byte_equivalent(np, left, left.copy()))
        self.assertFalse(nonzero_observations_are_byte_equivalent(
            np, left, np.array([0.0, 0.25, -0.4], dtype=np.float64),
        ))
        zeros = np.zeros(3, dtype=np.float64)
        self.assertFalse(nonzero_observations_are_byte_equivalent(np, zeros, zeros.copy()))

    def test_population_binding_rejects_unsealed_index_before_waveform_access(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "population_index.json").write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "index SHA mismatch"):
                bind_h26_population_observation(
                    np, self.plan, root,
                    expected_population_index_sha256="0" * 64,
                    fixture_id="H26-F-P01",
                )

    def _write_artificial_population(
        self, root: Path, fixture_id: str, waveform: np.ndarray,
    ) -> tuple[str, H26BoundObservation]:
        waveform_raw = waveform.astype("<f8", copy=False).tobytes(order="C")
        mask = h26_materializer_module._validity_masks(
            np, self.plan.fixture(fixture_id),
        )
        mask_raw = mask.sample_valid.astype(np.uint8).tobytes(order="C")
        (root / "waveforms").mkdir()
        (root / "masks").mkdir()
        (root / "waveforms" / f"{fixture_id}.f64le").write_bytes(waveform_raw)
        (root / "masks" / f"{fixture_id}.u8").write_bytes(mask_raw)
        records = []
        for current_id in self.plan.fixture_ids:
            record = {"fixture_id": current_id}
            if current_id == fixture_id:
                record.update({
                    "waveform": f"waveforms/{fixture_id}.f64le",
                    "waveform_sha256": hashlib.sha256(waveform_raw).hexdigest(),
                    "sample_valid": f"masks/{fixture_id}.u8",
                    "sample_valid_sha256": hashlib.sha256(mask_raw).hexdigest(),
                    "invalid_candidate_partial_ranks": list(mask.invalid_candidate_partial_ranks),
                    "alternate_waveform": None,
                    "alternate_waveform_sha256": None,
                })
            records.append(record)
        raw = (
            json.dumps({
                "schema_version": 1,
                "population_namespace": "H26_SYNTHETIC_V1",
                "records": records,
            }, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        (root / "population_index.json").write_bytes(raw)
        index_sha = hashlib.sha256(raw).hexdigest()
        bound = bind_h26_population_observation(
            np, self.plan, root,
            expected_population_index_sha256=index_sha,
            fixture_id=fixture_id,
        )
        return index_sha, bound

    def test_producer_rejects_directly_forged_bound_observation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            waveform = np.zeros(h26_materializer_module.SAMPLE_COUNT, dtype=np.float64)
            index_sha, bound = self._write_artificial_population(root, "H26-F-P01", waveform)
            forged_waveform = np.ones_like(waveform)
            forged = H26BoundObservation(
                fixture_id=bound.fixture_id,
                population_root=bound.population_root,
                population_index_sha256=bound.population_index_sha256,
                waveform_sha256=hashlib.sha256(
                    forged_waveform.astype("<f8").tobytes(order="C")
                ).hexdigest(),
                waveform=forged_waveform,
                sample_valid_sha256=bound.sample_valid_sha256,
                sample_valid=bound.sample_valid,
                invalid_candidate_partial_ranks=bound.invalid_candidate_partial_ranks,
                alternate_waveform_sha256=None,
                alternate_waveform=None,
            )
            with mock.patch.object(
                h26_engine_module, "_require_scientific",
                return_value=(self.plan, index_sha),
            ):
                with self.assertRaisesRegex(ValueError, "sealed population record"):
                    produce_h26_fixture_evidence(
                        np, object(), fixture_id="H26-F-P01", observation=forged,
                    )

    def test_producer_measures_at_target_then_resolves_one_hop_later(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            waveform = np.zeros(h26_materializer_module.SAMPLE_COUNT, dtype=np.float64)
            index_sha, bound = self._write_artificial_population(root, "H26-F-A10", waveform)
            with mock.patch.object(
                h26_engine_module, "_require_scientific",
                return_value=(self.plan, index_sha),
            ):
                evidence = produce_h26_fixture_evidence(
                    np, object(), fixture_id="H26-F-A10", observation=bound,
                )
            self.assertEqual(evidence.operands["proposal_hop_end"], 16383)
            self.assertEqual(evidence.operands["resolution_hop_end"], 16639)
            self.assertEqual(evidence.operands["maximum_sample_read"], 16383)
            self.assertFalse(evidence.measurement["support_valid"])

    def test_producer_full_path_wires_target_and_transform_without_invalid_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            waveform = np.zeros(h26_materializer_module.SAMPLE_COUNT, dtype=np.float64)
            index_sha, bound = self._write_artificial_population(root, "H26-F-P01", waveform)
            candidate_pitch = int(self.plan.fixture("H26-F-P01")["candidate_pitch"])
            raw_operands = H26RawOperands(
                False, True, False, (2, 3), (3.0, 3.0), 20.0,
                100.0, 90.0, 1.0, 0.8, 100.0, 95.0, 16383,
                tuple(
                    (pitch, 1.0, 0.8 if pitch == candidate_pitch else 1.0)
                    for pitch in range(24, 97)
                ),
            )
            with (
                mock.patch.object(
                    h26_engine_module, "_require_scientific",
                    return_value=(self.plan, index_sha),
                ),
                mock.patch.object(
                    h26_engine_module, "causal_spectrum",
                    return_value=object(),
                ),
                mock.patch.object(
                    h26_engine_module, "exclusive_partial_ranks",
                    autospec=True, return_value=(2, 3),
                ) as exclusive,
                mock.patch.object(
                    h26_engine_module, "extract_raw_operands",
                    autospec=True, return_value=raw_operands,
                ) as extract,
            ):
                evidence = produce_h26_fixture_evidence(
                    np, object(), fixture_id="H26-F-P01", observation=bound,
                )
            self.assertEqual(evidence.operands["maximum_sample_read"], 16383)
            self.assertNotIn("transform_order", exclusive.call_args.kwargs)
            self.assertEqual(extract.call_args.kwargs["target_hop_end"], 16383)
            self.assertEqual(extract.call_args.kwargs["transform_order"], "ascending")

    def test_p2_cells_are_read_from_contract_with_exact_cardinalities(self) -> None:
        expected = {
            "P2_GAIN_V1": 3,
            "P2_PHASE_V1": 4,
            "P2_NOISE_V1": 6,
            "P2_CENTS_INHARMONICITY_V1": 9,
            "P2_HOP_SHIFT_V1": 3,
            "P2_PERMUTATION_V1": 8,
            "P2_RUNTIME_V1": 2,
        }
        for grid_id, count in expected.items():
            self.assertEqual(len(p2_cells(self.plan.contract, grid_id)), count)

    def test_p2_transform_is_bound_to_manifest_and_derives_seed_without_audio(self) -> None:
        cell = p2_cells(self.plan.contract, "P2_NOISE_V1")[4]
        transform = build_h26_p2_transform(
            self.plan, fixture_id="H26-F-N05", test_id="H26-T-P2-003",
            grid_id="P2_NOISE_V1", cell=cell,
        )
        self.assertEqual(transform.recipe["noise"]["seed_preimage"], "H26|H26-F-N05|P2-003|pink|20")
        self.assertEqual(
            transform.recipe["noise"]["seed_uint64_decimal"],
            str(int.from_bytes(hashlib.sha256(b"H26|H26-F-N05|P2-003|pink|20").digest()[:8], "little")),
        )
        with self.assertRaisesRegex(ValueError, "outside the preregistered test"):
            build_h26_p2_transform(
                self.plan, fixture_id="H26-F-P01", test_id="H26-T-P2-003",
                grid_id="P2_NOISE_V1", cell=cell,
            )

    def test_support_validity_is_derived_from_masks_on_artificial_inputs(self) -> None:
        valid = np.ones(9000, dtype=np.bool_)
        self.assertTrue(required_support_is_valid(
            np, sample_valid=valid, invalid_candidate_partial_ranks=(),
            target_hop_end=8999, exclusive_partial_ranks_used=(2, 3), policy=self.policy,
        ))
        valid[1000] = False
        self.assertFalse(required_support_is_valid(
            np, sample_valid=valid, invalid_candidate_partial_ranks=(),
            target_hop_end=8999, exclusive_partial_ranks_used=(2, 3), policy=self.policy,
        ))
        valid[:] = True
        self.assertFalse(required_support_is_valid(
            np, sample_valid=valid, invalid_candidate_partial_ranks=(3,),
            target_hop_end=8999, exclusive_partial_ranks_used=(2, 3), policy=self.policy,
        ))

    def _measurements(self, **changes) -> H26Measurements:
        values = dict(
            candidate_active=False,
            support_valid=True,
            observation_equivalent=False,
            exclusive_partial_ranks=(2, 3),
            exclusive_energy_ratios=(0.03, 0.03),
            onset_rise=0.06,
            active_only_residual_improvement=0.11,
            candidate_lower_bounds=(0.03, 0.03),
            negative_margin_ratios=(1.0, 1.0),
            long_window_persistence=0.0,
            maximum_sample_read=100,
        )
        values.update(changes)
        return H26Measurements(**values)

    def test_resolver_order_and_certificate_regions_on_artificial_operands(self) -> None:
        self.assertEqual(resolve_h26(self.plan.contract, self._measurements(candidate_active=True)).outcome, "ALREADY_ACTIVE_HISTORY")
        self.assertEqual(resolve_h26(self.plan.contract, self._measurements(support_valid=False)).outcome, "AMBIGUOUS")
        self.assertEqual(resolve_h26(self.plan.contract, self._measurements(observation_equivalent=True)).outcome, "AMBIGUOUS")
        self.assertEqual(resolve_h26(self.plan.contract, self._measurements()).outcome, "BIRTH_SUPPORTED")
        negative = self._measurements(
            exclusive_energy_ratios=(0.001, 0.001), onset_rise=0.001,
            active_only_residual_improvement=0.0001,
            candidate_lower_bounds=(0.03, 0.03), negative_margin_ratios=(30.0, 30.0),
        )
        self.assertEqual(resolve_h26(self.plan.contract, negative).outcome, "NO_BIRTH")
        self.assertEqual(resolve_h26(self.plan.contract, self._measurements(onset_rise=0.02)).outcome, "AMBIGUOUS")

    def test_independent_recomputer_matches_artificial_certificate_cases(self) -> None:
        measurement = self._measurements()
        raw = {key: getattr(measurement, key) for key in measurement.__dataclass_fields__}
        recomputed = recompute_h26_resolution(self.plan, fixture_id="H26-F-P01", measurement=raw)
        self.assertEqual(recomputed.outcome, "BIRTH_SUPPORTED")
        raw.update({
            "exclusive_energy_ratios": [0.001, 0.001],
            "onset_rise": 0.001,
            "active_only_residual_improvement": 0.0001,
            "candidate_lower_bounds": [0.03, 0.03],
            "negative_margin_ratios": [30.0, 30.0],
        })
        self.assertEqual(
            recompute_h26_resolution(self.plan, fixture_id="H26-F-P01", measurement=raw).outcome,
            "NO_BIRTH",
        )

    def test_independent_recomputer_derives_features_from_artificial_raw_operands(self) -> None:
        operands = {
            "candidate_active": False, "support_valid": True,
            "observation_equivalent": False,
            "exclusive_partial_ranks": (2, 3),
            "exclusive_band_energies": (3.0, 3.0),
            "shared_band_energy": 20.0,
            "current_short_total_power": 100.0,
            "previous_short_total_power": 90.0,
            "active_only_residual": 1.0,
            "active_plus_candidate_residual": 0.8,
            "current_long_total_power": 100.0,
            "previous_long_total_power": 95.0,
            "pitch_dilution_residual_triplets": tuple(
                (pitch, 1.0, 0.8 if pitch == 52 else 1.0)
                for pitch in range(24, 97)
            ),
            "maximum_sample_read": 16383,
            "proposal_hop_end": 16383, "resolution_hop_end": 16639,
            "state_before": "PENDING_NEW", "state_after": "BIRTH_SUPPORTED",
            "active_pitches": (40,), "candidate_pitch": 52,
            "perturbation": None,
        }
        recomputed = recompute_h26_evidence_from_raw_operands(
            self.plan, fixture_id="H26-F-P01", operands=operands,
        )
        self.assertEqual(recomputed.resolution.outcome, "BIRTH_SUPPORTED")
        self.assertEqual(recomputed.measurement["exclusive_energy_ratios"], (0.03, 0.03))
        corrupt = dict(operands, expected="BIRTH_SUPPORTED")
        with self.assertRaisesRegex(ValueError, "forbidden oracle"):
            recompute_h26_evidence_from_raw_operands(
                self.plan, fixture_id="H26-F-P01", operands=corrupt,
            )

    def test_producer_side_raw_operand_projection_matches_independent_recomputer(self) -> None:
        raw = H26RawOperands(
            False, True, False, (2, 3), (3.0, 3.0), 20.0,
            100.0, 90.0, 1.0, 0.8, 100.0, 95.0, 100,
            tuple(
                (pitch, 1.0, 0.8 if pitch == 52 else 1.0)
                for pitch in range(24, 97)
            ),
        )
        produced = measurements_from_raw_operands(self.policy, raw)
        self.assertEqual(produced.exclusive_energy_ratios, (0.03, 0.03))
        self.assertEqual(produced.onset_rise, 0.1)
        self.assertAlmostEqual(produced.active_only_residual_improvement, 0.2)
        masked = recompute_h26_evidence_from_raw_operands(
            self.plan, fixture_id="H26-F-A10", operands={
                "candidate_active": False, "support_valid": False,
                "observation_equivalent": False,
                "maximum_sample_read": 16383,
                "proposal_hop_end": 16383, "resolution_hop_end": 16639,
                "state_before": "PENDING_NEW", "state_after": "AMBIGUOUS",
                "active_pitches": (),
                "candidate_pitch": 40, "perturbation": None,
            },
        )
        self.assertEqual(masked.resolution.outcome, "AMBIGUOUS")

    def test_recomputer_binds_p2_cell_and_exact_shifted_coordinates(self) -> None:
        cell = dict(p2_cells(self.plan.contract, "P2_HOP_SHIFT_V1")[0])
        shift = int(cell["sample_shift"])
        operands = {
            "candidate_active": False, "support_valid": False,
            "observation_equivalent": False,
            "maximum_sample_read": 16383 + shift,
            "proposal_hop_end": 16383 + shift,
            "resolution_hop_end": 16639 + shift,
            "state_before": "PENDING_NEW", "state_after": "AMBIGUOUS",
            "active_pitches": (), "candidate_pitch": 52,
            "perturbation": {
                "test_id": "H26-T-P2-008", "grid_id": "P2_HOP_SHIFT_V1",
                "cell": cell,
            },
        }
        result = recompute_h26_evidence_from_raw_operands(
            self.plan, fixture_id="H26-F-P09", operands=operands,
        )
        self.assertEqual(result.resolution.outcome, "AMBIGUOUS")
        wrong_cell = dict(cell, sample_shift=shift + 1)
        with self.assertRaisesRegex(ValueError, "outside sealed grid"):
            recompute_h26_evidence_from_raw_operands(
                self.plan, fixture_id="H26-F-P09",
                operands={**operands, "perturbation": {**operands["perturbation"], "cell": wrong_cell}},
            )

    def test_causal_state_resolves_exactly_one_hop_later_on_artificial_coordinates(self) -> None:
        proposal = begin_h26_causal_proposal(
            self.policy, candidate_pitch=52,
            proposal_hop_end=1000, resolution_hop_end=1256,
        )
        resolution = resolve_h26(self.plan.contract, self._measurements())
        self.assertEqual(
            finish_h26_causal_proposal(proposal, resolution, maximum_sample_read=1256),
            "BIRTH_SUPPORTED",
        )
        with self.assertRaisesRegex(ValueError, "exactly one hop"):
            begin_h26_causal_proposal(
                self.policy, candidate_pitch=52,
                proposal_hop_end=1000, resolution_hop_end=1257,
            )

    def test_small_non_h26_numeric_kernels_have_fixed_shapes(self) -> None:
        samples = np.arange(9000, dtype=np.float64)
        toy = np.sin(2.0 * np.pi * 220.0 * samples / 44100.0).astype(np.float64)
        view = extract_causal_view(np, toy, hop_end=8999, length=4096)
        spectrum = causal_spectrum(np, view, policy=self.policy)
        self.assertEqual(spectrum.n_fft, 32768)
        self.assertEqual(spectrum.power.shape, (16385,))
        matrix = np.eye(2, dtype=np.float64)
        target = np.array([1.0, 2.0], dtype=np.float64)
        result = fixed_nnls_v1(np, matrix, target, policy=self.policy)
        self.assertLessEqual(result.residual, 1e-24)
        self.assertEqual(result.coefficients, (1.0, 2.0))

    def test_transcript_prefix_is_structural_and_fail_closed(self) -> None:
        first, second = self.plan.tests[:2]
        records = [
            H26TranscriptRecord(first.test_id, first.order, first.phase, "FAILED", None, first.kill_status),
            H26TranscriptRecord(second.test_id, second.order, second.phase, "NOT_RUN_BY_KILL_RULE", None, None),
        ]
        validate_transcript_prefix(self.plan, records)
        records[1] = H26TranscriptRecord(second.test_id, second.order, second.phase, "PASSED", "a" * 64, None)
        with self.assertRaisesRegex(ValueError, "after first failure"):
            validate_transcript_prefix(self.plan, records)


if __name__ == "__main__":
    unittest.main()
