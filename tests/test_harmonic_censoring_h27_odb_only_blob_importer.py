from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_import_exact_blobs_odb_only_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_importer_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_importer_identity_binding_external_seal.json"
CONTRACT = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_import_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_odb_only_blob_import_contract_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def identity(path: str) -> dict[str, object]:
    raw = (ROOT / path).read_bytes()
    return {
        "path": path,
        "git_blob_sha1": blob(raw),
        "size_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


class TestH27OdbOnlyBlobImporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h27_odb_importer", RUNNER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.contract = json.loads(CONTRACT.read_bytes())

    def test_runner_binding_and_seal_are_exact(self) -> None:
        for raw in (RUNNER.read_bytes(), self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.binding["runner"], identity("scripts/h27_import_exact_blobs_odb_only_one_shot.py"))
        current_contract = {
            "path": "configs/harmonic_censoring_h27_odb_only_blob_import_contract.json",
            "git_blob_sha1": "7f5905f0d2b24eb96a6e1f1555dbe3993e85adbd",
            "size_bytes": 8149,
            "raw_sha256": "8e4a00fdba0d7e56c0d77e66f141a914de5c29d08cff914ba2ff53ff7d39d420",
        }
        current_contract_seal = {
            "path": "configs/harmonic_censoring_h27_odb_only_blob_import_contract_external_seal.json",
            "git_blob_sha1": "8cfdaba605115f43fffb66fc28161bd85e8cada9",
            "size_bytes": 6054,
            "raw_sha256": "745d80d1d163e67b68efb2dae1d4b337e068e4909d40718000848916eaff9573",
        }
        self.assertEqual(self.binding["approved_contract"], current_contract)
        self.assertEqual(self.binding["approved_contract_external_seal"], current_contract_seal)
        self.assertEqual(self.binding["approved_contract_commit"], "5abab29c2687d41e54cc2e63f99f97afb87f0166")
        self.assertEqual(self.binding["approved_contract"], identity("configs/harmonic_censoring_h27_odb_only_blob_import_contract.json"))
        self.assertEqual(self.binding["approved_contract_external_seal"], identity("configs/harmonic_censoring_h27_odb_only_blob_import_contract_external_seal.json"))
        self.assertEqual(self.binding["normative_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(self.seal["identity_binding"], identity("configs/harmonic_censoring_h27_odb_only_blob_importer_identity_binding.json"))
        self.assertEqual(self.seal["runner"], self.binding["runner"])
        self.assertEqual(self.seal["approved_contract"], self.binding["approved_contract"])
        self.assertEqual(self.seal["approved_contract_external_seal"], self.binding["approved_contract_external_seal"])
        self.assertEqual(self.seal["approved_contract_commit"], self.binding["approved_contract_commit"])
        expected_files_proof = {
            "proof_id": "H27_FILES_BACKEND_COMPATIBLE_WITH_APPLE_GIT_2_39_V1",
            "repository_format_stdout_exact": "0\n",
            "ref_storage_extension_returncode_exact": 1,
            "ref_storage_extension_stdout_exact": "",
            "ref_storage_extension_stderr_exact": "",
            "refs_directory_real_non_symlink_required": True,
            "reftable_directory_absent_required": True,
            "verified_before_snapshot_before_first_write_and_after_all_writes": True,
        }
        self.assertEqual(self.binding["reference_storage_files_proof"], expected_files_proof)
        self.assertEqual(self.seal["future_reference_storage_files_proof"], expected_files_proof)
        self.assertEqual(self.seal["future_normative_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(set(self.seal), {
            "schema_version", "seal_id", "status", "identity_binding", "runner",
            "approved_contract_commit", "approved_contract", "approved_contract_external_seal",
            "future_platform_exact", "future_acknowledgement_environment_exact",
            "future_source_git_database_environment_required", "future_arguments_forbidden",
            "future_source_must_be_real_non_symlink_git_directory_outside_target_checkout",
            "future_source_checkout_or_file_fallback_forbidden",
            "future_git_no_lazy_fetch_exact", "future_network_fetch_pull_sync_forbidden",
            "future_all_payloads_buffered_and_prevalidated_before_any_write",
            "future_target_write_operation_exact", "future_exact_write_count",
            "future_reference_storage_files_proof",
            "future_object_database_path_delta_exactly_eight_expected_loose_objects",
            "future_preexisting_object_paths_and_metadata_unchanged", "future_normative_order",
            "future_single_attempt_only", "future_partial_import_terminal_consumed_failure",
            "future_retry_cleanup_repair_rollback_or_automatic_recovery_forbidden",
            "runner_externally_reviewed", "runner_externally_sealed", "runner_executed",
            "import_executed", "target_odb_changed", "head_changed", "index_changed",
            "worktree_changed", "detach_executed", "registry_opened", "authority_reserved",
            "creator_invoked", "control_bundle_created", "materializer_executed",
            "science_or_locked_test", "next_action",
        })
        self.assertTrue(self.seal["future_single_attempt_only"])
        self.assertEqual(self.seal["future_git_no_lazy_fetch_exact"], "GIT_NO_LAZY_FETCH=1")
        self.assertTrue(self.seal["future_network_fetch_pull_sync_forbidden"])
        self.assertTrue(self.seal["future_partial_import_terminal_consumed_failure"])
        self.assertTrue(self.seal["future_retry_cleanup_repair_rollback_or_automatic_recovery_forbidden"])
        for key in (
            "runner_externally_reviewed", "runner_externally_sealed", "runner_executed",
            "import_executed", "target_odb_changed", "head_changed", "index_changed",
            "worktree_changed", "detach_executed", "registry_opened", "authority_reserved",
            "creator_invoked", "control_bundle_created", "materializer_executed",
            "science_or_locked_test",
        ):
            self.assertFalse(self.seal[key])

    def test_files_backend_proof_is_exact_and_fail_closed(self) -> None:
        repository_format = subprocess.CompletedProcess([], 0, stdout=b"0\n", stderr=b"")
        no_ref_storage = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"")
        with tempfile.TemporaryDirectory() as temporary:
            git_database = Path(temporary).resolve()
            refs_directory = git_database / "refs"
            refs_directory.mkdir()
            with (
                mock.patch.object(self.module, "GIT_DATABASE", git_database),
                mock.patch.object(self.module, "target_git", side_effect=[repository_format, no_ref_storage]) as target,
            ):
                self.module.require_reference_storage_files()
            self.assertEqual(target.call_args_list, [
                mock.call(["config", "--local", "--get", "core.repositoryFormatVersion"]),
                mock.call(["config", "--local", "--get", "extensions.refStorage"], expected=(0, 1)),
            ])

            invalid_git_results = (
                (subprocess.CompletedProcess([], 0, stdout=b"1\n", stderr=b""), no_ref_storage),
                (repository_format, subprocess.CompletedProcess([], 0, stdout=b"reftable\n", stderr=b"")),
            )
            for first, second in invalid_git_results:
                with (
                    self.subTest(first=first.stdout, second=second.stdout),
                    mock.patch.object(self.module, "GIT_DATABASE", git_database),
                    mock.patch.object(self.module, "target_git", side_effect=[first, second]),
                ):
                    with self.assertRaisesRegex(PermissionError, "sealed files backend"):
                        self.module.require_reference_storage_files()

            refs_directory.rmdir()
            with (
                mock.patch.object(self.module, "GIT_DATABASE", git_database),
                mock.patch.object(self.module, "target_git", side_effect=[repository_format, no_ref_storage]),
            ):
                with self.assertRaisesRegex(PermissionError, "sealed files backend"):
                    self.module.require_reference_storage_files()
            refs_directory.mkdir()
            (git_database / "reftable").mkdir()
            with (
                mock.patch.object(self.module, "GIT_DATABASE", git_database),
                mock.patch.object(self.module, "target_git", side_effect=[repository_format, no_ref_storage]),
            ):
                with self.assertRaisesRegex(PermissionError, "sealed files backend"):
                    self.module.require_reference_storage_files()

    def test_all_payloads_are_received_and_prevalidated_before_return(self) -> None:
        source = Path("/external/source/.git")
        contract_raw = subprocess.run(
            ["git", "cat-file", "blob", self.module.CONTRACT_IDENTITY["git_blob_sha1"]],
            cwd=ROOT, check=True, stdout=subprocess.PIPE,
        ).stdout
        seal_raw = subprocess.run(
            ["git", "cat-file", "blob", self.module.CONTRACT_SEAL_IDENTITY["git_blob_sha1"]],
            cwd=ROOT, check=True, stdout=subprocess.PIPE,
        ).stdout
        raws = {
            self.module.CONTRACT_IDENTITY["git_blob_sha1"]: contract_raw,
            self.module.CONTRACT_SEAL_IDENTITY["git_blob_sha1"]: seal_raw,
        }
        for item in self.module.PAYLOADS:
            raws[item["git_blob_sha1"]] = (ROOT / item["path"]).read_bytes()
        events: list[str] = []

        def read(_source, blob_sha1):
            events.append("source_read")
            return raws[blob_sha1]

        def hash_without_write(arguments, *, stdin=None, expected=(0,)):
            events.append("hash_prevalidation")
            self.assertEqual(arguments, ["hash-object", "--stdin"])
            assert stdin is not None
            return subprocess.CompletedProcess(arguments, 0, stdout=(blob(stdin) + "\n").encode("ascii"), stderr=b"")

        with (
            mock.patch.object(self.module, "read_source_blob", side_effect=read) as source_read,
            mock.patch.object(self.module, "target_git", side_effect=hash_without_write) as target_read,
        ):
            payloads, contract = self.module.receive_and_prevalidate_all(source)
        self.assertEqual(len(payloads), 8)
        self.assertEqual(contract["payloads"], list(self.module.PAYLOADS))
        self.assertEqual(source_read.call_count, 10)
        self.assertEqual(target_read.call_count, 8)
        self.assertEqual(events, ["source_read"] * 10 + ["hash_prevalidation"] * 8)

    def test_write_operation_is_exactly_eight_calls_in_declared_order(self) -> None:
        payloads = {item["git_blob_sha1"]: (ROOT / item["path"]).read_bytes() for item in self.module.PAYLOADS}
        calls: list[tuple[list[str], bytes]] = []

        def run(arguments, *, stdin=None, expected=(0,)):
            assert stdin is not None
            calls.append((arguments, stdin))
            return subprocess.CompletedProcess(arguments, 0, stdout=(blob(stdin) + "\n").encode("ascii"), stderr=b"")

        with mock.patch.object(self.module, "run_git", side_effect=run):
            self.module.write_exact_payloads(payloads)
        self.assertEqual(len(calls), 8)
        self.assertEqual([blob(raw) for _, raw in calls], [item["git_blob_sha1"] for item in self.module.PAYLOADS])
        for arguments, _raw in calls:
            self.assertEqual(arguments, [
                "git", "--no-replace-objects",
                "--git-dir=/Users/amcarene/midi-worker/repository/.git",
                "hash-object", "-w", "--stdin",
            ])

    def test_orchestration_revalidates_before_and_after_the_only_effect(self) -> None:
        events: list[str] = []
        payloads = {item["git_blob_sha1"]: b"payload" for item in self.module.PAYLOADS}
        before = {"objects/pack/pack-a.pack": (1, 2, 3, 4, 5)}
        expected_new = {
            "objects/" + item["git_blob_sha1"][:2] + "/" + item["git_blob_sha1"][2:]: (9, 9, 9, 9, 9)
            for item in self.module.PAYLOADS
        }

        def event(name):
            def record(*_args, **_kwargs):
                events.append(name)
            return record

        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments", side_effect=event("platform")),
            mock.patch.object(self.module, "verify_checkout_odb_and_source_realpaths", return_value=Path("/external/.git")),
            mock.patch.object(self.module, "require_reference_storage_files", side_effect=event("format")),
            mock.patch.object(self.module, "require_baseline", side_effect=event("baseline")),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "root_refs_snapshot", return_value=((b"HEAD", b"ref"),)),
            mock.patch.object(self.module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(self.module, "require_detach_runner_absent", side_effect=event("process")),
            mock.patch.object(self.module, "receive_and_prevalidate_all", return_value=(payloads, {})),
            mock.patch.object(self.module, "require_all_target_blobs_absent", side_effect=event("absent")),
            mock.patch.object(self.module, "object_paths_snapshot", side_effect=[before, {**before, **expected_new}]),
            mock.patch.object(self.module, "write_exact_payloads", side_effect=event("write")) as write,
            mock.patch.object(self.module, "require_all_target_blobs_exact", side_effect=event("exact")),
        ):
            result = self.module.import_exact_blobs()
        self.assertEqual(write.call_count, 1)
        self.assertEqual(events, [
            "platform", "format", "baseline", "process", "format", "baseline",
            "process", "absent", "write", "exact", "format", "baseline", "process",
        ])
        self.assertEqual(result["status"], "H27_ODB_ONLY_EXACT_EIGHT_BLOB_IMPORT_TERMINAL_SUCCESS")
        self.assertFalse(result["science_or_locked_test"])

    def test_failure_before_or_after_first_write_has_no_retry_or_cleanup(self) -> None:
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_odb_and_source_realpaths", return_value=Path("/external/.git")),
            mock.patch.object(self.module, "require_reference_storage_files"),
            mock.patch.object(self.module, "require_baseline"),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "root_refs_snapshot", return_value=()),
            mock.patch.object(self.module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(self.module, "require_detach_runner_absent"),
            mock.patch.object(self.module, "receive_and_prevalidate_all", side_effect=PermissionError("pre")),
            mock.patch.object(self.module, "write_exact_payloads") as write,
        ):
            with self.assertRaisesRegex(PermissionError, "pre"):
                self.module.import_exact_blobs()
        write.assert_not_called()

        payloads = {item["git_blob_sha1"]: b"payload" for item in self.module.PAYLOADS}
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_odb_and_source_realpaths", return_value=Path("/external/.git")),
            mock.patch.object(self.module, "require_reference_storage_files"),
            mock.patch.object(self.module, "require_baseline"),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "root_refs_snapshot", return_value=()),
            mock.patch.object(self.module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(self.module, "require_detach_runner_absent"),
            mock.patch.object(self.module, "receive_and_prevalidate_all", return_value=(payloads, {})),
            mock.patch.object(self.module, "require_all_target_blobs_absent"),
            mock.patch.object(self.module, "object_paths_snapshot", return_value={}),
            mock.patch.object(self.module, "write_exact_payloads"),
            mock.patch.object(self.module, "require_all_target_blobs_exact", side_effect=PermissionError("post")) as exact,
        ):
            with self.assertRaisesRegex(PermissionError, "post"):
                self.module.import_exact_blobs()
        self.assertEqual(exact.call_count, 1)


if __name__ == "__main__":
    unittest.main()
