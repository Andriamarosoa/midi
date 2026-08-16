from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_production_materializer_dormant as reviewed
from src.polyphonic import harmonic_censoring_h27_review4_materializer as review4


ROOT = Path(__file__).resolve().parents[1]
HELPERS = (
    "_canonical_json_bytes", "_numeric", "_f0", "_envelope", "_accumulate_sources",
    "_add_noise", "_render_recipe", "_render_collision", "_grid_cells",
    "_fixture_active_pitches", "_descriptors", "_transformed_recipe", "_mask_bytes",
    "_render_record", "_write_new", "_fsync_directory", "_rename_no_replace", "_publish",
)


def normalized_function(module: object, name: str) -> str:
    tree = ast.parse(inspect.getsource(getattr(module, name)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "H27ProductionMaterializationCapability":
            node.id = "CAPABILITY"
    return ast.dump(tree, include_attributes=False)


class Review4MaterializerTests(unittest.TestCase):
    def setUp(self) -> None:
        review4._ISSUED = False

    def test_scientific_and_publication_functions_are_mechanically_identical(self) -> None:
        for name in HELPERS:
            self.assertEqual(normalized_function(reviewed, name), normalized_function(review4, name), name)

    def test_forged_capability_and_direct_entry_fail_before_publish(self) -> None:
        with mock.patch.object(review4, "_publish") as publish:
            with self.assertRaises(PermissionError):
                review4.materialize_h27_production_population(object(), object(), object())
        publish.assert_not_called()

    def test_single_capability_is_consumed_before_publish_and_never_retries(self) -> None:
        capability = review4._issue_review4_capability()
        with self.assertRaises(PermissionError):
            review4._issue_review4_capability()
        states: list[str] = []
        with mock.patch.object(review4, "_publish", side_effect=lambda cap, _np, _plan: states.append(cap._state)):
            review4.materialize_h27_production_population(object(), capability, object())
        self.assertEqual(states, ["active"])
        self.assertEqual(capability._state, "terminal")
        with self.assertRaises(PermissionError):
            review4.materialize_h27_production_population(object(), capability, object())

    def test_post_consumption_failure_is_terminal(self) -> None:
        capability = review4._issue_review4_capability()
        with mock.patch.object(review4, "_publish", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                review4.materialize_h27_production_population(object(), capability, object())
        self.assertEqual(capability._state, "terminal")

    def test_runner_has_no_science_or_locked_test_surface(self) -> None:
        source = (ROOT / "scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('"locked_test_opened": False'), 1)
        self.assertNotIn("run_h27_engine", source)
        self.assertNotIn("run_h27_independent_recomputer", source)
        self.assertIn('"total_records": 124', source)
        self.assertIn('"baseline_records": baseline', source)
        self.assertIn('"p2_records": p2', source)


if __name__ == "__main__":
    unittest.main()
