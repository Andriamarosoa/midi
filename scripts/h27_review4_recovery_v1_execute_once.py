#!/usr/bin/env python3
"""Independent one-shot H27 Review-4 recovery activation wrapper."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

BASE = Path("/Users/amcarene/h27-admin-recovery-v1/runner-r1/h27_review4_execute_once.py")
ROOT = Path("/Users/amcarene/h27-admin-recovery-v1")
OLD_ROOT = Path("/Users/amcarene/h27-admin")
ACTIVATION_ID = "101ef27d0bd246816696623a24608433d50850bfcaf5d4f02a2affb85d59ee5b"
AUTHORITY_INSTANCE_ID = "f1e8fb1a5c9fab6a75608a19a73916791bab406334d8a1c7162cbe3d8c5035e2"
ISSUER_ID = "h27-recovery-execution-codex-mac-primary"
ACTIVATION_SHA256 = "a5f1e68b66b59b343785fe8ab66d02f3eceb69e9b05b63581ae7f2d7678a75ac"
BASE_SIZE = 28265
BASE_GIT_BLOB_SHA1 = "53a5d243b9b3ac614856ae35a052ea46f49b30ad"
BASE_RAW_SHA256 = "94dc4fe68fe9950f04df9ffd2c5ac7481a45712ffac16d05bc5fe4e8a019594d"


def load_base():
    raw = BASE.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if (len(raw), blob, hashlib.sha256(raw).hexdigest()) != (BASE_SIZE, BASE_GIT_BLOB_SHA1, BASE_RAW_SHA256):
        raise PermissionError("H27 recovery base runner identity mismatch")
    spec = importlib.util.spec_from_file_location("h27_review4_recovery_v1_base", BASE)
    if spec is None or spec.loader is None:
        raise ImportError("H27 recovery base runner loader unavailable")
    module = importlib.util.module_from_spec(spec)
    if module.__name__ in sys.modules:
        raise RuntimeError("H27 recovery base runner module collision")
    sys.modules[module.__name__] = module
    try:
        spec.loader.exec_module(module)
        return module
    except BaseException:
        sys.modules.pop(module.__name__, None)
        raise


def configure(module) -> None:
    module.ADMIN = ROOT
    module.ACTIVATION = ROOT / "activation/h27-materialization-recovery-v1.json"
    module.AUTHORITY = ROOT / "authority/h27-materialization-recovery-v1.json"
    module.CLAIM = ROOT / "claims/h27-synthetic-v1-recovery.consumed.json"
    module.TERMINAL = ROOT / "terminal/h27-materialization-recovery-v1.json"
    module.POPULATION_PARENT = ROOT / "population"
    module.FINAL_NAME = "h27-synthetic-v1"
    module.STAGING_NAME = ".h27-synthetic-v1-recovery.staging"
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
        (
            "authority",
            OLD_ROOT / "authority/h27-materialization-v1.json",
            {"authority_instance_id": "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a", "single_use": True, "science_authorized": False, "locked_test_used": False},
        ),
        (
            "claim",
            OLD_ROOT / "claims/h27-synthetic-v1.consumed.json",
            {"activation_sha256": "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2", "consumed": True, "retry_allowed": False},
        ),
    )


def main() -> int:
    module = load_base()
    configure(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
