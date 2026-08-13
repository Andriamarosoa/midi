from __future__ import annotations

import copy
import pickle
from pathlib import Path
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact_builder
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]


def _ticket(**overrides: object) -> publication._H27DormantPublicationTicket:
    values: dict[str, object] = {
        "schema_version": 1,
        "activation_id": "synthetic-publication",
        "population_namespace": "H27_SYNTHETIC_V1",
        "gate_module_blob": "a" * 40,
        "gate_identity_binding_sha256": "b" * 64,
        "authority_sha256": "c" * 64,
        "claim_sha256": "d" * 64,
        "invocation_nonce": "synthetic-nonce",
        "process_id": 1234,
        "code_identity_sha256": "e" * 64,
        "materializer_blob": "f" * 40,
        "terminal_step11_binding_sha256": "1" * 64,
        "created_at_utc": "2026-08-13T12:34:56.123456Z",
        "terminal": True,
    }
    values.update(overrides)
    return publication._make_mock_ticket(**values)


def _adapters(ticket: publication._H27DormantPublicationTicket, order: list[str]) -> publication.H27DormantPublicationAdapters:
    def preconditions() -> dict[str, bool]:
        order.append("preconditions")
        return {name: True for name in publication._PRECONDITIONS}
    def unique(value: str) -> bool:
        order.append("unique")
        return value == "synthetic-publication"
    def absent() -> bool:
        order.append("absent")
        return True
    def create(raw: bytes) -> tuple[bool, bool]:
        order.append("create")
        if not raw.endswith(b"\n"):
            raise AssertionError("payload is not canonical LF JSON")
        return False, False
    def flush() -> tuple[bool, bool]:
        order.append("flush")
        return False, False
    def visible() -> bool:
        order.append("visible")
        return False
    def reopen(raw: bytes) -> bool:
        order.append("reopen")
        if not raw:
            raise AssertionError("empty payload")
        return False
    def parent() -> bool:
        order.append("parent")
        return False
    def finalize(received: object, raw: bytes) -> object:
        order.append("finalize")
        if received is not ticket or not raw:
            raise AssertionError("wrong finalizer input")
        return ticket
    return publication.H27DormantPublicationAdapters(
        preconditions, unique, absent, create, flush, visible, reopen, parent, finalize
    )


class H27ActivationArtifactPublicationDormantTests(unittest.TestCase):
    def test_success_is_in_memory_terminal_and_ordered(self) -> None:
        exact = _ticket()
        order: list[str] = []
        trace = publication._exercise_dormant_publication(exact, exact, _adapters(exact, order))
        self.assertEqual(trace.verified_inputs, 48)
        self.assertEqual(trace.payload_fields, publication._FIELDS)
        self.assertEqual(order, ["preconditions", "unique", "absent", "create", "flush", "visible", "reopen", "parent", "finalize"])
        self.assertFalse(trace.artifact_created)
        self.assertFalse(trace.artifact_written)
        self.assertFalse(trace.composition_to_bridge_connected)
        self.assertFalse(trace.bridge_to_materializer_connected)
        self.assertEqual(trace.materializer_invocations, 0)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_exactly_forty_eight_unique_inputs_are_rehashed_before_adapters(self) -> None:
        calls: list[str] = []
        original = publication._verify_exact
        def observed(*args: object) -> bytes:
            calls.append(str(args[0]))
            return original(*args)
        with mock.patch.object(publication, "_verify_exact", side_effect=observed):
            publication._verify_forty_eight_inputs()
        self.assertEqual(len(set(calls)), 48)
        exact = _ticket()
        adapters = publication.H27DormantPublicationAdapters(*(mock.Mock() for _ in range(9)))
        with mock.patch.object(publication, "_verify_forty_eight_inputs", side_effect=PermissionError("drift")):
            with self.assertRaises(PermissionError):
                publication._exercise_dormant_publication(exact, exact, adapters)
        for callback in adapters:
            callback.assert_not_called()

    def test_payload_and_preconditions_fail_closed_before_consumption(self) -> None:
        for bad in (
            _ticket(schema_version=2), _ticket(activation_id=""), _ticket(process_id=0),
            _ticket(created_at_utc="garbageZ"), _ticket(created_at_utc="2026-99-99T99:99:99Z"),
            _ticket(authority_sha256="bad"), _ticket(terminal=False),
        ):
            with self.assertRaises(PermissionError):
                publication._exercise_dormant_publication(bad, bad, _adapters(bad, []))
        exact = _ticket()
        base = _adapters(exact, [])
        for replacement in (
            {"observe_preconditions": mock.Mock(return_value={})},
            {"observe_activation_id_unique": mock.Mock(return_value=False)},
            {"observe_destination_absent": mock.Mock(return_value=False)},
        ):
            with self.assertRaises(PermissionError):
                publication._exercise_dormant_publication(exact, exact, base._replace(**replacement))

    def test_all_simulated_effects_must_remain_false(self) -> None:
        replacements = (
            {"simulate_create_exclusive": mock.Mock(return_value=(True, False))},
            {"simulate_create_exclusive": mock.Mock(return_value=(False, True))},
            {"simulate_flush_and_file_fsync": mock.Mock(return_value=(True, False))},
            {"simulate_atomic_visibility_without_replace": mock.Mock(return_value=True)},
            {"simulate_reopen_and_rehash": mock.Mock(return_value=True)},
            {"simulate_parent_directory_fsync": mock.Mock(return_value=True)},
        )
        for replacement in replacements:
            exact = _ticket()
            with self.assertRaises(PermissionError):
                publication._exercise_dormant_publication(exact, exact, _adapters(exact, [])._replace(**replacement))
            with self.assertRaises((StopIteration, RuntimeError)):
                publication._exercise_dormant_publication(exact, exact, _adapters(exact, []))

    def test_success_second_call_and_postconsume_failure_retry_are_rejected(self) -> None:
        exact = _ticket()
        publication._exercise_dormant_publication(exact, exact, _adapters(exact, []))
        with self.assertRaises((StopIteration, RuntimeError)):
            publication._exercise_dormant_publication(exact, exact, _adapters(exact, []))
        failing = _ticket()
        broken = _adapters(failing, [])._replace(simulate_create_exclusive=mock.Mock(side_effect=RuntimeError("synthetic")))
        with self.assertRaises(RuntimeError):
            publication._exercise_dormant_publication(failing, failing, broken)
        with self.assertRaises((StopIteration, RuntimeError)):
            publication._exercise_dormant_publication(failing, failing, _adapters(failing, []))

    def test_ticket_is_private_immutable_noncopyable_and_nonserializable(self) -> None:
        with self.assertRaises(PermissionError):
            publication._H27DormantPublicationTicket()
        exact = _ticket()
        with self.assertRaises(TypeError):
            exact.anything = True
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError):
                operation(exact)

    def test_all_seven_public_edges_are_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact_builder.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")

    def test_source_has_no_real_publication_or_science_api(self) -> None:
        source = Path(publication.__file__).read_text(encoding="utf-8")
        for forbidden in ("os.open", "O_EXCL", "write_bytes", "numpy", "locked_test"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
