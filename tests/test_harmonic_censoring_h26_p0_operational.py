from __future__ import annotations

from dataclasses import asdict
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src.polyphonic.harmonic_censoring_h26_contract import (
    canonical_json_bytes,
    load_h26_dormant_plan,
)
from src.polyphonic.harmonic_censoring_h26_recomputer import H26TranscriptRecord
from src.polyphonic import run_h26_p0_operational as p0


ROOT = Path(__file__).resolve().parents[1]


class _FakeEvaluator:
    fail_at: str | None = None
    calls: list[str] = []

    def __init__(self, np, plan, boundary):
        del np
        self.plan = plan
        self.boundary = boundary
        self._capability = object()

    def run(self, test_id):
        self.calls.append(test_id)
        return {
            "test_id": test_id,
            "assertions": {"synthetic": test_id != self.fail_at},
            "passed": test_id != self.fail_at,
            "fixture_evidence_sha256": {},
        }


class H26P0OperationalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = load_h26_dormant_plan(ROOT)

    def setUp(self) -> None:
        _FakeEvaluator.fail_at = None
        _FakeEvaluator.calls = []

    def test_contract_is_exactly_dormant(self) -> None:
        contract = p0._load_contract()
        raw = (ROOT / p0.CONTRACT_PATH).read_bytes()
        self.assertEqual(raw, canonical_json_bytes(json.loads(raw), line=True))
        self.assertEqual(contract["status"], "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_P0")
        self.assertIs(contract["real_execution_authorized"], False)
        self.assertEqual(tuple(contract["test_ids"]), p0.P0_IDS)
        self.assertFalse(contract["p1_authorized"])
        self.assertFalse(contract["p2_authorized"])

    def test_dormant_lifecycle_blocks_before_any_external_access(self) -> None:
        with mock.patch.object(p0, "_git") as git, mock.patch.object(
            p0.stop4, "_read_runtime_artifacts"
        ) as runtime:
            with self.assertRaisesRegex(PermissionError, "not externally authorized"):
                p0._require_execution_boundary()
        git.assert_not_called()
        runtime.assert_not_called()

    def test_only_two_lifecycle_triples_are_accepted(self) -> None:
        raw = json.loads((ROOT / p0.CONTRACT_PATH).read_text(encoding="utf-8"))
        active = dict(raw)
        active.update({
            "status": "AUTHORIZED_REAL_P0_ONE_SHOT",
            "real_execution_authorized": True,
            "next_action": "Run the single authorized H26 P0 invocation, then stop for external review",
        })
        invalid = dict(raw); invalid["status"] = "AUTHORIZED_REAL_P0_RETRY"
        with mock.patch.object(p0, "parse_strict_json", return_value=active):
            self.assertTrue(p0._load_contract()["real_execution_authorized"])
        with mock.patch.object(p0, "parse_strict_json", return_value=invalid):
            with self.assertRaisesRegex(ValueError, "contract mismatch"):
                p0._load_contract()

    def test_entrypoint_accepts_no_arguments(self) -> None:
        with mock.patch.object(sys, "argv", ["runner", "unexpected"]):
            with self.assertRaisesRegex(SystemExit, "accepts no arguments"):
                p0.main()

    def test_forged_boundary_is_rejected(self) -> None:
        forged = object.__new__(p0._H26P0Boundary)
        with self.assertRaisesRegex(PermissionError, "attested"):
            p0._require_boundary(forged)

    def _population(self, root: Path) -> tuple[dict[str, object], str]:
        waveform = b"waveform"
        mask = b"mask"
        (root / "wave.bin").write_bytes(waveform)
        (root / "mask.bin").write_bytes(mask)
        common = {
            "waveform": "wave.bin",
            "waveform_sha256": hashlib.sha256(waveform).hexdigest(),
            "sample_valid": "mask.bin",
            "sample_valid_sha256": hashlib.sha256(mask).hexdigest(),
            "alternate_waveform": None,
            "alternate_waveform_sha256": None,
        }
        records = [{"fixture_id": fixture_id, **common} for fixture_id in self.plan.fixture_ids]
        p2_records = [
            {
                "fixture_id": self.plan.fixture_ids[index % 40],
                "test_id": f"H26-T-P2-{index // 17 + 1:03d}",
                "grid_id": "P2_TEST",
                "cell": {"index": index},
                **common,
            }
            for index in range(153)
        ]
        index = {
            "schema_version": 2,
            "population_namespace": "H26_SYNTHETIC_V1",
            "records": records,
            "p2_records": p2_records,
        }
        raw = canonical_json_bytes(index)
        (root / "population_index.json").write_bytes(raw)
        return index, hashlib.sha256(raw).hexdigest()

    def test_complete_population_preflight_and_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, digest = self._population(root)
            with mock.patch.object(p0, "POPULATION_ROOT", root), mock.patch.object(
                p0, "POPULATION_INDEX_SHA", digest
            ):
                value = p0._preflight_population(self.plan)
                self.assertEqual(len(value["records"]), 40)
                self.assertEqual(len(value["p2_records"]), 153)
                (root / "wave.bin").write_bytes(b"corrupt")
                with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                    p0._preflight_population(self.plan)

    def test_population_index_mismatch_precedes_record_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._population(root)
            with mock.patch.object(p0, "POPULATION_ROOT", root), mock.patch.object(
                p0, "POPULATION_INDEX_SHA", "0" * 64
            ):
                with self.assertRaisesRegex(ValueError, "population-index SHA"):
                    p0._preflight_population(self.plan)

    def _fake_boundary(self):
        return object.__new__(p0._H26P0Boundary)

    def _fake_publish(self, root: Path):
        def publish(path, value):
            target = root / path.name if path.parent == p0.EVIDENCE_DIRECTORY else root / path.name
            raw = canonical_json_bytes(value, line=True)
            target.write_bytes(raw)
            return raw, hashlib.sha256(raw).hexdigest()
        return publish

    def test_fake_all_pass_produces_nine_valid_records_and_restores_adapter(self) -> None:
        from src.polyphonic import harmonic_censoring_h26_engine as engine_module

        boundary = self._fake_boundary()
        original = engine_module._require_scientific
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            p0, "_require_boundary", return_value=boundary
        ), mock.patch.object(p0, "_Evaluator", _FakeEvaluator), mock.patch.object(
            p0, "_publish", side_effect=self._fake_publish(Path(directory))
        ):
            records, terminal = p0._run_p0(boundary, self.plan)
        self.assertEqual(terminal, p0.TERMINAL_PASS)
        self.assertEqual(len(records), 9)
        self.assertTrue(all(record.status == "PASSED" for record in records))
        self.assertIs(engine_module._require_scientific, original)

    def test_failure_applies_kill_rule_and_never_calls_later_evaluator(self) -> None:
        boundary = self._fake_boundary()
        _FakeEvaluator.fail_at = "H26-T-P0-004"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            p0, "_require_boundary", return_value=boundary
        ), mock.patch.object(p0, "_Evaluator", _FakeEvaluator), mock.patch.object(
            p0, "_publish", side_effect=self._fake_publish(Path(directory))
        ):
            records, terminal = p0._run_p0(boundary, self.plan)
        self.assertEqual(terminal, p0.TERMINAL_FAIL)
        self.assertEqual(_FakeEvaluator.calls, list(p0.P0_IDS[:4]))
        self.assertEqual(records[3].status, "FAILED")
        self.assertTrue(all(record.status == "NOT_RUN_BY_KILL_RULE" for record in records[4:]))

    def test_exception_after_claim_publishes_inconclusive_and_never_retries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim, transcript, receipt = root / "claim.json", root / "transcript.json", root / "receipt.json"
            evidence = root / "evidence"

            def publish(path, value):
                raw = canonical_json_bytes(value, line=True)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    raise FileExistsError(path)
                path.write_bytes(raw)
                return raw, hashlib.sha256(raw).hexdigest()

            with mock.patch.multiple(
                p0, CLAIM_PATH=claim, TRANSCRIPT_PATH=transcript, RECEIPT_PATH=receipt,
                EVIDENCE_DIRECTORY=evidence, OUTPUT_ROOT=root,
            ), mock.patch.object(p0, "_require_execution_boundary", return_value="a" * 40), mock.patch.object(
                p0, "_require_stop3_stop4"
            ), mock.patch.object(p0, "load_h26_dormant_plan", return_value=self.plan), mock.patch.object(
                p0, "_preflight_population"
            ), mock.patch.object(p0, "_require_scientific_bindings"), mock.patch.object(
                p0, "_require_output_slots_absent"
            ), mock.patch.object(p0, "_publish", side_effect=publish), mock.patch.object(
                p0, "_run_p0", side_effect=RuntimeError("synthetic failure")
            ):
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    p0.execute_h26_p0_once()
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["terminal_status"], p0.TERMINAL_INCONCLUSIVE)
            self.assertEqual(payload["scientific_runner_invocations"], 1)
            self.assertFalse(payload["retry_allowed"])

    def test_scientific_source_blobs_are_unchanged(self) -> None:
        for relative, expected in p0.SOURCE_BLOBS.items():
            actual = subprocess.check_output(
                ("git", "rev-parse", f"HEAD:{relative.as_posix()}"),
                cwd=ROOT, text=True, encoding="utf-8",
            ).strip()
            self.assertEqual(actual, expected)

    def test_source_has_no_locked_test_training_or_model_import(self) -> None:
        source = (ROOT / "src/polyphonic/run_h26_p0_operational.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(any(token in name.lower() for name in imported for token in (
            "locked", "train", "tensorflow", "keras", "checkpoint", "calibr"
        )))
        self.assertNotIn("P1_FAKE", source)
        self.assertNotIn("P2_FAKE", source)


if __name__ == "__main__":
    unittest.main()
