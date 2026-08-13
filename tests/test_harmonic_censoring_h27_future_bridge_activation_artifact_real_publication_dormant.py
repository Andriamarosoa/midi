from __future__ import annotations

from pathlib import Path
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant as real_publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


def _ticket(**overrides: object) -> publication._H27DormantPublicationTicket:
    values: dict[str, object] = {
        "schema_version": 1,
        "activation_id": "synthetic-real-publication",
        "population_namespace": "H27_SYNTHETIC_V1",
        "gate_module_blob": publication._GATE_BLOB,
        "gate_identity_binding_sha256": publication._GATE_BINDING_SHA,
        "authority_sha256": "c" * 64,
        "claim_sha256": "d" * 64,
        "invocation_nonce": "3" * 64,
        "process_id": 1234,
        "code_identity_sha256": "e" * 64,
        "materializer_blob": publication._MATERIALIZER_BLOB,
        "terminal_step11_binding_sha256": "1" * 64,
        "created_at_utc": "2026-08-13T13:00:00Z",
        "terminal": True,
    }
    values.update(overrides)
    return publication._make_mock_ticket(**values)


def _adapters(ticket: object, order: list[str]) -> real_publication.H27DormantRealPublicationAdapters:
    def requirements() -> dict[str, bool]:
        order.append("requirements")
        return {name: True for name in real_publication._REQUIREMENTS}
    def absent() -> bool:
        order.append("absent")
        return True
    def create(raw: bytes) -> tuple[bool, bool]:
        order.append("create")
        if not raw.endswith(b"\n"):
            raise AssertionError("payload is not canonical")
        return False, False
    def write_flush_fsync() -> tuple[bool, bool, bool]:
        order.append("write_flush_fsync")
        return False, False, False
    def visible() -> bool:
        order.append("visible")
        return False
    def reopen(raw: bytes) -> bool:
        order.append("reopen")
        if not raw:
            raise AssertionError("payload missing")
        return False
    def parent() -> bool:
        order.append("parent")
        return False
    def finalize(received: object, raw: bytes) -> object:
        order.append("finalize")
        if received is not ticket or not raw:
            raise AssertionError("wrong finalizer input")
        return ticket
    return real_publication.H27DormantRealPublicationAdapters(
        requirements, absent, create, write_flush_fsync, visible, reopen, parent, finalize
    )


class H27DormantRealPublicationTests(unittest.TestCase):
    def test_effect_free_success_is_ordered_terminal_and_has_no_destination(self) -> None:
        exact = _ticket()
        order: list[str] = []
        trace = real_publication._exercise_dormant_real_publication(exact, exact, _adapters(exact, order))
        self.assertEqual(trace.verified_identities, 54)
        self.assertIsNone(trace.destination_path)
        self.assertEqual(order, [
            "requirements", "absent", "create", "write_flush_fsync",
            "visible", "reopen", "parent", "finalize",
        ])
        self.assertFalse(trace.artifact_created)
        self.assertFalse(trace.artifact_written)
        self.assertFalse(trace.composition_to_bridge_connected)
        self.assertFalse(trace.bridge_to_materializer_connected)
        self.assertEqual(trace.materializer_invocations, 0)
        self.assertEqual(trace.science_invocations, 0)
        self.assertTrue(trace.terminal)

    def test_exactly_fifty_four_identities_are_rehashed_before_any_adapter(self) -> None:
        calls: list[str] = []
        original = real_publication._verify_exact
        def observed(*args: object) -> bytes:
            calls.append(str(args[0]))
            return original(*args)
        with mock.patch.object(real_publication, "_verify_exact", side_effect=observed):
            real_publication._verify_fifty_four_inputs()
        self.assertEqual(len(set(calls)), 56)
        exact = _ticket()
        adapters = real_publication.H27DormantRealPublicationAdapters(*(mock.Mock() for _ in range(8)))
        with mock.patch.object(real_publication, "_verify_fifty_four_inputs", side_effect=PermissionError("drift")):
            with self.assertRaises(PermissionError):
                real_publication._exercise_dormant_real_publication(exact, exact, adapters)
        for callback in adapters:
            callback.assert_not_called()

    def test_payload_requirements_identity_and_destination_fail_before_consumption(self) -> None:
        bad = _ticket(gate_module_blob="a" * 40)
        order: list[str] = []
        with self.assertRaises(PermissionError):
            real_publication._exercise_dormant_real_publication(bad, bad, _adapters(bad, order))
        self.assertEqual(order, [])
        self.assertIsNotNone(bad._consume(bad))
        for replacement in (
            {"observe_requirements": mock.Mock(return_value={})},
            {"observe_destination_absent": mock.Mock(return_value=False)},
        ):
            exact = _ticket()
            with self.assertRaises(PermissionError):
                real_publication._exercise_dormant_real_publication(
                    exact, exact, _adapters(exact, [])._replace(**replacement)
                )
            self.assertIsNotNone(exact._consume(exact))
        exact = _ticket()
        with self.assertRaises(PermissionError):
            real_publication._exercise_dormant_real_publication(exact, _ticket(), _adapters(exact, []))
        self.assertIsNotNone(exact._consume(exact))

    def test_every_effect_probe_must_report_no_effect_and_consumes_one_shot(self) -> None:
        replacements = (
            {"probe_create_exclusive": mock.Mock(return_value=(True, False))},
            {"probe_create_exclusive": mock.Mock(return_value=(False, True))},
            {"probe_full_write_flush_and_file_fsync": mock.Mock(return_value=(True, False, False))},
            {"probe_atomic_visibility_without_replace": mock.Mock(return_value=True)},
            {"probe_reopen_and_rehash": mock.Mock(return_value=True)},
            {"probe_parent_directory_fsync": mock.Mock(return_value=True)},
        )
        for replacement in replacements:
            exact = _ticket()
            with self.assertRaises(PermissionError):
                real_publication._exercise_dormant_real_publication(
                    exact, exact, _adapters(exact, [])._replace(**replacement)
                )
            with self.assertRaises((StopIteration, RuntimeError)):
                real_publication._exercise_dormant_real_publication(exact, exact, _adapters(exact, []))

    def test_success_and_postconsume_failure_are_terminal_without_retry(self) -> None:
        exact = _ticket()
        real_publication._exercise_dormant_real_publication(exact, exact, _adapters(exact, []))
        with self.assertRaises((StopIteration, RuntimeError)):
            real_publication._exercise_dormant_real_publication(exact, exact, _adapters(exact, []))
        failing = _ticket()
        broken = _adapters(failing, [])._replace(probe_create_exclusive=mock.Mock(side_effect=RuntimeError("synthetic")))
        with self.assertRaises(RuntimeError):
            real_publication._exercise_dormant_real_publication(failing, failing, broken)
        with self.assertRaises((StopIteration, RuntimeError)):
            real_publication._exercise_dormant_real_publication(failing, failing, _adapters(failing, []))

    def test_all_eight_public_edges_are_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            real_publication.publish_h27_future_bridge_activation_artifact_real,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")

    def test_source_contains_no_direct_real_filesystem_or_science_api(self) -> None:
        source = Path(real_publication.__file__).read_text(encoding="utf-8")
        for forbidden in ("os.open", "O_EXCL", "write_bytes", "import numpy"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
