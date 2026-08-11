from pathlib import Path
import hashlib
import os
from types import SimpleNamespace
import tempfile
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as primitives
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as qualifier
from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation as activation
from src.polyphonic import run_h26_runtime_qualification_operational as runner


class H26RuntimeOperationalEntrypointTests(unittest.TestCase):
    def _activation(self, root: Path):
        fields, _, fixed = activation._activation_rules()
        value = dict(fixed)
        value.update(
            activation_id="placeholder",
            activation_contract_commit=activation.ACTIVATION_CONTRACT_COMMIT,
            activation_contract_raw_sha256=activation.ACTIVATION_CONTRACT_RAW_SHA256,
            administrative_root=str(root),
            issued_at="2026-08-12T12:00:00Z",
            issuer_identity=runner.ISSUER_IDENTITY,
        )
        self.assertEqual(set(value), set(fields))
        value["activation_id"] = activation.derive_runtime_qualification_operational_activation_id(value)
        return value, primitives.canonical_json_bytes(value)

    def _qualified_observation(self):
        contract = qualifier.load_runtime_qualification_contract()
        expected = contract.expected_runtime
        return qualifier.RuntimeObservation(
            runtime=expected.identity,
            process_environment=contract.process_environment_exact,
            executable=qualifier.BinaryProof("/tmp/python", 1, "1" * 64),
            numpy_multiarray=qualifier.BinaryProof(
                "/tmp/multiarray", expected.numpy_multiarray_size_bytes,
                expected.numpy_multiarray_sha256,
            ),
            blas_library=qualifier.BinaryProof(
                "/tmp/blas", expected.blas_library_size_bytes,
                expected.blas_library_sha256,
            ),
        )

    def _contexts(self, root: Path, activation_id: str, activation_sha: str):
        head = "a" * 40

        def git_output(*arguments):
            return head if arguments == ("rev-parse", "HEAD") else ""

        environment = dict(qualifier._EXPECTED_ENVIRONMENT_ITEMS)
        environment.update(
            {
                runner.ACKNOWLEDGEMENT_VARIABLE: "1",
                runner.AUTHORIZATION_COMMIT_VARIABLE: head,
            }
        )
        return (
            mock.patch.object(runner, "ADMINISTRATIVE_ROOT", str(root)),
            mock.patch.object(runner, "ACTIVATION_ID", activation_id),
            mock.patch.object(runner, "ACTIVATION_RAW_SHA256", activation_sha),
            mock.patch.object(runner, "_load_execution_contract", return_value={}),
            mock.patch.object(runner, "_git_output", side_effect=git_output),
            mock.patch.object(runner, "_is_darwin", return_value=True),
            mock.patch.dict(os.environ, environment, clear=False),
        )

    def _prepare(self, directory: str):
        root = Path(directory).resolve()
        for name in (
            "activation", "authority", "claim", "observer-entry",
            "runtime-record", "receipt",
        ):
            (root / name).mkdir()
        value, raw = self._activation(root)
        (root / "activation" / "activation.json").write_bytes(raw)
        return root, value, raw

    def test_contract_is_exact_and_unconsumed(self):
        value = runner._load_execution_contract()
        self.assertEqual(value["approved_activation_id"], runner.ACTIVATION_ID)
        self.assertFalse(value["runtime_consumed"])
        self.assertFalse(value["locked_test_used"])

    def test_boundary_rejects_before_activation_or_filesystem_access(self):
        with mock.patch.object(runner, "_is_darwin", return_value=False), mock.patch.object(
            runner, "_load_activation"
        ) as load_activation:
            with self.assertRaises(RuntimeError):
                runner.execute_h26_runtime_qualification_once()
        load_activation.assert_not_called()

    def test_forged_capability_cannot_reach_observer_or_filesystem(self):
        forged = object.__new__(runner._H26RuntimeBoundaryCapability)
        forged.head = "a" * 40
        with self.assertRaises(PermissionError):
            runner._observe_primary_runtime(forged)
        with self.assertRaises(PermissionError):
            runner._publish(forged, Path("x"), Path("y"), b"{}\n")
        forged_observer = object.__new__(runner._H26ObserverEntryCapability)
        forged_observer.execution = forged
        forged_observer.claim_id = "claim"
        with self.assertRaises(PermissionError):
            runner._evidence(forged_observer, {}, "a" * 64, {}, "b" * 64)

    def test_complete_temporary_flow_publishes_in_exact_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            order = []
            original_publish = runner._publish
            original_enter = runner._enter_observer_boundary
            original_evidence = runner._evidence

            def publish(*arguments):
                order.append(arguments[1].parent.name)
                return original_publish(*arguments)

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            def enter(*arguments):
                order.append("observer-boundary")
                return original_enter(*arguments)

            def create_evidence(*arguments):
                order.append("evidence-create")
                return original_evidence(*arguments)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime", return_value=self._qualified_observation()
            ) as observer, mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(
                runner, "_enter_observer_boundary", side_effect=enter
            ), mock.patch.object(
                runner, "_evidence", side_effect=create_evidence
            ), mock.patch.object(runner, "_publish", side_effect=publish):
                result = runner.execute_h26_runtime_qualification_once()

            self.assertEqual(
                order,
                [
                    "authority", "claim", "observer-boundary", "evidence-create",
                    "observer-entry", "runtime-record", "receipt",
                ],
            )
            observer.assert_called_once()
            self.assertEqual(result["observer_invocation_count"], 1)
            self.assertEqual(result["terminal_status"], qualifier.STATUS_QUALIFIED)
            for name in ("authority", "claim", "observer-entry", "runtime-record", "receipt"):
                files = tuple((root / name).iterdir())
                self.assertEqual(len(files), 1)
                self.assertFalse(files[0].name.startswith("."))

    def test_observer_failure_writes_inconclusive_receipt_last_without_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            order = []
            original_publish = runner._publish

            def publish(*arguments):
                order.append(arguments[1].parent.name)
                return original_publish(*arguments)

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime", side_effect=RuntimeError("observer failed")
            ), mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(runner, "_publish", side_effect=publish):
                with self.assertRaisesRegex(RuntimeError, "observer failed"):
                    runner.execute_h26_runtime_qualification_once()

            self.assertEqual(order, ["authority", "claim", "observer-entry", "receipt"])
            self.assertFalse(any((root / "runtime-record").iterdir()))
            receipt_path = next((root / "receipt").iterdir())
            receipt_raw = receipt_path.read_bytes()
            self.assertNotIn(b"\r", receipt_raw, repr(receipt_raw))
            receipt = primitives.parse_canonical_json_bytes(receipt_raw)
            self.assertEqual(receipt["terminal_status"], qualifier.STATUS_INCONCLUSIVE)
            self.assertFalse(receipt["runtime_record_exists"])

    def test_evidence_publication_failure_after_boundary_writes_terminal_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            order = []
            original_enter = runner._enter_observer_boundary
            original_publish = runner._publish

            def enter(*arguments):
                order.append("observer-boundary")
                return original_enter(*arguments)

            def publish(*arguments):
                artifact_kind = arguments[1].parent.name
                if artifact_kind == "observer-entry":
                    order.append("evidence-attempt")
                    raise OSError("evidence publication failed")
                order.append(artifact_kind)
                return original_publish(*arguments)

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime"
            ) as observer, mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(
                runner, "_enter_observer_boundary", side_effect=enter
            ), mock.patch.object(runner, "_publish", side_effect=publish):
                with self.assertRaisesRegex(OSError, "evidence publication failed"):
                    runner.execute_h26_runtime_qualification_once()

            self.assertEqual(
                order,
                ["authority", "claim", "observer-boundary", "evidence-attempt", "receipt"],
            )
            observer.assert_not_called()
            self.assertFalse(any((root / "observer-entry").iterdir()))
            self.assertFalse(any((root / "runtime-record").iterdir()))
            receipt_path = next((root / "receipt").iterdir())
            receipt = primitives.parse_canonical_json_bytes(receipt_path.read_bytes())
            self.assertEqual(receipt["terminal_status"], qualifier.STATUS_INCONCLUSIVE)
            self.assertFalse(receipt["runtime_record_exists"])

    def test_evidence_validation_failure_after_boundary_writes_terminal_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            original_validate = primitives.validate_artificial_observer_entry_evidence
            validation_calls = 0

            def validate(*arguments):
                nonlocal validation_calls
                validation_calls += 1
                if validation_calls == 2:
                    raise ValueError("evidence validation failed")
                return original_validate(*arguments)

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime"
            ) as observer, mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(
                primitives,
                "validate_artificial_observer_entry_evidence",
                side_effect=validate,
            ):
                with self.assertRaisesRegex(ValueError, "evidence validation failed"):
                    runner.execute_h26_runtime_qualification_once()

            observer.assert_not_called()
            self.assertEqual(validation_calls, 3)
            self.assertFalse(any((root / "observer-entry").iterdir()))
            self.assertFalse(any((root / "runtime-record").iterdir()))
            receipt_path = next((root / "receipt").iterdir())
            receipt = primitives.parse_canonical_json_bytes(receipt_path.read_bytes())
            self.assertEqual(receipt["terminal_status"], qualifier.STATUS_INCONCLUSIVE)
            self.assertFalse(receipt["runtime_record_exists"])

    def test_evidence_reconstruction_failure_after_boundary_uses_atomic_terminal_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime"
            ) as observer, mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(
                runner, "_evidence", side_effect=RuntimeError("evidence reconstruction failed")
            ):
                with self.assertRaisesRegex(RuntimeError, "evidence reconstruction failed"):
                    runner.execute_h26_runtime_qualification_once()

            observer.assert_not_called()
            self.assertFalse(any((root / "observer-entry").iterdir()))
            self.assertFalse(any((root / "runtime-record").iterdir()))
            receipt_path = next((root / "receipt").iterdir())
            receipt = primitives.parse_canonical_json_bytes(receipt_path.read_bytes())
            self.assertEqual(receipt["terminal_status"], qualifier.STATUS_INCONCLUSIVE)
            self.assertFalse(receipt["runtime_record_exists"])

    def test_evidence_serialization_failure_after_boundary_uses_atomic_terminal_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            original_canonical = primitives.canonical_json_bytes
            evidence_serializations = 0

            def canonical(value):
                nonlocal evidence_serializations
                if value.get("schema_identity") == "H26_RUNTIME_QUALIFICATION_OBSERVER_ENTRY_EVIDENCE_V1":
                    evidence_serializations += 1
                    if evidence_serializations == 2:
                        raise ValueError("evidence serialization failed")
                return original_canonical(value)

            def rename(source, destination):
                if destination.exists():
                    raise FileExistsError(str(destination))
                os.rename(source, destination)

            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner,
                "validate_artificial_runtime_qualification_operational_activation",
                return_value=SimpleNamespace(
                    activation_id=value["activation_id"], canonical_bytes=raw
                ),
            ), mock.patch.object(
                runner, "_observe_primary_runtime"
            ) as observer, mock.patch.object(
                runner, "_rename_no_replace", side_effect=rename
            ), mock.patch.object(
                runner.os, "fchmod", create=True
            ), mock.patch.object(
                runner, "_sync_directory"
            ), mock.patch.object(
                primitives, "canonical_json_bytes", side_effect=canonical
            ):
                with self.assertRaisesRegex(ValueError, "evidence serialization failed"):
                    runner.execute_h26_runtime_qualification_once()

            observer.assert_not_called()
            self.assertEqual(evidence_serializations, 3)
            self.assertFalse(any((root / "observer-entry").iterdir()))
            self.assertFalse(any((root / "runtime-record").iterdir()))
            receipt_path = next((root / "receipt").iterdir())
            receipt = primitives.parse_canonical_json_bytes(receipt_path.read_bytes())
            self.assertEqual(receipt["terminal_status"], qualifier.STATUS_INCONCLUSIVE)
            self.assertFalse(receipt["runtime_record_exists"])

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "uname") and os.uname().sysname == "Darwin",
        "Darwin-only real operational filesystem primitives",
    )
    def test_real_darwin_filesystem_flow_uses_fake_observation_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value, raw = self._prepare(directory)
            contexts = self._contexts(
                root, value["activation_id"], hashlib.sha256(raw).hexdigest()
            )
            with contexts[0], contexts[1], contexts[2], contexts[3], contexts[4], contexts[5], contexts[6], mock.patch.object(
                runner, "_observe_primary_runtime", return_value=self._qualified_observation()
            ) as observer:
                result = runner.execute_h26_runtime_qualification_once()
            observer.assert_called_once()
            self.assertEqual(result["terminal_status"], qualifier.STATUS_QUALIFIED)
            for name in ("authority", "claim", "observer-entry", "runtime-record", "receipt"):
                artifact = next((root / name).iterdir())
                self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
