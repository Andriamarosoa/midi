"""Adapter-only dormant publisher for one prevalidated H26 activation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import H26ActivationIssuancePlan

class H26IssuanceFilesystemAdapter(Protocol):
    def exists(self, path: str) -> bool: ...
    def create_exclusive(self, path: str, data: bytes) -> None: ...
    def sync_file(self, path: str) -> None: ...
    def rename_no_replace(self, source: str, destination: str) -> None: ...
    def sync_directory(self, path: str) -> None: ...

@dataclass(frozen=True)
class H26ActivationIssuanceReceipt:
    activation_id: str
    activation_raw_sha256: str
    final_path: str
    published: bool

def publish_prevalidated_activation_with_adapter(plan: H26ActivationIssuancePlan, adapter: H26IssuanceFilesystemAdapter) -> H26ActivationIssuanceReceipt:
    """Apply create-once/no-replace semantics through a caller-supplied adapter."""
    if type(plan) is not H26ActivationIssuancePlan:
        raise TypeError("exact H26ActivationIssuancePlan required")
    if adapter.exists(plan.final_path) or adapter.exists(plan.staging_path):
        raise FileExistsError("terminal activation issuance collision")
    adapter.create_exclusive(plan.staging_path, plan.canonical_bytes)
    adapter.sync_file(plan.staging_path)
    adapter.rename_no_replace(plan.staging_path, plan.final_path)
    adapter.sync_directory(f"{plan.administrative_root}/activation")
    return H26ActivationIssuanceReceipt(plan.activation_id, plan.activation_raw_sha256, plan.final_path, True)

__all__ = ["H26ActivationIssuanceReceipt", "H26IssuanceFilesystemAdapter", "publish_prevalidated_activation_with_adapter"]
