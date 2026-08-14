from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_external_seal.json"
CONTRACT = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


class TestControlBundleCreationAuthorityArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = ARTIFACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.artifact = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.contract = json.loads(CONTRACT.read_bytes())

    def test_exact_artifact_seal_and_reviewed_binding(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.raw, json.dumps(self.artifact, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n")
        check(self, self.seal["authority_artifact"])
        check(self, self.seal["reviewed_contract_binding"])
        check(self, self.seal["contract_binding_external_seal"])
        self.assertEqual(self.seal["reviewed_contract_binding"]["reviewed_commit"], "7ee0a8977208bfa389e284b07207abc40a3517fd")
        self.assertEqual(self.seal["reviewed_contract_binding"]["external_review_verdict"], "PASS")

    def test_closed_schema_and_canonical_identifier(self) -> None:
        order = self.contract["future_artifact_canonical_top_level_order"]
        self.assertEqual(list(self.artifact), order)
        schema = self.contract["future_artifact_schema"]
        self.assertIs(type(self.artifact["schema_version"]), int)
        self.assertEqual(self.artifact["schema_version"], schema["schema_version"]["exact_value"])
        self.assertEqual(self.artifact["artifact_type"], schema["artifact_type"]["exact_value"])
        self.assertRegex(self.artifact["creation_authority_artifact_id"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.artifact["expected_execution_git_head"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.artifact["expected_execution_git_head"], "7ee0a8977208bfa389e284b07207abc40a3517fd")
        self.assertEqual(self.artifact["authorization_chain_identity"], schema["authorization_chain_identity"]["exact_values"])
        bundle = schema["bundle_definition_identity"]
        self.assertEqual(self.artifact["bundle_definition_identity"], {
            "final_bundle_root": bundle["final_bundle_root_exact"],
            "closed_manifest_file_count": bundle["closed_manifest_file_count_exact"],
            "source_git_object_database": bundle["source_git_object_database_exact"],
        })
        self.assertIs(self.artifact["single_use"], True)
        self.assertIs(self.artifact["consumed"], False)
        payload = {key: value for key, value in self.artifact.items() if key != "creation_authority_artifact_id"}
        self.assertEqual(list(payload), schema["creation_authority_artifact_id"]["canonical_payload_field_order_after_omitting_creation_authority_artifact_id"])
        canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), self.artifact["creation_authority_artifact_id"])
        self.assertEqual((self.seal["creation_authority_artifact_id"], self.seal["expected_execution_git_head"]), (self.artifact["creation_authority_artifact_id"], self.artifact["expected_execution_git_head"]))

    def test_unconsumed_state_and_no_backrefs(self) -> None:
        self.assertIs(self.seal["single_use"], True)
        self.assertIs(self.seal["consumed"], False)
        self.assertIs(self.seal["authority_artifact_exists"], True)
        for key in ("authority_artifact_externally_reviewed", "authority_artifact_externally_sealed", "administrative_control_bundle_exists", "bundle_path_observed", "filesystem_operation_authorized", "persistent_registry_opened", "identity_nonce_reserved", "constructor_invoked_really", "destination_observed", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)
        self.assertEqual(self.seal["public_edges_closed"], 8)
        for identity in (self.seal["reviewed_contract_binding"], self.seal["contract_binding_external_seal"]):
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertNotIn(ARTIFACT.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
