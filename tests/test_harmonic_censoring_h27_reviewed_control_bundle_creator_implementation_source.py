from __future__ import annotations

import hashlib
import importlib.util
import inspect
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

    def test_dormant_fail_closed_execution_order_and_state(self) -> None:
        source = self.source_raw.decode("utf-8")
        self.assertIn('if __name__ == "__main__":', source)
        self.assertEqual(self.module.SOURCE_ROOT, Path("/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1"))
        self.assertEqual(self.module.GIT_DATABASE, Path("/Users/amcarene/midi-worker/repository/.git"))
        self.assertEqual(self.module.REGISTRY, Path("/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl"))
        execute = inspect.getsource(self.module.execute_reviewed_control_bundle_creator)
        ordered = ["_verify_source()", "_require_exact_environment()", "verify_bound_predecessors(_read_blob)", "_validate_registry_locked(registry)", "_append_fsync(registry, reserved)", "_append_fsync(registry, pending_consumed)", "_publish_bundle(files)", "_append_fsync(registry, success)"]
        positions = [execute.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("fcntl.flock(registry.fileno(), fcntl.LOCK_EX)", execute)
        self.assertIn("terminal_failure", execute)
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
