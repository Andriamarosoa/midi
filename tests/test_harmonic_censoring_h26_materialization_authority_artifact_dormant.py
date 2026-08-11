from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h26_materialization_authority_artifact as artifact
from src.polyphonic import harmonic_censoring_h26_materialization_runtime_execution_proof as proof
from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as runtime
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as qualifier


def _load_proof_fixture_class():
    path = Path(__file__).with_name(
        "test_harmonic_censoring_h26_materialization_runtime_execution_proof_dormant.py"
    )
    spec = importlib.util.spec_from_file_location("_h26_proof_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load H26 proof fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DormantMaterializationRuntimeExecutionProofTests


_ProofFixture = _load_proof_fixture_class()


class DormantMaterializationAuthorityArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _ProofFixture(methodName="test_exact_qualified_proof_is_accepted_and_projection_is_immutable")

    def chain(self, status: str = qualifier.STATUS_QUALIFIED):
        return self.fixture.chain(status)

    def valid_authority(self, chain=None) -> dict[str, object]:
        chain = chain or self.chain()
        contract = artifact.load_materialization_authority_artifact_contract()
        rules = contract["future_authority_artifact"]
        value: dict[str, object] = dict(rules["fixed_values"])
        projection = proof.validate_artificial_materialization_runtime_execution_proof(
            chain[0], chain[2], chain[4], chain[6],
            chain[1], chain[3], chain[5], chain[7], chain[8],
        )
        for field in projection.__dataclass_fields__:
            value[field] = getattr(projection, field)
        value.update(
            authority_id="placeholder",
            absolute_destination="/var/tmp/h26/artificial-authority",
            issued_at="2026-08-11T20:00:00Z",
            issuer_identity="reviewer:h26/test",
        )
        value["authority_id"] = artifact.derive_materialization_authority_id(value)
        return value

    def validate(self, authority_value, chain=None):
        chain = chain or self.chain()
        return artifact.validate_artificial_materialization_authority_artifact(
            authority_value,
            runtime_authority=chain[0],
            runtime_claim=chain[2],
            runtime_evidence=chain[4],
            runtime_receipt=chain[6],
            runtime_authority_raw_sha256=chain[1],
            runtime_claim_raw_sha256=chain[3],
            runtime_evidence_raw_sha256=chain[5],
            runtime_receipt_raw_sha256=chain[7],
            runtime_record=chain[8],
        )

    def test_valid_authority_is_accepted_and_result_is_frozen(self) -> None:
        chain = self.chain()
        authority_value = self.valid_authority(chain)
        result = self.validate(authority_value, chain)
        self.assertEqual(result.authority_id, authority_value["authority_id"])
        self.assertEqual(result.raw_sha256, hashlib.sha256(result.canonical_bytes).hexdigest())
        self.assertTrue(result.canonical_bytes.endswith(b"\n"))
        with self.assertRaises(FrozenInstanceError):
            result.raw_sha256 = "0" * 64

    def test_id_and_canonical_bytes_are_deterministic(self) -> None:
        chain = self.chain()
        first = self.valid_authority(chain)
        second = dict(reversed(tuple(first.items())))
        self.assertEqual(
            artifact.derive_materialization_authority_id(first),
            artifact.derive_materialization_authority_id(second),
        )
        one = self.validate(first, chain)
        two = self.validate(second, chain)
        self.assertEqual(one.canonical_bytes, two.canonical_bytes)
        self.assertEqual(one.raw_sha256, two.raw_sha256)

    def test_missing_extra_bad_type_and_bad_fixed_value_are_rejected(self) -> None:
        cases = []
        missing = self.valid_authority()
        missing.pop("issuer_identity")
        cases.append(missing)
        extra = self.valid_authority()
        extra["extra"] = "forbidden"
        cases.append(extra)
        bad_type = self.valid_authority()
        bad_type["authority_schema_version"] = True
        cases.append(bad_type)
        bad_fixed = self.valid_authority()
        bad_fixed["retry_allowed"] = True
        cases.append(bad_fixed)
        for index, value in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.validate(value)

    def test_forged_id_and_proof_projection_are_rejected(self) -> None:
        forged_id = self.valid_authority()
        forged_id["authority_id"] = "h26-materialization-authority-v1-" + "0" * 64
        with self.assertRaisesRegex(ValueError, "authority_id"):
            self.validate(forged_id)

        forged_projection = self.valid_authority()
        forged_projection["runtime_execution_claim_id"] = "forged-claim"
        forged_projection["authority_id"] = artifact.derive_materialization_authority_id(forged_projection)
        with self.assertRaisesRegex(ValueError, "projection"):
            self.validate(forged_projection)

    def test_nonqualified_and_mixed_runtime_proofs_are_rejected(self) -> None:
        qualified = self.chain()
        authority_value = self.valid_authority(qualified)
        nonqualified = self.chain(qualifier.STATUS_DISQUALIFIED)
        with self.assertRaisesRegex(ValueError, "must be QUALIFIED"):
            self.validate(authority_value, nonqualified)

        mixed = list(qualified)
        mixed[7] = "0" * 64
        with self.assertRaisesRegex(ValueError, "canonical receipt bytes"):
            self.validate(authority_value, tuple(mixed))

    def test_invalid_destination_date_and_issuer_are_rejected(self) -> None:
        mutations = (
            ("absolute_destination", "relative/path"),
            ("absolute_destination", "/bad/../path"),
            ("issued_at", "2026-02-30T12:00:00Z"),
            ("issued_at", "2026-08-11T20:00:00+00:00"),
            ("issuer_identity", "bad issuer"),
            ("issuer_identity", ""),
        )
        for field, changed in mutations:
            with self.subTest(field=field, changed=changed):
                value = self.valid_authority()
                value[field] = changed
                value["authority_id"] = artifact.derive_materialization_authority_id(value)
                with self.assertRaises(ValueError):
                    self.validate(value)

    def test_validator_calls_approved_proof_validator_once(self) -> None:
        chain = self.chain()
        value = self.valid_authority(chain)
        with mock.patch.object(
            proof,
            "validate_artificial_materialization_runtime_execution_proof",
            wraps=proof.validate_artificial_materialization_runtime_execution_proof,
        ) as validator:
            self.validate(value, chain)
        validator.assert_called_once()

    def test_validation_has_no_destination_filesystem_effect(self) -> None:
        chain = self.chain()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self.valid_authority(chain)
            value["absolute_destination"] = "/tmp/h26-must-not-be-created/authority.json"
            value["authority_id"] = artifact.derive_materialization_authority_id(value)
            before = tuple(root.iterdir())
            with mock.patch.object(Path, "mkdir") as mkdir, mock.patch.object(
                Path, "write_bytes"
            ) as write_bytes, mock.patch.object(Path, "touch") as touch, mock.patch.object(
                Path, "rename"
            ) as rename:
                self.validate(value, chain)
            after = tuple(root.iterdir())
        self.assertEqual(before, after)
        mkdir.assert_not_called()
        write_bytes.assert_not_called()
        touch.assert_not_called()
        rename.assert_not_called()

    def test_public_bindings_and_alternate_contract_bytes_fail_closed(self) -> None:
        original = artifact.ARTIFACT_CONTRACT_COMMIT
        try:
            artifact.ARTIFACT_CONTRACT_COMMIT = "0" * 40
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                artifact.load_materialization_authority_artifact_contract()
        finally:
            artifact.ARTIFACT_CONTRACT_COMMIT = original

        source = (
            Path(artifact.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_materialization_authority_artifact_contract.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / source.name
            changed.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                artifact.load_materialization_authority_artifact_contract(changed)


if __name__ == "__main__":
    unittest.main()
