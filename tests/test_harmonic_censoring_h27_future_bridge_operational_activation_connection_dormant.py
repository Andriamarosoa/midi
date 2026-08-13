from __future__ import annotations

import copy
import json
from pathlib import Path
import pickle
import shutil
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
NONCE = "d" * 64
PID = 4321


def _ticket(**overrides: object) -> gate._H27DormantActivationConnectionTicket:
    values = dict(
        step11_binding=object(),
        authority_sha256=SHA_A,
        claim_sha256=SHA_B,
        invocation_nonce=NONCE,
        process_id=PID,
        code_identity_sha256=SHA_C,
    )
    values.update(overrides)
    return gate._make_mock_activation_connection_ticket(**values)


def _adapters(
    order: list[str],
    ticket: gate._H27DormantActivationConnectionTicket,
) -> gate.H27DormantActivationConnectionAdapters:
    def call(name: str, result: object = None):
        def inner(*_: object) -> object:
            order.append(name)
            return result
        return inner

    return gate.H27DormantActivationConnectionAdapters(
        verify_git_and_code_identities=call("git_code"),
        observe_step11_binding=call("step11", (ticket.step11_binding, True)),
        observe_authority_claim=call("authority_claim", (SHA_A, SHA_B, True)),
        observe_runtime_binding=call("runtime", (NONCE, PID, SHA_C)),
        observe_bridge_terminal_state=call("bridge_terminal", True),
        observe_materializer=call("materializer", (gate._MATERIALIZER_BLOB, True)),
        observe_composition_to_bridge=call("composition_bridge", (False, False)),
        observe_bridge_to_materializer=call("bridge_materializer", (False, False)),
        finalize_synthetic_gate=call("finalize", ticket),
    )


class H27FutureBridgeOperationalActivationConnectionDormantTests(unittest.TestCase):
    def test_successful_harness_terminates_without_activation_connection_or_science(self) -> None:
        exact = _ticket()
        order: list[str] = []
        trace = gate._exercise_dormant_activation_connection(exact, exact, _adapters(order, exact))
        self.assertEqual(
            order,
            ["git_code", "step11", "authority_claim", "runtime", "bridge_terminal", "materializer", "composition_bridge", "bridge_materializer", "finalize"],
        )
        self.assertFalse(trace.activation_created)
        self.assertFalse(trace.composition_to_bridge_connected)
        self.assertFalse(trace.bridge_to_materializer_connected)
        self.assertEqual(trace.materializer_invocations, 0)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_nonidentical_ticket_and_wrong_types_are_rejected_before_adapters(self) -> None:
        exact = _ticket()
        for received in (_ticket(), {}, (), object()):
            order: list[str] = []
            with self.subTest(received=type(received)):
                with self.assertRaises(PermissionError):
                    gate._exercise_dormant_activation_connection(exact, received, _adapters(order, exact))
                self.assertEqual(order, [])

    def test_malformed_ticket_fields_are_rejected_before_adapters(self) -> None:
        cases = (
            _ticket(step11_binding=None),
            _ticket(authority_sha256="bad"),
            _ticket(claim_sha256="bad"),
            _ticket(invocation_nonce="bad"),
            _ticket(process_id=0),
            _ticket(code_identity_sha256="bad"),
        )
        for malformed in cases:
            order: list[str] = []
            with self.subTest(ticket=malformed):
                with self.assertRaises(PermissionError):
                    gate._exercise_dormant_activation_connection(malformed, malformed, _adapters(order, malformed))
                self.assertEqual(order, [])

    def test_each_semantic_stage_failure_stops_later_stages(self) -> None:
        exact = _ticket()
        fields = (
            ("git_code", "verify_git_and_code_identities"),
            ("step11", "observe_step11_binding"),
            ("authority_claim", "observe_authority_claim"),
            ("runtime", "observe_runtime_binding"),
            ("bridge_terminal", "observe_bridge_terminal_state"),
            ("materializer", "observe_materializer"),
            ("composition_bridge", "observe_composition_to_bridge"),
            ("bridge_materializer", "observe_bridge_to_materializer"),
            ("finalize", "finalize_synthetic_gate"),
        )
        names = [name for name, _ in fields]
        for index, (name, field) in enumerate(fields):
            order: list[str] = []
            adapters = _adapters(order, exact)._replace(**{field: mock.Mock(side_effect=PermissionError(name))})
            with self.subTest(stage=name):
                with self.assertRaises(PermissionError):
                    gate._exercise_dormant_activation_connection(exact, exact, adapters)
                self.assertEqual(order, names[:index])

    def test_all_mismatches_and_open_edges_fail_closed(self) -> None:
        exact = _ticket()
        cases = (
            {"observe_step11_binding": mock.Mock(return_value=(object(), True))},
            {"observe_step11_binding": mock.Mock(return_value=(exact.step11_binding, False))},
            {"observe_authority_claim": mock.Mock(return_value=("e" * 64, SHA_B, True))},
            {"observe_authority_claim": mock.Mock(return_value=(SHA_A, "e" * 64, True))},
            {"observe_authority_claim": mock.Mock(return_value=(SHA_A, SHA_B, False))},
            {"observe_runtime_binding": mock.Mock(return_value=("e" * 64, PID, SHA_C))},
            {"observe_runtime_binding": mock.Mock(return_value=(NONCE, PID + 1, SHA_C))},
            {"observe_runtime_binding": mock.Mock(return_value=(NONCE, PID, "e" * 64))},
            {"observe_bridge_terminal_state": mock.Mock(return_value=False)},
            {"observe_materializer": mock.Mock(return_value=("e" * 40, True))},
            {"observe_materializer": mock.Mock(return_value=(gate._MATERIALIZER_BLOB, False))},
            {"observe_composition_to_bridge": mock.Mock(return_value=(True, False))},
            {"observe_composition_to_bridge": mock.Mock(return_value=(False, True))},
            {"observe_bridge_to_materializer": mock.Mock(return_value=(True, False))},
            {"observe_bridge_to_materializer": mock.Mock(return_value=(False, True))},
        )
        for replacement in cases:
            with self.subTest(field=next(iter(replacement))):
                with self.assertRaises(PermissionError):
                    gate._exercise_dormant_activation_connection(exact, exact, _adapters([], exact)._replace(**replacement))

    def test_ticket_is_immutable_noncopyable_nonserializable_and_single_use(self) -> None:
        with self.assertRaises(PermissionError):
            gate._H27DormantActivationConnectionTicket()
        exact = _ticket()
        with self.assertRaises(TypeError):
            exact.process_id = PID + 1
        with self.assertRaises(TypeError):
            exact._consume_gate_right = lambda _: object()
        with self.assertRaises(TypeError):
            copy.copy(exact)
        with self.assertRaises(TypeError):
            copy.deepcopy(exact)
        with self.assertRaises(TypeError):
            pickle.dumps(exact)

    def test_second_full_call_and_retry_after_postconsume_failure_are_terminal(self) -> None:
        successful = _ticket()
        self.assertTrue(gate._exercise_dormant_activation_connection(successful, successful, _adapters([], successful)).terminal)
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            gate._exercise_dormant_activation_connection(successful, successful, _adapters([], successful))

        interrupted = _ticket()
        failing = _adapters([], interrupted)._replace(
            finalize_synthetic_gate=mock.Mock(side_effect=RuntimeError("interrupt"))
        )
        with self.assertRaisesRegex(RuntimeError, "interrupt"):
            gate._exercise_dormant_activation_connection(interrupted, interrupted, failing)
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            gate._exercise_dormant_activation_connection(interrupted, interrupted, _adapters([], interrupted))

    def test_each_of_thirty_two_sealed_inputs_fails_before_any_mock(self) -> None:
        binding = json.loads((ROOT / gate._ACTIVATION_CONNECTION_INPUTS[2][0]).read_bytes())
        predecessors = tuple(item["path"] for item in binding["byte_identical_predecessor_chains"].values())
        direct = tuple(item[0] for group in (
            gate._ACTIVATION_CONNECTION_INPUTS,
            gate._BRIDGE_INPUTS,
            gate._COMPATIBILITY_INPUTS,
        ) for item in group)
        all_paths = direct + predecessors
        self.assertEqual(len(all_paths), 32)
        for target in all_paths:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                sandbox = Path(tmp)
                for relative in set(all_paths):
                    destination = sandbox / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / relative, destination)
                with (sandbox / target).open("ab") as handle:
                    handle.write(b"drift")
                exact = _ticket()
                order: list[str] = []
                with mock.patch.object(gate, "_ROOT", sandbox):
                    with self.assertRaises(PermissionError):
                        gate._exercise_dormant_activation_connection(exact, exact, _adapters(order, exact))
                self.assertEqual(order, [])

    def test_new_and_existing_public_edges_are_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")

    def test_source_has_no_science_materializer_invocation_or_admin_write(self) -> None:
        source = Path(gate.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("materialize_h27_activation_capable_production_population(", source)
        self.assertNotIn("/Users/amcarene", source)
        self.assertNotIn("h27-admin", source)
        self.assertNotIn("locked_test", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("open(", source)


if __name__ == "__main__":
    unittest.main()
