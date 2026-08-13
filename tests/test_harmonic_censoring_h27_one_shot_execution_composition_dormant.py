from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


class H27OneShotExecutionCompositionDormantTests(unittest.TestCase):
    def _adapters(self, order: list[str], *, failure: str | None = None):
        binding = object()
        capability = object()

        def step(name: str):
            def run(*args):
                del args
                order.append(name)
                if failure == name:
                    raise PermissionError(f"synthetic {name} failure")
                if name == "create_durable_claim":
                    return object()
                if name == "construct_capability":
                    return capability, binding
                if name == "consume_attested":
                    return binding
                return None
            return run

        return composition.H27DormantCompositionAdapters(*(step(name) for name in composition._STEPS))

    def test_exact_order_stops_before_science(self) -> None:
        order: list[str] = []
        trace = composition._exercise_dormant_composition(self._adapters(order))
        self.assertEqual(tuple(order), composition._STEPS)
        self.assertEqual(trace.steps, composition._STEPS)
        self.assertTrue(trace.claim_created)
        self.assertTrue(trace.capability_consumed)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_each_sealed_administrative_input_is_verified_before_adapters(self) -> None:
        for index, binding in enumerate(composition._SEALED_ADMINISTRATIVE_INPUTS):
            with self.subTest(path=binding[0]), tempfile.TemporaryDirectory() as parent:
                fake_root = Path(parent)
                for relative, _, _, _ in composition._SEALED_ADMINISTRATIVE_INPUTS:
                    target = fake_root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((composition._ROOT / relative).read_bytes())
                (fake_root / binding[0]).write_bytes(b"drift")
                order: list[str] = []
                with mock.patch.object(composition, "_ROOT", fake_root):
                    with self.assertRaisesRegex(PermissionError, "administrative binding drift"):
                        composition._exercise_dormant_composition(self._adapters(order))
                if binding in composition._COMPOSITION_INPUTS:
                    expected = ["verify_fixed_paths"]
                elif binding in composition._HISTORICAL_INPUTS:
                    expected = ["verify_fixed_paths", "verify_contract_chain"]
                else:
                    expected = ["verify_fixed_paths", "verify_contract_chain", "verify_historical_chain"]
                self.assertEqual(order, expected, index)

    def test_every_failure_is_terminal_and_later_steps_are_not_called(self) -> None:
        for failed_index, failed in enumerate(composition._STEPS):
            with self.subTest(failed=failed):
                order: list[str] = []
                with self.assertRaisesRegex(PermissionError, failed):
                    composition._exercise_dormant_composition(self._adapters(order, failure=failed))
                self.assertEqual(order, list(composition._STEPS[: failed_index + 1]))

    def test_foreign_consumption_binding_is_rejected_after_claim(self) -> None:
        order: list[str] = []
        adapters = self._adapters(order)._replace(consume_attested=mock.Mock(return_value=object()))
        with self.assertRaisesRegex(PermissionError, "foreign binding"):
            composition._exercise_dormant_composition(adapters)

    def test_bad_capability_pair_is_rejected_without_science(self) -> None:
        for value in (None, (object(),), [object(), object()]):
            with self.subTest(value=value):
                adapters = self._adapters([])._replace(construct_capability=mock.Mock(return_value=value))
                with self.assertRaisesRegex(PermissionError, "exact pair"):
                    composition._exercise_dormant_composition(adapters)

    def test_public_edge_is_native_closed_barrier(self) -> None:
        edge = composition.execute_h27_one_shot_composition
        self.assertIs(type(edge), type(().__getitem__))
        self.assertEqual(edge.__self__, ())
        self.assertEqual(edge.__name__, "__getitem__")
        exploding = mock.Mock(side_effect=AssertionError("must not inspect"))
        with self.assertRaises((IndexError, TypeError)):
            edge(exploding)
        exploding.assert_not_called()

    def test_harness_has_no_science_or_filesystem_parameters(self) -> None:
        parameters = inspect.signature(composition._exercise_dormant_composition).parameters
        self.assertEqual(tuple(parameters), ("adapters",))
        source = Path(composition.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import numpy",
            "materialize_h27_activation_capable_production_population",
            "/Users/amcarene",
            "write_bytes",
            "os.open",
            "locked_test",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
