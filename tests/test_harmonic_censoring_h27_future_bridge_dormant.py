from __future__ import annotations

import copy
import json
from pathlib import Path
import pickle
import shutil
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
NONCE = "d" * 64
MATERIALIZER_BLOB = "79f399359e366781f9526098c98a93cca71b1b49"
PID = 4321


def _binding(**overrides: object) -> bridge._H27DormantStep11Binding:
    values = dict(
        authority_sha256=SHA_A,
        claim_sha256=SHA_B,
        materializer_blob=MATERIALIZER_BLOB,
        invocation_nonce=NONCE,
        process_id=PID,
        code_identity_sha256=SHA_C,
    )
    values.update(overrides)
    return bridge._make_mock_step11_binding(**values)


def _adapters(order: list[str]) -> bridge.H27DormantBridgeAdapters:
    def call(name: str, result: object = None):
        def inner(*_: object) -> object:
            order.append(name)
            return result
        return inner

    return bridge.H27DormantBridgeAdapters(
        verify_contract_semantics=call("contract"),
        verify_predecessor_semantics=call("predecessors"),
        verify_module_identities=call("modules"),
        observe_authority_claim=call("authority_claim", (SHA_A, SHA_B, True)),
        observe_runtime_binding=call("runtime", (NONCE, PID, SHA_C)),
        observe_materializer=call("materializer", (MATERIALIZER_BLOB, True)),
        derive_simulated_materializer_capability=call("derive", object()),
    )


class H27FutureBridgeDormantTests(unittest.TestCase):
    def test_successful_harness_terminates_before_materializer_or_science(self) -> None:
        exact = _binding()
        order: list[str] = []
        trace = bridge._exercise_dormant_bridge(exact, exact, _adapters(order))
        self.assertEqual(order, ["contract", "predecessors", "modules", "authority_claim", "runtime", "materializer", "derive"])
        self.assertEqual(
            trace.steps,
            (
                "receive_exact_step11_binding",
                "verify_bridge_contract_chain",
                "verify_twenty_predecessors",
                "verify_module_identities",
                "verify_authority_claim",
                "verify_nonce_process_code_identity",
                "verify_materializer_identity_and_barrier",
                "consume_simulated_local_invocation_right",
                "derive_simulated_materializer_capability",
            ),
        )
        self.assertTrue(trace.binding_attested)
        self.assertTrue(trace.local_invocation_right_consumed)
        self.assertTrue(trace.simulated_materializer_capability_derived)
        self.assertEqual(trace.materializer_invocations, 0)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_nonidentical_equal_binding_and_wrong_types_are_rejected_first(self) -> None:
        exact = _binding()
        for received in (_binding(), tuple(vars(exact)) if hasattr(exact, "__dict__") else (), {
            "authority_sha256": SHA_A
        }, object()):
            order: list[str] = []
            with self.subTest(type=type(received)):
                with self.assertRaises(PermissionError):
                    bridge._exercise_dormant_bridge(exact, received, _adapters(order))
                self.assertEqual(order, [])

    def test_each_semantic_stage_failure_stops_every_later_stage(self) -> None:
        exact = _binding()
        names = ["contract", "predecessors", "modules", "authority_claim", "runtime", "materializer", "derive"]
        fields = {
            "contract": "verify_contract_semantics",
            "predecessors": "verify_predecessor_semantics",
            "modules": "verify_module_identities",
            "authority_claim": "observe_authority_claim",
            "runtime": "observe_runtime_binding",
            "materializer": "observe_materializer",
            "derive": "derive_simulated_materializer_capability",
        }
        for failed_index, failed_name in enumerate(names):
            order: list[str] = []
            adapters = _adapters(order)._replace(
                **{fields[failed_name]: mock.Mock(side_effect=PermissionError(failed_name))}
            )
            with self.subTest(stage=failed_name):
                with self.assertRaises(PermissionError):
                    bridge._exercise_dormant_bridge(exact, exact, adapters)
                self.assertEqual(order, names[:failed_index])

    def test_stale_claim_and_each_binding_field_mismatch_are_rejected(self) -> None:
        exact = _binding()
        cases = (
            ("stale_claim", {"observe_authority_claim": mock.Mock(return_value=(SHA_A, SHA_B, False))}),
            ("authority_sha", {"observe_authority_claim": mock.Mock(return_value=("e" * 64, SHA_B, True))}),
            ("claim_sha", {"observe_authority_claim": mock.Mock(return_value=(SHA_A, "e" * 64, True))}),
            ("nonce", {"observe_runtime_binding": mock.Mock(return_value=("e" * 64, PID, SHA_C))}),
            ("pid", {"observe_runtime_binding": mock.Mock(return_value=(NONCE, PID + 1, SHA_C))}),
            ("code_identity", {"observe_runtime_binding": mock.Mock(return_value=(NONCE, PID, "e" * 64))}),
            ("materializer_blob", {"observe_materializer": mock.Mock(return_value=("e" * 40, True))}),
            ("materializer_barrier", {"observe_materializer": mock.Mock(return_value=(MATERIALIZER_BLOB, False))}),
        )
        for name, replacement in cases:
            order: list[str] = []
            with self.subTest(case=name):
                with self.assertRaises(PermissionError):
                    bridge._exercise_dormant_bridge(exact, exact, _adapters(order)._replace(**replacement))

    def test_malformed_exact_binding_fields_are_rejected_before_adapters(self) -> None:
        exact = _binding()
        cases = (
            _binding(authority_sha256="bad"),
            _binding(claim_sha256="bad"),
            _binding(materializer_blob="bad"),
            _binding(invocation_nonce="bad"),
            _binding(process_id=0),
            _binding(code_identity_sha256="bad"),
        )
        for malformed in cases:
            order: list[str] = []
            with self.subTest(binding=malformed):
                with self.assertRaises(PermissionError):
                    bridge._exercise_dormant_bridge(malformed, malformed, _adapters(order))
                self.assertEqual(order, [])

    def test_local_invocation_right_is_identity_bound_single_use_and_no_retry(self) -> None:
        exact = _binding()
        consumer = bridge._single_use_local_right(exact)
        next(consumer)
        token = consumer.send(exact)
        self.assertEqual(type(token).__name__, "_SimulatedLocalInvocationRight")
        with self.assertRaises(StopIteration):
            consumer.send(exact)
        with self.assertRaises(StopIteration):
            consumer.send(exact)
        foreign = bridge._single_use_local_right(exact)
        next(foreign)
        with self.assertRaises(PermissionError):
            foreign.send(_binding())

    def test_step11_binding_has_no_public_constructor_or_mutable_retry_state(self) -> None:
        with self.assertRaises(PermissionError):
            bridge._H27DormantStep11Binding()
        exact = _binding()
        with self.assertRaises(TypeError):
            exact.authority_sha256 = SHA_B
        with self.assertRaises(TypeError):
            exact._consume_bridge_right = lambda _: object()
        with self.assertRaises(TypeError):
            copy.copy(exact)
        with self.assertRaises(TypeError):
            copy.deepcopy(exact)
        with self.assertRaises(TypeError):
            pickle.dumps(exact)

    def test_second_full_harness_call_with_same_binding_is_terminally_rejected(self) -> None:
        exact = _binding()
        first = bridge._exercise_dormant_bridge(exact, exact, _adapters([]))
        self.assertTrue(first.terminal)
        second_order: list[str] = []
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            bridge._exercise_dormant_bridge(exact, exact, _adapters(second_order))
        self.assertEqual(second_order, ["contract", "predecessors", "modules", "authority_claim", "runtime", "materializer"])

    def test_derive_failure_after_consumption_makes_retry_terminal(self) -> None:
        exact = _binding()
        first_order: list[str] = []
        failing = _adapters(first_order)._replace(
            derive_simulated_materializer_capability=mock.Mock(side_effect=RuntimeError("interrupt"))
        )
        with self.assertRaisesRegex(RuntimeError, "interrupt"):
            bridge._exercise_dormant_bridge(exact, exact, failing)
        retry_order: list[str] = []
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            bridge._exercise_dormant_bridge(exact, exact, _adapters(retry_order))
        self.assertEqual(retry_order, ["contract", "predecessors", "modules", "authority_claim", "runtime", "materializer"])

    def test_each_of_twenty_four_sealed_inputs_is_rejected_before_its_mock(self) -> None:
        contract = json.loads((ROOT / bridge._BRIDGE_CHAIN_INPUTS[0][0]).read_bytes())
        predecessors = tuple(binding["path"] for binding in contract["sealed_predecessors"].values())
        bridge_paths = tuple(binding[0] for binding in bridge._BRIDGE_CHAIN_INPUTS)
        all_paths = bridge_paths + predecessors
        self.assertEqual(len(all_paths), 24)
        for target in all_paths:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                sandbox = Path(tmp)
                for relative in all_paths:
                    destination = sandbox / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / relative, destination)
                with (sandbox / target).open("ab") as handle:
                    handle.write(b"drift")
                exact = _binding()
                order: list[str] = []
                with mock.patch.object(bridge, "_ROOT", sandbox):
                    with self.assertRaises(PermissionError):
                        bridge._exercise_dormant_bridge(exact, exact, _adapters(order))
                self.assertEqual(order, [] if target in bridge_paths else ["contract"])

    def test_public_edge_is_exact_native_empty_tuple_barrier(self) -> None:
        edge = bridge.invoke_h27_future_bridge
        self.assertIs(type(edge), type(().__getitem__))
        self.assertEqual(edge.__self__, ())
        self.assertEqual(edge.__name__, "__getitem__")

    def test_source_has_no_operation_science_or_admin_path(self) -> None:
        source = Path(bridge.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("materialize_h27_activation_capable_production_population", source)
        self.assertNotIn("/Users/amcarene", source)
        self.assertNotIn("h27-admin", source)
        self.assertNotIn("locked_test", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("open(", source)


if __name__ == "__main__":
    unittest.main()
