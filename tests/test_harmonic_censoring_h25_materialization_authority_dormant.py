import copy
import inspect
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from src.polyphonic import harmonic_censoring_h25_materialization_authority as authority


ROOT = Path(__file__).resolve().parents[1]


class H25MaterializationAuthorityDormantTests(unittest.TestCase):
    def test_contract_binds_reviewed_materializer_and_all_inputs(self):
        contract = json.loads((ROOT / authority.AUTHORITY_CONTRACT).read_text(encoding="utf-8"))
        reviewed = contract["reviewed_materializer"]
        self.assertEqual(reviewed["commit"], authority.REVIEWED_MATERIALIZER_COMMIT)
        self.assertEqual(reviewed["source_git_blob"], authority.REVIEWED_MATERIALIZER_BLOB)
        self.assertEqual(len(contract["sealed_git_blobs"]), 5)
        self.assertFalse(contract["scope"]["capability_issuance_authorized_now"])
        self.assertFalse(contract["future_authorization_seal"]["exists_in_this_commit"])
        self.assertEqual(len(contract["future_authorization_seal"]["exact_fields"]), 11)

    def test_issuer_fails_before_plan_runtime_or_numpy_when_seal_absent(self):
        with mock.patch.object(authority.materializer, "load_dormant_plan") as plan:
            with self.assertRaisesRegex(PermissionError, "seal absent"):
                authority.issue_h25_materialization_authority(ROOT)
            plan.assert_not_called()

    def test_wrapper_is_factory_only_and_not_copyable(self):
        with self.assertRaisesRegex(PermissionError, "factory-only"):
            authority.IssuedH25MaterializationAuthority(object())
        source = inspect.getsource(authority.IssuedH25MaterializationAuthority)
        self.assertIn('self.__state = "CONSUMED_BEFORE_DELEGATION"', source)
        self.assertLess(source.index('self.__state = "CONSUMED_BEFORE_DELEGATION"'), source.index("materialize_and_publish_h25_population"))
        self.assertNotIn("capability(self", source)

    def test_no_cli_and_no_authority_artifact_exists(self):
        source = inspect.getsource(authority)
        self.assertNotIn("__main__", source)
        self.assertNotIn("argparse", source)
        self.assertFalse((ROOT / authority.AUTHORIZATION_SEAL).exists())

    def test_future_path_orders_seal_before_plan_runtime_and_capability(self):
        source = inspect.getsource(authority.issue_h25_materialization_authority)
        self.assertLess(source.index("_validate_future_seal"), source.index("load_dormant_plan"))
        self.assertLess(source.index("require_reference_environment_before_numpy"), source.index("H25MaterializationCapability"))
        self.assertLess(source.index("_ISSUED = True"), source.index("return wrapper"))
        validator = inspect.getsource(authority._validate_future_seal)
        self.assertLess(validator.index("hashlib.sha256(raw)"), validator.index("parse_sealed_json"))
        self.assertIn("AUTHORIZATION_SEAL_SHA256_ENV", validator)
        self.assertIn("HEAD:{binding['path']}", validator)
        self.assertIn("HEAD:src/polyphonic/harmonic_censoring_h25_population_materializer.py", validator)

    def test_external_seal_digest_fails_before_json_parsing(self):
        with mock.patch.object(authority.materializer, "parse_sealed_json") as parse:
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(PermissionError, "external SHA binding"):
                    authority._validate_future_seal(ROOT, b"{}")
            parse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
