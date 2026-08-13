from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / "src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py"
MATERIALIZER_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json"
BINDING = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json"
BINDING_SEAL = ROOT / "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json"
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


class H27ActivationCapableMaterializerIdentityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.materializer_seal_raw = MATERIALIZER_SEAL.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.binding_seal_raw = BINDING_SEAL.read_bytes()
        cls.materializer_seal = json.loads(cls.materializer_seal_raw)
        cls.binding = json.loads(cls.binding_raw)
        cls.binding_seal = json.loads(cls.binding_seal_raw)

    def test_all_contract_files_are_canonical_lf_json_without_self_hash(self) -> None:
        for raw in (self.materializer_seal_raw, self.binding_raw, self.binding_seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
            json.loads(raw)
        self.assertNotIn("seal_sha256", self.materializer_seal)
        self.assertNotIn("seal_sha256", self.binding_seal)

    def test_materializer_seal_binds_exact_reviewed_commit_bytes(self) -> None:
        implementation = self.materializer_seal["implementation"]
        reviewed_raw = subprocess.run(
            ["git", "show", f"{self.materializer_seal['reviewed_commit']}:{implementation['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(reviewed_raw, IMPLEMENTATION.read_bytes())
        self.assertEqual(implementation["git_blob_sha1"], _blob(reviewed_raw))
        self.assertEqual(implementation["size_bytes"], len(reviewed_raw))
        self.assertEqual(implementation["raw_sha256"], hashlib.sha256(reviewed_raw).hexdigest())
        self.assertEqual(self.materializer_seal["external_review_verdict"], "PASS")

    def test_materializer_seal_preserves_exact_historical_bindings(self) -> None:
        for key, path in (
            ("prior_activation_contract", ACTIVATION_CONTRACT),
            ("prior_activation_contract_external_seal", ACTIVATION_SEAL),
            ("prior_authority_contract", AUTHORITY_CONTRACT),
            ("prior_authority_contract_external_seal", AUTHORITY_SEAL),
        ):
            _assert_binding(self, self.materializer_seal[key], path)

    def test_identity_binding_binds_seal_and_historical_contracts_exactly(self) -> None:
        _assert_binding(self, self.binding["materializer_external_review_seal"], MATERIALIZER_SEAL)
        for key, path in (
            ("historical_activation_contract", ACTIVATION_CONTRACT),
            ("historical_activation_contract_external_seal", ACTIVATION_SEAL),
            ("historical_authority_contract", AUTHORITY_CONTRACT),
            ("historical_authority_contract_external_seal", AUTHORITY_SEAL),
        ):
            _assert_binding(self, self.binding[key], path)
            self.assertTrue(self.binding[key]["remains_byte_identical"])

    def test_overlay_only_rebinds_reviewed_materializer_identity(self) -> None:
        historical = json.loads(AUTHORITY_CONTRACT.read_bytes())["future_activation_capable_materializer"]
        overlay = self.binding["normative_overlay"]
        replacements = overlay["replacements"]
        self.assertFalse(historical["exists"])
        self.assertIsNone(historical["path"])
        self.assertTrue(replacements["exists"])
        self.assertFalse(replacements["implementation_authorized"])
        self.assertEqual(replacements["path"], self.binding["reviewed_materializer"]["path"])
        self.assertEqual(replacements["git_blob_sha1"], self.binding["reviewed_materializer"]["git_blob_sha1"])
        self.assertEqual(replacements["external_seal_sha256"], hashlib.sha256(self.materializer_seal_raw).hexdigest())
        self.assertEqual(overlay["supplements_only"], "historical_authority_contract.future_activation_capable_materializer")
        self.assertTrue(overlay["all_other_historical_activation_authority_runtime_input_count_destination_one_shot_and_scientific_semantics_inherited_unchanged"])
        self.assertTrue(overlay["does_not_patch_or_activate_reviewed_module_constants"])

    def test_binding_seal_binds_exact_contract_and_reviewed_identity(self) -> None:
        _assert_binding(self, self.binding_seal["identity_binding"], BINDING)
        _assert_binding(self, self.binding_seal["materializer_external_review_seal"], MATERIALIZER_SEAL)
        for field in ("path", "reviewed_commit", "git_blob_sha1", "size_bytes", "raw_sha256"):
            self.assertEqual(self.binding_seal["reviewed_materializer"][field], self.binding["reviewed_materializer"][field])

    def test_every_operational_or_scientific_state_remains_false(self) -> None:
        state = self.binding["current_state"]
        self.assertTrue(state["reviewed_materializer_exists"])
        self.assertTrue(state["reviewed_materializer_externally_reviewed"])
        self.assertTrue(state["reviewed_materializer_externally_sealed"])
        for field, value in state.items():
            if field not in {
                "reviewed_materializer_exists",
                "reviewed_materializer_externally_reviewed",
                "reviewed_materializer_externally_sealed",
            }:
                self.assertIs(value, False, field)
        for field, value in self.binding_seal["seal_semantics"].items():
            if field.endswith("_exists") or field.endswith("_authorized") or field in {"materialization_authorized", "scientific_execution_authorized", "locked_test_used"}:
                self.assertIs(value, False, field)

    def test_reviewed_module_remains_dormant_and_unpatched(self) -> None:
        source = IMPLEMENTATION.read_text(encoding="utf-8")
        self.assertIn("FUTURE_MATERIALIZER_REVIEWED_BLOB: str | None = None", source)
        self.assertIn("FUTURE_MATERIALIZER_EXTERNAL_SEAL_SHA256: str | None = None", source)
        self.assertIn("FUTURE_MATERIALIZER_EXTERNAL_SEAL_PATH: Path | None = None", source)
        self.assertIn("materialize_h27_activation_capable_production_population = _DORMANT_NATIVE_BARRIER", source)


if __name__ == "__main__":
    unittest.main()
