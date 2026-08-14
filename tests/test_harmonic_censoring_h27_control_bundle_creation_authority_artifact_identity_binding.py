from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract_identity_binding import hundred_twenty_four

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


def hundred_twenty_six(contract_binding: dict[str, object]) -> list[dict[str, object]]:
    contract = json.loads((ROOT / contract_binding["reviewed_contract"]["path"]).read_bytes())
    return [contract_binding["reviewed_contract"], contract_binding["contract_external_seal"], *hundred_twenty_four(contract)]


class TestAuthorityArtifactIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_128_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        artifact_seal = json.loads((ROOT / self.binding["artifact_external_seal"]["path"]).read_bytes())
        contract_binding = json.loads((ROOT / artifact_seal["reviewed_contract_binding"]["path"]).read_bytes())
        entries = [self.binding["reviewed_artifact"], self.binding["artifact_external_seal"], *hundred_twenty_six(contract_binding)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (128, 128))
        for entry in entries:
            check(self, entry)

    def test_preserved_exact_artifact_state_and_edges(self) -> None:
        artifact = json.loads((ROOT / self.binding["reviewed_artifact"]["path"]).read_bytes())
        preserved = self.binding["preserved_artifact"]
        self.assertEqual(preserved, {
            "exact_top_level_field_count": 8,
            "artifact_type": artifact["artifact_type"],
            "creation_authority_artifact_id": artifact["creation_authority_artifact_id"],
            "expected_execution_git_head": artifact["expected_execution_git_head"],
            "canonical_identifier_recomputed": True,
            "authorization_chain_six_exact_values": True,
            "bundle_definition_three_exact_values": True,
            "single_use": True,
            "consumed": False,
        })
        payload = {key: value for key, value in artifact.items() if key != "creation_authority_artifact_id"}
        canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), preserved["creation_authority_artifact_id"])
        self.assertEqual(self.binding["preserved_authorization_chain_identity"], artifact["authorization_chain_identity"])
        self.assertEqual(self.binding["preserved_bundle_definition_identity"], artifact["bundle_definition_identity"])
        self.assertEqual(list(self.binding["preserved_guards"]), ["authority_still_unconsumed", "bundle_creation_or_observation_forbidden", "filesystem_operation_forbidden", "persistent_registry_open_forbidden", "identity_nonce_reservation_forbidden", "constructor_invocation_forbidden", "post_consumption_failure_terminal", "retry_after_consumption_forbidden"])
        self.assertTrue(all(self.binding["preserved_guards"].values()))
        allowed = {"authority_artifact_exists", "authority_artifact_externally_reviewed", "authority_artifact_externally_sealed", "authority_artifact_identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_twenty_eight_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual((self.seal["bound_identity_count"], self.seal["creation_authority_artifact_id"], self.seal["expected_execution_git_head"], self.seal["public_edges_closed"]), (128, artifact["creation_authority_artifact_id"], artifact["expected_execution_git_head"], 8))
        self.assertIs(self.seal["single_use"], True)
        self.assertIs(self.seal["consumed"], False)
        for key in ("administrative_control_bundle_exists", "bundle_path_observed", "filesystem_operation_authorized", "persistent_registry_opened", "identity_nonce_reserved", "constructor_invoked_really", "destination_observed", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_no_backrefs(self) -> None:
        artifact_seal = json.loads((ROOT / self.binding["artifact_external_seal"]["path"]).read_bytes())
        contract_binding = json.loads((ROOT / artifact_seal["reviewed_contract_binding"]["path"]).read_bytes())
        for entry in [self.binding["reviewed_artifact"], self.binding["artifact_external_seal"], *hundred_twenty_six(contract_binding)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
