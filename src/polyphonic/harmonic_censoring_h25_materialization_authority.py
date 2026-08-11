"""Dormant one-shot H25 materialization authority.

No authorization seal exists in this commit, so issuance always fails before
runtime or scientific access.  The wrapper never exposes the raw capability.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import threading
from typing import Any, Callable

from . import harmonic_censoring_h25_population_materializer as materializer


AUTHORITY_CONTRACT = Path("configs/harmonic_censoring_h25_population_materialization_one_shot_authority_contract.json")
AUTHORIZATION_SEAL = Path("configs/harmonic_censoring_h25_population_materialization_authorization_seal.json")
AUTHORIZATION_ENV = "H25_POPULATION_MATERIALIZATION_AUTHORIZATION_COMMIT"
AUTHORIZATION_SEAL_SHA256_ENV = "H25_POPULATION_MATERIALIZATION_AUTHORIZATION_SEAL_SHA256"
REVIEWED_MATERIALIZER_COMMIT = "0036853ff6c9c49dda6ed3767146b16db310589f"
REVIEWED_MATERIALIZER_BLOB = "77bebf42e343771acca390c848962fbd05fde3c3"
_ISSUE_LOCK = threading.Lock()
_ISSUED = False


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8").strip()


def _validate_future_seal(root: Path, raw: bytes) -> dict[str, object]:
    external_digest = os.environ.get(AUTHORIZATION_SEAL_SHA256_ENV)
    if external_digest is None or hashlib.sha256(raw).hexdigest() != external_digest:
        raise PermissionError("H25 authorization seal external SHA binding mismatch before parsing.")
    seal = materializer.parse_sealed_json(raw, "materialization authorization seal")
    expected_fields = {
        "schema_version", "purpose", "status", "authorized_action", "activation_commit",
        "reviewed_authority_commit", "authority_source_blob", "authority_contract_sha256",
        "reviewed_materializer_commit", "materializer_source_blob", "sealed_input_raw_sha256",
    }
    if set(seal) != expected_fields or seal.get("schema_version") != 1:
        raise ValueError("H25 authorization seal schema mismatch.")
    if seal.get("purpose") != "harmonic_censoring_h25_population_materialization_authorization_seal":
        raise ValueError("H25 authorization seal purpose mismatch.")
    if seal.get("status") != "reviewed_H25_population_materialization_authorized_once" or seal.get("authorized_action") != "AUTHORIZED_TO_MATERIALIZE_H25_SYNTHETIC_V1_ONCE":
        raise PermissionError("H25 authorization seal is not active.")
    if seal.get("reviewed_materializer_commit") != REVIEWED_MATERIALIZER_COMMIT or seal.get("materializer_source_blob") != REVIEWED_MATERIALIZER_BLOB:
        raise ValueError("H25 reviewed materializer binding mismatch.")
    if _git(root, "rev-parse", "HEAD") != seal.get("activation_commit") or os.environ.get(AUTHORIZATION_ENV) != seal.get("activation_commit"):
        raise PermissionError("H25 activation HEAD/OS binding mismatch.")
    if _git(root, "status", "--porcelain"):
        raise RuntimeError("H25 issuance requires a clean worktree.")
    if _git(root, "merge-base", "--is-ancestor", seal["reviewed_authority_commit"], "HEAD"):
        raise ValueError("H25 authority commit is not an ancestor.")
    authority_blob = _git(root, "rev-parse", f"{seal['reviewed_authority_commit']}:src/polyphonic/harmonic_censoring_h25_materialization_authority.py")
    if authority_blob != seal.get("authority_source_blob"):
        raise ValueError("H25 authority source blob mismatch.")
    contract_raw = (root / AUTHORITY_CONTRACT).read_bytes()
    if hashlib.sha256(contract_raw).hexdigest() != seal.get("authority_contract_sha256"):
        raise ValueError("H25 authority contract SHA mismatch.")
    contract = materializer.parse_sealed_json(contract_raw, "authority contract")
    actual_hashes = {
        name: hashlib.sha256((root / binding["path"]).read_bytes()).hexdigest()
        for name, binding in contract["sealed_git_blobs"].items()
    }
    if seal.get("sealed_input_raw_sha256") != actual_hashes:
        raise ValueError("H25 sealed input hash map mismatch.")
    for name, binding in contract["sealed_git_blobs"].items():
        if _git(root, "rev-parse", f"HEAD:{binding['path']}") != binding["git_blob"]:
            raise ValueError(f"H25 sealed input Git blob mismatch for {name}.")
    if _git(root, "rev-parse", "HEAD:src/polyphonic/harmonic_censoring_h25_population_materializer.py") != REVIEWED_MATERIALIZER_BLOB:
        raise ValueError("H25 materializer HEAD blob mismatch.")
    return seal


class IssuedH25MaterializationAuthority:
    __slots__ = ("__capability", "__state", "__lock")

    def __init__(self, capability: materializer.H25MaterializationCapability, *, _token: object = None) -> None:
        if _token is not _WRAPPER_TOKEN:
            raise PermissionError("H25 one-shot authority is factory-only.")
        self.__capability = capability
        self.__state = "ISSUED"
        self.__lock = threading.Lock()

    def __copy__(self):
        raise TypeError("H25 one-shot authority cannot be copied.")

    def __deepcopy__(self, memo):
        raise TypeError("H25 one-shot authority cannot be deep-copied.")

    def __reduce_ex__(self, protocol):
        raise TypeError("H25 one-shot authority cannot be serialized.")

    @property
    def state(self) -> str:
        return self.__state

    def execute_once(self, numpy_loader: Callable[[], Any] = lambda: __import__("numpy")) -> Path:
        with self.__lock:
            if self.__state != "ISSUED":
                raise PermissionError("H25 one-shot authority is already consumed.")
            self.__state = "CONSUMED_BEFORE_DELEGATION"
        return materializer.materialize_and_publish_h25_population(self.__capability, numpy_loader)


_WRAPPER_TOKEN = object()


def issue_h25_materialization_authority(repository_root: Path) -> IssuedH25MaterializationAuthority:
    """Future issuer.  Dormant now because the required seal does not exist."""
    global _ISSUED
    root = repository_root.resolve(strict=True)
    seal_path = (root / AUTHORIZATION_SEAL).resolve()
    if not seal_path.is_file():
        raise PermissionError("H25 materialization issuer remains dormant: authorization seal absent.")
    seal = _validate_future_seal(root, seal_path.read_bytes())
    with _ISSUE_LOCK:
        if _ISSUED:
            raise PermissionError("H25 materialization authority was already issued in this process.")
        plan = materializer.load_dormant_plan(root)
        materializer.require_reference_environment_before_numpy(plan)
        materializer._require_output_paths_before_numpy(plan)
        capability = materializer.H25MaterializationCapability(
            plan, seal["activation_commit"], REVIEWED_MATERIALIZER_BLOB,
            _token=materializer._CAPABILITY_TOKEN,
        )
        wrapper = IssuedH25MaterializationAuthority(capability, _token=_WRAPPER_TOKEN)
        _ISSUED = True
        return wrapper


__all__ = ["IssuedH25MaterializationAuthority", "issue_h25_materialization_authority"]
