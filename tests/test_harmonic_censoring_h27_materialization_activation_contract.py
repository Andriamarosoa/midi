from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic.harmonic_censoring_h27_scientific_capability_dormant import (
    H27_SEALED_RECORD_BINDING_FIELDS,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json"
ENGINE_CONTRACT = ROOT / "configs/harmonic_censoring_h27_engine_recomputer_contract.json"


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class H27MaterializationActivationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_raw = CONTRACT.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.contract = json.loads(cls.contract_raw.decode("utf-8"))
        cls.seal = json.loads(cls.seal_raw.decode("utf-8"))

    def test_contract_and_seal_are_strict_lf_json_without_self_reference(self) -> None:
        for raw in (self.contract_raw, self.seal_raw):
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", raw)
        self.assertNotIn("external_seal_sha256", self.contract)
        self.assertNotIn("seal_sha256", self.seal)
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(self.seal["schema_version"], 1)

    def test_external_seal_binds_exact_contract_bytes(self) -> None:
        binding = self.seal["contract"]
        self.assertEqual(binding["path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(binding["size_bytes"], len(self.contract_raw))
        self.assertEqual(binding["raw_sha256"], hashlib.sha256(self.contract_raw).hexdigest())
        self.assertEqual(binding["git_blob_sha1"], _git_blob_sha1(self.contract_raw))

    def test_dormant_reference_and_five_h27_inputs_are_bound_to_reviewed_parent(self) -> None:
        parent = self.contract["reviewed_parent_commit"]
        reference = self.contract["dormant_reviewed_reference"]
        raw = (ROOT / reference["path"]).read_bytes()
        self.assertEqual(reference["git_blob_sha1"], _git_blob_sha1(raw))
        self.assertEqual(reference["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.seal["dormant_reviewed_reference"]["git_blob_sha1"], _git_blob_sha1(raw))
        self.assertFalse(reference["future_activation_execution_target"])
        self.assertTrue(reference["must_remain_unissuable"])
        for binding in self.contract["sealed_h27_inputs"].values():
            payload = (ROOT / binding["path"]).read_bytes()
            self.assertEqual(binding["git_blob_sha1"], _git_blob_sha1(payload))
            self.assertEqual(binding["raw_sha256"], hashlib.sha256(payload).hexdigest())
            reviewed = subprocess.check_output(
                ["git", "rev-parse", f"{parent}:{binding['path']}"],
                cwd=ROOT, text=True, encoding="utf-8",
            ).strip()
            self.assertEqual(reviewed, binding["git_blob_sha1"])

    def test_runtime_is_exact_primary_profile_from_sealed_source(self) -> None:
        source_raw = ENGINE_CONTRACT.read_bytes()
        source = json.loads(source_raw.decode("utf-8"))
        binding = self.contract["sealed_runtime_source"]
        self.assertEqual(binding["git_blob_sha1"], _git_blob_sha1(source_raw))
        self.assertEqual(binding["raw_sha256"], hashlib.sha256(source_raw).hexdigest())
        self.assertEqual(self.contract["runtime_exact"], source["runtime_contract"]["primary"])
        self.assertEqual(
            self.contract["process_environment_exact"],
            source["runtime_contract"]["process_environment_exact"],
        )
        self.assertTrue(source["runtime_contract"]["future_runtime_qualification_required"])

    def test_activation_authority_claim_and_execution_remain_absent(self) -> None:
        self.assertFalse(self.contract["future_activation"]["activation_exists"])
        self.assertFalse(self.contract["future_materialization_authority"]["authority_exists"])
        state = self.contract["current_state"]
        self.assertTrue(state["external_seal_exists"])
        for field, value in state.items():
            if field != "external_seal_exists":
                self.assertIs(value, False, field)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["contract_and_external_seal_creation_authorized"])
        for field, value in authorization.items():
            if field != "contract_and_external_seal_creation_authorized":
                self.assertIs(value, False, field)
        for field in (
            "activation_exists", "authority_exists", "capability_exists", "claim_exists",
            "materialization_authorized", "population_exists", "population_index_exists",
            "scientific_execution_authorized", "locked_test_used",
            "training_or_calibration_authorized",
        ):
            self.assertIs(self.seal[field], False, field)
        for field in (
            "future_production_materializer_exists",
            "future_production_materializer_implementation_authorized",
            "future_production_materializer_seal_exists",
        ):
            self.assertIs(self.seal[field], False, field)

    def test_future_production_materializer_is_absent_and_blocks_issuance(self) -> None:
        future = self.contract["future_production_materializer"]
        self.assertFalse(future["exists"])
        self.assertFalse(future["implementation_authorized"])
        for field in (
            "path", "reviewed_commit", "git_blob_sha1", "raw_sha256",
            "external_seal_path", "external_seal_sha256",
        ):
            self.assertIsNone(future[field])
        self.assertTrue(future["must_be_separately_implemented_reviewed_and_sealed"])
        authority = self.contract["future_materialization_authority"]
        self.assertTrue(authority["issuance_must_fail_before_claim_if_future_production_materializer_or_its_seal_is_absent"])
        self.assertTrue(authority["dormant_reviewed_reference_must_never_be_invoked_by_activation"])

    def test_one_shot_and_atomic_publication_contract_is_closed(self) -> None:
        implementation = self.contract["future_production_materializer"]
        authority = self.contract["future_materialization_authority"]
        publication = self.contract["atomic_publication"]
        self.assertEqual(implementation["invocations_maximum"], 1)
        self.assertFalse(implementation["retry_allowed"])
        self.assertTrue(authority["claim_create_exclusive_before_numpy_or_first_scientific_allocation"])
        self.assertTrue(authority["claim_persists_after_success_failure_interrupt_or_timeout"])
        self.assertTrue(authority["retry_after_claim_forbidden"])
        self.assertEqual(publication["expected_record_count"], 124)
        self.assertEqual(publication["expected_baseline_record_count"], 17)
        self.assertEqual(publication["expected_p2_record_count"], 107)
        for field in (
            "preexisting_staging_or_final_is_terminal_failure", "staging_create_exclusive",
            "payload_files_written_before_index", "each_payload_size_and_sha256_verified_before_index",
            "population_index_written_last_inside_staging", "population_index_fsync_before_publish",
            "staging_tree_rehashed_against_index_before_publish", "atomic_no_replace_rename_to_final",
            "final_parent_directory_fsync", "partial_staging_never_authoritative",
            "delete_overwrite_or_retry_forbidden",
        ):
            self.assertTrue(publication[field], field)

    def test_population_index_is_the_only_future_source_of_record_binding(self) -> None:
        index = self.contract["population_index_record_contract"]
        derivation = self.contract["future_sealed_record_binding_derivation"]
        self.assertEqual(tuple(derivation["binding_field_order"]), H27_SEALED_RECORD_BINDING_FIELDS)
        self.assertEqual(derivation["only_input_selector"], "record_identity")
        self.assertTrue(derivation["load_and_hash_population_index_once_before_lookup"])
        self.assertTrue(derivation["verify_index_sha256_against_future_authority"])
        self.assertTrue(derivation["derive_all_binding_fields_from_verified_index_row_and_fixed_population_root"])
        self.assertTrue(derivation["caller_override_of_any_binding_field_forbidden"])
        self.assertFalse(derivation["binding_loader_exists"])
        self.assertTrue(derivation["engine_and_recomputer_guards_remain_unconditional"])
        self.assertTrue(index["record_identity_order_must_equal_canonical_h27_record_identities"])
        self.assertTrue(index["unknown_or_additional_fields_forbidden"])


if __name__ == "__main__":
    unittest.main()
