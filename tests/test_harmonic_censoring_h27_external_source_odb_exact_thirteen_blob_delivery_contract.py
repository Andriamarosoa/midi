from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract_external_seal.json"


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


class TestH27ExternalSourceOdbExactThirteenBlobDeliveryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_contract_and_seal_bytes_are_canonical(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))

    def test_exact_thirteen_reviewed_blobs_are_bound(self) -> None:
        objects = self.contract["objects"]
        self.assertEqual((len(objects), len({item["path"] for item in objects}), len({item["git_blob_sha1"] for item in objects})), (13, 13, 13))
        self.assertEqual(objects, [identity(item["path"]) for item in objects])
        self.assertEqual(self.seal["object_count_exact"], 13)
        self.assertEqual(self.seal["object_blob_ids_in_declared_order"], [item["git_blob_sha1"] for item in objects])
        self.assertEqual(self.contract["approved_importer_commit"], "c0bb8d20862f80cabc72ea64a5d437750b7c12e8")
        self.assertEqual(self.seal["approved_importer_commit"], self.contract["approved_importer_commit"])

    def test_transport_and_only_effect_are_exact(self) -> None:
        self.assertEqual(self.contract["future_transport"], {
            "receiver_form": "single reviewed self-contained UTF-8 LF Python source with all thirteen raw payloads embedded as canonical base64 literals",
            "local_runner_rehash_required_before_transport": True,
            "invocation_exact": "ssh -T amcarene@100.89.128.87 env H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 /usr/bin/python3 -",
            "stdin_exact": "raw bytes of the future reviewed self-contained receiver source",
            "remote_arguments_forbidden": True,
            "remote_acknowledgement_environment_exact": "H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1",
            "remote_receiver_filesystem_staging_forbidden": True,
            "remote_receiver_source_file_creation_forbidden": True,
            "scp_sftp_rsync_fetch_pull_push_bundle_pack_index_pack_forbidden": True,
            "only_the_exact_ssh_standard_input_stream_allowed": True,
            "network_access_other_than_the_exact_ssh_transport_forbidden": True,
        })
        self.assertEqual(self.contract["future_write"], {
            "operation_exact": "git --no-replace-objects --git-dir=/Users/amcarene/midi/.git hash-object -w --stdin",
            "one_write_per_object_in_declared_order": True,
            "returned_blob_id_must_equal_expected_immediately": True,
            "exactly_thirteen_new_loose_object_paths_required": True,
            "preexisting_object_paths_and_metadata_unchanged": True,
            "ref_update_forbidden": True,
            "head_change_forbidden": True,
            "index_change_forbidden": True,
            "worktree_change_forbidden": True,
            "unexpected_object_forbidden": True,
        })
        self.assertEqual(self.seal["future_transport"]["invocation_exact"], self.contract["future_transport"]["invocation_exact"])
        self.assertEqual(self.seal["future_effect"]["operation_exact"], self.contract["future_write"]["operation_exact"])
        self.assertEqual(self.seal["future_effect"]["write_count_exact"], 13)

    def test_every_git_subprocess_uses_a_closed_environment(self) -> None:
        environment = self.contract["git_subprocess_environment"]
        self.assertTrue(environment["applies_to_every_sender_and_receiver_git_subprocess"])
        self.assertEqual(environment["delete_every_inherited_key_whose_name_starts_with_exact"], "GIT_")
        self.assertEqual(environment["reintroduce_only_exact"], {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
        })
        self.assertTrue(environment["all_other_git_prefixed_environment_variables_forbidden"])
        for key in (
            "GIT_OBJECT_DIRECTORY_forbidden", "GIT_COMMON_DIR_forbidden",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES_forbidden", "GIT_INDEX_FILE_forbidden",
            "GIT_WORK_TREE_forbidden", "GIT_DIR_forbidden",
            "GIT_CONFIG_GLOBAL_forbidden", "GIT_CONFIG_SYSTEM_forbidden",
            "GIT_CONFIG_COUNT_forbidden", "GIT_CONFIG_KEY_value_pairs_forbidden",
        ):
            self.assertTrue(environment[key])
        self.assertEqual(self.seal["future_git_subprocess_environment"], {
            "applies_to_every_sender_and_receiver_git_subprocess": True,
            "delete_every_inherited_GIT_prefixed_key": True,
            "only_reintroduced_GIT_variables": environment["reintroduce_only_exact"],
            "GIT_OBJECT_DIRECTORY_GIT_COMMON_DIR_GIT_ALTERNATE_OBJECT_DIRECTORIES_GIT_INDEX_FILE_GIT_WORK_TREE_GIT_DIR_and_GIT_CONFIG_redirectors_forbidden": True,
            "git_database_and_worktree_selected_only_by_literal_command_line_arguments": True,
        })

    def test_sender_never_selects_the_repository_from_implicit_cwd(self) -> None:
        sender = self.contract["sender"]
        prefix = "git --no-optional-locks --no-replace-objects -C C:\\Users\\user\\Desktop\\midi\\tmp\\local\\worktrees\\independent-note-neural-v2"
        self.assertEqual(sender["repository_selector_prefix_exact"], prefix)
        self.assertTrue(sender["all_sender_git_commands_must_start_with_repository_selector_prefix_exact"])
        self.assertEqual(sender["all_payload_reads_exact"], prefix + " cat-file blob <expected-sha1>")
        self.assertTrue(sender["implicit_current_working_directory_repository_selection_forbidden"])
        self.assertEqual(self.seal["future_sender_repository_selection"], {
            "review_worktree_exact": sender["review_worktree_exact"],
            "repository_selector_prefix_exact": prefix,
            "all_payload_reads_exact": sender["all_payload_reads_exact"],
            "implicit_cwd_repository_selection_forbidden": True,
        })

    def test_fail_closed_order_and_consumption_policy_are_sealed(self) -> None:
        order = self.contract["future_fail_closed_order"]
        self.assertEqual(len(order), 13)
        self.assertEqual(order[8], "remote_reverify_files_backend_baseline_and_all_thirteen_objects_absent")
        self.assertEqual(order[9], "remote_write_each_exact_blob_once_in_declared_order_and_require_returned_id")
        self.assertEqual(self.seal["future_fail_closed_order"], order)
        self.assertTrue(self.contract["failure_policy"]["single_attempt_only"])
        self.assertTrue(self.contract["failure_policy"]["partial_delivery_is_terminal_consumed_failure"])
        self.assertTrue(self.contract["failure_policy"]["transport_interruption_after_remote_ack_is_terminal_consumed_failure"])
        self.assertTrue(self.seal["future_single_attempt_only"])
        self.assertTrue(self.seal["future_partial_delivery_terminal_consumed_failure"])
        self.assertTrue(self.seal["future_retry_cleanup_repair_rollback_or_automatic_recovery_forbidden"])

    def test_seal_identity_and_current_state_are_exactly_dormant(self) -> None:
        self.assertEqual(self.seal["contract"], identity("configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract.json"))
        state = dict(self.contract["current_state"])
        self.assertTrue(state.pop("contract_only"))
        self.assertTrue(state.pop("external_seal_created"))
        self.assertFalse(any(state.values()))
        for key in (
            "current_receiver_implemented", "current_mac_preflight_executed",
            "current_transport_started", "current_object_delivery_executed",
            "current_source_odb_changed", "current_target_odb_changed",
            "current_import_executed", "current_detach_executed",
            "current_downstream_executed", "science_or_locked_test",
        ):
            self.assertFalse(self.seal[key])


if __name__ == "__main__":
    unittest.main()
