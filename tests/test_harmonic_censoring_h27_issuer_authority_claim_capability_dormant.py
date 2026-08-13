from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import tempfile
import threading
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as boundary
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as materializer


NONCE = "4" * 64
ISSUED_AT = "2026-08-13T12:34:56Z"


class H27IssuerAuthorityClaimCapabilityDormantTests(unittest.TestCase):
    def _sandbox(self, parent: str) -> Path:
        root = Path(parent) / "h27-dormant-boundary"
        root.mkdir()
        return root

    def test_exact_reviewed_bindings_validate_without_side_effects(self) -> None:
        loaded = boundary.validate_h27_dormant_issuer_bindings()
        self.assertEqual(
            set(loaded),
            {
                "identity_binding",
                "identity_binding_seal",
                "materializer_seal",
                "activation_contract",
                "activation_seal",
                "authority_contract",
                "authority_contract_seal",
            },
        )
        self.assertEqual(loaded["identity_binding"]["reviewed_materializer"]["git_blob_sha1"], "79f399359e366781f9526098c98a93cca71b1b49")
        self.assertFalse(loaded["identity_binding"]["current_state"]["authority_exists"])

    def test_authority_template_is_deterministic_complete_and_non_operational(self) -> None:
        first = boundary.build_h27_future_authority_payload_template(NONCE, ISSUED_AT)
        second = boundary.build_h27_future_authority_payload_template(NONCE, ISSUED_AT)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        self.assertNotIn(b"\r", first)
        value = boundary.validate_h27_future_authority_payload_template(first)
        self.assertEqual(value["issuer_identity"], "h27-execution-codex-mac-primary")
        self.assertEqual(value["expected_counts"], {"baseline_record_count": 17, "p2_record_count": 107, "record_count": 124})
        self.assertEqual(len(value["sealed_h27_inputs"]), 5)
        self.assertFalse(value["activation_artifact"]["exists"])
        for field in ("authority_exists", "materialization_authorized", "scientific_execution_authorized", "locked_test_used"):
            self.assertIs(value[field], False)

    def test_authority_template_rejects_bad_nonce_time_and_tampering(self) -> None:
        with self.assertRaises(ValueError):
            boundary.build_h27_future_authority_payload_template("x" * 64, ISSUED_AT)
        with self.assertRaises(ValueError):
            boundary.build_h27_future_authority_payload_template(NONCE, "2026-08-13")
        raw = boundary.build_h27_future_authority_payload_template(NONCE, ISSUED_AT)
        value = json.loads(raw)
        value["materialization_authorized"] = True
        tampered = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(PermissionError):
            boundary.validate_h27_future_authority_payload_template(tampered)

    def test_public_operational_edge_is_native_dormant_barrier(self) -> None:
        edge = boundary.issue_h27_materialization_authority_and_capability
        self.assertIs(type(edge), type(().__getitem__))
        self.assertEqual(edge.__self__, ())
        self.assertEqual(edge.__name__, "__getitem__")
        exploding = mock.Mock(side_effect=AssertionError("must not inspect"))
        with self.assertRaises((TypeError, IndexError)):
            edge(exploding)
        self.assertFalse(exploding.called)

    def test_sandbox_lifecycle_creates_durable_authority_then_claim_and_consumes_once(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = self._sandbox(parent)
            real_open = os.open
            modes: list[int] = []
            flags_seen: list[int] = []

            def capture_open(path: object, flags: int, mode: int = 0o777) -> int:
                if flags & os.O_CREAT:
                    modes.append(mode)
                    flags_seen.append(flags)
                return real_open(path, flags, mode)

            with mock.patch.object(boundary.os, "open", side_effect=capture_open), mock.patch.object(
                boundary, "_fsync_directory", wraps=boundary._fsync_directory,
            ) as sync_directory:
                session = boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)
            self.assertEqual(modes, [0o600, 0o600])
            self.assertTrue(all(flags & os.O_EXCL and flags & os.O_CREAT and flags & os.O_WRONLY for flags in flags_seen))
            self.assertEqual(sync_directory.call_count, 2)
            self.assertTrue(session.authority_path.is_file())
            self.assertTrue(session.claim_path.is_file())
            self.assertEqual(hashlib.sha256(session.authority_path.read_bytes()).hexdigest(), session.authority_sha256)
            self.assertEqual(hashlib.sha256(session.claim_path.read_bytes()).hexdigest(), session.claim_sha256)
            session.consume(session.capability)
            with self.assertRaisesRegex(PermissionError, "already consumed"):
                session.consume(session.capability)

    def test_capability_is_process_local_identity_attested_noncopyable_and_not_materializer_capability(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            session = boundary._issue_dormant_sandbox_session(self._sandbox(parent), NONCE, ISSUED_AT)
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                with self.assertRaises((TypeError, PermissionError)):
                    operation(session.capability)
            forged = object.__new__(boundary._H27DormantBoundaryCapability)
            with self.assertRaisesRegex(PermissionError, "identity/process mismatch"):
                session.consume(forged)
            with self.assertRaises(PermissionError):
                boundary._H27DormantBoundaryCapability()
            self.assertEqual(boundary._H27DormantBoundaryCapability.__slots__, ("__weakref__",))
            self.assertFalse(hasattr(boundary, "_CAPABILITY_REGISTRY"))
            self.assertNotIsInstance(session.capability, materializer.H27ActivationCapableProductionMaterializationCapability)

    def test_process_mismatch_rejected_without_consuming_valid_capability(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            session = boundary._issue_dormant_sandbox_session(self._sandbox(parent), NONCE, ISSUED_AT)
            real_pid = os.getpid()
            with mock.patch.object(boundary.os, "getpid", return_value=real_pid + 1):
                with self.assertRaisesRegex(PermissionError, "identity/process mismatch"):
                    session.consume(session.capability)
            session.consume(session.capability)

    def test_atomic_consumption_allows_only_one_concurrent_winner(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            session = boundary._issue_dormant_sandbox_session(self._sandbox(parent), NONCE, ISSUED_AT)
            results: list[str] = []
            lock = threading.Lock()

            def run() -> None:
                try:
                    session.consume(session.capability)
                    result = "ok"
                except PermissionError:
                    result = "rejected"
                with lock:
                    results.append(result)

            workers = [threading.Thread(target=run) for _ in range(8)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
            self.assertEqual(results.count("ok"), 1)
            self.assertEqual(results.count("rejected"), 7)

    def test_post_claim_code_drift_is_terminal_and_capability_stays_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            identity = [b"reviewed-code"]
            session = boundary._issue_dormant_sandbox_session(
                self._sandbox(parent), NONCE, ISSUED_AT, identity_supplier=lambda: identity[0],
            )
            identity[0] = b"drifted-code"
            with self.assertRaisesRegex(PermissionError, "post-claim code identity drift"):
                session.consume(session.capability)
            self.assertTrue(session.claim_path.exists())
            with self.assertRaisesRegex(PermissionError, "already consumed"):
                session.consume(session.capability)

    def test_existing_authority_or_claim_is_terminal_before_new_write(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = self._sandbox(parent)
            first = boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)
            authority_before = first.authority_path.read_bytes()
            claim_before = first.claim_path.read_bytes()
            with self.assertRaises(FileExistsError):
                boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)
            self.assertEqual(first.authority_path.read_bytes(), authority_before)
            self.assertEqual(first.claim_path.read_bytes(), claim_before)

    def test_claim_fsync_interruption_leaves_claim_and_prevents_retry(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = self._sandbox(parent)
            real_fsync = os.fsync
            calls = 0

            def fail_claim_file(descriptor: int) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic claim fsync interruption")
                real_fsync(descriptor)

            with mock.patch.object(boundary.os, "fsync", side_effect=fail_claim_file):
                with self.assertRaisesRegex(OSError, "claim fsync interruption"):
                    boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)
            authority_path = root / "authority" / "h27-materialization-v1.json"
            claim_path = root / "claims" / "h27-synthetic-v1.consumed.json"
            self.assertTrue(authority_path.exists())
            self.assertTrue(claim_path.exists())
            with self.assertRaises(FileExistsError):
                boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)

    def test_claim_parent_fsync_interruption_leaves_claim_and_prevents_retry(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = self._sandbox(parent)
            calls = 0

            def fail_claim_parent(path: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic claim parent fsync interruption")

            with mock.patch.object(boundary, "_fsync_directory", side_effect=fail_claim_parent):
                with self.assertRaisesRegex(OSError, "claim parent fsync interruption"):
                    boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)
            self.assertTrue((root / "authority" / "h27-materialization-v1.json").exists())
            self.assertTrue((root / "claims" / "h27-synthetic-v1.consumed.json").exists())
            with self.assertRaises(FileExistsError):
                boundary._issue_dormant_sandbox_session(root, NONCE, ISSUED_AT)

    def test_sandbox_restriction_rejects_non_temp_and_real_administrative_roots(self) -> None:
        with self.assertRaises(PermissionError):
            boundary._require_sandbox_root(Path.cwd())
        with self.assertRaises((PermissionError, FileNotFoundError)):
            boundary._require_sandbox_root(Path("/Users/amcarene/h27-admin"))


if __name__ == "__main__":
    unittest.main()
