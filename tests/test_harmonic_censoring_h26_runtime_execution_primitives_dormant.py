from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as runtime


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


if __name__ == "__main__":
    unittest.main()
