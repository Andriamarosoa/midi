from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts/h27_publish_reviewed_creator_source_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_reviewed_creator_source_publisher_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_creator_source_publisher_identity_binding_external_seal.json"


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
        for identity in self.binding["approved_implementation_source_chain"]:
            check(self, identity)
        self.assertEqual(self.binding["publisher"], self.seal["publisher"])

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
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key == "publisher_versioned", key)
        for key in (
            "publisher_externally_reviewed",
            "publisher_externally_sealed",
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


if __name__ == "__main__":
    unittest.main()
