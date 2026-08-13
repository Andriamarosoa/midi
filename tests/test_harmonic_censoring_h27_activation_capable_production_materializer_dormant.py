from __future__ import annotations

import ast
import copy
import inspect
import pickle
import hashlib
import platform
import sys
import tempfile
from pathlib import Path
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as target
from src.polyphonic import harmonic_censoring_h27_production_materializer_dormant as reviewed


class _Exploding:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"forbidden input access: {name}")

    def __fspath__(self) -> str:
        raise AssertionError("forbidden filesystem access")


def _forged_capability() -> target.H27ActivationCapableProductionMaterializationCapability:
    return object.__new__(target.H27ActivationCapableProductionMaterializationCapability)


class H27ActivationCapableProductionMaterializerDormantTests(unittest.TestCase):
    def assertDormantBarrier(self, call: object) -> None:
        with self.assertRaises((KeyError, TypeError)):
            call()

    def test_normative_contracts_and_seals_validate_without_override(self) -> None:
        result = target.validate_normative_authority_bindings()
        self.assertEqual(set(result), {"authority_contract", "authority_seal", "activation_contract", "activation_seal"})
        self.assertEqual(result["activation_contract"]["population_namespace"], "H27_SYNTHETIC_V1")

    def test_no_issuer_authority_or_claim_api_exists(self) -> None:
        names = set(vars(target))
        self.assertFalse(any(name.startswith("issue_") for name in names))
        self.assertFalse(any(name.startswith("create_authority") for name in names))
        self.assertFalse(any(name.startswith("create_claim") for name in names))

    def test_forged_authority_cannot_be_supplied_to_entry(self) -> None:
        self.assertDormantBarrier(lambda: target.materialize_h27_activation_capable_production_population(_Exploding(), object(), _Exploding()))

    def test_forged_capability_via_object_new_is_rejected(self) -> None:
        self.assertDormantBarrier(lambda: target.materialize_h27_activation_capable_production_population(_Exploding(), _forged_capability(), _Exploding()))

    def test_copy_deepcopy_and_pickle_are_rejected(self) -> None:
        forged = _forged_capability()
        with self.assertRaises(PermissionError):
            copy.copy(forged)
        with self.assertRaises(PermissionError):
            copy.deepcopy(forged)
        with self.assertRaises((TypeError, pickle.PicklingError)):
            pickle.dumps(forged)

    def test_no_mutable_capability_registry_or_allowlist_exists(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        self.assertNotIn("WeakKeyDictionary", source)
        self.assertNotIn("_CAPABILITIES", source)
        self.assertNotIn("allowlist", source.lower())

    def test_guard_module_rebinding_cannot_unlock_frozen_entry(self) -> None:
        with mock.patch.object(target, "_require_capability", return_value=None):
            self.assertDormantBarrier(lambda: target.materialize_h27_activation_capable_production_population(_Exploding(), _forged_capability(), _Exploding()))
        self.assertFalse(hasattr(target._FROZEN_CAPABILITY_GUARD, "__code__"))
        self.assertFalse(hasattr(target._DORMANT_NATIVE_BARRIER, "__code__"))

    def test_publisher_monkeypatch_is_not_reached(self) -> None:
        with mock.patch.object(target, "_publish", side_effect=AssertionError("publisher reached")):
            self.assertDormantBarrier(lambda: target.materialize_h27_activation_capable_production_population(_Exploding(), _forged_capability(), _Exploding()))

    def test_direct_call_of_every_production_helper_fails_before_inputs(self) -> None:
        forged = _forged_capability()
        calls = (
            lambda: target._envelope(forged, _Exploding(), 0),
            lambda: target._accumulate_sources(forged, _Exploding(), _Exploding()),
            lambda: target._add_noise(forged, _Exploding(), _Exploding(), _Exploding()),
            lambda: target._render_recipe(forged, _Exploding(), _Exploding()),
            lambda: target._render_collision(forged, _Exploding(), _Exploding(), _Exploding()),
            lambda: target._mask_bytes(forged, _Exploding(), _Exploding()),
            lambda: target._render_record(forged, _Exploding(), _Exploding(), _Exploding()),
            lambda: target._write_new(forged, _Exploding(), _Exploding()),
            lambda: target._fsync_directory(forged, _Exploding()),
            lambda: target._rename_no_replace(forged, _Exploding(), _Exploding()),
            lambda: target._publish(forged, _Exploding(), _Exploding()),
        )
        for call in calls:
            with self.subTest(call=call):
                self.assertDormantBarrier(call)

    def test_wrong_or_missing_materializer_blob_and_seal_are_terminal(self) -> None:
        self.assertIsNone(target.FUTURE_MATERIALIZER_REVIEWED_BLOB)
        self.assertIsNone(target.FUTURE_MATERIALIZER_EXTERNAL_SEAL_SHA256)
        with self.assertRaisesRegex(PermissionError, "not reviewed or sealed"):
            target._require_reviewed_self_identity()

    def test_wrong_runtime_or_environment_cannot_reach_science(self) -> None:
        with mock.patch.dict("os.environ", {"MIDI_FORCE_CPU": "0"}):
            with self.assertRaisesRegex(PermissionError, "runtime mismatch|environment mismatch"):
                target.validate_preclaim_runtime_git_and_destinations()

    def test_preexisting_destinations_are_not_inspected_before_guard(self) -> None:
        runtime = {
            "implementation": platform.python_implementation(), "version": platform.python_version(),
            "platform_system": platform.system(), "platform_release": platform.release(),
            "platform_machine": platform.machine(), "resolved_executable": Path(sys.executable).resolve().as_posix(),
            "executable_size_bytes": Path(sys.executable).stat().st_size,
            "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        }
        activation = {"runtime_exact": runtime, "process_environment_exact": {}, "atomic_publication": {}}
        completed = mock.Mock(stdout="f" * 40 + "\n")
        with mock.patch.object(target, "validate_normative_authority_bindings", return_value={"activation_contract": activation}), mock.patch.object(
            target, "FUTURE_ACTIVATION_REVIEWED_HEAD", "f" * 40,
        ), mock.patch.object(target.subprocess, "run", side_effect=(completed, mock.Mock(stdout=""))), mock.patch.object(
            target.os.path, "lexists", return_value=True,
        ):
            with self.assertRaises(FileExistsError):
                target.validate_preclaim_runtime_git_and_destinations()

    def test_claim_write_or_fsync_path_does_not_exist_in_this_lot(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        self.assertNotIn("consumed.json", source)
        self.assertNotIn("invocation_nonce", source)

    def test_second_capability_consumption_is_impossible(self) -> None:
        forged = _forged_capability()
        for _ in range(2):
            self.assertDormantBarrier(lambda: target.materialize_h27_activation_capable_production_population(_Exploding(), forged, _Exploding()))

    def test_post_claim_identity_drift_has_no_claim_to_consume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seal = Path(directory) / "seal.json"
            seal.write_bytes(b"{}\n")
            with mock.patch.object(target, "FUTURE_MATERIALIZER_REVIEWED_BLOB", "0" * 40), mock.patch.object(
                target, "FUTURE_MATERIALIZER_EXTERNAL_SEAL_SHA256", hashlib.sha256(seal.read_bytes()).hexdigest(),
            ), mock.patch.object(target, "FUTURE_MATERIALIZER_EXTERNAL_SEAL_PATH", seal):
                with self.assertRaisesRegex(PermissionError, "identity drift"):
                    target._require_reviewed_self_identity()

    def test_scientific_helpers_are_mechanically_identical_to_reviewed_blob(self) -> None:
        old_source = Path(reviewed.__file__).read_text(encoding="utf-8")
        new_source = Path(target.__file__).read_text(encoding="utf-8")
        old_tree = ast.parse(old_source)
        new_tree = ast.parse(new_source)
        names = {
            "_canonical_json_bytes", "_numeric", "_f0", "_envelope", "_accumulate_sources",
            "_add_noise", "_render_recipe", "_render_collision", "_grid_cells",
            "_fixture_active_pitches", "_descriptors", "_transformed_recipe", "_mask_bytes",
            "_render_record", "_write_new", "_fsync_directory", "_rename_no_replace", "_publish",
        }
        def segments(tree: ast.Module, source: str) -> dict[str, str]:
            return {node.name: ast.get_source_segment(source, node) for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names}
        old = segments(old_tree, old_source)
        new = segments(new_tree, new_source)
        self.assertEqual(set(old), names)
        self.assertEqual(set(new), names)
        normalized = {key: value.replace("H27ActivationCapableProductionMaterializationCapability", "H27ProductionMaterializationCapability") for key, value in new.items()}
        self.assertEqual(normalized, old)


if __name__ == "__main__":
    unittest.main()
