from __future__ import annotations

from dataclasses import asdict
import ast
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
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

    def _rewrite_index(self, root: Path, index: dict[str, object]) -> str:
        raw = canonical_json_bytes(index)
        (root / "population_index.json").write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_population_schema_namespace_cardinality_and_order_fail_closed(self) -> None:
        mutations = (
            ("schema", lambda value: value.__setitem__("schema_version", 3)),
            ("namespace", lambda value: value.__setitem__("population_namespace", "WRONG")),
            ("cardinality", lambda value: value["records"].pop()),
            ("order", lambda value: value["records"].reverse()),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                index, _ = self._population(root)
                mutate(index)
                digest = self._rewrite_index(root, index)
                with mock.patch.object(p0, "POPULATION_ROOT", root), mock.patch.object(
                    p0, "POPULATION_INDEX_SHA", digest
                ):
                    with self.assertRaisesRegex(ValueError, "schema/namespace|cardinality|order"):
                        p0._preflight_population(self.plan)

    def test_population_path_escape_and_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outer = Path(directory).resolve()
            root = outer / "population"; root.mkdir()
            index, _ = self._population(root)
            escaped = outer / "escaped.bin"; escaped.write_bytes(b"waveform")
            index["records"][0]["waveform"] = "../escaped.bin"
            digest = self._rewrite_index(root, index)
            with mock.patch.object(p0, "POPULATION_ROOT", root), mock.patch.object(
                p0, "POPULATION_INDEX_SHA", digest
            ):
                with self.assertRaisesRegex(ValueError, "escapes root"):
                    p0._preflight_population(self.plan)

            link = root / "linked.bin"
            try:
                link.symlink_to(root / "wave.bin")
            except OSError:
                self.skipTest("symlink creation unavailable")
            index["records"][0]["waveform"] = "linked.bin"
            digest = self._rewrite_index(root, index)
            with mock.patch.object(p0, "POPULATION_ROOT", root), mock.patch.object(
                p0, "POPULATION_INDEX_SHA", digest
            ):
                with self.assertRaisesRegex(ValueError, "symlink forbidden"):
                    p0._preflight_population(self.plan)

    def test_stop3_and_live_runtime_mismatch_fail_before_authority(self) -> None:
        with mock.patch.object(
            p0.stop4, "_read_runtime_artifacts", side_effect=ValueError("STOP3 SHA mismatch")
        ), mock.patch.object(p0, "_regular_file") as regular:
            with self.assertRaisesRegex(ValueError, "STOP3 SHA mismatch"):
                p0._require_stop3_stop4()
        regular.assert_not_called()
        with mock.patch.object(
            p0.stop4, "_read_runtime_artifacts", return_value=(object(), object(), object(), object(), object())
        ), mock.patch.object(
            p0.stop4, "_require_live_runtime_matches_stop3", side_effect=ValueError("live runtime mismatch")
        ), mock.patch.object(p0, "_regular_file") as regular:
            with self.assertRaisesRegex(ValueError, "live runtime mismatch"):
                p0._require_stop3_stop4()
        regular.assert_not_called()

    def test_authority_id_sha_and_seal_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority_dir = root / "authority"; authority_dir.mkdir()
            seal_dir = root / "seal"; seal_dir.mkdir()
            authority = authority_dir / f"{p0.AUTHORITY_SHA}.json"
            seal = seal_dir / f"{p0.AUTHORITY_SHA}.json"
            authority.write_bytes(canonical_json_bytes({"authority_id": "wrong"}, line=True))
            seal.write_bytes(b"wrong-seal")
            common = (
                mock.patch.object(p0.stop4, "AUTHORITY_DIRECTORY", authority_dir),
                mock.patch.object(p0.stop4, "SEAL_DIRECTORY", seal_dir),
                mock.patch.object(p0.stop4, "_read_runtime_artifacts", return_value=(0, 0, 0, 0, 0)),
                mock.patch.object(p0.stop4, "_require_live_runtime_matches_stop3"),
            )
            with common[0], common[1], common[2], common[3], mock.patch.object(
                p0, "_sha", side_effect=lambda path: p0.AUTHORITY_SHA if path == authority else hashlib.sha256(path.read_bytes()).hexdigest()
            ):
                with self.assertRaisesRegex(ValueError, "authority ID mismatch"):
                    p0._require_stop3_stop4()
            with common[0], common[1], common[2], common[3]:
                with self.assertRaisesRegex(ValueError, "authority SHA mismatch"):
                    p0._require_stop3_stop4()
            authority.write_bytes(canonical_json_bytes({"authority_id": p0.AUTHORITY_ID}, line=True))
            with common[0], common[1], common[2], common[3], mock.patch.object(
                p0, "_sha", side_effect=lambda path: p0.AUTHORITY_SHA if path == authority else "0" * 64
            ):
                with self.assertRaisesRegex(ValueError, "authority seal mismatch"):
                    p0._require_stop3_stop4()

    def test_scientific_source_blob_mismatch_fails_closed(self) -> None:
        with mock.patch.object(p0, "_git", return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "source blob mismatch"):
                p0._require_scientific_bindings()

    def test_output_slots_and_parent_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            admin = Path(directory).resolve() / "admin"; admin.mkdir()
            science = admin / "science"; output = science / "p0"
            claim, transcript, receipt = output / "claim.json", output / "transcript.json", output / "receipt.json"
            evidence = output / "evidence"
            with mock.patch.multiple(
                p0, ADMIN_ROOT=admin, OUTPUT_ROOT=output, CLAIM_PATH=claim,
                TRANSCRIPT_PATH=transcript, RECEIPT_PATH=receipt,
                EVIDENCE_DIRECTORY=evidence,
            ):
                p0._require_output_slots_absent()
                claim.write_bytes(b"occupied")
                with self.assertRaisesRegex(FileExistsError, "output root"):
                    p0._require_output_slots_absent()
            if science.exists():
                shutil.rmtree(science)
            elsewhere = Path(directory).resolve() / "elsewhere"; elsewhere.mkdir()
            try:
                science.symlink_to(elsewhere, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlink creation unavailable")
            with mock.patch.multiple(p0, ADMIN_ROOT=admin, OUTPUT_ROOT=output):
                with self.assertRaisesRegex(ValueError, "ancestor symlink"):
                    p0._require_output_slots_absent()

    def test_each_terminal_slot_or_staging_slot_prevents_consumption(self) -> None:
        for slot_name in ("claim.json", "transcript.json", "receipt.json"):
            for staged in (False, True):
                with self.subTest(slot=slot_name, staged=staged), tempfile.TemporaryDirectory() as directory:
                    admin = Path(directory).resolve() / "admin"; admin.mkdir()
                    output = admin / "science" / "p0"; output.mkdir(parents=True)
                    claim, transcript, receipt = output / "claim.json", output / "transcript.json", output / "receipt.json"
                    target = output / slot_name
                    if staged:
                        target = target.with_name("." + target.name + ".part")
                    target.write_bytes(b"occupied")
                    with mock.patch.multiple(
                        p0, ADMIN_ROOT=admin, OUTPUT_ROOT=output, CLAIM_PATH=claim,
                        TRANSCRIPT_PATH=transcript, RECEIPT_PATH=receipt,
                        EVIDENCE_DIRECTORY=output / "evidence",
                    ):
                        with self.assertRaises(FileExistsError):
                            p0._require_output_slots_absent()

    def test_boundary_revalidates_head_claim_and_population(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.json"; claim.write_bytes(b"claim")
            population = root / "population"; population.mkdir()
            index = population / "population_index.json"; index.write_bytes(b"index")
            claim_sha = hashlib.sha256(b"claim").hexdigest()
            index_sha = hashlib.sha256(b"index").hexdigest()
            with mock.patch.object(p0, "CLAIM_PATH", claim), mock.patch.object(
                p0, "POPULATION_ROOT", population
            ), mock.patch.object(p0, "POPULATION_INDEX_SHA", index_sha), mock.patch.object(
                p0, "_git", side_effect=lambda *args: "a" * 40 if args == ("rev-parse", "HEAD") else ""
            ):
                boundary = p0._mint_boundary("a" * 40, claim_sha)
                self.assertIs(p0._require_boundary(boundary), boundary)
                index.write_bytes(b"changed")
                with self.assertRaisesRegex(PermissionError, "population index changed"):
                    p0._require_boundary(boundary)

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

    def test_evidence_publication_failure_restores_adapter(self) -> None:
        from src.polyphonic import harmonic_censoring_h26_engine as engine_module

        boundary = self._fake_boundary()
        original = engine_module._require_scientific
        with mock.patch.object(p0, "_require_boundary", return_value=boundary), mock.patch.object(
            p0, "_Evaluator", _FakeEvaluator
        ), mock.patch.object(p0, "_publish", side_effect=OSError("evidence publish failed")):
            with self.assertRaisesRegex(OSError, "evidence publish failed"):
                p0._run_p0(boundary, self.plan)
        self.assertIs(engine_module._require_scientific, original)
        self.assertEqual(_FakeEvaluator.calls, [p0.P0_IDS[0]])

    def test_transcript_publication_failure_is_terminal_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim, transcript, receipt = root / "claim.json", root / "transcript.json", root / "receipt.json"
            evidence = root / "evidence"

            def publish(path, value):
                if path == transcript:
                    raise OSError("transcript publish failed")
                raw = canonical_json_bytes(value, line=True)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                return raw, hashlib.sha256(raw).hexdigest()

            records = [
                H26TranscriptRecord(test.test_id, test.order, test.phase, "PASSED", "a" * 64, None)
                for test in self.plan.tests[:9]
            ]
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
                p0, "_run_p0", return_value=(records, p0.TERMINAL_PASS)
            ):
                with self.assertRaisesRegex(OSError, "transcript publish failed"):
                    p0.execute_h26_p0_once()
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["terminal_status"], p0.TERMINAL_INCONCLUSIVE)
            self.assertIsNone(payload["transcript_raw_sha256"])

    @unittest.skipUnless(platform.system() == "Darwin", "Darwin no-replace primitive")
    def test_real_darwin_publish_is_create_exclusive_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            p0.stop4._publish(path, b"first\n")
            with self.assertRaises(FileExistsError):
                p0.stop4._publish(path, b"second\n")
            self.assertEqual(path.read_bytes(), b"first\n")

    def test_p0_005_oracle_checks_nonzero_equation_bytes_mask_and_state(self) -> None:
        import numpy as np

        evaluator = object.__new__(p0._Evaluator)
        evaluator.np = np
        evaluator.plan = self.plan
        evaluator._cache = {}
        evaluator._observation_cache = {}
        waveform = np.ones(16640, dtype=np.float64)
        mask = np.ones(16640, dtype=np.bool_)
        for fixture_id in (f"H26-F-A{i:02d}" for i in range(1, 7)):
            evaluator._cache[fixture_id] = SimpleNamespace(
                measurement={"observation_equivalent": True},
                resolution={"outcome": "AMBIGUOUS"},
                operands={"state_before": "PENDING_NEW", "state_after": "AMBIGUOUS"},
            )
            evaluator._observation_cache[fixture_id] = SimpleNamespace(
                waveform=waveform.copy(), alternate_waveform=waveform.copy(), sample_valid=mask.copy()
            )
        evaluator.evidence = lambda fixture_id: evaluator._cache[fixture_id]
        assertions = evaluator._005()
        self.assertTrue(all(assertions.values()))
        evaluator._observation_cache["H26-F-A01"].alternate_waveform[0] = 2.0
        self.assertFalse(evaluator._005()["H26-F-A01_observation_mask_state_equal"])

    def test_p0_007_checks_exact_preregistered_endpoints(self) -> None:
        evaluator = object.__new__(p0._Evaluator)
        evaluator.plan = self.plan
        evaluator._cache = {}
        for fixture_id in ("H26-F-P02", "H26-F-N02", "H26-F-H02", "H26-F-A02"):
            evaluator._cache[fixture_id] = SimpleNamespace(operands={
                "proposal_hop_end": 16383, "resolution_hop_end": 16639,
                "maximum_sample_read": 16383, "state_before": "PENDING_NEW",
                "state_after": "AMBIGUOUS",
            })
        evaluator.evidence = lambda fixture_id: evaluator._cache[fixture_id]
        self.assertTrue(all(evaluator._007().values()))
        evaluator._cache["H26-F-P02"].operands["proposal_hop_end"] = 16382
        self.assertFalse(evaluator._007()["H26-F-P02"])

    def test_p0_008_rejects_every_preregistered_leakage_field(self) -> None:
        evaluator = object.__new__(p0._Evaluator)
        evaluator.plan = self.plan
        evaluator._cache = {}
        base = {
            "candidate_active": False, "support_valid": False,
            "observation_equivalent": False, "exclusive_partial_ranks": (),
            "maximum_sample_read": 16383, "proposal_hop_end": 16383,
            "resolution_hop_end": 16639, "state_before": "PENDING_NEW",
            "state_after": "AMBIGUOUS", "active_pitches": (),
            "candidate_pitch": 60, "perturbation": None,
        }
        for fixture_id in ("H26-F-P03", "H26-F-N03", "H26-F-H03", "H26-F-A03"):
            evaluator._cache[fixture_id] = SimpleNamespace(operands=dict(base))
        evaluator.evidence = lambda fixture_id: evaluator._cache[fixture_id]
        assertions = evaluator._008()
        self.assertTrue(all(assertions.values()))

    def test_evidence_hashes_are_limited_to_current_test_fixtures(self) -> None:
        evaluator = object.__new__(p0._Evaluator)
        evaluator.plan = self.plan
        declared = tuple(self.plan.tests[1].fixture_ids)
        record = SimpleNamespace(measurement={}, resolution={}, operands={})
        evaluator._cache = {fixture_id: record for fixture_id in (*declared, "H26-F-P10")}
        with mock.patch.object(p0._Evaluator, "_002", return_value={"oracle": True}):
            result = evaluator.run("H26-T-P0-002")
        self.assertEqual(tuple(result["fixture_evidence_sha256"]), declared)

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
