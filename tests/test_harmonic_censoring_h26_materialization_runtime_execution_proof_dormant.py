from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h26_materialization_runtime_execution_proof as proof
from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as runtime
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as qualifier


class DormantMaterializationRuntimeExecutionProofTests(unittest.TestCase):
    def authority(self) -> dict[str, object]:
        return {
            "schema_identity": "H26_RUNTIME_QUALIFICATION_EXECUTION_AUTHORITY_V1",
            "schema_version": 1,
            "execution_authority_contract_commit": runtime.EXECUTION_AUTHORITY_CONTRACT_COMMIT,
            "execution_authority_contract_raw_sha256": runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256,
            "runtime_qualification_contract_commit": runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
            "runtime_qualification_contract_git_blob_sha": runtime.RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
            "runtime_qualification_contract_raw_sha256": runtime.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
            "qualifier_commit": runtime.APPROVED_DORMANT_QUALIFIER_COMMIT,
            "qualifier_git_blob_sha": runtime.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
            "materialization_authority_contract_commit": runtime.MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT,
            "materialization_authority_contract_git_blob_sha": runtime.MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
            "target_runtime_role": runtime.TARGET_RUNTIME_ROLE,
            "authority_id": "artificial-authority-proof-A",
            "single_use": True,
            "maximum_claims_per_authority": 1,
            "maximum_observer_invocations": 1,
            "authority_consumed_by_first_claim_creation": True,
            "retry_allowed": False,
            "execution_authorized": True,
            "issued_at": "artificial-issued-at",
            "issuer_identity": "artificial-issuer",
        }

    def claim(
        self, authority: dict[str, object], authority_sha: str
    ) -> dict[str, object]:
        authority_id = str(authority["authority_id"])
        return {
            "schema_identity": "H26_RUNTIME_QUALIFICATION_SINGLE_USE_CLAIM_V1",
            "schema_version": 1,
            "claim_id": runtime.derive_claim_id(authority_id, authority_sha),
            "authority_id": authority_id,
            "authority_raw_sha256": authority_sha,
            "execution_authority_contract_commit": authority[
                "execution_authority_contract_commit"
            ],
            "execution_authority_contract_raw_sha256": authority[
                "execution_authority_contract_raw_sha256"
            ],
            "runtime_qualification_contract_commit": runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
            "runtime_qualification_contract_git_blob_sha": runtime.RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
            "runtime_qualification_contract_raw_sha256": runtime.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
            "qualifier_commit": runtime.APPROVED_DORMANT_QUALIFIER_COMMIT,
            "qualifier_git_blob_sha": runtime.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
            "target_runtime_role": runtime.TARGET_RUNTIME_ROLE,
            "single_use": True,
            "maximum_claims_per_authority": 1,
            "maximum_observer_invocations": 1,
            "authority_consumed": True,
            "claim_consumed": True,
            "retry_allowed": False,
        }

    def evidence(
        self,
        authority: dict[str, object],
        authority_sha: str,
        claim: dict[str, object],
        claim_sha: str,
    ) -> dict[str, object]:
        return {
            "schema_identity": "H26_RUNTIME_QUALIFICATION_OBSERVER_ENTRY_EVIDENCE_V1",
            "schema_version": 1,
            "observer_entry_evidence_id": runtime.derive_observer_entry_evidence_id(
                str(authority["authority_id"]),
                authority_sha,
                str(claim["claim_id"]),
                claim_sha,
            ),
            "authority_id": authority["authority_id"],
            "authority_raw_sha256": authority_sha,
            "claim_id": claim["claim_id"],
            "claim_raw_sha256": claim_sha,
            "qualifier_commit": runtime.APPROVED_DORMANT_QUALIFIER_COMMIT,
            "qualifier_git_blob_sha": runtime.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
            "observer_entry_ordinal": 1,
        }

    def runtime_record(
        self, status: str = qualifier.STATUS_QUALIFIED
    ) -> qualifier.H26RuntimeQualificationRecord:
        contract = qualifier.load_runtime_qualification_contract()
        expected = contract.expected_runtime
        observation = qualifier.RuntimeObservation(
            runtime=expected.identity,
            process_environment=contract.process_environment_exact,
            executable=qualifier.BinaryProof(
                resolved_path="/artificial/python3.11",
                size_bytes=123456,
                sha256="1" * 64,
            ),
            numpy_multiarray=qualifier.BinaryProof(
                resolved_path="/artificial/_multiarray_umath.so",
                size_bytes=expected.numpy_multiarray_size_bytes,
                sha256=expected.numpy_multiarray_sha256,
            ),
            blas_library=qualifier.BinaryProof(
                resolved_path="/artificial/libopenblas64_.dylib",
                size_bytes=expected.blas_library_size_bytes,
                sha256=expected.blas_library_sha256,
            ),
        )
        if status == qualifier.STATUS_DISQUALIFIED:
            observation = replace(
                observation,
                runtime=replace(expected.identity, version="3.11.8"),
            )
        elif status == qualifier.STATUS_INCONCLUSIVE:
            observation = replace(observation, executable=None)
        elif status != qualifier.STATUS_QUALIFIED:
            raise ValueError("unsupported artificial status")
        return qualifier.build_runtime_qualification_record(contract, observation)

    def receipt(
        self,
        authority: dict[str, object],
        authority_sha: str,
        claim: dict[str, object],
        claim_sha: str,
        evidence: dict[str, object],
        evidence_sha: str,
        record: qualifier.H26RuntimeQualificationRecord | None,
    ) -> dict[str, object]:
        if record is None:
            record_sha = None
            terminal_status = qualifier.STATUS_INCONCLUSIVE
        else:
            raw = qualifier.serialize_runtime_qualification_record(record)
            record_sha = hashlib.sha256(raw).hexdigest()
            terminal_status = record.as_dict()["terminal_status"]
        return {
            "schema_identity": "H26_RUNTIME_QUALIFICATION_EXECUTION_RECEIPT_V1",
            "schema_version": 1,
            "claim_id": claim["claim_id"],
            "claim_raw_sha256": claim_sha,
            "authority_id": authority["authority_id"],
            "authority_raw_sha256": authority_sha,
            "qualifier_commit": runtime.APPROVED_DORMANT_QUALIFIER_COMMIT,
            "qualifier_git_blob_sha": runtime.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
            "runtime_qualification_contract_commit": runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
            "runtime_qualification_contract_raw_sha256": runtime.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
            "observer_entered": True,
            "observer_entry_evidence_id": evidence["observer_entry_evidence_id"],
            "observer_entry_evidence_raw_sha256": evidence_sha,
            "runtime_record_exists": record is not None,
            "runtime_record_raw_sha256": record_sha,
            "terminal_status": terminal_status,
            "observer_invocation_count": 1,
            "claim_consumed": True,
            "retry_allowed": False,
        }

    def chain(self, status: str = qualifier.STATUS_QUALIFIED):
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        claim_sha = runtime.canonical_artifact_raw_sha256(claim)
        evidence = self.evidence(authority, authority_sha, claim, claim_sha)
        evidence_sha = runtime.canonical_artifact_raw_sha256(evidence)
        record = self.runtime_record(status)
        receipt = self.receipt(
            authority,
            authority_sha,
            claim,
            claim_sha,
            evidence,
            evidence_sha,
            record,
        )
        receipt_sha = runtime.canonical_artifact_raw_sha256(receipt)
        return (
            authority,
            authority_sha,
            claim,
            claim_sha,
            evidence,
            evidence_sha,
            receipt,
            receipt_sha,
            record,
        )

    def validate(self, chain):
        return proof.validate_artificial_materialization_runtime_execution_proof(
            chain[0], chain[2], chain[4], chain[6],
            chain[1], chain[3], chain[5], chain[7], chain[8],
        )

    def test_exact_qualified_proof_is_accepted_and_projection_is_immutable(self) -> None:
        chain = self.chain()
        result = self.validate(chain)
        expected_record_sha = hashlib.sha256(
            qualifier.serialize_runtime_qualification_record(chain[8])
        ).hexdigest()
        self.assertEqual(
            asdict(result),
            {
                "runtime_execution_authority_id": chain[0]["authority_id"],
                "runtime_execution_authority_raw_sha256": chain[1],
                "runtime_execution_claim_id": chain[2]["claim_id"],
                "runtime_execution_claim_raw_sha256": chain[3],
                "runtime_execution_observer_entry_evidence_id": chain[4][
                    "observer_entry_evidence_id"
                ],
                "runtime_execution_observer_entry_evidence_raw_sha256": chain[5],
                "runtime_execution_receipt_raw_sha256": chain[7],
                "runtime_execution_terminal_status": qualifier.STATUS_QUALIFIED,
                "qualified_runtime_record_sha256": expected_record_sha,
            },
        )
        with self.assertRaises(FrozenInstanceError):
            result.runtime_execution_terminal_status = qualifier.STATUS_DISQUALIFIED

    def test_reuses_the_approved_terminal_receipt_validator_exactly_once(self) -> None:
        chain = self.chain()
        with mock.patch.object(
            runtime,
            "validate_artificial_terminal_execution_receipt",
            wraps=runtime.validate_artificial_terminal_execution_receipt,
        ) as terminal_validator:
            self.validate(chain)
        terminal_validator.assert_called_once()

    def test_disqualified_and_inconclusive_records_are_rejected(self) -> None:
        for status in (
            qualifier.STATUS_DISQUALIFIED,
            qualifier.STATUS_INCONCLUSIVE,
        ):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "must be QUALIFIED"):
                    self.validate(self.chain(status))

    def test_receipt_without_record_is_rejected(self) -> None:
        chain = list(self.chain())
        receipt = self.receipt(
            chain[0], chain[1], chain[2], chain[3], chain[4], chain[5], None
        )
        chain[6] = receipt
        chain[7] = runtime.canonical_artifact_raw_sha256(receipt)
        chain[8] = None
        with self.assertRaisesRegex(ValueError, "requires a runtime record"):
            self.validate(tuple(chain))

    def test_forged_receipt_and_record_sha_are_rejected(self) -> None:
        chain = list(self.chain())
        chain[7] = "0" * 64
        with self.assertRaisesRegex(ValueError, "canonical receipt bytes"):
            self.validate(tuple(chain))

        chain = list(self.chain())
        altered_receipt = dict(chain[6])
        altered_receipt["runtime_record_raw_sha256"] = "0" * 64
        chain[6] = altered_receipt
        chain[7] = runtime.canonical_artifact_raw_sha256(altered_receipt)
        with self.assertRaisesRegex(ValueError, "runtime_record_raw_sha256"):
            self.validate(tuple(chain))

    def test_forged_authority_claim_and_evidence_are_rejected(self) -> None:
        mutations = (
            (0, "authority_id", "forged-authority"),
            (2, "claim_id", "h26-runtime-claim-v1-" + "0" * 64),
            (4, "observer_entry_evidence_id", "h26-runtime-entry-v1-" + "0" * 64),
        )
        for index, field, value in mutations:
            with self.subTest(field=field):
                chain = list(self.chain())
                altered = dict(chain[index])
                altered[field] = value
                chain[index] = altered
                with self.assertRaises(ValueError):
                    self.validate(tuple(chain))

    def test_public_contract_and_blob_bindings_cannot_redirect_validation(self) -> None:
        chain = self.chain()
        cases = (
            ("MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT", "0" * 40),
            ("MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA", "0" * 40),
            ("TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA", "0" * 40),
            ("RUNTIME_QUALIFIER_GIT_BLOB_SHA", "0" * 40),
            ("VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA", "0" * 40),
        )
        for name, changed in cases:
            with self.subTest(name=name):
                original = getattr(proof, name)
                try:
                    setattr(proof, name, changed)
                    with self.assertRaisesRegex(ValueError, "binding mismatch"):
                        self.validate(chain)
                finally:
                    setattr(proof, name, original)

    def test_alternate_contract_bytes_are_rejected(self) -> None:
        source = (
            Path(proof.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_population_materialization_authority_contract.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / source.name
            altered.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                proof.load_materialization_runtime_execution_proof_contract(altered)

    def test_validation_creates_no_files_and_imports_no_materializer(self) -> None:
        materializer_module = "src.polyphonic.harmonic_censoring_h26_materializer"
        self.assertNotIn(materializer_module, sys.modules)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = tuple(root.iterdir())
            self.validate(self.chain())
            after = tuple(root.iterdir())
        self.assertEqual(before, after)
        self.assertNotIn(materializer_module, sys.modules)


if __name__ == "__main__":
    unittest.main()
