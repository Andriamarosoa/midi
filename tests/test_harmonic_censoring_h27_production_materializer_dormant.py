from __future__ import annotations

import ast
import copy
import inspect
import pickle
from pathlib import Path
import unittest

from src.polyphonic import harmonic_censoring_h27_production_materializer_dormant as materializer


class _Exploding:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"dormant entry inspected {name}")

    def __fspath__(self) -> str:
        raise AssertionError("dormant entry inspected destination")


class H27ProductionMaterializerDormantTests(unittest.TestCase):
    def test_capability_has_no_constructor_copy_or_pickle_path(self) -> None:
        with self.assertRaises(PermissionError):
            materializer.H27ProductionMaterializationCapability()
        forged = object.__new__(materializer.H27ProductionMaterializationCapability)
        with self.assertRaises((TypeError, PermissionError)):
            copy.copy(forged)
        with self.assertRaises((TypeError, pickle.PicklingError)):
            pickle.dumps(forged)

    def test_entry_guard_precedes_every_input_access(self) -> None:
        forged = object.__new__(materializer.H27ProductionMaterializationCapability)
        with self.assertRaisesRegex(PermissionError, "remains dormant"):
            materializer.materialize_h27_production_population(
                _Exploding(), forged, _Exploding(),
            )

    def test_guard_is_unconditional_and_has_no_registry(self) -> None:
        source = inspect.getsource(materializer._require_capability)
        tree = ast.parse(source)
        self.assertEqual(len(tree.body), 1)
        function = tree.body[0]
        self.assertIsInstance(function, ast.FunctionDef)
        self.assertEqual(len(function.body), 2)  # docstring then raise
        self.assertIsInstance(function.body[-1], ast.Raise)
        module_source = Path(materializer.__file__).read_text(encoding="utf-8")
        self.assertNotIn("WeakKeyDictionary", module_source)
        self.assertNotIn("_CAPABILITIES", module_source)
        self.assertNotIn("def issue", module_source)

    def test_entry_calls_guard_as_first_statement(self) -> None:
        function = ast.parse(inspect.getsource(materializer.materialize_h27_production_population)).body[0]
        body = function.body[1:]  # skip docstring
        self.assertIsInstance(body[0], ast.Expr)
        self.assertEqual(ast.unparse(body[0].value), "_require_capability(capability)")

    def test_production_constants_and_index_contract_are_exact(self) -> None:
        self.assertEqual(materializer.SAMPLE_COUNT, 16640)
        self.assertEqual(materializer.SAMPLE_RATE_HZ, 44100)
        self.assertEqual(materializer.POPULATION_NAMESPACE, "H27_SYNTHETIC_V1")
        self.assertEqual(materializer.FINAL_DESTINATION.as_posix(), "/Users/amcarene/h27-admin/population/h27-synthetic-v1")
        self.assertEqual(materializer.STAGING_DESTINATION.as_posix(), "/Users/amcarene/h27-admin/population/.h27-synthetic-v1.staging")
        self.assertEqual(materializer.INDEX_FIELDS, (
            "record_identity", "record_directory", "population_namespace", "payload_sha256",
            "candidate_pitch", "active_pitches", "proposal_hop_end", "resolution_hop_end",
            "cents", "inharmonicity",
        ))

    def test_cell_enumerator_is_axis_ordered_and_deterministic_on_toy_data(self) -> None:
        grid = {
            "axis_names": ("a", "b"),
            "axes": {
                "a": ({"value": 1, "value_token": "one"}, {"value": 2, "value_token": "two"}),
                "b": ({"value": "x", "value_token": "x"}, {"value": "y", "value_token": "y"}),
            },
        }
        first = materializer._grid_cells(grid)
        second = materializer._grid_cells(grid)
        self.assertEqual(first, second)
        self.assertEqual([cell["cell_id"] for cell in first], [
            "a=one__b=x", "a=one__b=y", "a=two__b=x", "a=two__b=y",
        ])

    def test_canonical_json_is_utf8_lf_and_preserves_inserted_field_order(self) -> None:
        raw = materializer._canonical_json_bytes({"z": 1, "a": [2, 3]})
        self.assertEqual(raw, b'{"z":1,"a":[2,3]}\n')
        self.assertNotIn(b"\r", raw)

    def test_new_module_is_independent_of_h26_and_dormant_reference(self) -> None:
        source = Path(materializer.__file__).read_text(encoding="utf-8")
        self.assertNotIn("harmonic_censoring_h26", source)
        self.assertNotIn("harmonic_censoring_h27_materializer_dormant", source)
        self.assertNotIn("import numpy", source)
        self.assertIn("renameatx_np", source)
        self.assertIn("O_EXCL", source)
        self.assertIn("population_index.json", source)


if __name__ == "__main__":
    unittest.main()
