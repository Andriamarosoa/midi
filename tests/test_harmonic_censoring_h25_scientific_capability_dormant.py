import copy
import inspect
import hashlib
import json
import platform
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h25_scientific_capability as capability
from src.polyphonic import run_harmonic_censoring_h25_scientific as runner
from src.polyphonic.harmonic_censoring_h25_scientific_engine import (
    load_h25_dormant_scientific_plan,
)


ROOT = Path(__file__).resolve().parents[1]


class H25ScientificCapabilityDormantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = load_h25_dormant_scientific_plan(ROOT)

    def _capability(self, directory: Path, *, command=()) -> capability.AttestedH25ScientificCapability:
        identity = {
            "implementation": "TEST-ONLY",
            "version": "0",
            "platform_system": "TEST-ONLY",
            "platform_release": "TEST-ONLY",
            "platform_machine": "TEST-ONLY",
            "resolved_executable": str(Path(sys.executable).resolve()),
            "executable_size_bytes": Path(sys.executable).resolve().stat().st_size,
            "executable_sha256": hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
            "command_sha256": hashlib.sha256(runner._canonical(list(command))).hexdigest(),
            "observer_payload_path": "TEST-ONLY",
            "observer_payload_size_bytes": 1,
            "observer_payload_sha256": "a" * 64,
        }
        return capability._new_capability(
            repository_root=ROOT,
            authorization_commit="1" * 40,
            activation_sha256="2" * 64,
            seal_sha256="3" * 64,
            capability_contract_sha256="4" * 64,
            authority_source_blob="5" * 40,
            runner_source_blob="6" * 40,
            engine_source_blob=capability.REVIEWED_ENGINE_BLOB,
            recomputer_source_blob=capability.REVIEWED_RECOMPUTER_BLOB,
            population_directory=directory / "TEST-ONLY-H25-POPULATION",
            population_index_sha256="7" * 64,
            population_provenance_sha256="8" * 64,
            population_receipt_sha256="9" * 64,
            administrative_qualification_sha256=capability.ADMINISTRATIVE_QUALIFICATION_SHA256,
            ordered_fixture_ids=self.plan.fixture_ids,
            ordered_test_ids=self.plan.test_ids,
            ordered_test_phases=tuple(item.phase for item in self.plan.tests),
            claim_path=directory / "TEST-ONLY-H25.claimed.json",
            staging_directory=directory / "TEST-ONLY-H25.staging",
            success_directory=directory / "TEST-ONLY-H25.success",
            terminal_path=directory / "TEST-ONLY-H25.terminal.json",
            forensic_terminal_path=directory / "TEST-ONLY-H25.forensic.json",
            secondary_runtime_command=tuple(command),
            secondary_runtime_timeout_seconds=5,
            secondary_runtime_identity=identity,
        )

    def test_contract_binds_approved_base_population_and_dormant_scope(self) -> None:
        contract = json.loads((ROOT / capability.CAPABILITY_CONTRACT).read_text(encoding="utf-8"))
        reviewed = contract["reviewed_scientific_base"]
        self.assertEqual(reviewed["commit"], capability.REVIEWED_SCIENTIFIC_COMMIT)
        self.assertEqual(reviewed["engine"]["git_blob"], capability.REVIEWED_ENGINE_BLOB)
        self.assertEqual(reviewed["recomputer"]["git_blob"], capability.REVIEWED_RECOMPUTER_BLOB)
        self.assertEqual(reviewed["runner"]["git_blob"], capability.REVIEWED_RUNNER_BLOB)
        population = contract["published_population"]
        self.assertEqual(population["fixture_count"], 36)
        self.assertEqual(population["index"]["raw_sha256"], "814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53")
        self.assertEqual(population["runtime_provenance"]["raw_sha256"], "cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db")
        self.assertEqual(population["receipt"]["raw_sha256"], "dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9")
        self.assertFalse(contract["scope"]["scientific_capability_emitted_now"])
        self.assertEqual(contract["scope"]["P0_P1_P2_executed_counts"], [0, 0, 0])
        self.assertTrue(contract["cross_runtime_P2_007"]["manual_observation_injection_forbidden"])

    def test_issuer_is_dormant_before_contract_population_plan_or_numpy(self) -> None:
        with mock.patch.object(capability, "_validate_dormant_contract") as contract, mock.patch(
            "src.polyphonic.harmonic_censoring_h25_scientific_engine.load_h25_dormant_scientific_plan"
        ) as plan:
            with self.assertRaisesRegex(PermissionError, "seal and activation are absent"):
                capability._issue_h25_scientific_authority(ROOT)
        contract.assert_not_called()
        plan.assert_not_called()
        self.assertNotIn("import numpy", Path(capability.__file__).read_text(encoding="utf-8"))

    def test_capability_and_wrapper_are_factory_only_uncopyable_and_unserializable(self) -> None:
        with self.assertRaisesRegex(TypeError, "no public constructor"):
            capability.AttestedH25ScientificCapability()
        with tempfile.TemporaryDirectory() as temporary:
            value = self._capability(Path(temporary))
            with self.assertRaisesRegex(TypeError, "cannot be copied"):
                copy.copy(value)
            with self.assertRaisesRegex(TypeError, "deep-copied"):
                copy.deepcopy(value)
            with self.assertRaisesRegex(PermissionError, "factory-only"):
                capability.IssuedH25ScientificAuthority(value)

    def test_wrapper_consumes_before_delegation_and_never_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self._capability(Path(temporary))
            authority = capability.IssuedH25ScientificAuthority(
                value, _token=capability._WRAPPER_TOKEN
            )
            self.assertEqual(tuple(inspect.signature(authority.execute_once).parameters), ("repository_root",))
            observed = []

            def fail(checked):
                observed.append(authority.state)
                raise RuntimeError("TEST-ONLY delegate failure")

            with mock.patch.object(
                runner, "_execute_attested_h25_scientific_execution", side_effect=fail
            ):
                with self.assertRaisesRegex(RuntimeError, "delegate failure"):
                    authority.execute_once(ROOT)
            self.assertEqual(observed, ["CONSUMED_BEFORE_DELEGATION"])
            self.assertEqual(authority.state, "CONSUMED_BEFORE_DELEGATION")
            with self.assertRaisesRegex(PermissionError, "already consumed"):
                authority.execute_once(ROOT)

    def test_claim_is_O_EXCL_durable_and_never_reusable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self._capability(Path(temporary))
            claimed = capability._claim_h25_scientific_execution(value)
            self.assertIs(capability.require_claimed_h25_scientific_capability(claimed), value)
            raw = value.claim_path.read_bytes()
            marker = json.loads(raw)
            self.assertEqual(marker["claim_state"], "CLAIMED_BEFORE_FIRST_POPULATION_WAVEFORM")
            self.assertEqual(marker["ordered_test_ids"], list(self.plan.test_ids))
            self.assertFalse(marker["locked_test_used"])
            with self.assertRaises(FileExistsError):
                capability._claim_h25_scientific_execution(value)
            self.assertEqual(value.claim_path.read_bytes(), raw)

    def test_operational_closure_is_atomic_complete_and_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self._capability(Path(temporary))
            capability._claim_h25_scientific_execution(value)
            writer = runner._H25TranscriptWriter(self.plan, value)
            writer.fill_operational_suffix(RuntimeError("TEST-ONLY postclaim failure"))
            writer.publish()
            terminal = runner._finalize(value, self.plan)
            self.assertEqual(terminal, value.terminal_path)
            payload = json.loads(terminal.read_text(encoding="utf-8"))
            self.assertEqual(payload["scientific_status"], runner.H25_INCONCLUSIVE_STATUS)
            self.assertEqual(payload["transcript_record_count"], 27)
            self.assertEqual(payload["operational_error_count"], 1)
            self.assertEqual(payload["not_run_by_operational_failure_count"], 26)
            self.assertFalse((value.terminal_path.parent / (value.terminal_path.name + ".part")).exists())

    def test_secondary_runtime_is_automatic_stdout_only_and_schema_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            script = directory / "secondary.py"
            command = (str(Path(sys.executable).resolve()), str(script.resolve()))
            script.write_text(
                "import hashlib,json,platform,sys\n"
                "from pathlib import Path\n"
                "def canonical(value):\n"
                " return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')+b'\\n'\n"
                "exe=Path(sys.executable).resolve()\n"
                "observer=Path(__file__).resolve()\n"
                "command=[str(exe),str(observer)]\n"
                "identity={'implementation':platform.python_implementation(),'version':platform.python_version(),'platform_system':platform.system(),'platform_release':platform.release(),'platform_machine':platform.machine(),'resolved_executable':str(exe),'executable_size_bytes':exe.stat().st_size,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'command_sha256':hashlib.sha256(canonical(command)).hexdigest(),'observer_payload_path':str(observer),'observer_payload_size_bytes':observer.stat().st_size,'observer_payload_sha256':hashlib.sha256(observer.read_bytes()).hexdigest()}\n"
                "payload={'runtime_id':hashlib.sha256(canonical(identity)).hexdigest(),'runtime_identity':identity,'fixture_measurements':[],'test_records':[]}\n"
                "sys.stdout.buffer.write(canonical(payload))\n",
                encoding="utf-8",
            )
            executable = Path(sys.executable).resolve()
            identity = {
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
                "platform_system": platform.system(),
                "platform_release": platform.release(),
                "platform_machine": platform.machine(),
                "resolved_executable": str(executable),
                "executable_size_bytes": executable.stat().st_size,
                "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "command_sha256": hashlib.sha256(runner._canonical(list(command))).hexdigest(),
                "observer_payload_path": str(script.resolve()),
                "observer_payload_size_bytes": script.stat().st_size,
                "observer_payload_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            }
            value = self._capability(Path(temporary), command=command)
            object.__setattr__(value, "secondary_runtime_identity", identity)
            capability._claim_h25_scientific_execution(value)
            with mock.patch.object(runner, "_validate_recomputed_runtime_test_records") as validate:
                observed = runner._secondary_runtime_observation(value, self.plan)
            self.assertEqual(observed["runtime_identity"], identity)
            validate.assert_called_once_with(self.plan, [])
        self.assertNotIn("input(", Path(runner.__file__).read_text(encoding="utf-8"))

    def test_activation_has_no_self_referential_commit_field(self) -> None:
        contract = json.loads((ROOT / capability.CAPABILITY_CONTRACT).read_text(encoding="utf-8"))
        fields = contract["future_authority_transition"]["activation_exact_fields"]
        self.assertNotIn("activation_commit", fields)
        source = Path(capability.__file__).read_text(encoding="utf-8")
        self.assertNotIn('activation.get("activation_commit")', source)

    def test_forensic_terminal_survives_existing_primary_part(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self._capability(Path(temporary))
            capability._claim_h25_scientific_execution(value)
            primary_part = value.terminal_path.with_name(value.terminal_path.name + ".part")
            primary_part.write_bytes(b"TEST-ONLY failed primary publication")
            terminal = runner._publish_forensic_inconclusive(
                value, RuntimeError("TEST-ONLY primary terminal failure")
            )
            self.assertEqual(terminal, value.forensic_terminal_path)
            self.assertEqual(primary_part.read_bytes(), b"TEST-ONLY failed primary publication")
            payload = json.loads(terminal.read_text(encoding="utf-8"))
            self.assertEqual(payload["scientific_status"], runner.H25_INCONCLUSIVE_STATUS)

    def test_runner_contains_no_prefabricated_pass_test_records(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn('{"test_id": item.test_id, "status": "PASS"}', source)
        self.assertIn("_derive_recomputed_runtime_test_records", source)
        fabricated = [
            {"test_id": item.test_id, "status": "PASS"}
            for item in self.plan.tests
        ]
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            runner._validate_recomputed_runtime_test_records(self.plan, fabricated)

    def test_secondary_runtime_identity_binds_executable_bytes_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(sys.executable).resolve()
            observer = Path(temporary) / "observer.py"
            observer.write_bytes(b"# TEST-ONLY observer\n")
            command = (str(executable), str(observer.resolve()))
            identity = {
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
                "platform_system": platform.system(),
                "platform_release": platform.release(),
                "platform_machine": platform.machine(),
                "resolved_executable": str(executable),
                "executable_size_bytes": executable.stat().st_size,
                "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "command_sha256": hashlib.sha256(runner._canonical(list(command))).hexdigest(),
                "observer_payload_path": str(observer.resolve()),
                "observer_payload_size_bytes": observer.stat().st_size,
                "observer_payload_sha256": hashlib.sha256(observer.read_bytes()).hexdigest(),
            }
            checked = capability._validate_secondary_runtime_identity(ROOT, command, identity)
            self.assertEqual(dict(checked), identity)
            forged = {**identity, "command_sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "command identity mismatch"):
                capability._validate_secondary_runtime_identity(ROOT, command, forged)

    def test_public_runner_is_single_entrypoint_and_stops_at_dormant_issuer(self) -> None:
        with mock.patch.object(
            runner,
            "_issue_h25_scientific_authority",
            side_effect=PermissionError("TEST-ONLY dormant issuer"),
        ) as issue, mock.patch.object(
            runner, "_execute_attested_h25_scientific_execution"
        ) as execute:
            with self.assertRaisesRegex(PermissionError, "dormant issuer"):
                runner.run_h25_scientific_execution(ROOT)
        issue.assert_called_once_with(ROOT)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
