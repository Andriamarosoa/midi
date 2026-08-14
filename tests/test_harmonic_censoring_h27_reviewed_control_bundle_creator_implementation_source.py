from __future__ import annotations

import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import subprocess
import unittest

from tests.test_harmonic_censoring_h27_reviewed_control_bundle_creator_contract_identity_binding import hundred_thirty
from tests.test_harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_contract_identity_binding import hundred_thirty_four

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/h27_reviewed_control_bundle_creator.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


def load_module():
    spec = importlib.util.spec_from_file_location("h27_reviewed_creator_test_subject", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestReviewedCreatorImplementationSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw = SOURCE.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_source_seal_and_139_identities(self) -> None:
        for raw in (self.source_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        check(self, self.seal["implementation_entrypoint"])
        source_contract = json.loads((ROOT / self.binding["reviewed_source_contract_chain"][0]["path"]).read_bytes())
        entries = [self.binding["implementation_entrypoint"], *self.binding["reviewed_source_contract_chain"], *hundred_thirty_four(source_contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (139, 139))
        for entry in entries:
            check(self, entry)

    def test_embedded_predecessors_bundle_and_registry_are_exact(self) -> None:
        creator_contract = json.loads((ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_contract.json").read_bytes())
        self.assertEqual(list(self.module.bound_predecessor_identities()), hundred_thirty(creator_contract))

        def read_blob(blob_sha1: str) -> bytes:
            return subprocess.run(["git", "cat-file", "blob", blob_sha1], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout

        self.module.verify_bound_predecessors(read_blob)
        bundle_contract = json.loads((ROOT / "configs/harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract.json").read_bytes())
        self.assertEqual(list(self.module.BUNDLE_FILES), bundle_contract["closed_six_file_manifest"])
        reserved = self.module.canonical_registry_record(transition_index=0, state="reserved", prior_record_raw_sha256=None, creator_sha256="a" * 64, bundle_sha256=None, failure_stage=None)
        consumed = self.module.canonical_registry_record(transition_index=1, state="consumed", prior_record_raw_sha256=hashlib.sha256(reserved).hexdigest(), creator_sha256="a" * 64, bundle_sha256=None, failure_stage=None)
        success = self.module.canonical_registry_record(transition_index=2, state="bundle_creation_succeeded", prior_record_raw_sha256=hashlib.sha256(consumed).hexdigest(), creator_sha256="a" * 64, bundle_sha256="b" * 64, failure_stage=None)
        for raw, state, index in ((reserved, "reserved", 0), (consumed, "consumed", 1), (success, "bundle_creation_succeeded", 2)):
            record = json.loads(raw)
            self.assertEqual((tuple(record), record["state"], record["transition_index"]), (self.module.RECORD_FIELDS, state, index))
            prefix = {key: record[key] for key in self.module.RECORD_FIELDS[:-1]}
            expected = hashlib.sha256((json.dumps(prefix, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")).hexdigest()
            self.assertEqual(record["record_id"], expected)

        creator_sha = "a" * 64
        with self.assertRaisesRegex(PermissionError, "permanently non-reusable"):
            self.module._validate_registry_locked(io.BytesIO(reserved + consumed + success), creator_sha)

        def recanonicalize(record: dict[str, object]) -> bytes:
            prefix = {key: record[key] for key in self.module.RECORD_FIELDS[:-1]}
            record["record_id"] = hashlib.sha256((json.dumps(prefix, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")).hexdigest()
            return (json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")

        malformed = [
            b" " + reserved,
            reserved.replace(b'{"schema_version":1', b'{"schema_version":1,"schema_version":1', 1),
        ]
        wrong_type = json.loads(reserved)
        wrong_type["schema_version"] = True
        malformed.append(recanonicalize(wrong_type))
        wrong_id = json.loads(reserved)
        wrong_id["record_id"] = "0" * 64
        malformed.append((json.dumps(wrong_id, separators=(",", ":")) + "\n").encode("utf-8"))
        wrong_authority = json.loads(reserved)
        wrong_authority["creation_authority_artifact_id"] = "0" * 64
        malformed.append(recanonicalize(wrong_authority))
        bad_prior = self.module.canonical_registry_record(transition_index=1, state="consumed", prior_record_raw_sha256="0" * 64, creator_sha256=creator_sha, bundle_sha256=None, failure_stage=None)
        malformed.append(reserved + bad_prior)
        for raw in malformed:
            with self.assertRaises(PermissionError):
                self.module._validate_registry_locked(io.BytesIO(raw), creator_sha)

        for raw in (b'{"a":1, "b":2}\n', b'{"a":1,"a":2}\n', b'{"a":1}\n\n'):
            with self.assertRaises(PermissionError):
                self.module._strict_json(raw)

        class FailBeforeWrite(io.BytesIO):
            def write(self, value: bytes) -> int:
                raise OSError("synthetic pre-write failure")

        with self.assertRaises(self.module._RegistryAppendUnchangedError):
            self.module._append_fsync(FailBeforeWrite(), b"x")
        uncertain = io.BytesIO()
        with self.assertRaises(self.module._RegistryAppendOutcomeUncertainError):
            self.module._append_fsync(uncertain, b"x")
        self.assertEqual(uncertain.getvalue(), b"x")

        manifest = {
            "schema_version": True,
            "source_id": "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_IMPLEMENTATION_SOURCE_V1",
            "reviewed_creator_contract_identity": {"git_blob_sha1":"cee37fbececa8387266ba693ae915aeb8ce3ac4e","size_bytes":9920,"raw_sha256":"8decca47ec6947951fddfb8becdaa550609fa50e2c12e310d7a4476210f583da"},
            "reviewed_creator_binding_identity": {"git_blob_sha1":"b5ec9c1c65e1f15a8eff65fec7749d808c1193ae","size_bytes":3248,"raw_sha256":"54a31600aa1898d946b57bcda5330993e6740a642aec5f1a7ca35d5bb96b380c"},
            "root": str(self.module.SOURCE_ROOT),
            "entrypoint": {"path":self.module.SOURCE_ENTRYPOINT.name,"git_blob_sha1":blob(self.source_raw),"size_bytes":len(self.source_raw),"raw_sha256":hashlib.sha256(self.source_raw).hexdigest()},
        }
        manifest_raw = (json.dumps(manifest, separators=(",", ":")) + "\n").encode("utf-8")
        with self.assertRaises(PermissionError):
            self.module._validate_source_manifest(manifest_raw, self.source_raw)

    def test_dormant_fail_closed_execution_order_and_state(self) -> None:
        source = self.source_raw.decode("utf-8")
        self.assertIn('if __name__ == "__main__":', source)
        self.assertEqual(self.module.SOURCE_ROOT, Path("/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1"))
        self.assertEqual(self.module.GIT_DATABASE, Path("/Users/amcarene/midi-worker/repository/.git"))
        self.assertEqual(self.module.REGISTRY, Path("/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl"))
        execute = inspect.getsource(self.module.execute_reviewed_control_bundle_creator)
        ordered = ["_verify_source()", "_require_exact_environment()", "verify_bound_predecessors(_read_blob)", "_open_locked_registry()", "_validate_registry_locked(registry, creator_sha)", "_append_fsync(registry, reserved)", "_append_fsync(registry, consumed)", "_publish_bundle(files)", "_append_fsync(registry, success)"]
        positions = [execute.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        opened = inspect.getsource(self.module._open_locked_registry)
        for token in ("os.O_NOFOLLOW", "os.fstat(fd)", "os.stat(REGISTRY, follow_symlinks=False)", "fcntl.flock(fd, fcntl.LOCK_EX)"):
            self.assertIn(token, opened)
        self.assertIn("terminal_failure", execute)
        self.assertEqual(execute.count("_append_fsync(registry, failure)"), 3)
        self.assertNotIn("pending_consumed", execute)
        self.assertIn("_RegistryAppendOutcomeUncertainError", inspect.getsource(self.module._append_fsync))
        publish = inspect.getsource(self.module._publish_bundle)
        for token in ("os.O_EXCL", "renameatx_np", "RENAME_EXCL", "_closed_bundle_digest(STAGING_BUNDLE)", "_closed_bundle_digest(FINAL_BUNDLE)"):
            self.assertIn(token, publish)
        allowed = {"implementation_source_contract_exists", "implementation_source_contract_externally_reviewed", "implementation_source_contract_externally_sealed", "implementation_source_contract_identity_binding_exists", "implementation_source_contract_identity_binding_externally_reviewed", "implementation_source_contract_identity_binding_externally_sealed", "implementation_git_entrypoint_exists", "implementation_source_identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        for key in ("future_admin_source_published", "future_admin_source_observed", "filesystem_operation_authorized", "creator_invoked_really", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "bundle_path_observed", "administrative_control_bundle_exists", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_thirty_nine_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])


if __name__ == "__main__":
    unittest.main()
