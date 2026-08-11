from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h26_runtime_qualification as runtime


class H26DormantRuntimeQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = runtime.load_runtime_qualification_contract()

    def exact_observation(self) -> runtime.RuntimeObservation:
        expected = self.contract.expected_runtime
        environment = dict(self.contract.process_environment_exact)
        environment.update({"PATH": "/synthetic/bin", "HOME": "/synthetic/home"})
        return runtime.RuntimeObservation(
            runtime=expected.identity,
            process_environment=runtime.environment_items(environment),
            executable=runtime.BinaryProof(
                resolved_path="/synthetic/python3.11",
                size_bytes=123456,
                sha256="1" * 64,
            ),
            numpy_multiarray=runtime.BinaryProof(
                resolved_path="/synthetic/_multiarray_umath.so",
                size_bytes=expected.numpy_multiarray_size_bytes,
                sha256=expected.numpy_multiarray_sha256,
            ),
            blas_library=runtime.BinaryProof(
                resolved_path="/synthetic/libopenblas64_.dylib",
                size_bytes=expected.blas_library_size_bytes,
                sha256=expected.blas_library_sha256,
            ),
        )

    def test_contract_is_bound_to_reviewed_commit_and_blob(self) -> None:
        self.assertEqual(
            self.contract.qualification_contract_commit,
            "89cc0659de3afb5194afcf8e7ea9ac6c300e1f92",
        )
        self.assertEqual(
            self.contract.qualification_contract_git_blob_sha,
            "c3a021872dfd3a99b6977fdef1302d5edc755fea",
        )
        source = Path(runtime.__file__).resolve().parents[2] / "configs" / (
            "harmonic_censoring_h26_materialization_runtime_qualification_contract.json"
        )
        raw = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / source.name
            altered.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                runtime.load_runtime_qualification_contract(altered)

    def test_rejected_old_blob_and_commit_blob_cross_bindings_fail_closed(self) -> None:
        old_rejected_blob = "c1e503abfde9b3059ed5efd304705a12e2d8fc36"
        with mock.patch.object(
            runtime,
            "RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA",
            old_rejected_blob,
        ):
            with self.assertRaisesRegex(ValueError, "blob binding mismatch"):
                runtime.load_runtime_qualification_contract()
        with mock.patch.object(
            runtime,
            "RUNTIME_QUALIFICATION_CONTRACT_COMMIT",
            "0" * 40,
        ):
            with self.assertRaisesRegex(ValueError, "commit binding mismatch"):
                runtime.load_runtime_qualification_contract()

    def test_strict_json_rejects_duplicate_nonfinite_and_truncated(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            runtime._strict_json_loads(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, "non-finite JSON constant"):
            runtime._strict_json_loads(b'{"a":NaN}')
        with self.assertRaisesRegex(ValueError, "invalid JSON contract"):
            runtime._strict_json_loads(b'{"a":')

    def test_capability_has_no_constructor_factory_or_forged_fallback(self) -> None:
        with self.assertRaisesRegex(PermissionError, "no issuer"):
            runtime.H26RuntimeQualificationCapability()
        self.assertFalse(hasattr(runtime, "issue_runtime_qualification_capability"))
        forged = object.__new__(runtime.H26RuntimeQualificationCapability)
        with mock.patch.object(runtime.importlib, "import_module") as importer:
            with self.assertRaisesRegex(PermissionError, "unavailable"):
                runtime.observe_primary_runtime(forged)
            importer.assert_not_called()

    def test_module_has_no_eager_numpy_import(self) -> None:
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        self.assertNotIn("\nimport numpy", source)
        self.assertNotIn("\nfrom numpy", source)
        self.assertEqual(source.count('import_module("numpy")'), 1)

    def test_exact_artificial_observation_is_qualified_and_ignores_os_extras(self) -> None:
        observation = self.exact_observation()
        self.assertEqual(
            runtime.derive_runtime_terminal_status(self.contract, observation),
            runtime.STATUS_QUALIFIED,
        )

    def test_valid_runtime_identity_mismatches_are_disqualified(self) -> None:
        base = self.exact_observation()
        cases = (
            replace(base.runtime, version="3.11.8"),
            replace(base.runtime, platform_release="24.4.0"),
        )
        for identity in cases:
            with self.subTest(identity=identity):
                observation = replace(base, runtime=identity)
                self.assertEqual(
                    runtime.derive_runtime_terminal_status(
                        self.contract, observation
                    ),
                    runtime.STATUS_DISQUALIFIED,
                )

    def test_valid_numpy_and_blas_sha_mismatches_are_disqualified(self) -> None:
        base = self.exact_observation()
        cases = (
            replace(base, numpy_multiarray=replace(base.numpy_multiarray, sha256="2" * 64)),
            replace(base, blas_library=replace(base.blas_library, sha256="3" * 64)),
        )
        for observation in cases:
            with self.subTest(observation=observation):
                self.assertEqual(
                    runtime.derive_runtime_terminal_status(
                        self.contract, observation
                    ),
                    runtime.STATUS_DISQUALIFIED,
                )

    def test_missing_or_wrong_control_key_is_disqualified(self) -> None:
        base = self.exact_observation()
        values = dict(base.process_environment)
        missing = dict(values)
        missing.pop("TZ")
        wrong = dict(values)
        wrong["TZ"] = "Indian/Mauritius"
        for environment in (missing, wrong):
            with self.subTest(environment=environment):
                observation = replace(
                    base,
                    process_environment=runtime.environment_items(environment),
                )
                self.assertEqual(
                    runtime.derive_runtime_terminal_status(
                        self.contract, observation
                    ),
                    runtime.STATUS_DISQUALIFIED,
                )

    def test_environment_read_failure_is_inconclusive(self) -> None:
        observation = replace(self.exact_observation(), process_environment=None)
        self.assertEqual(
            runtime.derive_runtime_terminal_status(self.contract, observation),
            runtime.STATUS_INCONCLUSIVE,
        )

    def test_missing_or_inaccessible_binary_proofs_are_inconclusive(self) -> None:
        base = self.exact_observation()
        inaccessible = runtime.BinaryProof(
            resolved_path=None,
            size_bytes=None,
            sha256=None,
            acquisition_error="synthetic unavailable proof",
        )
        cases = (
            replace(base, executable=None),
            replace(base, numpy_multiarray=inaccessible),
            replace(base, blas_library=inaccessible),
        )
        for observation in cases:
            with self.subTest(observation=observation):
                self.assertEqual(
                    runtime.derive_runtime_terminal_status(
                        self.contract, observation
                    ),
                    runtime.STATUS_INCONCLUSIVE,
                )

    def test_malformed_proof_is_inconclusive_not_a_mismatch(self) -> None:
        base = self.exact_observation()
        malformed = replace(base.numpy_multiarray, sha256="NOT-A-SHA")
        observation = replace(base, numpy_multiarray=malformed)
        self.assertEqual(
            runtime.derive_runtime_terminal_status(self.contract, observation),
            runtime.STATUS_INCONCLUSIVE,
        )

    def test_record_builder_derives_status_and_uses_canonical_runtime(self) -> None:
        record = runtime.build_runtime_qualification_record(
            self.contract, self.exact_observation()
        )
        payload = record.as_dict()
        self.assertEqual(payload["terminal_status"], runtime.STATUS_QUALIFIED)
        self.assertEqual(
            tuple(payload["observed_runtime"]),
            (
                "implementation",
                "version",
                "platform_system",
                "platform_release",
                "platform_machine",
                "numpy_version",
                "blas_provider",
            ),
        )
        self.assertNotIn("numpy_multiarray_sha256", payload["observed_runtime"])
        self.assertEqual(
            payload["numpy_multiarray_sha256"],
            self.contract.expected_runtime.numpy_multiarray_sha256,
        )
        self.assertEqual(payload["process_environment_exact"]["TZ"], "UTC")
        self.assertEqual(payload["observed_process_environment"]["TZ"], "UTC")
        self.assertNotIn("PATH", payload["observed_process_environment"])

    def test_caller_cannot_supply_terminal_status_or_construct_record(self) -> None:
        self.assertNotIn(
            "terminal_status",
            inspect.signature(runtime.build_runtime_qualification_record).parameters,
        )
        with self.assertRaises(TypeError):
            runtime.build_runtime_qualification_record(
                self.contract,
                self.exact_observation(),
                terminal_status=runtime.STATUS_QUALIFIED,
            )
        with self.assertRaisesRegex(PermissionError, "sealed builder"):
            runtime.H26RuntimeQualificationRecord()

    def test_observed_runtime_rejects_extra_binary_field(self) -> None:
        values = self.contract.expected_runtime.identity.as_dict()
        values["numpy_multiarray_sha256"] = "0" * 64
        with self.assertRaises(TypeError):
            runtime.RuntimeIdentity(**values)

    def test_serializer_is_deterministic_finite_and_has_no_self_sha(self) -> None:
        record = runtime.build_runtime_qualification_record(
            self.contract, self.exact_observation()
        )
        first = runtime.serialize_runtime_qualification_record(record)
        second = runtime.serialize_runtime_qualification_record(record)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        payload = json.loads(first.decode("utf-8"))
        self.assertFalse(
            {"record_sha256", "runtime_record_sha256", "self_sha256"}
            & set(payload)
        )

        forged = object.__new__(runtime.H26RuntimeQualificationRecord)
        object.__setattr__(
            forged,
            "_payload",
            MappingProxyType({"record_sha256": "0" * 64}),
        )
        with self.assertRaisesRegex(ValueError, "own SHA256"):
            runtime.serialize_runtime_qualification_record(forged)

    def test_atomic_writer_is_unreachable_before_any_file_creation(self) -> None:
        record = runtime.build_runtime_qualification_record(
            self.contract, self.exact_observation()
        )
        forged = object.__new__(runtime.H26RuntimeQualificationCapability)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "runtime-record.json"
            with self.assertRaisesRegex(PermissionError, "unavailable"):
                runtime.write_runtime_qualification_record_atomic(
                    forged, record, destination
                )
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_name(destination.name + ".part").exists())


if __name__ == "__main__":
    unittest.main()
