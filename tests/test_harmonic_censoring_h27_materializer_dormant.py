"""Structural tests for the dormant H27 loader/materializer boundary.

No test uses a real H27 recipe, FFT, NNLS, publication directory, or runtime
authority.  Numeric checks deliberately use tiny caller-provided toy recipes.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from src.polyphonic.harmonic_censoring_h27_contract import (
    FUTURE_POPULATION_PATH,
    HYPOTHESIS_ID,
    REVIEWED_GIT_BLOBS,
    canonical_h27_record_identities,
    git_blob_sha1,
    load_h27_dormant_plan,
)
from src.polyphonic.harmonic_censoring_h27_materializer_dormant import (
    H27MaterializationCapability,
    inspect_h27_materialization_plan,
    materialize_h27_population,
    render_toy_collision_pair,
    render_toy_recipe,
    role_major_mask_bytes,
    synthesize_h27_fixture,
)


ROOT = Path(__file__).resolve().parents[1]


class _FailIfTouchedNP:
    """Sentinel proving a rejected production request cannot reach NumPy."""

    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"numeric runtime touched before fail-closed guard: {name}")


def _toy_source(*, pitch: int = 60, onset: int = 0) -> dict[str, object]:
    return {
        "pitch": pitch,
        "gain": 0.25,
        "phase_radians": 0.0,
        "cents": 0,
        "B": 0.0,
        "partial_ranks": [1, 2],
        "onset_sample": onset,
        "envelope_id": "H27_ENV_ATTACK_DECAY_V1",
        "envelope_parameters": {},
    }


class HarmonicCensoringH27DormantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = load_h27_dormant_plan(ROOT)

    def test_loader_binds_reviewed_blobs_and_population_shape(self) -> None:
        inspection = inspect_h27_materialization_plan(self.plan)
        self.assertEqual(len(self.plan.fixture_ids), 17)
        self.assertEqual(len(self.plan.tests), 27)
        self.assertEqual(len(inspection.record_identities), 124)
        self.assertEqual(len(set(inspection.record_identities)), 124)
        self.assertEqual(inspection.record_identities, canonical_h27_record_identities(self.plan))
        self.assertFalse(inspection.materialization_authorized)
        self.assertEqual(self.plan.preregistration["hypothesis_id"], HYPOTHESIS_ID)

    def test_all_reviewed_files_match_their_git_blob_binding(self) -> None:
        for relative, expected in REVIEWED_GIT_BLOBS.items():
            self.assertEqual(git_blob_sha1((ROOT / relative).read_bytes()), expected)

    def test_mutated_reviewed_bytes_are_refused_before_design_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "repo"
            shutil.copytree(ROOT / "configs", copied / "configs")
            target = copied / FUTURE_POPULATION_PATH
            target.write_bytes(target.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "reviewed Git blob mismatch"):
                load_h27_dormant_plan(copied)

    def test_capability_cannot_be_issued(self) -> None:
        with self.assertRaisesRegex(PermissionError, "no issuer"):
            H27MaterializationCapability()

    def test_fixture_and_population_boundaries_fail_before_work(self) -> None:
        forged = object.__new__(H27MaterializationCapability)
        forbidden = ROOT / "tmp" / "must-not-be-inspected-by-dormant-test"
        with self.assertRaisesRegex(PermissionError, "remains dormant"):
            synthesize_h27_fixture(np, forged, self.plan, "H27-F-P01")
        with self.assertRaisesRegex(PermissionError, "remains dormant"):
            materialize_h27_population(np, forged, self.plan, forbidden)
        self.assertFalse(forbidden.exists())

    def test_role_major_mask_is_exact_and_role_independent(self) -> None:
        encoded = role_major_mask_bytes(
            sample_count=8,
            role_order=("toy_current", "toy_previous"),
            required_intervals={"toy_current": (2, 4), "toy_previous": (0, 1)},
            exceptions=({"role": "toy_current", "sample_index": 3, "byte": 0},),
        )
        self.assertEqual(encoded, bytes((0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0)))
        with self.assertRaisesRegex(ValueError, "outside required support"):
            role_major_mask_bytes(
                sample_count=8, role_order=("toy_current",),
                required_intervals={"toy_current": (2, 4)},
                exceptions=({"role": "toy_current", "sample_index": 1, "byte": 0},),
            )
        with self.assertRaisesRegex(ValueError, "production role names"):
            role_major_mask_bytes(sample_count=8, role_order=("current_short",), required_intervals={"current_short": (2, 4)})
        with self.assertRaisesRegex(ValueError, "toy mask sample count"):
            role_major_mask_bytes(sample_count=16640, role_order=("toy_current",), required_intervals={"toy_current": (0, 1)})

    def test_toy_recipe_is_deterministic_and_supports_symbolic_power(self) -> None:
        source = _toy_source(onset=2)
        source["gain"] = "2^-80"
        recipe = {"sources": [source], "noise": {"kind": "NONE"}}
        first = render_toy_recipe(np, recipe, sample_count=32, sample_rate_hz=8000)
        second = render_toy_recipe(np, recipe, sample_count=32, sample_rate_hz=8000)
        self.assertEqual(first.dtype, np.float64)
        self.assertEqual(first.shape, (32,))
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(first[:2].tobytes(), np.zeros(2, dtype=np.float64).tobytes())
        with self.assertRaisesRegex(ValueError, "toy audio domain"):
            render_toy_recipe(_FailIfTouchedNP(), recipe, sample_count=16640, sample_rate_hz=8000)
        with self.assertRaisesRegex(ValueError, "toy audio domain"):
            render_toy_recipe(_FailIfTouchedNP(), recipe, sample_count=32, sample_rate_hz=44100)

    def test_collision_pair_is_independent_and_byte_identical(self) -> None:
        first, second = render_toy_collision_pair(
            np, sample_count=64, sample_rate_hz=8000, old_pitch=48,
            collision_rank=2, old_gain=0.4, candidate_gain=0.2,
            old_onset=0, collision_onset=8, phase=0.0,
        )
        self.assertIsNot(first, second)
        self.assertEqual(first.dtype, np.float64)
        self.assertEqual(first.tobytes(), second.tobytes())
        with self.assertRaisesRegex(ValueError, "equation"):
            render_toy_collision_pair(
                np, sample_count=64, sample_rate_hz=8000, old_pitch=48,
                collision_rank=2, old_gain=0.4, candidate_gain=0.3,
                old_onset=0, collision_onset=8, phase=0.0,
            )
        with self.assertRaisesRegex(ValueError, "toy audio domain"):
            render_toy_collision_pair(np, sample_count=16640, sample_rate_hz=8000, old_pitch=48, collision_rank=2, old_gain=0.4, candidate_gain=0.2, old_onset=0, collision_onset=8, phase=0.0)
        with self.assertRaisesRegex(ValueError, "toy audio domain"):
            render_toy_collision_pair(np, sample_count=64, sample_rate_hz=44100, old_pitch=48, collision_rank=2, old_gain=0.4, candidate_gain=0.2, old_onset=0, collision_onset=8, phase=0.0)


if __name__ == "__main__":
    unittest.main()
