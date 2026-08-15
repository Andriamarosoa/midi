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
RUNNER = ROOT / "scripts/h27_create_control_parent_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_control_parent_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_creator_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_control_parent_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestControlParentCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner_raw = RUNNER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_runner_binding_seal_and_eight_path_graph(self) -> None:
        for raw in (self.runner_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["runner"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["runner"])
        identities = [
            self.binding["runner"],
            *self.binding["approved_contract_chain"],
            *self.binding["transitive_contract_identities"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (8, 8))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_seven_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha1],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

        original_read_blob = self.module.read_blob
        original_require_git_database = self.module.require_git_database
        try:
            self.module.read_blob = local_blob
            self.module.require_git_database = lambda: None
            verified = self.module.verify_identity_graph()
        finally:
            self.module.read_blob = original_read_blob
            self.module.require_git_database = original_require_git_database
        self.assertEqual((len(verified), len(set(verified))), (7, 7))
        source = inspect.getsource(self.module.verify_identity_graph)
        self.assertLess(source.index("require_git_database()"), source.index("read_blob("))

    def test_exact_binding_seal_boundary_and_dormant_state(self) -> None:
        self.assertEqual(
            self.binding["identity_graph"],
            {
                "combined_unique_path_count_including_runner": 8,
                "runner_rehashes_seven_predecessor_identities_before_parent_observation": True,
                "duplicates_forbidden": True,
                "path_or_identity_drift_forbidden": True,
                "acyclic": True,
                "self_hash_present": False,
            },
        )
        self.assertEqual(
            self.binding["execution_binding"],
            {
                "platform_exact": "darwin",
                "acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
                "arguments_forbidden": True,
                "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
                "parent_path_exact": "/Users/amcarene/h27-admin",
                "parent_device_exact": 16777233,
                "parent_inode_exact": 1445438,
                "target_leaf_exact": "control",
                "target_path_exact": "/Users/amcarene/h27-admin/control",
                "target_type_exact": "directory",
                "target_mode_exact_octal": "0700",
                "execution_from_exact_reviewed_git_blob_only": True,
                "checkout_or_worktree_fallback_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["creation_safeguards"],
            {
                "all_seven_predecessor_identities_rehashed_before_parent_observation": True,
                "exact_macos_ack_and_zero_arguments_before_parent_observation": True,
                "parent_opened_o_nofollow_as_directory_and_anchored_by_verified_dirfd": True,
                "parent_exact_terminal_device_and_inode_required": True,
                "single_target_absence_probe_relative_to_parent_dirfd": True,
                "parent_identity_reverified_before_first_effect_and_before_success": True,
                "exact_leaf_mkdir_mode_0700_first_and_only_irreversible_effect": True,
                "mkdir_parents_forbidden": True,
                "parent_fsynced_after_creation": True,
                "created_leaf_opened_o_nofollow_as_directory_and_mode_inode_device_verified": True,
                "cleanup_retry_repair_or_recreation_forbidden": True,
                "registry_authority_creator_bundle_constructor_materializer_and_science_forbidden": True,
            },
        )
        self.assertEqual(
            self.seal,
            {
                "schema_version": 1,
                "seal_id": "H27_CONTROL_PARENT_ONE_SHOT_CREATOR_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
                "status": "SEALED_PENDING_EXTERNAL_REVIEW_RUNNER_DORMANT_NO_FILESYSTEM_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
                "identity_binding": {"path": "configs/harmonic_censoring_h27_control_parent_creator_identity_binding.json", "git_blob_sha1": "4a1b1ac62395d9880e747dc24395c2e2a0edce85", "size_bytes": 4881, "raw_sha256": "5d1bc87e54cbd0b9e6f7162767fa3eddfec5e6a1e63e3aa7bd2f74f89fc314bc"},
                "runner": {"path": "scripts/h27_create_control_parent_one_shot.py", "git_blob_sha1": "96df05111a5e40a418e12fb2b3db4bd9516bcab3", "size_bytes": 9415, "raw_sha256": "42c3563aabfc3ede5090a0756ab4c58d601016190f502769859bc9279878261f"},
                "approved_contract_binding_commit": "a8662780533c9c613b22f709bd5da94d1526f314",
                "verified_predecessor_identity_count": 7,
                "future_acknowledgement_environment_exact": "H27_CONTROL_PARENT_CREATE_EXECUTE=1",
                "future_arguments_forbidden": True,
                "future_execution_from_exact_reviewed_git_blob_only": True,
                "future_parent_path_exact": "/Users/amcarene/h27-admin",
                "future_parent_device_exact": 16777233,
                "future_parent_inode_exact": 1445438,
                "future_target_path_exact": "/Users/amcarene/h27-admin/control",
                "future_target_type_exact": "directory",
                "future_target_mode_exact_octal": "0700",
                "runner_externally_reviewed": False,
                "runner_externally_sealed": False,
                "control_parent_observed": False,
                "control_parent_created": False,
                "registry_opened": False,
                "authority_reserved": False,
                "authority_consumed": False,
                "creator_entrypoint_executed": False,
                "control_bundle_created": False,
                "constructor_or_materializer_executed": False,
                "science_or_locked_test": False,
                "next_action": "External review of the exact dormant control-parent creator, identity binding and seal only",
            },
        )
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key == "runner_exists", key)

    def test_exact_one_shot_order_and_single_irreversible_effect(self) -> None:
        source = inspect.getsource(self.module.create)
        ordered = [
            "verify_identity_graph()",
            "require_environment()",
            "open_verified_parent()",
            "probe_target_absence_once(parent_fd)",
            "require_parent_fd_still_named(parent_fd)",
            "os.mkdir(TARGET_LEAF, mode=0o700, dir_fd=parent_fd)",
            "os.fsync(parent_fd)",
            "open_created_leaf(parent_fd)",
            "verify_created_leaf(parent_fd, leaf_fd)",
            "require_parent_fd_still_named(parent_fd)",
        ]
        positions = [source.index(token) for token in ordered[:-1]] + [source.rindex(ordered[-1])]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("os.mkdir("), 1)
        for forbidden in ("rmtree", "unlink", "makedirs", "mkdir(parents"):
            self.assertNotIn(forbidden, source)

    def test_synthetic_call_order_has_single_effect(self) -> None:
        calls: list[str] = []

        def mark(name, result=None):
            def action(*args, **kwargs):
                calls.append(name)
                return result
            return action

        with (
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(7)})),
            mock.patch.object(self.module, "require_environment", side_effect=mark("environment")),
            mock.patch.object(self.module, "open_verified_parent", side_effect=mark("open_parent", 17)),
            mock.patch.object(self.module, "probe_target_absence_once", side_effect=mark("probe")),
            mock.patch.object(self.module, "require_parent_fd_still_named", side_effect=mark("parent")),
            mock.patch.object(self.module.os, "mkdir", side_effect=mark("mkdir")),
            mock.patch.object(self.module.os, "fsync", side_effect=mark("fsync")),
            mock.patch.object(self.module, "open_created_leaf", side_effect=mark("open_leaf", 18)),
            mock.patch.object(self.module, "verify_created_leaf", side_effect=mark("verify_leaf", (3, 5))),
            mock.patch.object(self.module.os, "close", side_effect=mark("close")),
        ):
            result = self.module.create()
        self.assertEqual(
            calls,
            ["identities", "environment", "open_parent", "probe", "parent", "mkdir", "fsync", "open_leaf", "verify_leaf", "parent", "close", "close"],
        )
        self.assertEqual(calls.count("mkdir"), 1)
        self.assertEqual(result["verified_identity_count"], 7)
        self.assertEqual(result["status"], "H27_CONTROL_PARENT_CREATED_TERMINAL_SUCCESS")

    def test_created_leaf_requires_exact_directory_mode_and_identity(self) -> None:
        descriptor = mock.Mock(st_mode=stat.S_IFDIR | 0o700, st_dev=3, st_ino=5)
        named = mock.Mock(st_mode=stat.S_IFDIR | 0o700, st_dev=3, st_ino=5)
        with mock.patch.object(self.module.os, "fstat", return_value=descriptor), mock.patch.object(self.module.os, "stat", return_value=named):
            self.assertEqual(self.module.verify_created_leaf(17, 18), (3, 5))
        named.st_mode = stat.S_IFDIR | 0o755
        with mock.patch.object(self.module.os, "fstat", return_value=descriptor), mock.patch.object(self.module.os, "stat", return_value=named):
            with self.assertRaises(PermissionError):
                self.module.verify_created_leaf(17, 18)


if __name__ == "__main__":
    unittest.main()
