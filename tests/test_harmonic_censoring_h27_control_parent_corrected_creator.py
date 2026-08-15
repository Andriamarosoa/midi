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
RUNNER = ROOT / "scripts/h27_create_control_parent_corrected_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_control_parent_corrected_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_parent_corrected_creator_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_corrected_control_parent_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestCorrectedControlParentCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner_raw = RUNNER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_runner_binding_seal_and_twelve_path_graph(self) -> None:
        for raw in (self.runner_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["runner"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["runner"])
        identities = [
            self.binding["runner"],
            *self.binding["approved_corrective_chain"],
            *self.binding["transitive_predecessor_identities"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (12, 12))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_eleven_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha1],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

        with (
            mock.patch.object(self.module, "read_blob", side_effect=local_blob),
            mock.patch.object(self.module, "require_git_database"),
        ):
            verified = self.module.verify_identity_graph()
        self.assertEqual((len(verified), len(set(verified))), (11, 11))
        source = inspect.getsource(self.module.verify_identity_graph)
        self.assertLess(source.index("require_git_database()"), source.index("read_blob("))

    def test_exact_corrected_boundary_and_stale_runner_revocation(self) -> None:
        self.assertEqual(self.binding["identity_graph"], {
            "combined_unique_path_count_including_runner": 12,
            "runner_rehashes_eleven_predecessor_identities_before_parent_observation": True,
            "corrective_roots_rehash_nine_transitive_identities": True,
            "duplicates_forbidden": True,
            "path_or_identity_drift_forbidden": True,
            "acyclic": True,
            "self_hash_present": False,
        })
        self.assertEqual(self.binding["execution_binding"]["parent_device_exact"], 16777234)
        self.assertEqual(self.binding["execution_binding"]["parent_inode_exact"], 1445438)
        self.assertEqual(self.binding["execution_binding"]["target_path_exact"], "/Users/amcarene/h27-admin/control")
        stale = self.binding["stale_runner_state"]
        self.assertEqual(stale["runner_git_blob_sha1"], "96df05111a5e40a418e12fb2b3db4bd9516bcab3")
        self.assertIs(stale["execution_authorization_revoked"], True)
        for key in ("executable", "executed", "consumed", "acknowledgement_set", "mkdir_attempted"):
            self.assertIs(stale[key], False)
        self.assertEqual(self.seal["verified_predecessor_identity_count"], 11)
        self.assertEqual(self.seal["combined_unique_identity_count_including_runner"], 12)
        self.assertIs(self.seal["mac_execution_authorized"], False)
        self.assertIs(self.seal["stale_runner_execution_authorization_revoked"], True)

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
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(11)})),
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
        self.assertEqual(calls, ["identities", "environment", "open_parent", "probe", "parent", "mkdir", "fsync", "open_leaf", "verify_leaf", "parent", "close", "close"])
        self.assertEqual(calls.count("mkdir"), 1)
        self.assertEqual(result["verified_identity_count"], 11)
        self.assertEqual(result["status"], "H27_CONTROL_PARENT_CORRECTED_CREATED_TERMINAL_SUCCESS")
        self.assertIs(result["stale_runner_executed"], False)
        self.assertIs(result["stale_runner_consumed"], False)

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
