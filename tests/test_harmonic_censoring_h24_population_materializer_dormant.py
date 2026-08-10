import ast
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h24_population_materializer as materializer


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "src/polyphonic/harmonic_censoring_h24_population_materializer.py"
CONTRACT_PATH = ROOT / "configs/harmonic_censoring_h24_population_materialization_one_shot_contract.json"


def _seal_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h24_population_materialization_authorization_seal",
        "status": "reviewed_dormant_materializer_authorized_for_one_shot_activation",
        "reviewed_materializer_commit": "a" * 40,
        "exact_changed_files": [
            "configs/harmonic_censoring_h24_population_materialization_authorization_seal.json",
            "src/polyphonic/harmonic_censoring_h24_population_materializer.py",
        ],
        "materializer_source_blob": "b" * 40,
        "materialization_contract_raw_sha256": materializer.H24_MATERIALIZATION_CONTRACT_RAW_SHA256,
        "authorized_action": "AUTHORIZED_TO_ACTIVATE_H24_ONE_SHOT_POPULATION_MATERIALIZATION",
    }


def _seal():
    return materializer.validate_h24_population_materialization_authorization_seal(
        _seal_payload(), raw_sha256="c" * 64
    )


class H24DormantPopulationMaterializerTests(unittest.TestCase):
    def _issue_synthetic_capability(self, repository: Path):
        dummy_plan = object()
        dummy_recipes = tuple()
        with mock.patch.object(
            materializer, "_load_authorization_seal", return_value=(_seal(), "d" * 40)
        ), mock.patch.object(
            materializer,
            "_zero_science_preflight",
            return_value=(dummy_plan, dummy_recipes),
        ):
            capability = materializer.issue_h24_population_materialization_capability(repository)
        return capability

    def test_source_and_contract_sha_are_bound_and_module_has_no_numpy_import(self):
        self.assertEqual(
            materializer._parse_json_object(
                CONTRACT_PATH.read_bytes(), "materialization contract"
            )["purpose"],
            "harmonic_censoring_h24_population_materialization_and_one_shot_contract",
        )
        self.assertEqual(
            hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
            materializer.H24_MATERIALIZATION_CONTRACT_RAW_SHA256,
        )
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertNotIn("numpy", imported)
        self.assertNotIn("tensorflow", imported)
        self.assertNotIn("data", imported)
        self.assertNotIn("evaluate_events", source)
        self.assertNotIn("if __name__", source)

    def test_dormant_factory_fails_before_plan_or_numpy_without_future_activation(self):
        self.assertFalse((ROOT / materializer.H24_AUTHORIZATION_SEAL_RELATIVE_PATH).exists())
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                materializer, "_zero_science_preflight"
            ) as preflight:
                with self.assertRaisesRegex(PermissionError, "remains dormant"):
                    materializer.issue_h24_population_materialization_capability(repository)
        preflight.assert_not_called()

    def test_preflight_runtime_probe_rejects_already_imported_numpy(self):
        with mock.patch.dict(materializer.sys.modules, {"numpy": object()}):
            with self.assertRaisesRegex(RuntimeError, "imported before"):
                materializer._runtime_identity_without_numpy_import()

    def test_authorization_seal_schema_is_exact_and_fail_closed(self):
        seal = _seal()
        self.assertEqual(seal.reviewed_materializer_commit, "a" * 40)
        extra = _seal_payload()
        extra["timestamp"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "keys mismatch"):
            materializer.validate_h24_population_materialization_authorization_seal(
                extra, raw_sha256="c" * 64
            )
        wrong = _seal_payload()
        wrong["materialization_contract_raw_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "contract binding"):
            materializer.validate_h24_population_materialization_authorization_seal(
                wrong, raw_sha256="c" * 64
            )

    def test_capability_has_exact_18_fields_and_is_factory_only_immutable(self):
        expected = {
            "population_id", "materialization_contract_raw_sha256",
            "implementation_commit", "materializer_source_blob",
            "harness_source_blob", "operator_source_blob",
            "successor_contract_raw_sha256", "population_manifest_raw_sha256",
            "test_manifest_raw_sha256", "manifest_binding_raw_sha256",
            "dormant_harness_contract_raw_sha256", "authorization_seal_path",
            "authorization_seal_raw_sha256", "claim_marker_path",
            "staging_directory", "success_directory", "terminal_record_path",
            "runtime_identity",
        }
        self.assertEqual(
            set(materializer.AttestedH24PopulationMaterializationCapability.__slots__)
            - {"__weakref__"},
            expected,
        )
        with self.assertRaisesRegex(TypeError, "factory-only"):
            materializer.AttestedH24PopulationMaterializationCapability()
        with tempfile.TemporaryDirectory() as temporary:
            capability = self._issue_synthetic_capability(Path(temporary))
            materializer.require_attested_h24_population_materialization_capability(capability)
            with self.assertRaises(AttributeError):
                capability.population_id = "forged"  # type: ignore[misc]
            with self.assertRaises(TypeError):
                copy.copy(capability)
            with self.assertRaises(TypeError):
                copy.deepcopy(capability)
            with self.assertRaises(TypeError):
                pickle.dumps(capability)

    def test_forged_lookalike_and_object_new_clone_are_not_attested(self):
        with tempfile.TemporaryDirectory() as temporary:
            capability = self._issue_synthetic_capability(Path(temporary))
            forged = object.__new__(materializer.AttestedH24PopulationMaterializationCapability)
            for name in materializer.AttestedH24PopulationMaterializationCapability.__slots__:
                if name != "__weakref__":
                    object.__setattr__(forged, name, getattr(capability, name))
            with self.assertRaisesRegex(PermissionError, "not factory-attested"):
                materializer.require_attested_h24_population_materialization_capability(forged)
            with self.assertRaises(TypeError):
                materializer.require_attested_h24_population_materialization_capability(object())

    def test_claim_payload_is_exact_and_claim_is_only_mocked_not_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            capability = self._issue_synthetic_capability(repository)
            captured: list[tuple[Path, bytes, bool]] = []

            def capture(path: Path, raw: bytes, *, create_parent: bool = True) -> None:
                captured.append((path, raw, create_parent))

            with mock.patch.object(materializer, "_revalidate_claim_authority"), mock.patch.object(
                materializer, "_write_exclusive_durable_file", side_effect=capture
            ):
                materializer.claim_h24_population_materialization_capability(capability)
            self.assertEqual(len(captured), 1)
            self.assertFalse(captured[0][2])
            self.assertFalse(captured[0][0].exists())
            payload = json.loads(captured[0][1])
            contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload), set(contract["future_claim_marker_contract"]["exact_fields"])
            )
            self.assertTrue(payload["population_consumed"])
            self.assertEqual(payload["runtime_identity"], dict(capability.runtime_identity))

    def test_failed_exclusive_claim_does_not_register_a_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            capability = self._issue_synthetic_capability(Path(temporary))
            with mock.patch.object(materializer, "_revalidate_claim_authority"), mock.patch.object(
                materializer,
                "_write_exclusive_durable_file",
                side_effect=FileExistsError("existing corrupt marker"),
            ):
                with self.assertRaises(FileExistsError):
                    materializer.claim_h24_population_materialization_capability(capability)
            with self.assertRaisesRegex(PermissionError, "not durably claimed"):
                materializer.require_claimed_h24_population_materialization_capability(capability)

    def test_materializer_refuses_unclaimed_capability_before_staging_or_numpy_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            capability = self._issue_synthetic_capability(repository)
            with self.assertRaisesRegex(PermissionError, "not durably claimed"):
                materializer.materialize_and_publish_h24_population(capability)
            self.assertFalse((repository / "tmp").exists())

    def test_waveform_validation_rejects_dtype_shape_nonfinite_and_byte_count(self):
        class Encoded:
            def __init__(self, raw: bytes):
                self.raw = raw

            def tobytes(self, *, order: str) -> bytes:
                self.order = order
                return self.raw

        class Waveform:
            def __init__(self, dtype: object, shape: tuple[int, ...], raw: bytes):
                self.dtype = dtype
                self.shape = shape
                self.raw = raw

            def astype(self, dtype: str, *, copy: bool):
                self.astype_call = (dtype, copy)
                return Encoded(self.raw)

        class FakeNp:
            float64 = object()

            @staticmethod
            def isfinite(value):
                return value

            @staticmethod
            def all(value):
                return value.finite

        np = FakeNp()
        good = Waveform(np.float64, (12544,), b"x" * 100352)
        good.finite = True
        self.assertEqual(materializer._encode_waveform(np, good), b"x" * 100352)
        self.assertEqual(good.astype_call, ("<f8", False))
        for waveform, message in (
            (Waveform(object(), (12544,), b"x" * 100352), "dtype or shape"),
            (Waveform(np.float64, (12543,), b"x" * 100352), "dtype or shape"),
            (Waveform(np.float64, (12544,), b"x" * 100351), "byte count"),
        ):
            waveform.finite = True
            with self.assertRaisesRegex(ValueError, message):
                materializer._encode_waveform(np, waveform)
        nonfinite = Waveform(np.float64, (12544,), b"x" * 100352)
        nonfinite.finite = False
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            materializer._encode_waveform(np, nonfinite)

    def test_reopened_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact"
            path.write_bytes(b"exact")
            materializer._require_reopened_hash(
                path, hashlib.sha256(b"exact").hexdigest(), "fixture"
            )
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                materializer._require_reopened_hash(path, "0" * 64, "fixture")

    def test_source_closes_numeric_trace_and_atomic_publish_without_dispatch(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        required = (
            "np.maximum(samples - onset, 0).astype(np.float64)",
            "fraction = np.minimum(elapsed / duration, 1.0)",
            "generator.standard_normal(bins)",
            "real = generator.standard_normal(bins)",
            "imag = generator.standard_normal(bins)",
            "local = np.arange(4096, dtype=np.float64)",
            "phase = 2.0 * np.pi * np.cumsum(frequency) / 44100.0",
            "for frequency in (233, 377, 611, 997, 1597)",
            "for harmonic in range(1, 9)",
            "waveform.astype(\"<f8\", copy=False).tobytes(order=\"C\")",
            "_verify_staging(staging, rows, receipt_raw)",
            "os.rename(staging, success)",
            "_atomic_terminal_write(terminal, terminal_payload)",
        )
        for needle in required:
            self.assertIn(needle, source)
        self.assertNotIn("scipy", source)
        self.assertNotIn("np.linspace", source)
        body = inspect.getsource(materializer._materialize_and_publish_h24_population_claimed)
        self.assertNotIn("P0", body)
        self.assertNotIn("P1", body)
        self.assertNotIn("P2", body)

    def test_real_s5_recipe_uses_the_exact_sealed_special_case_identifier(self):
        plan = materializer.load_h24_dormant_harness_plan(ROOT)
        recipes = materializer.translate_all_h24_fixture_specifications(plan)
        s5_recipes = tuple(recipe for recipe in recipes if recipe.base_id == "H24-F-S5")
        self.assertEqual(len(s5_recipes), 1)
        self.assertEqual(s5_recipes[0].base_id, "H24-F-S5")
        synthesis_source = inspect.getsource(materializer._synthesize_waveform)
        self.assertIn('recipe.base_id == "H24-F-S5"', synthesis_source)
        self.assertNotIn('recipe.base_id == "S5"', synthesis_source)

    def test_multisource_accumulation_is_global_per_harmonic_not_source_grouped(self):
        # The two algebraically similar orders are observably different in binary64.
        source_one = (1.0e16, 1.0)
        source_two = (-1.0e16, 1.0)
        global_per_harmonic = 0.0
        for source in (source_one, source_two):
            for term in source:
                global_per_harmonic += term
        grouped_per_source = sum(source_one) + sum(source_two)
        self.assertEqual(global_per_harmonic, 1.0)
        self.assertEqual(grouped_per_source, 0.0)

        accumulator_source = inspect.getsource(materializer._accumulate_source)
        self.assertNotIn("return waveform", accumulator_source)
        accumulator_tree = ast.parse(accumulator_source)
        waveform_assignments = [
            node
            for node in ast.walk(accumulator_tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and any(
                isinstance(target, ast.Name) and target.id == "waveform"
                for target in (
                    node.targets if isinstance(node, ast.Assign) else (node.target,)
                )
            )
        ]
        self.assertEqual(waveform_assignments, [])
        global_additions = [
            node
            for node in ast.walk(accumulator_tree)
            if isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "waveform"
            and isinstance(node.op, ast.Add)
        ]
        self.assertEqual(len(global_additions), 1)
        synthesis_source = inspect.getsource(materializer._synthesize_waveform)
        self.assertIn(
            "_accumulate_source(np, waveform, source, samples)", synthesis_source
        )
        self.assertNotIn("_render_source", SOURCE_PATH.read_text(encoding="utf-8"))

    def test_public_operations_have_no_caller_path_or_population_override(self):
        self.assertEqual(
            tuple(inspect.signature(materializer.issue_h24_population_materialization_capability).parameters),
            ("repository_root",),
        )
        self.assertEqual(
            tuple(inspect.signature(materializer.claim_h24_population_materialization_capability).parameters),
            ("value",),
        )
        self.assertEqual(
            tuple(inspect.signature(materializer.materialize_and_publish_h24_population).parameters),
            ("capability",),
        )

    def test_public_materializer_guard_has_no_numpy_bridge_even_if_claim_check_passes(self):
        with mock.patch.object(
            materializer,
            "require_claimed_h24_population_materialization_capability",
            return_value=object(),
        ):
            with self.assertRaisesRegex(PermissionError, "bridge remains unauthorized"):
                materializer.materialize_and_publish_h24_population(object())  # type: ignore[arg-type]

    def test_durable_writer_uses_exclusive_flags_and_mode_0600(self):
        source = inspect.getsource(materializer._write_exclusive_durable_file)
        self.assertIn("os.O_CREAT | os.O_EXCL | os.O_WRONLY", source)
        self.assertIn("0o600", source)
        self.assertIn("os.fsync(descriptor)", source)
        self.assertIn("_fsync_directory(path.parent)", source)


if __name__ == "__main__":
    unittest.main()
