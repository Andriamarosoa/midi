import inspect
from pathlib import Path
import unittest
from unittest import mock

from src.polyphonic import (
    harmonic_censoring_h26_runtime_one_shot_orchestrator as orchestrator,
)


class RuntimeOrchestratorTests(unittest.TestCase):
    def _call(
        self,
        order,
        *,
        activation_validator=None,
        evidence_validator=None,
        **overrides,
    ):
        def mark(name, result=None):
            def fn(*args, **kwargs):
                order.append(name)
                return result

            return fn

        def boundary(callback):
            order.append("boundary_enter")
            callback()

        values = {
            "activation": {},
            "authority": {},
            "claim": {},
            "receipt": {},
            "authority_raw_sha256": "a" * 64,
            "claim_raw_sha256": "b" * 64,
            "preflight": mark("preflight"),
            "enter_observer_boundary": boundary,
            "observer_entry_evidence_factory": mark(
                "evidence_create", ({}, "c" * 64)
            ),
            "observer": mark("observer", None),
        }
        values.update(overrides)
        patches = (
            mock.patch.object(
                orchestrator,
                "load_runtime_one_shot_orchestration_contract_external_seal",
                side_effect=mark("seal", {}),
            ),
            mock.patch.object(
                orchestrator,
                "validate_artificial_runtime_qualification_operational_activation",
                side_effect=activation_validator or mark("activation"),
            ),
            mock.patch.object(
                orchestrator.primitives,
                "validate_artificial_authority",
                side_effect=mark("authority"),
            ),
            mock.patch.object(
                orchestrator.primitives,
                "validate_artificial_claim",
                side_effect=mark("claim"),
            ),
            mock.patch.object(
                orchestrator.primitives,
                "validate_artificial_observer_entry_evidence",
                side_effect=evidence_validator or mark("evidence_validate"),
            ),
            mock.patch.object(
                orchestrator.primitives,
                "validate_artificial_terminal_execution_receipt",
                side_effect=mark("receipt"),
            ),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            return orchestrator.orchestrate_h26_runtime_with_injected_observer(
                **values
            )

    def test_exact_corrected_order_and_one_fake_observer_call(self):
        order = []
        result = self._call(order)
        self.assertEqual(
            order,
            [
                "seal",
                "activation",
                "preflight",
                "authority",
                "claim",
                "boundary_enter",
                "evidence_create",
                "evidence_validate",
                "observer",
                "receipt",
            ],
        )
        self.assertEqual(
            result.steps,
            (
                "validate_activation",
                "preflight",
                "validate_authority",
                "validate_claim",
                "enter_observer_boundary",
                "create_observer_entry_evidence_inside_boundary",
                "validate_observer_entry_evidence",
                "invoke_observer_exactly_once",
                "capture_optional_runtime_record",
                "validate_terminal_receipt",
            ),
        )
        self.assertEqual(result.observer_invocations, 1)

    def test_api_has_no_prebuilt_evidence_arguments(self):
        parameters = inspect.signature(
            orchestrator.orchestrate_h26_runtime_with_injected_observer
        ).parameters
        self.assertNotIn("evidence", parameters)
        self.assertNotIn("evidence_raw_sha256", parameters)
        self.assertIn("enter_observer_boundary", parameters)
        self.assertIn("observer_entry_evidence_factory", parameters)

    def test_failure_before_boundary_creates_no_evidence_and_calls_no_observer(self):
        order = []
        evidence_factory = mock.Mock()
        observer = mock.Mock()
        with self.assertRaisesRegex(ValueError, "terminal"):
            self._call(
                order,
                activation_validator=mock.Mock(side_effect=ValueError("terminal")),
                observer_entry_evidence_factory=evidence_factory,
                observer=observer,
            )
        evidence_factory.assert_not_called()
        observer.assert_not_called()

    def test_evidence_creation_failure_calls_no_observer(self):
        order = []
        observer = mock.Mock()
        with self.assertRaisesRegex(ValueError, "evidence creation"):
            self._call(
                order,
                observer_entry_evidence_factory=mock.Mock(
                    side_effect=ValueError("evidence creation")
                ),
                observer=observer,
            )
        self.assertIn("boundary_enter", order)
        observer.assert_not_called()

    def test_evidence_validation_failure_calls_no_observer(self):
        order = []
        observer = mock.Mock()
        with self.assertRaisesRegex(ValueError, "evidence validation"):
            self._call(
                order,
                evidence_validator=mock.Mock(
                    side_effect=ValueError("evidence validation")
                ),
                observer=observer,
            )
        observer.assert_not_called()

    def test_observer_error_is_terminal_without_retry_or_receipt(self):
        order = []
        observer = mock.Mock(side_effect=ValueError("observer failed"))
        with self.assertRaisesRegex(ValueError, "observer failed"):
            self._call(order, observer=observer)
        observer.assert_called_once_with()
        self.assertNotIn("receipt", order)

    def test_boundary_must_invoke_callback_exactly_once(self):
        for boundary in (lambda callback: None, lambda callback: (callback(), callback())):
            with self.subTest(boundary=boundary):
                order = []
                observer = mock.Mock(return_value=None)
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    self._call(
                        order,
                        enter_observer_boundary=boundary,
                        observer=observer,
                    )
                self.assertLessEqual(observer.call_count, 1)

    def test_real_runtime_symbols_absent(self):
        source = Path(orchestrator.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "observe_primary_runtime",
            "import numpy",
            "otool",
            "materializer",
            "locked_test",
            "write_bytes",
            "mkdir(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
