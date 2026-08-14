from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import stat
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_create_empty_registry_file_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_registry_file_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_file_creator_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


def load_module():
    spec = importlib.util.spec_from_file_location("h27_registry_file_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestRegistryFileCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner_raw = RUNNER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_runner_binding_seal_and_nine_path_graph(self) -> None:
        for raw in (self.runner_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["runner"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["runner"])
        identities = [self.binding["runner"], *self.binding["approved_contract_chain"], *self.binding["transitive_contract_identities"]]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (9, 9))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_eight_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(["git", "cat-file", "blob", blob_sha1], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout

        with (
            mock.patch.object(self.module, "read_blob", side_effect=local_blob),
            mock.patch.object(self.module, "require_git_database"),
        ):
            verified = self.module.verify_identity_graph()
        self.assertEqual((len(verified), len(set(verified))), (8, 8))
        source = inspect.getsource(self.module.verify_identity_graph)
        self.assertLess(source.index("require_git_database()"), source.index("read_blob("))

    def test_exact_binding_order_contract_and_complete_seal(self) -> None:
        source = inspect.getsource(self.module.create)
        ordered = [
            "verify_identity_graph()", "require_environment()", "open_verified_parent()",
            "probe_target_absence_once(parent_fd)", "require_parent_fd_still_named(parent_fd)",
            "created_fd = os.open(", "require_file_identity(parent_fd, created_fd)",
            "os.fsync(created_fd)", "os.fsync(parent_fd)", "reopened_fd = os.open(",
            "require_file_identity(parent_fd, reopened_fd",
        ]
        positions = [source.index(token) for token in ordered] + [source.rindex("require_parent_fd_still_named(parent_fd)")]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("os.O_CREAT"), 1)
        for forbidden_call in ("os.unlink(", "os.remove(", "shutil.rmtree(", "os.replace(", "os.rename("):
            self.assertNotIn(forbidden_call, source)
        self.assertEqual(self.binding["execution_binding"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE=1",
            "arguments_forbidden": True,
            "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "parent_path_exact": "/Users/amcarene/h27-admin/registry",
            "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1448669,
            "parent_fd_and_named_entry_must_match_terminal_identity": True,
            "target_leaf_exact": "h27-control-bundle-creation-authority-v1.jsonl",
            "target_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "target_initial_size_bytes_exact": 0,
            "target_nlink_exact": 1,
            "target_mode_exact_octal": "0600",
            "execution_from_exact_reviewed_git_blob_only": True,
            "checkout_or_worktree_fallback_forbidden": True,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "combined_unique_path_count_including_runner": 9,
            "runner_rehashes_eight_predecessor_identities_before_parent_observation": True,
            "duplicates_forbidden": True,
            "path_or_identity_drift_forbidden": True,
            "acyclic": True,
            "self_hash_present": False,
        })
        self.assertEqual(self.binding["creation_safeguards"], {
            "all_eight_predecessor_identities_rehashed_before_parent_observation": True,
            "parent_opened_o_nofollow_and_anchored_by_verified_dirfd": True,
            "parent_fd_and_named_entry_match_terminal_device_inode_before_probe_effect_and_success": True,
            "single_target_absence_probe_relative_to_parent_dirfd": True,
            "exact_file_open_o_creat_o_excl_o_nofollow_mode_0600_first_and_only_irreversible_effect": True,
            "created_fd_immediately_verified_regular_nlink_one_size_zero_mode_0600": True,
            "created_file_fsynced": True,
            "parent_fsynced_after_creation": True,
            "file_reopened_o_nofollow_and_fd_named_entry_inode_device_regular_nlink_size_mode_verified": True,
            "cleanup_retry_repair_or_recreation_forbidden": True,
            "registry_record_write_authority_reservation_consumption_creator_bundle_constructor_materializer_and_science_forbidden": True,
        })
        self.assertEqual(self.binding["authority_state"], {
            "registry_leaf_creation_authority_terminally_consumed": True,
            "registry_leaf_runner_retry_forbidden": True,
            "registry_file_creation_authority_unconsumed": True,
        })
        true_state = {"runner_exists", "registry_leaf_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in true_state, key)
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_EMPTY_AUTHORITY_REGISTRY_FILE_ONE_SHOT_CREATOR_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_RUNNER_DORMANT_NO_FILESYSTEM_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {"path": "configs/harmonic_censoring_h27_registry_file_creator_identity_binding.json", "git_blob_sha1": "9dbcef0f2e083d8e8f9796be63218329bf71014a", "size_bytes": 5781, "raw_sha256": "886c908dfe2b1fed1a76d72fdd2d2454ca9db55e68dfc4131dbac71d2364c4f3"},
            "runner": {"path": "scripts/h27_create_empty_registry_file_one_shot.py", "git_blob_sha1": "6f1ebfef57aeba640df44856906010ecf69bbb7f", "size_bytes": 11915, "raw_sha256": "36a497cfeaf339bbeda0d885a16398f727f55df869af802b663e0a27e1a79a45"},
            "approved_contract_binding_commit": "8c7152ccd5e50d8dbbb40c12ec582efadc58dd54",
            "bound_predecessor_identity_count": 8,
            "bound_unique_path_count_including_runner": 9,
            "future_acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE=1",
            "future_arguments_forbidden": True,
            "future_parent_path_exact": "/Users/amcarene/h27-admin/registry",
            "future_parent_expected_device_exact": 16777233,
            "future_parent_expected_inode_exact": 1448669,
            "future_target_path_exact": "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl",
            "future_target_initial_size_bytes_exact": 0,
            "future_target_nlink_exact": 1,
            "future_target_mode_exact_octal": "0600",
            "future_execution_from_exact_reviewed_git_blob_only": True,
            "registry_leaf_creation_authority_terminally_consumed": True,
            "registry_leaf_runner_retry_forbidden": True,
            "registry_file_creation_authority_consumed": False,
            "runner_externally_reviewed": False,
            "runner_externally_sealed": False,
            "parent_observed_by_registry_file_runner": False,
            "registry_file_observed": False,
            "registry_file_created": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact dormant empty-registry-file runner, identity binding and seal only",
        })

    def test_parent_and_empty_file_identity_are_fail_closed(self) -> None:
        directory = mock.Mock(st_mode=stat.S_IFDIR | 0o700, st_dev=16777233, st_ino=1448669)
        self.assertTrue(self.module.parent_identity_ok(directory, directory))
        self.assertFalse(self.module.parent_identity_ok(directory, mock.Mock(st_mode=stat.S_IFDIR | 0o700, st_dev=16777233, st_ino=1448670)))
        exact = mock.Mock(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_size=0)
        wrong_mode = mock.Mock(st_mode=stat.S_IFREG | 0o640, st_nlink=1, st_size=0)
        wrong_size = mock.Mock(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_size=1)
        wrong_nlink = mock.Mock(st_mode=stat.S_IFREG | 0o600, st_nlink=2, st_size=0)
        self.assertTrue(self.module.exact_empty_regular_file(exact))
        self.assertFalse(self.module.exact_empty_regular_file(wrong_mode))
        self.assertFalse(self.module.exact_empty_regular_file(wrong_size))
        self.assertFalse(self.module.exact_empty_regular_file(wrong_nlink))

    def test_synthetic_call_order_has_single_creation_effect(self) -> None:
        calls: list[str] = []

        def mark(name, result=None):
            def action(*args, **kwargs):
                calls.append(name)
                return result
            return action

        open_count = 0
        def open_file(*args, **kwargs):
            nonlocal open_count
            open_count += 1
            calls.append("create_open" if open_count == 1 else "reopen")
            flags = args[1]
            if open_count == 1:
                self.assertTrue(flags & self.module.os.O_CREAT)
                self.assertTrue(flags & self.module.os.O_EXCL)
                self.assertEqual(args[2], 0o600)
            else:
                self.assertFalse(flags & self.module.os.O_CREAT)
            self.assertTrue(flags & self.module.os.O_NOFOLLOW)
            self.assertEqual(kwargs["dir_fd"], 17)
            return 17 + open_count

        identity_count = 0
        def verify_file(*args, **kwargs):
            nonlocal identity_count
            identity_count += 1
            calls.append("verify_created" if identity_count == 1 else "verify_reopened")
            if identity_count == 2:
                self.assertEqual(args[2], (16777233, 1449000))
            return (16777233, 1449000)

        with (
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(8)})),
            mock.patch.object(self.module, "require_environment", side_effect=mark("environment")),
            mock.patch.object(self.module, "open_verified_parent", side_effect=mark("open_parent", 17)),
            mock.patch.object(self.module, "probe_target_absence_once", side_effect=mark("probe")),
            mock.patch.object(self.module, "require_parent_fd_still_named", side_effect=mark("parent")),
            mock.patch.object(self.module.os, "O_NOFOLLOW", 0x20000, create=True),
            mock.patch.object(self.module.os, "open", side_effect=open_file),
            mock.patch.object(self.module, "require_file_identity", side_effect=verify_file),
            mock.patch.object(self.module.os, "fsync", side_effect=mark("fsync")),
            mock.patch.object(self.module.os, "close", side_effect=mark("close")),
        ):
            result = self.module.create()
        self.assertEqual(calls, ["identities", "environment", "open_parent", "probe", "parent", "create_open", "verify_created", "fsync", "fsync", "reopen", "verify_reopened", "parent", "close", "close", "close"])
        self.assertEqual(result["verified_identity_count"], 8)
        self.assertEqual(result["status"], "H27_EMPTY_REGISTRY_FILE_CREATED_TERMINAL_SUCCESS")
        self.assertTrue(result["registry_file_creation_authority_consumed"])
        self.assertFalse(result["registry_record_written"])


if __name__ == "__main__":
    unittest.main()
