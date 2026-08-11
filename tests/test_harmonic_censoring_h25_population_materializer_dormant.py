import hashlib
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src.polyphonic import harmonic_censoring_h25_population_materializer as materializer


ROOT = Path(__file__).resolve().parents[1]


class H25DormantPopulationMaterializerTests(unittest.TestCase):
    def test_import_has_no_numpy_and_no_cli(self):
        source = inspect.getsource(materializer)
        prefix = source.split("def synthesize_fixture", 1)[0]
        self.assertNotIn("import numpy", prefix)
        self.assertNotIn("__main__", source)
        self.assertNotIn("argparse", source)

    def test_plan_loads_only_sealed_unmaterialized_contracts(self):
        plan = materializer.load_dormant_plan(ROOT)
        self.assertEqual(len(plan.fixtures), 36)
        self.assertEqual(plan.population["waveform_count"], 0)
        self.assertFalse(plan.population["materialized"])
        self.assertFalse(plan.specifications["generation_authorized"])

    def test_capability_cannot_be_constructed_or_operation_invoked(self):
        plan = materializer.load_dormant_plan(ROOT)
        with self.assertRaisesRegex(PermissionError, "no authorized issuer"):
            materializer.H25MaterializationCapability(plan, "0" * 40, "0" * 40)
        with self.assertRaisesRegex(PermissionError, "attested capability"):
            materializer.materialize_and_publish_h25_population(object())

    def test_standard_library_preflight_precedes_numpy_loader(self):
        loader = mock.Mock(side_effect=AssertionError("NumPy loader must stay unreachable"))
        with self.assertRaises(PermissionError):
            materializer.materialize_and_publish_h25_population(object(), loader)
        loader.assert_not_called()

    def test_canonical_json_is_compact_sorted_lf_and_rejects_nonfinite(self):
        self.assertEqual(materializer.canonical_json({"b": 2, "a": 1}), b'{"a":1,"b":2}\n')
        with self.assertRaises(ValueError):
            materializer.canonical_json({"x": float("nan")})

    def test_noise_seed_rule_is_exact(self):
        fixture_id = "H25-F-P11"
        expected = int.from_bytes(
            hashlib.sha256(("H25|" + fixture_id + "|noise").encode()).digest()[:8],
            "little", signed=False,
        )
        self.assertEqual(materializer._seed(fixture_id), expected)

    def test_fixture_artifacts_are_deterministic_on_synthetic_non_h25_record(self):
        import numpy as np

        fixture = {
            "id": "TEST-ONLY-NOT-H25-POPULATION", "order": 1,
            "category": "ambiguous", "family": "SYNTHETIC_OOD", "pitch_band": "none",
            "candidate_pitch": None, "parameters": {"kind": "impulse", "onset": 16128},
        }
        specs = {"base_families": {"SYNTHETIC_OOD": {"oracle": "AMBIGUOUS"}}}
        first = materializer.artifact_bytes(np, specs, fixture, 0)
        second = materializer.artifact_bytes(np, specs, fixture, 0)
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 133120)
        self.assertEqual(first[0][:8192 * 8], bytes(8192 * 8))
        self.assertEqual(json.loads(first[2]), {
            "schema_version": 1, "fixture_id": fixture["id"], "category": "ambiguous",
            "family": "SYNTHETIC_OOD", "oracle": "AMBIGUOUS",
        })

    def test_source_has_exact_pcg64_and_publication_primitives(self):
        source = inspect.getsource(materializer)
        self.assertIn("np.random.Generator(np.random.PCG64(_seed(fixture_id)))", source)
        self.assertIn("os.O_EXCL", source)
        self.assertIn("os.fsync", source)
        self.assertIn("np.asarray(waveform, dtype=\"<f8\", order=\"C\")", source)
        self.assertIn("verify_and_recompute_staging(np, plan, staging, rows)", source)
        self.assertIn("os.replace(staging, success)", source)
        self.assertIn("_fsync_directory(success.parent)", source)
        entry = inspect.getsource(materializer.materialize_and_publish_h25_population)
        self.assertLess(
            entry.index("_require_output_paths_before_numpy(plan)"),
            entry.index("numpy_loader()"),
        )
        preflight = inspect.getsource(materializer.require_reference_environment_before_numpy)
        self.assertIn("path.read_bytes()", preflight)
        self.assertIn('["otool", "-L"', preflight)
        self.assertIn('"Accelerate.framework" in dependency', preflight)
        for required in (
            "platform.mac_ver()[0]", "Path(sys.executable)",
            "Path(os.path.realpath(sys.executable))", "Path(sys.prefix)",
            'p["execution_device"] != "CPU"', 'p["gpu_count"] != 0',
        ):
            self.assertIn(required, preflight)
        final = inspect.getsource(materializer._verify_final_metadata)
        self.assertIn("len(reopened) != len(expected)", final)
        self.assertIn("_sha256(reopened) != _sha256(expected)", final)
        self.assertIn("reopened != expected", final)

    def test_inharmonic_bell_uses_exact_512_sample_decay(self):
        source = inspect.getsource(materializer._envelope)
        self.assertIn('kind == "bell"', source)
        self.assertIn("elapsed / np.float64(512.0)", source)

    def test_all_family_dispatches_and_noise_colours_on_test_only_ids(self):
        import numpy as np

        common = {"gain": 1.0, "phase_radians": 0.0, "cents": 0, "B": 0.0, "noise": None}
        cases = {
            "IDENTIFIABLE_OVERLAP": {**common, "old_pitch": 40, "new_onset": 16128},
            "ISOLATED_NEW": {**common, "new_onset": 16128},
            "SHARED_PARTIAL_TWO_SOURCE": {**common, "old_pitch": 40, "new_onset": 16128},
            "HARMONIC_ONLY": {**common, "old_pitch": 40},
            "ACTIVE_ONLY": {**common, "old_pitch": 52},
            "NATURAL_HARMONIC": {**common, "old_pitch": 40, "partial_subset": [2, 4]},
            "DECAY_NO_ATTACK": {**common, "old_pitch": 52},
            "EXACT_COLLISION_IDENTICAL": {**common, "old_pitch": 40, "collision_harmonic_rank": 2},
            "OVERLAP_WITHOUT_INDEPENDENT_EVIDENCE": {**common, "old_pitch": 40},
            "MISSING_FUNDAMENTAL": {**common, "source_pitch": 40, "partial_subset": [2, 3]},
        }
        for family, parameters in cases.items():
            with self.subTest(family=family):
                fixture = {
                    "id": "TEST-ONLY-" + family, "family": family,
                    "candidate_pitch": 52, "parameters": parameters,
                }
                waveform = materializer.synthesize_fixture(np, fixture)
                self.assertEqual(waveform.shape, (16640,))
                self.assertTrue(np.all(np.isfinite(waveform)))
                self.assertEqual(waveform[:8192].tobytes(), bytes(8192 * 8))
        for kind in ("impulse", "linear_chirp", "inharmonic_bell"):
            parameters = {"kind": kind, "onset": 16128}
            if kind == "linear_chirp":
                parameters.update(start_hz=110.0, end_hz=7040.0)
            if kind == "inharmonic_bell":
                parameters.update(nominal_pitch=52, B=0.004)
            fixture = {"id": "TEST-ONLY-OOD-" + kind, "family": "SYNTHETIC_OOD", "candidate_pitch": None, "parameters": parameters}
            self.assertEqual(materializer.synthesize_fixture(np, fixture).shape, (16640,))
        for colour in ("white", "pink"):
            fixture = {
                "id": "TEST-ONLY-NOISE-" + colour, "family": "HARMONIC_ONLY",
                "candidate_pitch": 52,
                "parameters": {**common, "old_pitch": 40, "noise": {"colour": colour, "snr_db": 20}},
            }
            first = materializer.synthesize_fixture(np, fixture)
            second = materializer.synthesize_fixture(np, fixture)
            self.assertEqual(first.tobytes(), second.tobytes())

    def test_runtime_identity_inverses_fail_before_binary_or_numpy_access(self):
        plan = materializer.load_dormant_plan(ROOT)
        expected = plan.contract["reference_runtime_identity"]
        environment = dict(expected["process_environment_exact"])
        common = (
            mock.patch.object(materializer.platform, "system", return_value="Darwin"),
            mock.patch.object(materializer.platform, "release", return_value="24.5.0"),
            mock.patch.object(materializer.platform, "machine", return_value="arm64"),
            mock.patch.object(materializer.platform, "python_implementation", return_value="CPython"),
            mock.patch.object(materializer.platform, "python_version", return_value="3.11.9"),
            mock.patch.object(materializer.sys, "executable", expected["python"]["executable"]),
            mock.patch.object(materializer.sys, "prefix", expected["python"]["venv_root"]),
            mock.patch.dict(os.environ, environment, clear=True),
        )
        for patcher in common:
            patcher.start()
            self.addCleanup(patcher.stop)
        with mock.patch.object(materializer.platform, "mac_ver", return_value=("15.4", ("", "", ""), "")):
            with self.assertRaisesRegex(RuntimeError, "platform/Python"):
                materializer.require_reference_environment_before_numpy(plan)
        with mock.patch.object(materializer.platform, "mac_ver", return_value=("15.5", ("", "", ""), "")), mock.patch.object(
            materializer.sys, "prefix", "/wrong/venv"
        ):
            with self.assertRaisesRegex(RuntimeError, "platform/Python"):
                materializer.require_reference_environment_before_numpy(plan)

    def test_final_metadata_is_recomputed_and_tampering_fails(self):
        plan = materializer.load_dormant_plan(ROOT)
        capability = SimpleNamespace(implementation_commit="1" * 40, source_blob="2" * 40)
        rows = tuple({"ordinal": i} for i in range(36))
        index = b"".join(materializer.canonical_json(row) for row in rows)
        provenance = materializer.canonical_json(materializer._runtime_provenance_payload(plan, capability))
        receipt = materializer.canonical_json(materializer._population_receipt_payload(plan, capability, index))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "population_index.jsonl").write_bytes(index)
            (root / "runtime_provenance.json").write_bytes(provenance)
            (root / "population_receipt.json").write_bytes(receipt)
            materializer._verify_final_metadata(root, plan, capability, rows)
            (root / "population_receipt.json").write_bytes(receipt + b" ")
            with self.assertRaisesRegex(ValueError, "population_receipt"):
                materializer._verify_final_metadata(root, plan, capability, rows)


if __name__ == "__main__":
    unittest.main()
