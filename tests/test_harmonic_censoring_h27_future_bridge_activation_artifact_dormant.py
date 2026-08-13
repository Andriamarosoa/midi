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
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
SHA_A, SHA_B, SHA_C, SHA_D = (letter * 64 for letter in "abcd")


def _ticket(**overrides: object) -> artifact._H27DormantActivationArtifactTicket:
    values = dict(
        schema_version=1, activation_id="synthetic-activation", population_namespace="H27_SYNTHETIC_V1",
        gate_module_blob=artifact._GATE_BLOB, gate_identity_binding_sha256=artifact._GATE_BINDING_SHA,
        authority_sha256=SHA_A, claim_sha256=SHA_B, invocation_nonce=SHA_C, process_id=4321,
        code_identity_sha256=SHA_D, materializer_blob=artifact._MATERIALIZER_BLOB,
        terminal_step11_binding_sha256="e" * 64, created_at_utc="2026-08-13T00:00:00Z", terminal=True,
    )
    values.update(overrides)
    return artifact._make_mock_ticket(**values)


def _adapters(ticket: artifact._H27DormantActivationArtifactTicket, order: list[str]) -> artifact.H27DormantActivationArtifactAdapters:
    def preconditions() -> dict[str, bool]:
        order.append("preconditions")
        return {name: True for name in artifact._PRECONDITIONS}
    def connections() -> tuple[bool, bool]:
        order.append("connections")
        return False, False
    def unique(activation_id: str) -> bool:
        order.append("unique")
        return activation_id == "synthetic-activation"
    def simulate(payload: dict[str, object]) -> tuple[bool, bool]:
        order.append("simulate")
        if tuple(payload) != artifact._FIELDS:
            raise AssertionError("field order")
        return False, False
    def finalize(_: object, __: dict[str, object]) -> object:
        order.append("finalize")
        return ticket
    return artifact.H27DormantActivationArtifactAdapters(preconditions, unique, connections, simulate, finalize)


class H27FutureBridgeActivationArtifactDormantTests(unittest.TestCase):
    def test_success_builds_exact_in_memory_schema_without_creation_or_write(self) -> None:
        exact = _ticket()
        order: list[str] = []
        trace = artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, order))
        self.assertEqual(trace.payload_fields, artifact._FIELDS)
        self.assertEqual(order, ["preconditions", "unique", "connections", "simulate", "finalize"])
        self.assertFalse(trace.artifact_created)
        self.assertFalse(trace.artifact_written)
        self.assertFalse(trace.composition_to_bridge_connected)
        self.assertFalse(trace.bridge_to_materializer_connected)
        self.assertEqual(trace.materializer_invocations, 0)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_nonidentical_and_malformed_tickets_fail_before_adapters(self) -> None:
        exact = _ticket()
        for received in (_ticket(), {}, object()):
            order: list[str] = []
            with self.assertRaises(PermissionError):
                artifact._exercise_dormant_activation_artifact(exact, received, _adapters(exact, order))
            self.assertEqual(order, [])
        for bad in (
            _ticket(schema_version=2), _ticket(activation_id=""), _ticket(authority_sha256="bad"),
            _ticket(process_id=0), _ticket(materializer_blob="f" * 40),
            _ticket(created_at_utc="bad"), _ticket(created_at_utc="garbageZ"),
            _ticket(created_at_utc="2026-99-99T99:99:99Z"), _ticket(terminal=False),
        ):
            order = []
            with self.assertRaises(PermissionError):
                artifact._exercise_dormant_activation_artifact(bad, bad, _adapters(bad, order))
            self.assertEqual(order, [])

    def test_incomplete_preconditions_open_connections_or_write_are_rejected(self) -> None:
        exact = _ticket()
        base = _adapters(exact, [])
        cases = (
            {"observe_preconditions": mock.Mock(return_value={})},
            {"observe_activation_id_unique": mock.Mock(return_value=False)},
            {"observe_connections": mock.Mock(return_value=(True, False))},
            {"simulate_atomic_create_exclusive": mock.Mock(return_value=(True, False))},
            {"simulate_atomic_create_exclusive": mock.Mock(return_value=(False, True))},
            {"finalize": mock.Mock(return_value=object())},
        )
        for replacement in cases:
            with self.assertRaises(PermissionError):
                artifact._exercise_dormant_activation_artifact(exact, exact, base._replace(**replacement))

    def test_rfc3339_utc_with_fraction_is_accepted(self) -> None:
        exact = _ticket(created_at_utc="2026-08-13T12:34:56.123456Z")
        trace = artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, []))
        self.assertTrue(trace.terminal)

    def test_ticket_is_immutable_noncopyable_nonserializable_and_terminal(self) -> None:
        with self.assertRaises(PermissionError):
            artifact._H27DormantActivationArtifactTicket()
        exact = _ticket()
        for operation in (lambda: copy.copy(exact), lambda: copy.deepcopy(exact), lambda: pickle.dumps(exact)):
            with self.assertRaises(TypeError):
                operation()
        with self.assertRaises(TypeError):
            exact._values = ()
        self.assertTrue(artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, [])).terminal)
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, []))

    def test_postconsume_failure_makes_retry_terminal(self) -> None:
        exact = _ticket()
        failing = _adapters(exact, [])._replace(finalize=mock.Mock(side_effect=RuntimeError("interrupt")))
        with self.assertRaisesRegex(RuntimeError, "interrupt"):
            artifact._exercise_dormant_activation_artifact(exact, exact, failing)
        with self.assertRaisesRegex(PermissionError, "already terminally consumed"):
            artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, []))

    def test_each_of_forty_inputs_drifts_before_first_mock(self) -> None:
        binding = json.loads((ROOT / artifact._ACTIVATION_ARTIFACT_INPUTS[2][0]).read_bytes())
        dependencies = tuple(
            item["path"]
            for name in ("reviewed_dormant_gate_chain", "activation_connection_chain", "reviewed_bridge_chain", "compatibility_chain", "byte_identical_predecessor_chains")
            for item in binding[name].values()
        )
        paths = tuple(item[0] for item in artifact._ACTIVATION_ARTIFACT_INPUTS) + dependencies
        self.assertEqual(len(paths), 40)
        for target in paths:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                sandbox = Path(tmp)
                for relative in set(paths):
                    destination = sandbox / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / relative, destination)
                with (sandbox / target).open("ab") as handle:
                    handle.write(b"drift")
                exact = _ticket()
                order: list[str] = []
                with mock.patch.object(artifact, "_ROOT", sandbox):
                    with self.assertRaises(PermissionError):
                        artifact._exercise_dormant_activation_artifact(exact, exact, _adapters(exact, order))
                self.assertEqual(order, [])

    def test_all_six_public_edges_are_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition, bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())

    def test_source_has_no_real_write_science_or_admin_path(self) -> None:
        source = Path(artifact.__file__).read_text(encoding="utf-8")
        for forbidden in ("import numpy", "write_bytes", "O_EXCL", "/Users/amcarene", "h27-admin", "locked_test", "open("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
