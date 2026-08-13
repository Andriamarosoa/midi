from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / "src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py"
BOUNDARY_SEAL = ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_boundary_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json"
MATERIALIZER = ROOT / "src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py"
MATERIALIZER_BINDING = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json"
MATERIALIZER_BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json"
MATERIALIZER_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json"
ACTIVATION_CONTRACT = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json"
ACTIVATION_SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json"
AUTHORITY_CONTRACT = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json"
AUTHORITY_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27IssuerAuthorityClaimCapabilityIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.boundary_seal_raw = BOUNDARY_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.boundary_seal = json.loads(cls.boundary_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_contract_files_are_canonical_lf_json_without_self_hash(self) -> None:
        for raw in (self.boundary_seal_raw, self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("seal_sha256", self.boundary_seal)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_boundary_seal_binds_exact_passed_commit_bytes(self) -> None:
        implementation = self.boundary_seal["implementation"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{self.boundary_seal['reviewed_commit']}:{implementation['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, IMPLEMENTATION.read_bytes())
        self.assertEqual(self.boundary_seal["reviewed_parent_commit"], "8812091656e2f5921f8bf51adcb0fcf1de8d7538")
        self.assertEqual(implementation["git_blob_sha1"], _blob(reviewed_raw))
        self.assertEqual(implementation["size_bytes"], len(reviewed_raw))
        self.assertEqual(implementation["raw_sha256"], hashlib.sha256(reviewed_raw).hexdigest())
        self.assertEqual(self.boundary_seal["external_review_verdict"], "PASS")

    def test_boundary_seal_preserves_all_reviewed_dependencies(self) -> None:
        for key, path in (
            ("reviewed_materializer_identity_binding", MATERIALIZER_BINDING),
            ("reviewed_materializer_identity_binding_external_seal", MATERIALIZER_BINDING_SEAL),
            ("materializer_external_review_seal", MATERIALIZER_SEAL),
            ("historical_activation_contract", ACTIVATION_CONTRACT),
            ("historical_activation_contract_external_seal", ACTIVATION_SEAL),
            ("historical_authority_contract", AUTHORITY_CONTRACT),
            ("historical_authority_contract_external_seal", AUTHORITY_SEAL),
        ):
            _assert_binding(self, self.boundary_seal[key], path)

    def test_identity_binding_is_exact_and_acyclic(self) -> None:
        _assert_binding(self, self.binding["boundary_external_review_seal"], BOUNDARY_SEAL)
        for field in ("path", "git_blob_sha1", "size_bytes", "raw_sha256"):
            self.assertEqual(self.binding["reviewed_boundary"][field], self.boundary_seal["implementation"][field])
        for field in ("reviewed_commit", "reviewed_parent_commit"):
            self.assertEqual(self.binding["reviewed_boundary"][field], self.boundary_seal[field])
        for key, path in (
            ("materializer_identity_binding", MATERIALIZER_BINDING),
            ("materializer_identity_binding_external_seal", MATERIALIZER_BINDING_SEAL),
            ("materializer_external_review_seal", MATERIALIZER_SEAL),
            ("historical_activation_contract", ACTIVATION_CONTRACT),
            ("historical_activation_contract_external_seal", ACTIVATION_SEAL),
            ("historical_authority_contract", AUTHORITY_CONTRACT),
            ("historical_authority_contract_external_seal", AUTHORITY_SEAL),
        ):
            _assert_binding(self, self.binding[key], path)
            self.assertTrue(self.binding[key]["remains_byte_identical"])
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertTrue(graph["does_not_modify_or_back_reference_from_historical_contracts"])
        self.assertFalse(any(BINDING.name in edge for edge in graph["edges"]))

    def test_binding_seal_binds_contract_boundary_and_reviewed_chain(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["boundary_external_review_seal"], BOUNDARY_SEAL)
        _assert_binding(self, self.binding_seal["materializer_identity_binding"], MATERIALIZER_BINDING)
        _assert_binding(self, self.binding_seal["materializer_identity_binding_external_seal"], MATERIALIZER_BINDING_SEAL)
        for field in ("path", "reviewed_commit", "reviewed_parent_commit", "git_blob_sha1", "size_bytes", "raw_sha256"):
            self.assertEqual(self.binding_seal["reviewed_boundary"][field], self.binding["reviewed_boundary"][field])

    def test_historical_materializer_and_contracts_remain_byte_identical(self) -> None:
        materializer_binding = json.loads(MATERIALIZER_BINDING.read_bytes())
        _assert_binding(self, materializer_binding["materializer_external_review_seal"], MATERIALIZER_SEAL)
        reviewed = materializer_binding["reviewed_materializer"]
        _assert_binding(self, reviewed, MATERIALIZER)
        for path in (ACTIVATION_CONTRACT, ACTIVATION_SEAL, AUTHORITY_CONTRACT, AUTHORITY_SEAL):
            self.assertTrue(path.is_file())

    def test_public_edge_remains_exact_native_empty_tuple_barrier(self) -> None:
        edge = boundary.issue_h27_materialization_authority_and_capability
        self.assertIs(type(edge), type(().__getitem__))
        self.assertEqual(edge.__self__, ())
        self.assertEqual(edge.__name__, "__getitem__")

    def test_all_operational_and_scientific_states_remain_false(self) -> None:
        for field, value in self.boundary_seal.items():
            if field.endswith("_exists") or field.endswith("_authorized") or field in {
                "public_operational_edge_open",
                "locked_test_used",
            }:
                self.assertIs(value, False, field)
        state = self.binding["current_state"]
        for field, value in state.items():
            if field in {
                "reviewed_boundary_exists",
                "reviewed_boundary_externally_reviewed",
                "reviewed_boundary_externally_sealed",
            }:
                self.assertIs(value, True, field)
            else:
                self.assertIs(value, False, field)
        for field, value in self.binding_seal["seal_semantics"].items():
            if field in {
                "identity_binding_only",
                "dependency_graph_acyclic",
                "historical_contracts_remain_byte_identical",
                "materializer_remains_byte_identical",
                "issuer_boundary_remains_byte_identical",
            }:
                self.assertIs(value, True, field)
            else:
                self.assertIs(value, False, field)


if __name__ == "__main__":
    unittest.main()
