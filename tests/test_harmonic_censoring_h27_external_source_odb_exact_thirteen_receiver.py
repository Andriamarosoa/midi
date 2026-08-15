from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RECEIVER = ROOT / "scripts/h27_receive_exact_thirteen_source_odb_blobs_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding_external_seal.json"
CONTRACT = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract_external_seal.json"
PREFLIGHT = ROOT / "readme/results/2026-08-15_harmonic-censoring-h27-external-source-odb-thirteen-delivery-read-only-preflight.md"


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


class TestH27ExternalSourceOdbExactThirteenReceiver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("h27_exact_thirteen_receiver", RECEIVER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.contract = json.loads(CONTRACT.read_bytes())
        cls.contract_seal = json.loads(CONTRACT_SEAL.read_bytes())
        cls.binding = json.loads(BINDING.read_bytes())
        cls.seal = json.loads(SEAL.read_bytes())

    def test_receiver_binding_seal_and_inputs_are_exact(self) -> None:
        for path in (RECEIVER, BINDING, SEAL):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(
            self.binding["receiver"],
            identity("scripts/h27_receive_exact_thirteen_source_odb_blobs_one_shot.py"),
        )
        self.assertEqual(self.binding["approved_contract"], identity(CONTRACT.relative_to(ROOT).as_posix()))
        self.assertEqual(
            self.binding["approved_contract_external_seal"],
            identity(CONTRACT_SEAL.relative_to(ROOT).as_posix()),
        )
        self.assertEqual(self.binding["approved_read_only_preflight"], identity(PREFLIGHT.relative_to(ROOT).as_posix()))
        self.assertEqual(self.binding["normative_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(self.seal["identity_binding"], identity(BINDING.relative_to(ROOT).as_posix()))
        for key in (
            "receiver", "approved_contract", "approved_contract_external_seal",
            "approved_read_only_preflight", "approved_contract_commit",
            "approved_read_only_preflight_commit",
        ):
            self.assertEqual(self.seal[key], self.binding[key])
        self.assertEqual(self.seal["future_normative_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(self.seal["future_embedded_object_count_exact"], 13)
        self.assertEqual(self.seal["future_exact_write_count"], 13)
        self.assertEqual(self.seal["future_embedded_blob_ids_in_declared_order"], [
            item["git_blob_sha1"] for item in self.contract["objects"]
        ])
        self.assertEqual(set(self.binding), {
            "schema_version", "binding_id", "status", "receiver",
            "approved_contract_commit", "approved_contract", "approved_contract_external_seal",
            "approved_read_only_preflight_commit", "approved_read_only_preflight",
            "identity_graph", "execution_binding", "embedded_objects",
            "reference_storage_files_proof", "implementation_invariants", "normative_order",
            "current_state", "next_action",
        })
        self.assertEqual(set(self.seal), {
            "schema_version", "seal_id", "status", "identity_binding", "receiver",
            "approved_contract_commit", "approved_contract", "approved_contract_external_seal",
            "approved_read_only_preflight_commit", "approved_read_only_preflight",
            "future_platform_exact", "future_acknowledgement_environment_exact",
            "future_arguments_forbidden", "future_checkout_exact",
            "future_git_object_database_exact", "future_transport_exact",
            "future_receiver_source_transport_only_over_exact_ssh_stdin",
            "future_remote_filesystem_staging_forbidden",
            "future_receiver_execution_from_exact_reviewed_git_blob_only",
            "future_git_environment", "future_embedded_object_count_exact",
            "future_embedded_aggregate_raw_size_bytes",
            "future_embedded_blob_ids_in_declared_order",
            "future_canonical_base64_size_sha256_and_git_blob_id_required",
            "future_all_thirteen_decoded_buffered_and_prevalidated_before_object_lookup_or_write",
            "future_reference_storage_files_proof", "future_write_operation_exact",
            "future_exact_write_count",
            "future_object_database_path_delta_exactly_thirteen_expected_loose_objects",
            "future_preexisting_object_paths_and_metadata_unchanged",
            "future_refs_head_index_worktree_and_target_odb_unchanged",
            "future_normative_order", "future_single_attempt_only",
            "future_partial_delivery_terminal_consumed_failure",
            "future_retry_cleanup_repair_rollback_or_automatic_recovery_forbidden",
            "receiver_externally_reviewed", "receiver_transported",
            "mac_acknowledgement_set", "object_delivery_executed", "source_odb_changed",
            "target_odb_changed", "import_executed", "detach_executed",
            "downstream_executed", "science_or_locked_test", "next_action",
        })
        self.assertEqual(self.binding["identity_graph"], {
            "unique_path_count": 4,
            "receiver_contract_seal_and_preflight_bound": True,
            "duplicates_forbidden": True,
            "path_or_identity_drift_forbidden": True,
            "acyclic": True,
            "self_hash_present": False,
        })
        self.assertEqual(self.binding["embedded_objects"], {
            "count_exact": 13,
            "aggregate_raw_size_bytes": 75730,
            "blob_ids_in_declared_order": [item["git_blob_sha1"] for item in self.contract["objects"]],
            "unique_paths_required": True,
            "unique_blob_ids_required": True,
            "canonical_base64_roundtrip_required": True,
            "size_sha256_and_git_blob_id_required": True,
        })
        self.assertEqual(self.binding["execution_binding"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1",
            "arguments_forbidden": True,
            "checkout_exact": "/Users/amcarene/midi",
            "git_object_database_exact": "/Users/amcarene/midi/.git",
            "receiver_transport_exact": "ssh -T amcarene@100.89.128.87 env H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 /usr/bin/python3 -",
            "receiver_source_transport_only_over_exact_ssh_stdin": True,
            "remote_receiver_source_or_payload_file_creation_forbidden": True,
            "receiver_execution_from_exact_reviewed_git_blob_only": True,
            "all_thirteen_payloads_embedded_as_canonical_base64": True,
            "all_thirteen_payloads_decoded_and_prevalidated_in_memory_before_object_lookup": True,
            "git_environment_removes_every_inherited_GIT_prefixed_key": True,
            "git_environment_reintroduces_only": {
                "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
            },
            "git_database_and_worktree_selected_only_by_literal_command_line_arguments": True,
            "write_operation_exact": "git --no-replace-objects --git-dir=/Users/amcarene/midi/.git hash-object -w --stdin",
        })
        expected_proof = {
            "proof_id": "H27_FILES_BACKEND_COMPATIBLE_WITH_APPLE_GIT_2_39_V1",
            "repository_format_stdout_exact": "0\n",
            "ref_storage_extension_returncode_exact": 1,
            "ref_storage_extension_stdout_exact": "",
            "ref_storage_extension_stderr_exact": "",
            "refs_directory_real_non_symlink_required": True,
            "reftable_directory_absent_required": True,
            "verified_before_decode_before_first_write_and_after_all_writes": True,
        }
        self.assertEqual(self.binding["reference_storage_files_proof"], expected_proof)
        self.assertEqual(self.seal["future_reference_storage_files_proof"], expected_proof)
        self.assertEqual(self.binding["implementation_invariants"], {
            "checkout_odb_objects_and_refs_realpaths_verified": True,
            "baseline_head_symbolic_head_cleanliness_lock_and_process_verified": True,
            "regular_refs_root_refs_pseudorefs_and_index_snapshotted_byte_exact": True,
            "all_thirteen_embedded_payloads_decoded_before_identity_prevalidation": True,
            "all_thirteen_payloads_prevalidated_before_any_object_lookup_or_write": True,
            "all_thirteen_source_blobs_absent_before_first_write": True,
            "object_database_snapshot_revalidated_immediately_before_first_write": True,
            "exactly_thirteen_writes_in_declared_order": True,
            "returned_blob_id_required_after_each_write": True,
            "all_thirteen_source_blobs_revalidated_byte_exact": True,
            "object_database_path_delta_exactly_thirteen_expected_loose_objects": True,
            "preexisting_object_paths_and_metadata_unchanged": True,
            "refs_head_index_worktree_and_target_odb_unchanged": True,
            "single_attempt_no_retry_cleanup_repair_or_rollback": True,
            "partial_delivery_terminal_consumed_failure": True,
        })
        self.assertEqual(self.seal["future_git_environment"], {
            "delete_every_inherited_GIT_prefixed_key": True,
            "only_reintroduced": {"GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1"},
            "repository_selected_only_by_literal_command_arguments": True,
        })
        for key in (
            "future_arguments_forbidden", "future_receiver_source_transport_only_over_exact_ssh_stdin",
            "future_remote_filesystem_staging_forbidden",
            "future_receiver_execution_from_exact_reviewed_git_blob_only",
            "future_canonical_base64_size_sha256_and_git_blob_id_required",
            "future_all_thirteen_decoded_buffered_and_prevalidated_before_object_lookup_or_write",
            "future_object_database_path_delta_exactly_thirteen_expected_loose_objects",
            "future_preexisting_object_paths_and_metadata_unchanged",
            "future_refs_head_index_worktree_and_target_odb_unchanged",
            "future_single_attempt_only", "future_partial_delivery_terminal_consumed_failure",
            "future_retry_cleanup_repair_rollback_or_automatic_recovery_forbidden",
        ):
            self.assertTrue(self.seal[key])
        for key in (
            "receiver_externally_reviewed", "receiver_transported", "mac_acknowledgement_set",
            "object_delivery_executed", "source_odb_changed", "target_odb_changed",
            "import_executed", "detach_executed", "downstream_executed",
            "science_or_locked_test",
        ):
            self.assertFalse(self.seal[key])

    def test_all_thirteen_embedded_payloads_match_the_reviewed_git_blobs(self) -> None:
        self.assertEqual(len(self.module.EMBEDDED_OBJECTS), 13)
        self.assertEqual(
            [{key: row[key] for key in ("path", "git_blob_sha1", "size_bytes", "raw_sha256")}
             for row in self.module.EMBEDDED_OBJECTS],
            self.contract["objects"],
        )
        decoded = self.module.decode_and_prevalidate_all()
        self.assertEqual(len(decoded), 13)
        self.assertEqual(sum(map(len, decoded.values())), 75730)
        for item in self.contract["objects"]:
            raw = subprocess.run(
                [
                    "git", "--no-optional-locks", "--no-replace-objects", "-C", str(ROOT),
                    "cat-file", "blob", item["git_blob_sha1"],
                ],
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertEqual(decoded[item["git_blob_sha1"]], raw)

    def test_complete_decode_precedes_complete_identity_validation(self) -> None:
        events: list[str] = []
        real_decode = base64.b64decode
        real_identity_ok = self.module.identity_ok

        def decode(*args, **kwargs):
            events.append("decode")
            return real_decode(*args, **kwargs)

        def validate(*args, **kwargs):
            events.append("validate")
            return real_identity_ok(*args, **kwargs)

        with (
            mock.patch.object(self.module.base64, "b64decode", side_effect=decode),
            mock.patch.object(self.module, "identity_ok", side_effect=validate),
        ):
            self.module.decode_and_prevalidate_all()
        self.assertEqual(events, ["decode"] * 13 + ["validate"] * 13)

    def test_git_environment_is_fail_closed(self) -> None:
        inherited = {
            "PATH": "safe",
            "GIT_DIR": "redirect",
            "GIT_OBJECT_DIRECTORY": "redirect",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "bad",
        }
        with mock.patch.object(self.module.os, "environ", inherited):
            cleaned = self.module.clean_git_environment()
        self.assertEqual(cleaned, {
            "PATH": "safe",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
        })

    def test_write_boundary_is_exactly_thirteen_calls_in_declared_order(self) -> None:
        decoded = self.module.decode_and_prevalidate_all()
        calls: list[tuple[list[str], bytes]] = []

        def run(arguments, *, stdin=None, expected=(0,)):
            assert stdin is not None
            calls.append((arguments, stdin))
            return subprocess.CompletedProcess(
                arguments, 0, stdout=(blob(stdin) + "\n").encode("ascii"), stderr=b""
            )

        with mock.patch.object(self.module, "run_git", side_effect=run):
            self.module.write_exact_objects(decoded)
        self.assertEqual(len(calls), 13)
        self.assertEqual([blob(raw) for _args, raw in calls], [
            item["git_blob_sha1"] for item in self.contract["objects"]
        ])
        for arguments, _raw in calls:
            self.assertEqual(arguments, [
                "git", "--no-replace-objects", "--git-dir=/Users/amcarene/midi/.git",
                "hash-object", "-w", "--stdin",
            ])

    def test_orchestration_has_one_effect_and_revalidates_both_sides(self) -> None:
        events: list[str] = []
        decoded = {item["git_blob_sha1"]: b"payload" for item in self.contract["objects"]}
        before = {"objects/pack/pack-a.pack": (1, 2, 3, 4, 5)}
        additions = {
            "objects/" + item["git_blob_sha1"][:2] + "/" + item["git_blob_sha1"][2:]: (9, 9, 9, 9, 9)
            for item in self.contract["objects"]
        }

        def event(name):
            def record(*_args, **_kwargs):
                events.append(name)
            return record

        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments", side_effect=event("platform")),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths", side_effect=event("realpaths")),
            mock.patch.object(self.module, "require_reference_storage_files", side_effect=event("format")),
            mock.patch.object(self.module, "decode_and_prevalidate_all", side_effect=lambda: (events.append("decode") or decoded)),
            mock.patch.object(self.module, "require_baseline", side_effect=event("baseline")),
            mock.patch.object(self.module, "require_conflicting_process_absent", side_effect=event("process")),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "root_refs_snapshot", return_value=((b"HEAD", b"ref"),)),
            mock.patch.object(self.module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(self.module, "object_paths_snapshot", side_effect=[before, before, {**before, **additions}]),
            mock.patch.object(self.module, "require_all_objects_absent", side_effect=event("absent")),
            mock.patch.object(self.module, "write_exact_objects", side_effect=event("write")) as write,
            mock.patch.object(self.module, "require_all_objects_exact", side_effect=event("exact")),
        ):
            result = self.module.receive_exact_thirteen()
        self.assertEqual(write.call_count, 1)
        self.assertEqual(events, [
            "platform", "realpaths", "format", "decode", "baseline", "process",
            "format", "baseline", "process", "absent", "write", "exact",
            "format", "baseline", "process",
        ])
        self.assertEqual(result["status"], "H27_SOURCE_ODB_EXACT_THIRTEEN_BLOB_DELIVERY_TERMINAL_SUCCESS")
        self.assertFalse(result["science_or_locked_test"])

    def test_failure_before_or_after_write_has_no_retry_or_cleanup(self) -> None:
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(self.module, "require_reference_storage_files"),
            mock.patch.object(self.module, "decode_and_prevalidate_all", side_effect=PermissionError("pre")),
            mock.patch.object(self.module, "write_exact_objects") as write,
        ):
            with self.assertRaisesRegex(PermissionError, "pre"):
                self.module.receive_exact_thirteen()
        write.assert_not_called()

        decoded = {item["git_blob_sha1"]: b"payload" for item in self.contract["objects"]}
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(self.module, "require_reference_storage_files"),
            mock.patch.object(self.module, "decode_and_prevalidate_all", return_value=decoded),
            mock.patch.object(self.module, "require_baseline"),
            mock.patch.object(self.module, "require_conflicting_process_absent"),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "root_refs_snapshot", return_value=()),
            mock.patch.object(self.module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(self.module, "object_paths_snapshot", side_effect=[{}, {}]),
            mock.patch.object(self.module, "require_all_objects_absent"),
            mock.patch.object(self.module, "write_exact_objects") as write,
            mock.patch.object(self.module, "require_all_objects_exact", side_effect=PermissionError("post")) as exact,
        ):
            with self.assertRaisesRegex(PermissionError, "post"):
                self.module.receive_exact_thirteen()
        self.assertEqual(write.call_count, 1)
        self.assertEqual(exact.call_count, 1)

    def test_receiver_has_no_transport_or_remote_staging_implementation(self) -> None:
        raw = RECEIVER.read_text(encoding="utf-8")
        for forbidden in ("ssh ", "scp ", "sftp ", "rsync ", "mkstemp", "NamedTemporaryFile"):
            self.assertNotIn(forbidden, raw)
        for forbidden_symbol in ("def retry", "def cleanup", "def rollback", "def repair"):
            self.assertNotIn(forbidden_symbol, raw.lower())


if __name__ == "__main__":
    unittest.main()
