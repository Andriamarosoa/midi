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
MODULE = ROOT / "src/polyphonic/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant.py"
MODULE_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_identity_binding_external_seal.json"


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _assert_binding(test: unittest.TestCase, binding: dict[str, object], path: Path) -> None:
    raw = path.read_bytes()
    test.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
    test.assertEqual(binding["git_blob_sha1"], _blob(raw))
    test.assertEqual(binding["size_bytes"], len(raw))
    test.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())


class H27PublicationDormantIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module_seal_raw = MODULE_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.module_seal = json.loads(cls.module_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_new_artifacts_are_canonical_without_self_hash(self) -> None:
        for raw in (self.module_seal_raw, self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("seal_sha256", self.module_seal)
        self.assertNotIn("binding_sha256", self.binding)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_module_seal_and_binding_use_exact_pass_module_bytes(self) -> None:
        reviewed = self.binding["reviewed_dormant_publication_module"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{reviewed['reviewed_commit']}:{reviewed['path']}"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, MODULE.read_bytes())
        self.assertEqual(reviewed["reviewed_commit"], "6ad0232d460819962a89dc1f307b59f7d13b8f6c")
        self.assertEqual(reviewed["reviewed_parent_commit"], "84c46f1f834efd4a4fed579dd9f5dbd696d24135")
        self.assertEqual(reviewed["external_review_verdict"], "PASS")
        _assert_binding(self, self.module_seal["implementation"], MODULE)
        _assert_binding(self, reviewed, MODULE)
        _assert_binding(self, self.binding["dormant_publication_module_external_review_seal"], MODULE_SEAL)

    def test_all_forty_eight_upstream_entries_are_unique_and_exact(self) -> None:
        entries = self.binding["upstream_entries"]
        self.assertEqual(len(entries), 48)
        self.assertEqual(len({item["path"] for item in entries}), 48)
        self.assertEqual(len({item["name"] for item in entries}), 48)
        for item in entries:
            _assert_binding(self, item, ROOT / item["path"])

    def test_binding_seal_binds_exact_binding_module_and_module_seal(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        for key in (
            "reviewed_dormant_publication_module",
            "dormant_publication_module_external_review_seal",
        ):
            self.assertEqual(self.binding_seal[key], self.binding[key])
            _assert_binding(self, self.binding_seal[key], ROOT / self.binding_seal[key]["path"])

    def test_graph_is_acyclic_without_self_hash_or_back_reference(self) -> None:
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"])
        self.assertFalse(graph["self_hash_present"])
        self.assertFalse(graph["historical_back_reference_present"])
        self.assertTrue(graph["all_edges_point_to_preexisting_reviewed_or_sealed_artifacts"])
        self.assertTrue(graph["all_forty_eight_upstream_entries_remain_byte_identical"])
        new_names = {MODULE_SEAL.name, BINDING.name, BINDING_SEAL.name}
        for item in self.binding["upstream_entries"]:
            raw = (ROOT / item["path"]).read_bytes()
            for name in new_names:
                self.assertNotIn(name.encode("ascii"), raw)

    def test_only_reviewed_module_administrative_states_are_true(self) -> None:
        allowed = {
            "dormant_publication_module_exists",
            "dormant_publication_module_externally_reviewed",
            "dormant_publication_module_externally_sealed",
        }
        for field, value in self.binding["current_state"].items():
            self.assertIs(value, field in allowed, field)
        semantics = self.binding_seal["seal_semantics"]
        for field in allowed:
            self.assertIs(semantics[field], True, field)
        for field, value in semantics.items():
            if field not in allowed and field not in {
                "administrative_identity_binding_only",
                "dependency_graph_acyclic",
                "all_forty_eight_upstream_entries_remain_byte_identical",
            }:
                self.assertIs(value, False, field)

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

    def test_no_new_artifact_opens_filesystem_or_science(self) -> None:
        joined = b"\n".join((self.module_seal_raw, self.binding_raw, self.binding_seal_raw))
        for forbidden in (b'"publication_implementation_exists": true', b'"artifact_created": true', b'"locked_test_used": true'):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
