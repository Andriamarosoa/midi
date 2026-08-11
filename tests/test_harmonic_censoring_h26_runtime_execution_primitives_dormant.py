from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest

from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as runtime
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as qualifier


class CanonicalJsonTests(unittest.TestCase):
    def test_quote_backslash_and_literal_solidus(self) -> None:
        self.assertEqual(
            runtime.canonical_json_bytes('"\\/'),
            b'"\\"\\\\/"\n',
        )

    def test_five_short_escapes_are_required(self) -> None:
        self.assertEqual(
            runtime.canonical_json_bytes("\b\t\n\f\r"),
            b'"\\b\\t\\n\\f\\r"\n',
        )

    def test_other_controls_use_lowercase_unicode_escape(self) -> None:
        self.assertEqual(
            runtime.canonical_json_bytes("\x00\x01\x1f"),
            b'"\\u0000\\u0001\\u001f"\n',
        )

    def test_printable_ascii_is_literal(self) -> None:
        self.assertEqual(runtime.canonical_json_bytes("Az 09~"), b'"Az 09~"\n')

    def test_bmp_and_supplementary_scalars(self) -> None:
        self.assertEqual(runtime.canonical_json_bytes("é"), b'"\\u00e9"\n')
        self.assertEqual(
            runtime.canonical_json_bytes("😀"),
            b'"\\ud83d\\ude00"\n',
        )

    def test_lone_surrogates_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "surrogate"):
            runtime.canonical_json_bytes("\ud800")
        with self.assertRaisesRegex(ValueError, "surrogate"):
            runtime.parse_canonical_json_bytes(b'"\\ud800"\n')

    def test_round_trip_and_logical_key_order(self) -> None:
        value = {"é": [None, True, -2], "z": "last", "a": "first"}
        raw = runtime.canonical_json_bytes(value)
        self.assertEqual(
            raw,
            b'{"a":"first","z":"last","\\u00e9":[null,true,-2]}\n',
        )
        self.assertEqual(runtime.parse_canonical_json_bytes(raw), value)

    def test_noncanonical_escape_spellings_are_rejected(self) -> None:
        invalid = (
            b'"\\/"\n',
            b'"\\u0041"\n',
            b'"\\u00E9"\n',
            b'"\\u0008"\n',
            b'"\\uD83D\\uDE00"\n',
        )
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "not canonical"):
                    runtime.parse_canonical_json_bytes(raw)

    def test_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runtime.parse_canonical_json_bytes(b'{"a":1,"a":2}\n')

    def test_floats_and_nonfinite_constants_are_rejected(self) -> None:
        for value in (1.0, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "floating"):
                    runtime.canonical_json_bytes(value)
        for raw in (b"1.0\n", b"1e2\n", b"NaN\n", b"Infinity\n"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "floating"):
                    runtime.parse_canonical_json_bytes(raw)

    def test_wrong_order_and_whitespace_are_rejected(self) -> None:
        for raw in (
            b'{"b":1,"a":2}\n',
            b'{"a": 1}\n',
            b' {"a":1}\n',
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "not canonical"):
                    runtime.parse_canonical_json_bytes(raw)

    def test_terminal_newline_and_crlf_are_exact(self) -> None:
        for raw in (b"{}", b"{}\n\n", b"{}\r\n"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    runtime.parse_canonical_json_bytes(raw)

    def test_bom_and_non_ascii_raw_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOM"):
            runtime.parse_canonical_json_bytes(b"\xef\xbb\xbf{}\n")
        with self.assertRaisesRegex(ValueError, "ASCII-safe"):
            runtime.parse_canonical_json_bytes('"é"\n'.encode("utf-8"))

    def test_cycles_and_unsupported_types_are_rejected(self) -> None:
        value: list[object] = []
        value.append(value)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            runtime.canonical_json_bytes(value)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            runtime.canonical_json_bytes({1, 2})
        with self.assertRaisesRegex(ValueError, "unsupported"):
            runtime.canonical_json_bytes((1, 2))


class IdentityPrimitiveTests(unittest.TestCase):
    AUTHORITY_ID = "auth-A"
    AUTHORITY_SHA = "0" * 64
    CLAIM_SHA = "1" * 64
    CLAIM_ID = (
        "h26-runtime-claim-v1-"
        "48d39b8c620ae179787926d0050483abeff4a23b6cb41bfb5ee5d6df2f31bb85"
    )
    ENTRY_ID = (
        "h26-runtime-entry-v1-"
        "df0a99be34159c684e5d81ca116b8a5691eadd7800e4164bfb06057c96b7df98"
    )

    def test_claim_id_vector_and_slot_identity(self) -> None:
        self.assertEqual(
            runtime.derive_claim_id(self.AUTHORITY_ID, self.AUTHORITY_SHA),
            self.CLAIM_ID,
        )
        self.assertEqual(
            runtime.derive_claim_slot_identity(self.AUTHORITY_ID, self.AUTHORITY_SHA),
            self.CLAIM_ID,
        )

    def test_claim_id_changes_with_bound_sha(self) -> None:
        changed = runtime.derive_claim_id(self.AUTHORITY_ID, "0" * 63 + "1")
        self.assertNotEqual(changed, self.CLAIM_ID)

    def test_entry_id_vector_and_slot_identity(self) -> None:
        arguments = (
            self.AUTHORITY_ID,
            self.AUTHORITY_SHA,
            self.CLAIM_ID,
            self.CLAIM_SHA,
        )
        self.assertEqual(runtime.derive_observer_entry_evidence_id(*arguments), self.ENTRY_ID)
        self.assertEqual(runtime.derive_observer_entry_slot_identity(*arguments), self.ENTRY_ID)

    def test_entry_id_changes_with_claim_sha(self) -> None:
        changed = runtime.derive_observer_entry_evidence_id(
            self.AUTHORITY_ID, self.AUTHORITY_SHA, self.CLAIM_ID, "1" * 63 + "2"
        )
        self.assertNotEqual(changed, self.ENTRY_ID)

    def test_entry_rejects_claim_not_derived_from_authority(self) -> None:
        other_claim = runtime.derive_claim_id("auth-B", self.AUTHORITY_SHA)
        with self.assertRaisesRegex(ValueError, "does not bind"):
            runtime.derive_observer_entry_evidence_id(
                self.AUTHORITY_ID, self.AUTHORITY_SHA, other_claim, self.CLAIM_SHA
            )

    def test_authority_id_and_sha_syntax_are_fail_closed(self) -> None:
        for authority_id in ("", " auth", "auth ", "é"):
            with self.subTest(authority_id=authority_id):
                with self.assertRaises(ValueError):
                    runtime.validate_authority_id(authority_id)
        for sha in ("A" * 64, "0" * 63, "g" * 64):
            with self.subTest(sha=sha):
                with self.assertRaisesRegex(ValueError, "lowercase"):
                    runtime.derive_claim_id(self.AUTHORITY_ID, sha)

    def test_internal_nul_authority_id_follows_the_sealed_domain(self) -> None:
        authority_id = "auth\x00suffix"
        self.assertEqual(runtime.validate_authority_id(authority_id), authority_id)
        self.assertEqual(
            runtime.derive_claim_id(authority_id, self.AUTHORITY_SHA),
            "h26-runtime-claim-v1-"
            "a3bfd32f562c5106fbe508f663dce25aa4befc03bacbbbe5b862bcb96af7cc7f",
        )

    def test_external_raw_sha256_hashes_exact_bytes(self) -> None:
        raw = b'{"a":1}\n'
        self.assertEqual(runtime.external_raw_sha256(raw), hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(
            runtime.external_raw_sha256(raw), runtime.external_raw_sha256(raw[:-1])
        )


class ContractAndSchemaTests(unittest.TestCase):
    def test_exact_reviewed_execution_contract_loads(self) -> None:
        payload = runtime.load_runtime_execution_contract()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            payload["bindings"]["runtime_qualification_contract_raw_sha256"],
            runtime.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        )

    def test_alternate_contract_bytes_are_rejected(self) -> None:
        source = (
            Path(runtime.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_runtime_qualification_execution_authority_contract.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / source.name
            altered.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                runtime.load_runtime_execution_contract(altered)

    def test_public_contract_binding_cannot_redirect_loader(self) -> None:
        original = runtime.EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA
        try:
            runtime.EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = "0" * 40
            with self.assertRaisesRegex(ValueError, "blob binding mismatch"):
                runtime.load_runtime_execution_contract()
        finally:
            runtime.EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = original

    def test_exact_external_seal_loads_and_rebinds_contract_bytes(self) -> None:
        payload = runtime.load_runtime_execution_external_seal()
        self.assertEqual(
            payload["execution_contract_raw_sha256"],
            "c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9",
        )
        self.assertFalse(any(
            value for value in payload["authorization_state"].values()
            if value is not None
        ))

    def test_modified_external_seal_is_rejected_before_semantic_use(self) -> None:
        source = (
            Path(runtime.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_runtime_qualification_execution_authority_contract_external_seal.json"
        )
        raw = source.read_bytes()
        mutations = (
            raw.replace(b'"schema_version": 1', b'"schema_version": 2', 1),
            raw.replace(
                b'DECLARATIVE_EXTERNAL_SEAL_ONLY_NO_EXECUTION_AUTHORITY',
                b'DECLARATIVE_EXTERNAL_SEAL_ONLY_EXECUTION_AUTHORITY',
                1,
            ),
            raw.replace(b'"authority_exists": false', b'"authority_exists": true', 1),
            raw.replace(
                runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256.encode("ascii"),
                b"0" * 64,
                1,
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, mutation in enumerate(mutations):
                with self.subTest(index=index):
                    altered = Path(directory) / f"altered-{index}.json"
                    altered.write_bytes(mutation)
                    with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                        runtime.load_runtime_execution_external_seal(altered)

    def test_external_seal_public_binding_cannot_redirect_loader(self) -> None:
        original = runtime.EXTERNAL_SEAL_GIT_BLOB_SHA
        try:
            runtime.EXTERNAL_SEAL_GIT_BLOB_SHA = "0" * 40
            with self.assertRaisesRegex(ValueError, "seal blob binding mismatch"):
                runtime.load_runtime_execution_external_seal()
        finally:
            runtime.EXTERNAL_SEAL_GIT_BLOB_SHA = original

    def test_raw_sha_public_binding_cannot_be_replaced(self) -> None:
        original = runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256
        try:
            runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "raw SHA256 binding mismatch"):
                runtime.canonical_execution_contract_raw_sha256()
        finally:
            runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256 = original

    def test_lf_and_crlf_checkouts_bind_the_same_git_contract_bytes(self) -> None:
        source = (
            Path(runtime.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_runtime_qualification_execution_authority_contract.json"
        )
        lf = source.read_bytes().replace(b"\r\n", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as directory:
            lf_path = Path(directory) / "contract-lf.json"
            crlf_path = Path(directory) / "contract-crlf.json"
            lf_path.write_bytes(lf)
            crlf_path.write_bytes(crlf)
            self.assertEqual(
                runtime.canonical_execution_contract_raw_sha256(lf_path),
                runtime.canonical_execution_contract_raw_sha256(crlf_path),
            )

    def test_exact_keyset_accepts_only_exact_fields(self) -> None:
        value = {key: None for key in runtime.CLAIM_REQUIRED_FIELDS}
        runtime.validate_claim_keyset(value)
        missing = dict(value)
        missing.pop("claim_id")
        with self.assertRaisesRegex(ValueError, "missing"):
            runtime.validate_claim_keyset(missing)
        extra = dict(value, unexpected=None)
        with self.assertRaisesRegex(ValueError, "extra"):
            runtime.validate_claim_keyset(extra)

    def test_all_declared_closed_keysets_are_unique(self) -> None:
        keysets = (
            runtime.AUTHORITY_REQUIRED_FIELDS,
            runtime.CLAIM_REQUIRED_FIELDS,
            runtime.OBSERVER_ENTRY_EVIDENCE_REQUIRED_FIELDS,
            runtime.RECEIPT_REQUIRED_FIELDS,
        )
        for fields in keysets:
            with self.subTest(first=fields[0]):
                self.assertEqual(len(fields), len(set(fields)))

    def test_module_has_no_execution_or_nondeterministic_imports(self) -> None:
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import numpy", "import random", "import uuid", "import time",
            "subprocess", "observe_primary_runtime(", "open(\"x\"",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class ArtificialArtifactValidatorTests(unittest.TestCase):
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
            "authority_id": "artificial-authority-A",
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
            record_bytes = qualifier.serialize_runtime_qualification_record(record)
            record_sha = hashlib.sha256(record_bytes).hexdigest()
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

    def artifact_chain(self) -> tuple[
        dict[str, object], str, dict[str, object], str, dict[str, object], str
    ]:
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        claim_sha = runtime.canonical_artifact_raw_sha256(claim)
        evidence = self.evidence(authority, authority_sha, claim, claim_sha)
        evidence_sha = runtime.canonical_artifact_raw_sha256(evidence)
        return authority, authority_sha, claim, claim_sha, evidence, evidence_sha

    def test_exact_artificial_authority_is_accepted(self) -> None:
        runtime.validate_artificial_authority(self.authority())

    def test_public_binding_cannot_redirect_artifact_validators(self) -> None:
        authority = self.authority()
        original = runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT
        try:
            runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT = "0" * 40
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                runtime.validate_artificial_authority(authority)
        finally:
            runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT = original

    def test_each_fixed_authority_binding_mutation_is_rejected(self) -> None:
        authority = self.authority()
        mutable_fields = tuple(
            key for key in authority
            if key not in {"authority_id", "issued_at", "issuer_identity"}
        )
        for key in mutable_fields:
            with self.subTest(key=key):
                altered = dict(authority)
                value = altered[key]
                if type(value) is bool:
                    altered[key] = not value
                elif type(value) is int:
                    altered[key] = value + 1
                else:
                    altered[key] = str(value) + "-changed"
                with self.assertRaisesRegex(ValueError, key):
                    runtime.validate_artificial_authority(altered)

    def test_authority_canonical_sha_exact_and_false(self) -> None:
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        runtime.validate_artificial_claim(authority, claim, authority_sha)
        with self.assertRaisesRegex(ValueError, "canonical authority bytes"):
            runtime.validate_artificial_claim(authority, claim, "0" * 64)

    def test_exact_claim_and_requested_mutations(self) -> None:
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        runtime.validate_artificial_claim(authority, claim, authority_sha)
        mutations = {
            "authority_raw_sha256": "0" * 64,
            "claim_id": "h26-runtime-claim-v1-" + "0" * 64,
            "execution_authority_contract_commit": "0" * 40,
            "execution_authority_contract_raw_sha256": "0" * 64,
            "qualifier_commit": "0" * 40,
            "runtime_qualification_contract_commit": "0" * 40,
        }
        for key, changed in mutations.items():
            with self.subTest(key=key):
                altered = dict(claim)
                altered[key] = changed
                with self.assertRaises(ValueError):
                    runtime.validate_artificial_claim(authority, altered, authority_sha)

    def test_exact_evidence_is_accepted(self) -> None:
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        claim_sha = runtime.canonical_artifact_raw_sha256(claim)
        evidence = self.evidence(authority, authority_sha, claim, claim_sha)
        runtime.validate_artificial_observer_entry_evidence(
            authority, claim, evidence, authority_sha, claim_sha
        )

    def test_evidence_requested_mutations_are_rejected(self) -> None:
        authority = self.authority()
        authority_sha = runtime.canonical_artifact_raw_sha256(authority)
        claim = self.claim(authority, authority_sha)
        claim_sha = runtime.canonical_artifact_raw_sha256(claim)
        evidence = self.evidence(authority, authority_sha, claim, claim_sha)
        mutations = {
            "claim_raw_sha256": "0" * 64,
            "claim_id": "h26-runtime-claim-v1-" + "0" * 64,
            "observer_entry_evidence_id": "h26-runtime-entry-v1-" + "0" * 64,
            "observer_entry_ordinal": 2,
        }
        for key, changed in mutations.items():
            with self.subTest(key=key):
                altered = dict(evidence)
                altered[key] = changed
                with self.assertRaises(ValueError):
                    runtime.validate_artificial_observer_entry_evidence(
                        authority, claim, altered, authority_sha, claim_sha
                    )
        with self.assertRaisesRegex(ValueError, "canonical claim bytes"):
            runtime.validate_artificial_observer_entry_evidence(
                authority, claim, evidence, authority_sha, "0" * 64
            )

    def test_logical_mutation_changes_sha_and_validation_has_no_effect(self) -> None:
        authority = self.authority()
        original_sha = runtime.canonical_artifact_raw_sha256(authority)
        altered = dict(authority)
        altered["issuer_identity"] = "another-artificial-issuer"
        self.assertNotEqual(
            original_sha, runtime.canonical_artifact_raw_sha256(altered)
        )
        with tempfile.TemporaryDirectory() as directory:
            before = tuple(Path(directory).iterdir())
            runtime.validate_artificial_authority(authority)
            after = tuple(Path(directory).iterdir())
            self.assertEqual(before, after)

    def test_terminal_receipt_accepts_all_three_rederived_record_statuses(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        for status in (
            qualifier.STATUS_QUALIFIED,
            qualifier.STATUS_DISQUALIFIED,
            qualifier.STATUS_INCONCLUSIVE,
        ):
            with self.subTest(status=status):
                record = self.runtime_record(status)
                receipt = self.receipt(
                    authority, authority_sha, claim, claim_sha,
                    evidence, evidence_sha, record,
                )
                runtime.validate_artificial_terminal_execution_receipt(
                    authority, claim, evidence, receipt,
                    authority_sha, claim_sha, evidence_sha, record,
                )

    def test_terminal_receipt_rejects_forged_record_sha_and_terminal(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        record = self.runtime_record()
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, record,
        )
        for key, value in (
            ("runtime_record_raw_sha256", "0" * 64),
            ("terminal_status", qualifier.STATUS_DISQUALIFIED),
        ):
            with self.subTest(key=key):
                altered = dict(receipt)
                altered[key] = value
                with self.assertRaisesRegex(ValueError, key):
                    runtime.validate_artificial_terminal_execution_receipt(
                        authority, claim, evidence, altered,
                        authority_sha, claim_sha, evidence_sha, record,
                    )

    def test_terminal_receipt_rejects_forged_evidence_and_sha(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        record = self.runtime_record()
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, record,
        )
        altered_evidence = dict(evidence)
        altered_evidence["observer_entry_ordinal"] = 2
        with self.assertRaises(ValueError):
            runtime.validate_artificial_terminal_execution_receipt(
                authority, claim, altered_evidence, receipt,
                authority_sha, claim_sha, evidence_sha, record,
            )
        with self.assertRaisesRegex(ValueError, "canonical evidence bytes"):
            runtime.validate_artificial_terminal_execution_receipt(
                authority, claim, evidence, receipt,
                authority_sha, claim_sha, "0" * 64, record,
            )

    def test_terminal_receipt_accepts_consumed_no_record_branch_only(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, None,
        )
        runtime.validate_artificial_terminal_execution_receipt(
            authority, claim, evidence, receipt,
            authority_sha, claim_sha, evidence_sha, None,
        )
        for key, value in (
            ("runtime_record_raw_sha256", "0" * 64),
            ("terminal_status", qualifier.STATUS_QUALIFIED),
        ):
            with self.subTest(key=key):
                altered = dict(receipt)
                altered[key] = value
                with self.assertRaises(ValueError):
                    runtime.validate_artificial_terminal_execution_receipt(
                        authority, claim, evidence, altered,
                        authority_sha, claim_sha, evidence_sha, None,
                    )

        record = self.runtime_record()
        with self.assertRaisesRegex(ValueError, "must not receive"):
            runtime.validate_artificial_terminal_execution_receipt(
                authority, claim, evidence, receipt,
                authority_sha, claim_sha, evidence_sha, record,
            )

    def test_terminal_receipt_requires_record_when_declared(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        record = self.runtime_record()
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, record,
        )
        with self.assertRaisesRegex(ValueError, "requires"):
            runtime.validate_artificial_terminal_execution_receipt(
                authority, claim, evidence, receipt,
                authority_sha, claim_sha, evidence_sha, None,
            )

    def test_terminal_receipt_rejects_redirected_qualifier_status(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, None,
        )
        original = qualifier.STATUS_INCONCLUSIVE
        try:
            qualifier.STATUS_INCONCLUSIVE = "redirected"
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                runtime.validate_artificial_terminal_execution_receipt(
                    authority, claim, evidence, receipt,
                    authority_sha, claim_sha, evidence_sha, None,
                )
        finally:
            qualifier.STATUS_INCONCLUSIVE = original

    def test_terminal_receipt_validator_has_no_filesystem_effect(self) -> None:
        chain = self.artifact_chain()
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha = chain
        record = self.runtime_record()
        receipt = self.receipt(
            authority, authority_sha, claim, claim_sha,
            evidence, evidence_sha, record,
        )
        with tempfile.TemporaryDirectory() as directory:
            before = tuple(Path(directory).iterdir())
            runtime.validate_artificial_terminal_execution_receipt(
                authority, claim, evidence, receipt,
                authority_sha, claim_sha, evidence_sha, record,
            )
            self.assertEqual(before, tuple(Path(directory).iterdir()))


if __name__ == "__main__":
    unittest.main()
