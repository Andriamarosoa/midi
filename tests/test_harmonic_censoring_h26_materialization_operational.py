from dataclasses import replace
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from src.polyphonic import run_h26_materialization_operational as runner
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as qualifier


class H26MaterializationOperationalTests(unittest.TestCase):
    def _qualified_record_and_mismatched_live_runtime(self):
        contract = qualifier.load_runtime_qualification_contract()
        expected = qualifier.RuntimeObservation(
            runtime=contract.expected_runtime.identity,
            process_environment=qualifier.environment_items(
                dict(contract.process_environment_exact)
            ),
            executable=qualifier.BinaryProof(
                resolved_path="/qualified/python",
                size_bytes=1,
                sha256="1" * 64,
            ),
            numpy_multiarray=qualifier.BinaryProof(
                resolved_path="/qualified/multiarray",
                size_bytes=contract.expected_runtime.numpy_multiarray_size_bytes,
                sha256=contract.expected_runtime.numpy_multiarray_sha256,
            ),
            blas_library=qualifier.BinaryProof(
                resolved_path="/qualified/openblas",
                size_bytes=contract.expected_runtime.blas_library_size_bytes,
                sha256=contract.expected_runtime.blas_library_sha256,
            ),
        )
        record = qualifier.build_runtime_qualification_record(contract, expected)
        mismatched = replace(
            expected,
            runtime=replace(expected.runtime, version="0.0.0"),
        )
        return record, expected, mismatched

    def test_entrypoint_contract_is_exact_canonical_json(self):
        value = runner._load_entrypoint_contract()
        raw = (runner._repo_root() / runner.ENTRYPOINT_CONTRACT).read_bytes()
        self.assertEqual(raw, runner.runtime.canonical_json_bytes(value))

    def test_pending_review_contract_fails_before_artifact_read(self):
        with mock.patch.object(runner.platform, "system", return_value="Darwin"), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner, "_read_runtime_artifacts") as read:
            with self.assertRaises(PermissionError):
                runner.execute_h26_materialization_once()
        read.assert_not_called()

    def test_missing_ack_fails_before_artifact_read_after_future_authorization(self):
        authorized = {"real_execution_authorized": True}
        with mock.patch.object(runner, "_load_entrypoint_contract", return_value=authorized), mock.patch.object(runner.platform, "system", return_value="Darwin"), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner, "_read_runtime_artifacts") as read:
            with self.assertRaisesRegex(PermissionError, "acknowledgement"):
                runner.execute_h26_materialization_once()
        read.assert_not_called()

    def test_complete_boundary_uses_fixed_authority_and_internal_materializer_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority_dir, seal_dir, population_parent = root / "authority", root / "seal", root / "population"
            for path in (authority_dir, seal_dir, population_parent): path.mkdir()
            destination = population_parent / "h26-synthetic-v1"
            raw = b'{"authority_id":"h26-materialization-authority-v1-' + b'a' * 64 + b'"}\n'
            sha = hashlib.sha256(raw).hexdigest()
            def rename(source, target): os.rename(source, target)
            with mock.patch.object(runner, "AUTHORITY_DIRECTORY", authority_dir), mock.patch.object(runner, "SEAL_DIRECTORY", seal_dir), mock.patch.object(runner, "DESTINATION", destination), mock.patch.object(runner, "_require_execution_boundary", return_value="b" * 40), mock.patch.object(runner, "_read_runtime_artifacts", return_value=(object(),) * 5), mock.patch.object(runner, "_require_live_runtime_matches_stop3"), mock.patch.object(runner, "_build_authority", return_value=({"authority_id": "h26-materialization-authority-v1-" + "a" * 64}, raw, sha)), mock.patch.object(runner, "_rename_no_replace", side_effect=rename), mock.patch.object(runner, "_sync_directory"), mock.patch.object(runner, "_invoke_real_materializer") as invoke:
                result = runner.execute_h26_materialization_once()
            invoke.assert_called_once()
            boundary = invoke.call_args.args[0]
            runner._require_materialization_boundary(boundary)
            self.assertEqual(result["materializer_invocations"], 1)
            self.assertEqual((authority_dir / f"{sha}.json").read_bytes(), raw)
            self.assertEqual(len(tuple(seal_dir.iterdir())), 1)
            self.assertFalse(destination.exists())

    def test_existing_slot_fails_before_any_publication_or_materializer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority_dir, seal_dir, population_parent = root / "authority", root / "seal", root / "population"
            for path in (authority_dir, seal_dir, population_parent):
                path.mkdir()
            destination = population_parent / "h26-synthetic-v1"
            destination.mkdir()
            raw = b'{}\n'
            sha = hashlib.sha256(raw).hexdigest()
            with mock.patch.object(runner, "AUTHORITY_DIRECTORY", authority_dir), mock.patch.object(runner, "SEAL_DIRECTORY", seal_dir), mock.patch.object(runner, "DESTINATION", destination), mock.patch.object(runner, "_require_execution_boundary", return_value="b" * 40), mock.patch.object(runner, "_read_runtime_artifacts", return_value=(object(),) * 5), mock.patch.object(runner, "_require_live_runtime_matches_stop3"), mock.patch.object(runner, "_build_authority", return_value=({"authority_id": "h26-materialization-authority-v1-" + "a" * 64}, raw, sha)), mock.patch.object(runner, "_publish") as publish, mock.patch.object(runner, "_invoke_real_materializer") as invoke:
                with self.assertRaisesRegex(FileExistsError, "slot already exists"):
                    runner.execute_h26_materialization_once()
            publish.assert_not_called()
            invoke.assert_not_called()

    def test_live_runtime_mismatch_blocks_publication_and_materializer(self):
        record, _, mismatched = self._qualified_record_and_mismatched_live_runtime()
        runtime_values = (object(), object(), object(), record, object())
        with mock.patch.object(runner, "_require_execution_boundary", return_value="b" * 40), mock.patch.object(runner, "_read_runtime_artifacts", return_value=runtime_values), mock.patch.object(runner, "_observe_live_materialization_runtime", return_value=mismatched), mock.patch.object(runner, "_publish") as publish, mock.patch.object(runner, "_invoke_real_materializer") as invoke:
            with self.assertRaisesRegex(PermissionError, "differs from STOP3"):
                runner.execute_h26_materialization_once()
        publish.assert_not_called()
        invoke.assert_not_called()

    def test_exact_live_runtime_match_is_accepted(self):
        record, expected, _ = self._qualified_record_and_mismatched_live_runtime()
        with mock.patch.object(
            runner, "_observe_live_materialization_runtime", return_value=expected,
        ):
            self.assertIs(runner._require_live_runtime_matches_stop3(record), expected)

    def test_forged_boundary_is_rejected(self):
        forged = object.__new__(runner._H26MaterializationBoundary)
        forged.head, forged.authority_sha256 = "a" * 40, "b" * 64
        forged.authority_path, forged.seal_path = Path("authority"), Path("seal")
        with self.assertRaises(PermissionError): runner._require_materialization_boundary(forged)

    def test_internal_materializer_adapter_is_restored_after_failure(self):
        from src.polyphonic import harmonic_censoring_h26_contract as contract
        from src.polyphonic import harmonic_censoring_h26_materializer as materializer

        with tempfile.TemporaryDirectory() as directory:
            authority_path = Path(directory) / "authority.json"
            authority_raw = b"{}\n"
            authority_sha = hashlib.sha256(authority_raw).hexdigest()
            authority_path.write_bytes(authority_raw)
            seal_path = Path(directory) / "seal.json"
            seal_path.write_bytes(runner._seal(authority_sha))
            boundary = runner._mint_boundary(
                "a" * 40, authority_sha, authority_path, seal_path,
            )
            plan = object()
            original_require = materializer._require_capability
            original_os = materializer.os

            def fail_after_private_capability(np_module, capability, destination):
                del np_module, destination
                self.assertIs(materializer._require_capability(capability), plan)
                with self.assertRaises(PermissionError):
                    materializer._require_capability(object())
                raise RuntimeError("synthetic materializer failure")

            with mock.patch.object(contract, "load_h26_dormant_plan", return_value=plan), mock.patch.object(materializer, "materialize_h26_population", side_effect=fail_after_private_capability):
                with self.assertRaisesRegex(RuntimeError, "synthetic materializer failure"):
                    runner._invoke_real_materializer(boundary)
            self.assertIs(materializer._require_capability, original_require)
            self.assertIs(materializer.os, original_os)

    def test_boundary_refuses_authority_tampering_after_mint(self):
        with tempfile.TemporaryDirectory() as directory:
            authority_path = Path(directory) / "authority.json"
            authority_raw = b"{}\n"
            authority_sha = hashlib.sha256(authority_raw).hexdigest()
            authority_path.write_bytes(authority_raw)
            seal_path = Path(directory) / "seal.json"
            seal_path.write_bytes(runner._seal(authority_sha))
            boundary = runner._mint_boundary(
                "a" * 40, authority_sha, authority_path, seal_path,
            )
            authority_path.write_bytes(b'{"changed":true}\n')
            with self.assertRaisesRegex(PermissionError, "authority changed"):
                runner._require_materialization_boundary(boundary)

    def test_runtime_sha_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for kind, filename in runner.RUNTIME_FILENAMES.items():
                path = root / kind / filename; path.parent.mkdir(); path.write_bytes(b"{}\n")
            with mock.patch.object(runner, "ADMIN_ROOT", root):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    runner._read_runtime_artifacts()


if __name__ == "__main__": unittest.main()
