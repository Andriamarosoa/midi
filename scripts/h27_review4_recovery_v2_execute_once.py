#!/usr/bin/env python3
"""Independent one-shot H27 Review-4 recovery V2 activation wrapper."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

BASE = Path("/Users/amcarene/h27-admin-recovery-v2/runner-r1/h27_review4_execute_once.py")
ROOT = Path("/Users/amcarene/h27-admin-recovery-v2")
OLD_ROOT = Path("/Users/amcarene/h27-admin")
FAILED_V1_ROOT = Path("/Users/amcarene/h27-admin-recovery-v1")
ACTIVATION_ID = "ecd4b7586422989eec31a6d61ebcc3a0bedae41c9ff77e10968994112290d22c"
AUTHORITY_INSTANCE_ID = "8b1b67d16a8753ac9528a405fd504f9bf22ac468476c9b81e729f02a8442f49c"
ISSUER_ID = "h27-recovery-v2-execution-codex-mac-primary"
ACTIVATION_SHA256 = "966452ed22a132b403646dae18547841c4072c9ad42949172cbe82df80624794"
BASE_SIZE = 29805
BASE_GIT_BLOB_SHA1 = "fdef83bcc1a4d1be26e48f4febe1d4d4e3f6440e"
BASE_RAW_SHA256 = "673a6099849ae95e643ee9067dd8131c0d0f3ac627e0f76a316b80787e298ddc"


def load_base():
    raw = BASE.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if (len(raw), blob, hashlib.sha256(raw).hexdigest()) != (BASE_SIZE, BASE_GIT_BLOB_SHA1, BASE_RAW_SHA256):
        raise PermissionError("H27 recovery V2 base runner identity mismatch")
    spec = importlib.util.spec_from_file_location("h27_review4_recovery_v2_base", BASE)
    if spec is None or spec.loader is None:
        raise ImportError("H27 recovery V2 base runner loader unavailable")
    module = importlib.util.module_from_spec(spec)
    if module.__name__ in sys.modules:
        raise RuntimeError("H27 recovery V2 base runner module collision")
    sys.modules[module.__name__] = module
    try:
        spec.loader.exec_module(module)
        return module
    except BaseException:
        sys.modules.pop(module.__name__, None)
        raise


def configure(module) -> None:
    module.ADMIN = ROOT
    module.ACTIVATION = ROOT / "activation/h27-materialization-recovery-v2.json"
    module.AUTHORITY = ROOT / "authority/h27-materialization-recovery-v2.json"
    module.CLAIM = ROOT / "claims/h27-synthetic-v1-recovery-v2.consumed.json"
    module.TERMINAL = ROOT / "terminal/h27-materialization-recovery-v2.json"
    module.POPULATION_PARENT = ROOT / "population"
    module.FINAL_NAME = "h27-synthetic-v1"
    module.STAGING_NAME = ".h27-synthetic-v1-recovery-v2.staging"
    module.OPERATIONAL_MODULE = ROOT / "runner-r1/harmonic_censoring_h27_review4_materializer.py"
    module.OPERATIONAL_PARENT_NAME = "runner-r1"
    module.TERMINAL_PARENT_NAME = "terminal"
    module.OPERATIONAL_BINDING_FILE = ROOT / "runner-r1/harmonic_censoring_h27_review4_materializer_identity_binding.json"
    module.OPERATIONAL_SEAL_FILE = ROOT / "runner-r1/harmonic_censoring_h27_review4_materializer_external_seal.json"
    module.AUTHORITY_INSTANCE_ID = AUTHORITY_INSTANCE_ID
    module.ACTIVATION_SHA256 = ACTIVATION_SHA256
    module.EXPECTED_ISSUER_ID = ISSUER_ID
    module.EXPECTED_ACTIVATION_ID = ACTIVATION_ID
    module.RECOVERY_PREDECESSOR = (
        ("authority", OLD_ROOT / "authority/h27-materialization-v1.json", {"authority_instance_id": "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a", "single_use": True, "science_authorized": False, "locked_test_used": False}),
        ("claim", OLD_ROOT / "claims/h27-synthetic-v1.consumed.json", {"activation_sha256": "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2", "consumed": True, "retry_allowed": False}),
    )
    module.RECOVERY_FAILED_ROOT = (
        FAILED_V1_ROOT,
        ("activation", "authority", "claims", "population", "runner-r1", "terminal"),
        (
            ("runner-r1/harmonic_censoring_h27_materialization_recovery_v1_contract.json", "242f3f4efc4dc07285fc6b62b58113a3afca2f3c", 5079, "e8d000ed37ac010c284290b3077a92768abee99825e03a843d0247e2a5a5eaf3", 0o400),
            ("activation/h27-materialization-recovery-v1.json", "4220e0de4916ed5d5d87bcc2e61aa9133bea7a33", 2382, "a5f1e68b66b59b343785fe8ab66d02f3eceb69e9b05b63581ae7f2d7678a75ac", 0o400),
            ("runner-r1/h27_review4_execute_once.py", "53a5d243b9b3ac614856ae35a052ea46f49b30ad", 28265, "94dc4fe68fe9950f04df9ffd2c5ac7481a45712ffac16d05bc5fe4e8a019594d", 0o400),
            ("runner-r1/h27_review4_recovery_v1_execute_once.py", "181c0afa18e7e9f1dcd6ed02cb4183426ac30f3e", 3659, "e23193d347c6bf17eb95fd3f2ba8102397c7cabb3d1c60ea371d6c72b1096205", 0o400),
            ("runner-r1/harmonic_censoring_h27_review4_materializer.py", "8cdafbd6a08ea893daa2d6f41cb62166bf9162cd", 33706, "2ecaabf1e1880688244b06ecb03a9b3eb7831d4659e209aa11e36b7b60948be3", 0o400),
            ("runner-r1/harmonic_censoring_h27_review4_materializer_identity_binding.json", "9371d80c75c2cf08ebf2cc33177c05c123c13efa", 5269, "204f61303277b4a813d23a4a6a478d6d33a17893d30a72156e7a7d2574dfb4da", 0o400),
            ("runner-r1/harmonic_censoring_h27_review4_materializer_external_seal.json", "370eaf40be9863ec381061678451a58409264244", 1198, "f396257c040b7d0504336b98384308f76e45a32614efba129eba91c53b55f1de", 0o400),
            ("runner-r1/harmonic_censoring_h27_materialization_recovery_v1_materializer_compatibility_binding.json", "96924daef1004643475b52c8380a962401fe9a6c", 2366, "fa44e6a36a20ae967120955a57548d642c8ecdc1012e9bd6802057af956a6a88", 0o400),
            ("runner-r1/harmonic_censoring_h27_materialization_recovery_v1_materializer_compatibility_external_seal.json", "596206fabb7bb23f24a666ab320403086924a7f2", 860, "f1fb80262d048de9935ad8420d095d18b9c73bdee175a739d1bc4a5b7371c332", 0o400),
        ),
        ("authority/h27-materialization-recovery-v1.json", "claims/h27-synthetic-v1-recovery.consumed.json", "population/h27-synthetic-v1", "population/.h27-synthetic-v1-recovery.staging", "terminal/h27-materialization-recovery-v1.json"),
    )


def main() -> int:
    module = load_base()
    configure(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
