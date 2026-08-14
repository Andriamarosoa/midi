from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts/h27_publish_reviewed_creator_source_terminal_parent_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_reviewed_creator_source_publisher_terminal_parent_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_creator_source_publisher_terminal_parent_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_reviewed_creator_source_publisher_test_subject", PUBLISHER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestReviewedCreatorSourcePublisher(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publisher_raw = PUBLISHER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_versioned_publisher_binding_and_seal(self) -> None:
        for raw in (self.publisher_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["publisher"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["publisher"])
        previous = self.binding["approved_previous_publisher_chain"]
        self.assertEqual((len(previous), len({identity["path"] for identity in previous})), (3, 3))
        old_publisher = subprocess.run(
            ["git", "cat-file", "blob", previous[0]["git_blob_sha1"]],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        self.assertEqual(
            (previous[0]["git_blob_sha1"], previous[0]["size_bytes"], previous[0]["raw_sha256"]),
            (blob(old_publisher), len(old_publisher), hashlib.sha256(old_publisher).hexdigest()),
        )
        for identity in previous[1:]:
            check(self, identity)
        check(self, self.binding["terminal_creator_leaf_evidence"])
        self.assertEqual(self.binding["publisher"], self.seal["publisher"])
        self.assertEqual(
            {
                "evidence_commit": self.seal["terminal_creator_leaf_evidence_commit"],
                "ack": self.seal["future_acknowledgement_environment_exact"],
                "arguments_forbidden": self.seal["future_arguments_forbidden"],
                "parent": self.seal["future_creator_parent_exact"],
                "device": self.seal["future_creator_parent_expected_device_exact"],
                "inode": self.seal["future_creator_parent_expected_inode_exact"],
                "fd_named_exact": self.seal["future_creator_parent_fd_and_named_entry_must_match_terminal_identity"],
                "publisher_consumed": self.seal["publisher_authorization_consumed"],
            },
            {
                "evidence_commit": "81acfa74ea9b6007bed3d02ce1ac7eec9d6a5ef9",
                "ack": "H27_REVIEWED_CREATOR_SOURCE_PUBLISH_EXECUTE=1",
                "arguments_forbidden": True,
                "parent": "/Users/amcarene/h27-admin/creator",
                "device": 16777233,
                "inode": 1447071,
                "fd_named_exact": True,
                "publisher_consumed": False,
            },
        )

    def test_exact_139_identity_preflight_from_git_blobs(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha1],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

        original_read_blob = self.module.read_blob
        original_database = self.module.GIT_DATABASE
        try:
            self.module.read_blob = local_blob
            self.module.GIT_DATABASE = "/Users/amcarene/midi-worker/repository/.git"
            verified = self.module.verify_identity_graph()
        finally:
            self.module.read_blob = original_read_blob
            self.module.GIT_DATABASE = original_database
        self.assertEqual((len(verified), len(set(verified))), (139, 139))
        self.assertEqual(len(self.module.canonical_manifest()), 795)

    def test_dirfd_race_safety_order_and_dormant_state(self) -> None:
        publish = inspect.getsource(self.module.publish)
        ordered = [
            "require_environment()",
            "verify_identity_graph()",
            "canonical_manifest()",
            "open_verified_parent()",
            "require_absent_at(parent_fd, FINAL_NAME)",
            "require_absent_at(parent_fd, STAGING_NAME)",
            "require_parent_fd_still_named(parent_fd)",
            "os.mkdir(STAGING_NAME, mode=0o700, dir_fd=parent_fd)",
            "write_exclusive(staging_fd, ENTRYPOINT_NAME, entrypoint)",
            "write_exclusive(staging_fd, MANIFEST_NAME, manifest)",
            "verify_closed(staging_fd, entrypoint, manifest)",
            "renameatx_np(parent_fd",
            "os.fsync(parent_fd)",
            "verify_closed(final_fd, entrypoint, manifest)",
            "require_parent_fd_still_named(parent_fd)",
        ]
        positions = [publish.index(token) for token in ordered[:-1]] + [publish.rindex(ordered[-1])]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Path.read_bytes", inspect.getsource(self.module.verify_closed))
        read_verified = inspect.getsource(self.module.read_verified_file)
        for token in ("os.O_NOFOLLOW", "os.fstat(fd)", "os.read(fd", "raw != expected"):
            self.assertIn(token, read_verified)
        for token in ("os.O_NOFOLLOW", "os.fstat(fd)", "os.stat(CREATOR_PARENT, follow_symlinks=False)"):
            self.assertIn(token, inspect.getsource(self.module.open_verified_parent))
        self.assertEqual(
            (self.module.CREATOR_PARENT_EXPECTED_DEVICE, self.module.CREATOR_PARENT_EXPECTED_INODE),
            (16777233, 1447071),
        )
        self.assertEqual(
            self.binding["terminal_creator_leaf"],
            {
                "status_exact": "H27_CREATOR_LEAF_CREATED_TERMINAL_SUCCESS",
                "verified_identity_count": 7,
                "path_exact": "/Users/amcarene/h27-admin/creator",
                "device_exact": 16777233,
                "inode_exact": 1447071,
                "creation_authority_terminally_consumed": True,
                "creator_leaf_runner_retry_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["execution_binding"],
            {
                "platform_exact": "darwin",
                "acknowledgement_environment_exact": "H27_REVIEWED_CREATOR_SOURCE_PUBLISH_EXECUTE=1",
                "arguments_forbidden": True,
                "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
                "creator_parent_exact": "/Users/amcarene/h27-admin/creator",
                "creator_parent_expected_device_exact": 16777233,
                "creator_parent_expected_inode_exact": 1447071,
                "creator_parent_fd_and_named_entry_must_match_terminal_identity": True,
                "final_root_exact": "/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1",
                "staging_root_exact": "/Users/amcarene/h27-admin/creator/.h27-reviewed-control-bundle-creator-v1.staging",
                "entrypoint_execution_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["publication_safeguards"],
            {
                "all_one_hundred_thirty_nine_identities_rehashed_before_root_observation": True,
                "parent_opened_no_follow_and_anchored_by_verified_dirfd": True,
                "parent_fd_and_named_entry_match_terminal_device_inode_before_root_observation_effect_and_success": True,
                "all_root_probes_writes_and_rename_relative_to_stable_parent_dirfd": True,
                "staging_creation_first_irreversible_effect": True,
                "exclusive_no_follow_writes": True,
                "files_read_and_rehashed_from_same_verified_file_descriptors": True,
                "closed_directory_set_rechecked_for_change": True,
                "atomic_rename_exclusive": True,
                "files_and_directories_fsynced": True,
                "cleanup_retry_repair_or_republication_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["authority_state"],
            {
                "creator_leaf_creation_authority_terminally_consumed": True,
                "creator_leaf_runner_retry_forbidden": True,
                "publisher_authorization_consumed": False,
                "publisher_retry_not_yet_authorized": True,
            },
        )
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key == "publisher_microfix_exists", key)
        for key in (
            "publisher_microfix_externally_reviewed",
            "publisher_microfix_externally_sealed",
            "publisher_executed_after_creator_leaf",
            "admin_source_published",
            "admin_source_root_observed",
            "creator_entrypoint_executed",
            "registry_opened",
            "authority_reserved",
            "authority_consumed",
            "control_bundle_created",
            "science_or_locked_test",
        ):
            self.assertIs(self.seal[key], False, key)

    def test_parent_fd_and_named_entry_must_match_terminal_tuple(self) -> None:
        expected = mock.Mock(st_mode=self.module.stat.S_IFDIR | 0o700, st_dev=16777233, st_ino=1447071)
        wrong = mock.Mock(st_mode=self.module.stat.S_IFDIR | 0o700, st_dev=16777233, st_ino=1447072)
        with (
            mock.patch.object(self.module.os, "fstat", return_value=expected),
            mock.patch.object(self.module.os, "stat", return_value=expected),
            mock.patch.object(self.module.Path, "resolve", return_value=self.module.CREATOR_PARENT),
            mock.patch.object(self.module.Path, "is_symlink", return_value=False),
        ):
            self.module.require_parent_fd_still_named(17)
        with (
            mock.patch.object(self.module.os, "fstat", return_value=expected),
            mock.patch.object(self.module.os, "stat", return_value=wrong),
            mock.patch.object(self.module.Path, "resolve", return_value=self.module.CREATOR_PARENT),
            mock.patch.object(self.module.Path, "is_symlink", return_value=False),
        ):
            with self.assertRaises(PermissionError):
                self.module.require_parent_fd_still_named(17)


if __name__ == "__main__":
    unittest.main()
