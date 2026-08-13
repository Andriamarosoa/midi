from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as artifact
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as bridge
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as gate
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as composition


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract.json"
CONTRACT_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_external_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_identity_binding_external_seal.json"
UPSTREAM_BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_identity_binding.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27RealPublicationContractIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = BINDING_SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.upstream = json.loads(UPSTREAM_BINDING.read_bytes())

    def test_binding_and_seal_are_canonical_without_self_hash(self) -> None:
        for raw in (self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.seal)

    def test_reviewed_contract_is_exact_pass_commit_and_seal_is_exact(self) -> None:
        reviewed = self.binding["reviewed_contract"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, CONTRACT.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "1115d5cc841e41a3ecd51620f3122117c270b6ad")
        self.assertEqual(reviewed["reviewed_parent_commit"], "2f8562d23a1b167bf9cd22db3d347f2d4238e661")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, reviewed, CONTRACT)
        _assert_binding(self, self.binding["contract_external_seal"], CONTRACT_SEAL)

    def test_all_fifty_four_bound_identities_are_unique_and_exact(self) -> None:
        roots = [self.binding["reviewed_contract"], self.binding["contract_external_seal"]]
        simulator = self.binding["reviewed_and_sealed_dormant_publication_simulator"]
        upstream = self.upstream["upstream_entries"]
        entries = roots + simulator + upstream
        self.assertEqual(len(roots), 2)
        self.assertEqual(len(simulator), 4)
        self.assertEqual(len(upstream), 48)
        self.assertEqual(len(entries), 54)
        self.assertEqual(len({item["path"] for item in entries}), 54)
        names = ["reviewed_contract", "contract_external_seal"] + [item["name"] for item in simulator + upstream]
        self.assertEqual(len(set(names)), 54)
        for item in entries:
            _assert_binding(self, item, ROOT / item["path"])
        self.assertEqual(self.binding["bound_identity_counts"]["combined_unique_identity_count"], 54)

    def test_binding_seal_binds_exact_binding_contract_and_contract_seal(self) -> None:
        _assert_binding(self, self.seal["identity_binding"], BINDING)
        self.assertEqual(self.seal["reviewed_contract"], self.binding["reviewed_contract"])
        self.assertEqual(self.seal["contract_external_seal"], self.binding["contract_external_seal"])
        _assert_binding(self, self.seal["reviewed_contract"], CONTRACT)
        _assert_binding(self, self.seal["contract_external_seal"], CONTRACT_SEAL)

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_fifty_four_bound_identities_remain_byte_identical"])
        roots = [self.binding["reviewed_contract"], self.binding["contract_external_seal"]]
        entries = roots + self.binding["reviewed_and_sealed_dormant_publication_simulator"] + self.upstream["upstream_entries"]
        for item in entries:
            raw = (ROOT / item["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(BINDING_SEAL.name.encode("ascii"), raw)

    def test_only_reviewed_contract_and_new_binding_administrative_states_are_true(self) -> None:
        allowed = {
            "real_publication_contract_exists",
            "real_publication_contract_externally_reviewed",
            "real_publication_contract_externally_sealed",
            "real_publication_contract_identity_binding_exists",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.seal["seal_semantics"]
        permitted_true = {
            "administrative_identity_binding_only", "dependency_graph_acyclic",
            "all_fifty_four_bound_identities_remain_byte_identical",
            *allowed,
        }
        for field, value in semantics.items():
            if field in {"self_hash_present", "historical_back_reference_present"}:
                self.assertIs(value, False, field)
            else:
                self.assertIs(value, field in permitted_true, field)

    def test_all_seven_public_edges_remain_native_closed_barriers(self) -> None:
        for edge in (
            composition.execute_h27_one_shot_composition,
            bridge.invoke_h27_future_bridge,
            gate.activate_and_connect_h27_future_bridge,
            artifact.construct_h27_future_bridge_activation_artifact,
            publication.simulate_h27_future_bridge_activation_artifact_publication,
            boundary.issue_h27_materialization_authority_and_capability,
            materializer.materialize_h27_activation_capable_production_population,
        ):
            self.assertIs(type(edge), type(().__getitem__))
            self.assertEqual(edge.__self__, ())
            self.assertEqual(edge.__name__, "__getitem__")


if __name__ == "__main__":
    unittest.main()
