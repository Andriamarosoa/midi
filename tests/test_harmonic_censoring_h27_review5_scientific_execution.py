from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from src.polyphonic.harmonic_censoring_h27_contract import (
    canonical_h27_record_identities, load_h27_dormant_plan,
)
from src.polyphonic.harmonic_censoring_h27_engine import H27EngineResult
from src.polyphonic.harmonic_censoring_h27_recomputer import H27RecomputedResult
from src.polyphonic.harmonic_censoring_h27_scientific_authority import (
    issue_h27_scientific_capability, require_operational_h27_binding,
)
import src.polyphonic.harmonic_censoring_h27_scientific_authority as authority
from src.polyphonic.harmonic_censoring_h27_sealed_population_loader import (
    load_h27_sealed_population_bindings,
)
import src.polyphonic.harmonic_censoring_h27_test_executor as executor
from scripts import h27_review5_scientific_execute_once as runner


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_review5_scientific_execution_contract.json"


def _raw(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


class H27Review5ScientificExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan_source = tempfile.TemporaryDirectory()
        plan_root = Path(self.plan_source.name)
        from src.polyphonic.harmonic_censoring_h27_contract import REVIEWED_GIT_BLOBS
        for relative, blob in REVIEWED_GIT_BLOBS.items():
            destination = plan_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(subprocess.check_output(("git", "cat-file", "blob", blob), cwd=ROOT))
        self.plan = load_h27_dormant_plan(plan_root)
        authority._CAPABILITIES.clear()
        authority._BINDINGS.clear()
        authority._ISSUED_ONCE = False
        claim = b'{"claim":"test"}\n'
        self.index = self._index_value()
        self.index_raw = _raw(self.index)
        self.capability = issue_h27_scientific_capability(
            claim_raw=claim, claim_sha256=hashlib.sha256(claim).hexdigest(),
            population_index_sha256=hashlib.sha256(self.index_raw).hexdigest(),
            execution_authorized=True,
        )

    def tearDown(self) -> None:
        authority._CAPABILITIES.clear()
        authority._BINDINGS.clear()
        authority._ISSUED_ONCE = False
        self.plan_source.cleanup()

    def _index_value(self):
        records = []
        for identity in canonical_h27_record_identities(self.plan):
            names = ["waveform.f64le", "sample-valid-mask.u8"]
            if identity == "baseline/H27-F-A01" or identity == "baseline/H27-F-A02" or "/H27-F-A01/" in identity or "/H27-F-A02/" in identity:
                names.append("alternate-waveform.f64le")
            records.append({
                "record_identity": identity,
                "record_directory": identity,
                "population_namespace": "H27_SYNTHETIC_V1",
                "payload_sha256": {name: hashlib.sha256(name.encode()).hexdigest() for name in names},
                "candidate_pitch": 40,
                "active_pitches": [],
                "proposal_hop_end": 16383,
                "resolution_hop_end": 16639,
                "cents": 0.0,
                "inharmonicity": 0.0,
            })
        return {
            "population_namespace": "H27_SYNTHETIC_V1",
            "record_count": 124,
            "records": records,
            "schema_version": 1,
        }
    def _population(self, root: Path):
        for record in self.index["records"]:
            directory = root / record["record_identity"]
            directory.mkdir(parents=True)
            for name in record["payload_sha256"]:
                (directory / name).touch()
        raw = self.index_raw
        (root / "population_index.json").write_bytes(raw)
        return raw, load_h27_sealed_population_bindings(
            capability=self.capability, plan=self.plan, population_root=root,
            expected_index_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def _result(self, binding, *, corrupt: bool = False):
        identity = binding.record_identity
        fixture = identity.split("/")[1] if identity.startswith("baseline/") else identity.split("/")[2]
        expected = {str(item["id"]): str(item["expected"]) for item in self.plan.fixtures}[fixture]
        if identity.startswith("p2/P2_ZERO_CONTEXT_BOUNDARY_V1/"):
            expected = "AMBIGUOUS"
        if corrupt and fixture == "H27-F-N01":
            expected = "AMBIGUOUS"
        kind = {
            "BIRTH_SUPPORTED":"POSITIVE", "NO_BIRTH":"NEGATIVE",
            "ALREADY_ACTIVE_HISTORY":"ACTIVE_HISTORY",
        }.get(expected, "EQUIVALENCE" if fixture in {"H27-F-A01","H27-F-A02"} else "NONE")
        reason = {
            "BIRTH_SUPPORTED":"complete_positive_certificate",
            "NO_BIRTH":"complete_bounded_negative_certificate",
            "ALREADY_ACTIVE_HISTORY":"candidate_active_before_proposal",
        }.get(expected, "observation_equivalent_latent_causes" if kind == "EQUIVALENCE" else "certificate_gap_or_conflict")
        classes = {role: "VALID_CURRENT_SHORT_ANALYSIS" for role in (
            "current_short", "previous_short", "current_long", "previous_long")}
        if fixture == "H27-F-P01" and identity.startswith("baseline/"):
            classes["previous_short"] = "VALID_EXACT_ZERO_PREVIOUS_SHORT"
            classes["previous_long"] = "VALID_EXACT_ZERO_PREVIOUS_LONG"
        values = dict(
            record_identity=identity, validated_payload_sha256=binding.payload_sha256,
            role_classifications=classes, mask_counts={role:4096 for role in classes},
            outcome=expected, certificate_kind=kind,
            certificate_complete=kind in {"POSITIVE","NEGATIVE","ACTIVE_HISTORY","EQUIVALENCE"},
            exclusive_partial_membership=(), exclusive_energy_ratios=None,
            onset_rise=None, residual_improvement=None, persistence=None,
            bounded_claim_lower_bounds=None, negative_margins=None,
            pitch_dilution_curve=None, early_resolution_reason=reason,
            maximum_sample_read=binding.proposal_hop_end,
        )
        return H27EngineResult(**values)

    def test_contract_is_dormant_and_post_science_work_is_separately_forbidden(self) -> None:
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(value["status"], "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_REAL_EXECUTION")
        for field in (
            "real_execution_authorized", "scientific_authority_creation_authorized",
            "scientific_claim_creation_authorized", "locked_test_authorized",
            "training_authorized", "calibration_authorized", "checkpoint_selection_authorized",
        ):
            self.assertIs(value[field], False)
        post = json.loads((ROOT / "configs/harmonic_censoring_h27_post_science_model_evaluation_contract.json").read_text(encoding="utf-8"))
        self.assertTrue(all(post[field] is False for field in (
            "training_authorized", "checkpoint_generation_authorized",
            "checkpoint_selection_authorized", "locked_test_authorized",
            "final_validation_authorized", "implementation_authorized",
        )))

    def test_runner_refuses_before_platform_or_output_when_not_authorized(self) -> None:
        contract = runner._load_contract(ROOT)
        with patch.object(runner.platform, "system", side_effect=AssertionError("platform accessed")):
            with self.assertRaisesRegex(PermissionError, "not externally authorized"):
                runner._preflight(ROOT, contract)

    def test_atomic_publisher_never_overwrites_an_existing_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            raw, digest = runner._atomic_publish(path, {"status":"complete"})
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                runner._atomic_publish(path, {"status":"replacement"})
            self.assertEqual(path.read_bytes(), raw)
            self.assertFalse((path.parent / ".receipt.json.part").exists())

    def test_process_capability_is_strictly_one_shot(self) -> None:
        with self.assertRaisesRegex(PermissionError, "already been issued"):
            issue_h27_scientific_capability(
                claim_raw=b'{}\n', claim_sha256=hashlib.sha256(b'{}\n').hexdigest(),
                population_index_sha256=hashlib.sha256(self.index_raw).hexdigest(),
                execution_authorized=True,
            )

    def test_loader_requires_issued_capability_and_binds_exact_index_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw, bindings = self._population(Path(temporary))
            self.assertEqual(len(bindings), 124)
            self.assertEqual(tuple(item.record_identity for item in bindings), canonical_h27_record_identities(self.plan))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), bindings[0].population_index_sha256)
            require_operational_h27_binding(bindings[-1])
            forged = object.__new__(type(self.capability))
            with self.assertRaisesRegex(PermissionError, "not operationally issued"):
                load_h27_sealed_population_bindings(
                    capability=forged, plan=self.plan, population_root=Path(temporary),
                    expected_index_sha256=hashlib.sha256(raw).hexdigest(),
                )

    def test_executor_runs_27_in_order_over_124_unique_records_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            secondary_calls = []
            def engine(_np, _capability, _root, binding):
                return self._result(binding)
            def recomputer(_np, _capability, _root, binding):
                return H27RecomputedResult(**vars(self._result(binding)))
            @contextmanager
            def boundary(_capability):
                yield
            def secondary(_plan, _root, identities):
                secondary_calls.append(identities)
                by_identity = {item.record_identity:item for item in bindings}
                return tuple(self._result(by_identity[identity]) for identity in identities)
            with patch.object(executor, "run_h27_engine", engine), patch.object(
                executor, "run_h27_independent_recomputer", recomputer
            ), patch.object(executor, "compare_h27_engine_and_recomputer"), patch.object(
                executor, "operational_h27_engine_boundary", boundary
            ), patch.object(executor, "_secondary_runtime_records", secondary
            ), patch.object(executor, "_require_primary_runtime_identity"
            ):
                result = executor.execute_h27_scientific_sequence(
                    np=object(), capability=self.capability, repository_root=ROOT,
                    plan=self.plan, bindings=bindings,
                )
            self.assertEqual(result.terminal_status, executor.PASS_STATUS)
            self.assertEqual((result.tests_passed, result.tests_failed, result.tests_not_run), (27,0,0))
            self.assertEqual(result.unique_records_evaluated, 124)
            self.assertEqual(result.record_evaluations, 248)
            self.assertEqual(tuple(item.test_id for item in result.test_results), executor.TEST_IDS)
            self.assertEqual(len(secondary_calls), 1)
            self.assertEqual(len(secondary_calls[0]), 4)
            self.assertTrue(all(identity.endswith("runtime=secondary") for identity in secondary_calls[0]))
            self.assertFalse(result.locked_test_used)
            self.assertFalse(result.training_used)

    def test_first_failure_kills_all_later_tests_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            def engine(_np, _capability, _root, binding):
                return self._result(binding, corrupt=True)
            def recomputer(_np, _capability, _root, binding):
                return H27RecomputedResult(**vars(self._result(binding, corrupt=True)))
            @contextmanager
            def boundary(_capability):
                yield
            def secondary(_plan, _root, identities):
                by_identity = {item.record_identity:item for item in bindings}
                return tuple(self._result(by_identity[identity], corrupt=True) for identity in identities)
            with patch.object(executor, "run_h27_engine", engine), patch.object(
                executor, "run_h27_independent_recomputer", recomputer
            ), patch.object(executor, "compare_h27_engine_and_recomputer"), patch.object(
                executor, "operational_h27_engine_boundary", boundary
            ), patch.object(executor, "_secondary_runtime_records", secondary
            ), patch.object(executor, "_require_primary_runtime_identity"
            ):
                result = executor.execute_h27_scientific_sequence(
                    np=object(), capability=self.capability, repository_root=ROOT,
                    plan=self.plan, bindings=bindings,
                )
            self.assertEqual(result.terminal_status, executor.KILL_STATUS["P0"])
            self.assertEqual(result.tests_failed, 1)
            self.assertGreater(result.tests_not_run, 0)
            self.assertEqual(result.test_results[-1].status, "FAIL")


if __name__ == "__main__":
    unittest.main()
