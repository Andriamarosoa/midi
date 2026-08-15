#!/usr/bin/env python3
"""Prepare, but never execute, the sealed H27 thirteen-blob SSH delivery."""
from __future__ import annotations

import ast
import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Mapping, Sequence


ACK_ENV = "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARE"
WORKTREE_TEXT = r"C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2"
WORKTREE = Path(WORKTREE_TEXT)
EXPECTED_HEAD = "c0bb8d20862f80cabc72ea64a5d437750b7c12e8"
EXPECTED_BRANCH = "refs/heads/codex/independent-note-neural-v2"
GIT_PREFIX = (
    "git", "--no-optional-locks", "--no-replace-objects", "-C", WORKTREE_TEXT,
)
SSH_COMMAND = (
    "ssh", "-T", "amcarene@100.89.128.87", "env",
    "H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1", "/usr/bin/python3", "-",
)
SSH_COMMAND_TEXT = (
    "ssh -T amcarene@100.89.128.87 env "
    "H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 /usr/bin/python3 -"
)

CONTRACT = {
    "path": "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract.json",
    "git_blob_sha1": "83fba2bc54bb22712680453bc3253b85aca50ca4",
    "size_bytes": 10717,
    "raw_sha256": "c538c3567f46993f8a1a420a272db552d07ea7e2f2362142700d9670b31f0df2",
}
CONTRACT_SEAL = {
    "path": "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract_external_seal.json",
    "git_blob_sha1": "b579a3604e1aa08d9485d10585ebba24febdf446",
    "size_bytes": 5112,
    "raw_sha256": "5c6535d8178f03cee8f91e14fac448567603900cca2e1261758e10ae13166daa",
}
RECEIVER = {
    "path": "scripts/h27_receive_exact_thirteen_source_odb_blobs_one_shot.py",
    "git_blob_sha1": "9d32cac8ddb29e43975a6b82f5c1c39a91f93df4",
    "size_bytes": 119406,
    "raw_sha256": "996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000",
}
RECEIVER_BINDING = {
    "path": "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding.json",
    "git_blob_sha1": "676b04ce154b2210b714f87d20ae191017aa57c1",
    "size_bytes": 6625,
    "raw_sha256": "47914c545457de3622d4c7aedf96cc5b457b2eb937f4ae95c970f5ff98bfe67b",
}
RECEIVER_SEAL = {
    "path": "configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding_external_seal.json",
    "git_blob_sha1": "60242774586277d9eccd8049d8d7c0062e08942b",
    "size_bytes": 6040,
    "raw_sha256": "e9d30ee756843fc9475a08673ca0415e7aa88a4ff9928f409c5b2d1b160d5ec6",
}
IDENTITY_KEYS = ("path", "git_blob_sha1", "size_bytes", "raw_sha256")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PreparedExactTransport:
    command: tuple[str, ...]
    command_text: str
    receiver_source: bytes
    object_count: int
    aggregate_raw_size_bytes: int
    transport_executed: bool = False

    def summary(self) -> dict[str, object]:
        return {
            "status": "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP",
            "sender_head": EXPECTED_HEAD,
            "sender_branch": EXPECTED_BRANCH,
            "receiver_git_blob_sha1": RECEIVER["git_blob_sha1"],
            "receiver_size_bytes": len(self.receiver_source),
            "receiver_raw_sha256": hashlib.sha256(self.receiver_source).hexdigest(),
            "object_count": self.object_count,
            "aggregate_raw_size_bytes": self.aggregate_raw_size_bytes,
            "ssh_invocation_exact": self.command_text,
            "transport_executed": self.transport_executed,
            "remote_acknowledgement_set": False,
            "object_delivery_executed": False,
            "source_odb_changed": False,
            "target_odb_changed": False,
            "science_or_locked_test": False,
        }


def clean_git_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    inherited = dict(os.environ if source is None else source)
    cleaned = {key: value for key, value in inherited.items() if not key.upper().startswith("GIT_")}
    cleaned["GIT_TERMINAL_PROMPT"] = "0"
    cleaned["GIT_NO_LAZY_FETCH"] = "1"
    return cleaned


def run_git(arguments: Sequence[str], *, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    command = [*GIT_PREFIX, *arguments]
    if tuple(command[: len(GIT_PREFIX)]) != GIT_PREFIX:
        raise PermissionError("every sender Git command must use the exact sealed repository prefix")
    return subprocess.run(
        command,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        env=clean_git_environment(),
    )


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def require_identity(raw: bytes, expected: Mapping[str, object]) -> None:
    if set(expected) != set(IDENTITY_KEYS):
        raise ValueError("identity key set drift")
    blob_id = expected["git_blob_sha1"]
    sha256 = expected["raw_sha256"]
    size = expected["size_bytes"]
    if not isinstance(blob_id, str) or HEX40.fullmatch(blob_id) is None:
        raise ValueError("invalid expected Git blob id")
    if not isinstance(sha256, str) or HEX64.fullmatch(sha256) is None:
        raise ValueError("invalid expected SHA-256")
    if type(size) is not int or size < 0:
        raise ValueError("invalid expected size")
    if len(raw) != size:
        raise ValueError(f"size mismatch for {expected['path']}")
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError(f"SHA-256 mismatch for {expected['path']}")
    if git_blob_id(raw) != blob_id:
        raise ValueError(f"Git blob mismatch for {expected['path']}")


def read_exact_blob(expected: Mapping[str, object]) -> bytes:
    blob_id = expected["git_blob_sha1"]
    if not isinstance(blob_id, str) or HEX40.fullmatch(blob_id) is None:
        raise ValueError("invalid blob identity before Git read")
    raw = run_git(("cat-file", "blob", blob_id)).stdout
    require_identity(raw, expected)
    return raw


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_object(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError(f"{label} must be UTF-8 LF without BOM")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def require_platform_ack_and_zero_arguments() -> None:
    if platform.system().lower() != "windows":
        raise PermissionError("sender preparation requires Windows")
    if os.environ.get(ACK_ENV) != "1":
        raise PermissionError(f"set {ACK_ENV}=1 for local dormant preparation")
    if len(sys.argv) != 1:
        raise PermissionError("sender preparation accepts zero arguments")


def verify_exact_sender_state() -> None:
    head = run_git(("rev-parse", "HEAD")).stdout.decode("ascii").strip()
    branch = run_git(("symbolic-ref", "-q", "HEAD")).stdout.decode("utf-8").strip()
    status = run_git(("status", "--porcelain=v1", "--untracked-files=all")).stdout
    if head != EXPECTED_HEAD:
        raise PermissionError("sender HEAD differs from the sealed reviewed commit")
    if branch != EXPECTED_BRANCH:
        raise PermissionError("sender branch differs from the sealed branch")
    if status != b"":
        raise PermissionError("sender worktree is not clean")


def extract_embedded_objects(receiver_source: bytes) -> tuple[dict[str, object], ...]:
    if receiver_source.startswith(b"\xef\xbb\xbf") or b"\r" in receiver_source or not receiver_source.endswith(b"\n"):
        raise ValueError("receiver source must be UTF-8 LF without BOM")
    tree = ast.parse(receiver_source.decode("utf-8"), filename=str(RECEIVER["path"]))
    values: list[object] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "EMBEDDED_OBJECTS" for target in node.targets):
            values.append(ast.literal_eval(node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "EMBEDDED_OBJECTS":
            values.append(ast.literal_eval(node.value))
    if len(values) != 1 or not isinstance(values[0], tuple):
        raise ValueError("receiver must define exactly one literal EMBEDDED_OBJECTS tuple")
    rows = values[0]
    if len(rows) != 13 or not all(isinstance(row, dict) for row in rows):
        raise ValueError("receiver must embed exactly thirteen object dictionaries")
    return tuple(dict(row) for row in rows)


def verify_receiver_graph_and_objects() -> tuple[bytes, int]:
    receiver_raw = read_exact_blob(RECEIVER)
    contract_raw = read_exact_blob(CONTRACT)
    contract_seal_raw = read_exact_blob(CONTRACT_SEAL)
    binding_raw = read_exact_blob(RECEIVER_BINDING)
    seal_raw = read_exact_blob(RECEIVER_SEAL)
    contract = parse_json_object(contract_raw, "contract")
    contract_seal = parse_json_object(contract_seal_raw, "contract seal")
    binding = parse_json_object(binding_raw, "receiver binding")
    seal = parse_json_object(seal_raw, "receiver seal")

    if contract.get("objects") is None or not isinstance(contract["objects"], list):
        raise ValueError("contract object list missing")
    expected_objects = contract["objects"]
    if len(expected_objects) != 13 or not all(isinstance(row, dict) for row in expected_objects):
        raise ValueError("contract must declare exactly thirteen objects")
    if contract.get("future_transport", {}).get("invocation_exact") != SSH_COMMAND_TEXT:
        raise ValueError("contract SSH invocation drift")
    if contract.get("sender", {}).get("git_head_exact") != EXPECTED_HEAD:
        raise ValueError("contract sender HEAD drift")
    if contract.get("sender", {}).get("branch_exact") != EXPECTED_BRANCH:
        raise ValueError("contract sender branch drift")
    if contract_seal.get("contract") != CONTRACT:
        raise ValueError("contract seal identity drift")
    if binding.get("receiver") != RECEIVER or seal.get("receiver") != RECEIVER:
        raise ValueError("receiver identity graph drift")
    if seal.get("identity_binding") != RECEIVER_BINDING:
        raise ValueError("receiver binding identity drift")
    if binding.get("approved_contract") != CONTRACT or seal.get("approved_contract") != CONTRACT:
        raise ValueError("approved contract identity drift")
    if binding.get("approved_contract_external_seal") != CONTRACT_SEAL:
        raise ValueError("approved contract seal identity drift")
    if seal.get("approved_contract_external_seal") != CONTRACT_SEAL:
        raise ValueError("sealed approved contract seal identity drift")

    embedded = extract_embedded_objects(receiver_raw)
    projected = [{key: row[key] for key in IDENTITY_KEYS} for row in embedded]
    if projected != expected_objects:
        raise ValueError("receiver embedded identity order differs from contract")
    aggregate = 0
    for embedded_row, expected in zip(embedded, expected_objects):
        if set(embedded_row) != {*IDENTITY_KEYS, "base64"}:
            raise ValueError("embedded object key set drift")
        encoded = embedded_row["base64"]
        if not isinstance(encoded, str):
            raise ValueError("embedded base64 must be text")
        decoded = base64.b64decode(encoded.encode("ascii"), validate=True)
        if base64.b64encode(decoded).decode("ascii") != encoded:
            raise ValueError("embedded payload is not canonical base64")
        require_identity(decoded, expected)
        source_raw = read_exact_blob(expected)
        if source_raw != decoded:
            raise ValueError(f"sender ODB bytes differ from receiver for {expected['path']}")
        aggregate += len(source_raw)
    if aggregate != 75730:
        raise ValueError("aggregate source payload size drift")
    return receiver_raw, aggregate


def prepare_exact_transport() -> PreparedExactTransport:
    require_platform_ack_and_zero_arguments()
    verify_exact_sender_state()
    receiver_raw, aggregate = verify_receiver_graph_and_objects()
    if SSH_COMMAND_TEXT != " ".join(SSH_COMMAND):
        raise ValueError("SSH command tuple/text mismatch")
    return PreparedExactTransport(
        command=SSH_COMMAND,
        command_text=SSH_COMMAND_TEXT,
        receiver_source=receiver_raw,
        object_count=13,
        aggregate_raw_size_bytes=aggregate,
    )


def main() -> int:
    prepared = prepare_exact_transport()
    print(json.dumps(prepared.summary(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
