from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from types import SimpleNamespace
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_contract as contract
from src.polyphonic import harmonic_censoring_h27_review4_materializer as review4

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER_PATH = ROOT / "src/polyphonic/harmonic_censoring_h27_review4_materializer.py"
REVIEWED_PATH = ROOT / "src/polyphonic/harmonic_censoring_h27_production_materializer_dormant.py"
SCIENTIFIC_HELPERS = (
    "_canonical_json_bytes", "_numeric", "_f0", "_envelope", "_accumulate_sources",
    "_add_noise", "_render_recipe", "_render_collision", "_grid_cells",
    "_fixture_active_pitches", "_descriptors", "_transformed_recipe", "_mask_bytes", "_render_record",
)

def function_ast(path: Path, name: str) -> str:
    tree=ast.parse(path.read_text(encoding="utf-8"))
    node=next(item for item in tree.body if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)) and item.name==name)
    for child in ast.walk(node):
        if isinstance(child,ast.Name) and child.id=="H27ProductionMaterializationCapability": child.id="CAPABILITY"
    return ast.dump(node,include_attributes=False)

def load_runner():
    path=ROOT / "scripts/h27_review4_execute_once.py"
    spec=importlib.util.spec_from_file_location("h27_review4_runner_test",path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def instantiate_for_test(code, boundary):
    name="h27_review4_test_injected"
    module=ModuleType(name); module.__file__=str(MATERIALIZER_PATH); module.__package__="src.polyphonic"
    module._H27_FROZEN_CONTRACT=contract; module._H27_BOUNDARY_SESSION=boundary
    sys.modules[name]=module
    try: exec(code,module.__dict__)
    finally: del sys.modules[name]
    return module

class Review4MaterializerTests(unittest.TestCase):
    def test_scientific_functions_remain_mechanically_identical(self) -> None:
        for name in SCIENTIFIC_HELPERS:
            self.assertEqual(function_ast(REVIEWED_PATH,name),function_ast(MATERIALIZER_PATH,name),name)

    def test_normal_import_has_only_native_barrier_and_no_mutable_allowlist(self) -> None:
        source=MATERIALIZER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("_ACTIVE_CAPABILITY",source)
        self.assertNotIn("H27Review4Session",source)
        self.assertNotIn("H27Review4CapabilityBinding",source)
        edge=review4.materialize_h27_production_population
        review4._require_capability=lambda value: None
        self.assertIs(review4.materialize_h27_production_population,edge)
        with self.assertRaises((IndexError,TypeError)):
            edge(lambda root: object(),Path("."))

    def test_injected_boundary_is_exact_and_consumes_before_plan(self) -> None:
        code=compile(MATERIALIZER_PATH.read_bytes(),str(MATERIALIZER_PATH),"exec")
        capability,binding=object(),object()
        forged={"capability":capability,"binding":binding,"consume_attested":lambda pair: object(),"population_parent_fd":3}
        module=instantiate_for_test(code,forged)
        with self.assertRaisesRegex(PermissionError,"attested consumption"):
            module.materialize_h27_production_population(lambda root: self.fail("plan reached"),ROOT)
        valid={"capability":capability,"binding":binding,"consume_attested":lambda pair: binding,"population_parent_fd":3}
        module=instantiate_for_test(code,valid)
        with mock.patch.dict("sys.modules",{"numpy":object()}):
            with self.assertRaisesRegex(RuntimeError,"plan marker"):
                module.materialize_h27_production_population(lambda root: (_ for _ in ()).throw(RuntimeError("plan marker")),ROOT)

    def test_operational_helpers_are_not_reexposed_by_module_rebinding(self) -> None:
        code=compile(MATERIALIZER_PATH.read_bytes(),str(MATERIALIZER_PATH),"exec")
        capability,binding=object(),object()
        module=instantiate_for_test(code,{"capability":capability,"binding":binding,"consume_attested":lambda pair: binding,"population_parent_fd":3})
        edge=module.materialize_h27_production_population
        for name in module._OPERATIONAL_GRAPH_NAMES:
            self.assertIs(getattr(module,name),module._DORMANT_NATIVE_BARRIER)
            setattr(module,name,lambda *args: None)
        self.assertIs(module.materialize_h27_production_population,edge)

    def test_attested_consumer_accepts_exact_pair_once(self) -> None:
        runner=load_runner(); capability=object()
        binding=runner.OperationalBinding("a"*64,"b"*64,"c"*40,"d"*64,7,"e"*64)
        consumer=runner.attested_consumer(capability,binding,0,1,2,3); next(consumer)
        with mock.patch.object(runner.os,"getpid",return_value=7),mock.patch.object(runner,"read_fd",side_effect=(b"activation",b"code",b"authority",b"claim")),mock.patch.object(runner,"digest",side_effect=(runner.ACTIVATION_SHA256,"e"*64,"a"*64,"b"*64)),mock.patch.object(runner,"git_blob",return_value="c"*40):
            self.assertIs(consumer.send((capability,binding)),binding)
            with self.assertRaises(StopIteration): consumer.send((capability,binding))

    def test_attested_consumer_rejects_forgery_and_post_claim_drift(self) -> None:
        runner=load_runner(); capability=object()
        binding=runner.OperationalBinding("a"*64,"b"*64,"c"*40,"d"*64,7,"e"*64)
        wrong=runner.attested_consumer(capability,binding,0,1,2,3); next(wrong)
        with self.assertRaises(PermissionError): wrong.send((object(),binding))
        drift=runner.attested_consumer(capability,binding,0,1,2,3); next(drift)
        with mock.patch.object(runner.os,"getpid",return_value=7),mock.patch.object(runner,"read_fd",side_effect=(b"activation",b"changed")),mock.patch.object(runner,"digest",side_effect=(runner.ACTIVATION_SHA256,"0"*64)):
            with self.assertRaisesRegex(PermissionError,"code drift"): drift.send((capability,binding))

    def test_frozen_module_supports_dataclass_and_cleans_registry(self) -> None:
        runner=load_runner(); name="h27_test_frozen_dataclass"
        raw=b"from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Row:\n    value: int\n"
        self.assertNotIn(name,sys.modules)
        module=runner.frozen_module(name,raw,"frozen_dataclass.py")
        self.assertEqual(module.Row(7).value,7)
        self.assertNotIn(name,sys.modules)

    def test_frozen_module_rejects_preexisting_registry_collision(self) -> None:
        runner=load_runner(); name="h27_test_frozen_collision"; existing=ModuleType(name)
        with mock.patch.dict(sys.modules,{name:existing}):
            with self.assertRaisesRegex(PermissionError,"name collision"):
                runner.frozen_module(name,b"executed=True\n","collision.py")
            self.assertIs(sys.modules[name],existing)
            self.assertFalse(hasattr(existing,"executed"))

    def test_frozen_module_cleans_registry_after_execution_error(self) -> None:
        runner=load_runner(); name="h27_test_frozen_error"
        with self.assertRaisesRegex(RuntimeError,"frozen marker"):
            runner.frozen_module(name,b"raise RuntimeError('frozen marker')\n","error.py")
        self.assertNotIn(name,sys.modules)

    def test_frozen_module_rejects_registry_replacement_and_cleans_it(self) -> None:
        runner=load_runner(); name="h27_test_frozen_replacement"
        raw=b"import sys\nsys.modules[__name__]=object()\n"
        with self.assertRaisesRegex(PermissionError,"registry drift"):
            runner.frozen_module(name,raw,"replacement.py")
        self.assertNotIn(name,sys.modules)

    def test_binding_seal_and_all_sixteen_administrative_inputs_are_exact(self) -> None:
        runner=load_runner(); raw=MATERIALIZER_PATH.read_bytes()
        materializer={"path":runner.OPERATIONAL_REPOSITORY_PATH,"git_blob_sha1":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),"size_bytes":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest()}
        binding_raw=(ROOT/runner.OPERATIONAL_BINDING_PATH).read_bytes(); binding=json.loads(binding_raw)
        seal=json.loads((ROOT/runner.OPERATIONAL_SEAL_PATH).read_bytes())
        expected=[{"path":path,"git_blob_sha1":blob,"size_bytes":size,"raw_sha256":sha} for path,blob,size,sha in runner.ADMINISTRATIVE_INPUTS]
        self.assertEqual(len(expected),16); self.assertEqual(binding["materializer"],materializer); self.assertEqual(binding["administrative_chain"],expected)
        self.assertEqual(seal["materializer"],materializer)
        self.assertEqual(seal["identity_binding"],{"path":runner.OPERATIONAL_BINDING_PATH,"git_blob_sha1":hashlib.sha1(b"blob "+str(len(binding_raw)).encode()+b"\0"+binding_raw).hexdigest(),"size_bytes":len(binding_raw),"raw_sha256":hashlib.sha256(binding_raw).hexdigest()})

    def test_execution_composition_runner_is_separately_bound_and_sealed(self) -> None:
        runner=load_runner(); runner_path=ROOT/"scripts/h27_review4_execute_once.py"; runner_raw=runner_path.read_bytes()
        runner_identity={"path":"scripts/h27_review4_execute_once.py","git_blob_sha1":hashlib.sha1(b"blob "+str(len(runner_raw)).encode()+b"\0"+runner_raw).hexdigest(),"size_bytes":len(runner_raw),"raw_sha256":hashlib.sha256(runner_raw).hexdigest()}
        binding_path=ROOT/"configs/harmonic_censoring_h27_review4_execution_composition_identity_binding.json"; binding_raw=binding_path.read_bytes(); binding=json.loads(binding_raw)
        seal=json.loads((ROOT/"configs/harmonic_censoring_h27_review4_execution_composition_external_seal.json").read_bytes())
        expected_admin=[{"path":path,"git_blob_sha1":blob,"size_bytes":size,"raw_sha256":sha} for path,blob,size,sha in runner.ADMINISTRATIVE_INPUTS]
        self.assertEqual(binding["runner"],runner_identity); self.assertEqual(binding["administrative_chain"],expected_admin)
        self.assertEqual(binding["required_target_head"],runner.REQUIRED_HEAD); self.assertEqual(seal["runner"],runner_identity)
        self.assertEqual(seal["execution_composition_identity_binding"],{"path":"configs/harmonic_censoring_h27_review4_execution_composition_identity_binding.json","git_blob_sha1":hashlib.sha1(b"blob "+str(len(binding_raw)).encode()+b"\0"+binding_raw).hexdigest(),"size_bytes":len(binding_raw),"raw_sha256":hashlib.sha256(binding_raw).hexdigest()})
        self.assertTrue(binding["bootstrap_contract"]["verify_runner_size_blob_sha_before_execution"])
        self.assertTrue(binding["bootstrap_contract"]["verification_must_precede_ack_and_runner_launch"])
        self.assertTrue(seal["seal_semantics"]["bootstrap_must_verify_runner_before_ack_and_launch"])

    def test_runner_orders_claim_then_injection_and_seals_authority_chain(self) -> None:
        source=(ROOT/"scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        self.assertLess(source.index("claim_fd,claim_raw=write_new_at"),source.index('name="h27_frozen_materializer"'))
        self.assertLess(source.index('name="h27_frozen_materializer"'),source.index("materialize_h27_production_population"))
        self.assertIn('"sealed_administrative_inputs":administrative',source)
        self.assertIn('compile(operational_raw',source)
        self.assertNotIn("H27Review4Session",source)
        self.assertNotIn("run_h27_engine",source); self.assertNotIn("run_h27_independent_recomputer",source)

    def test_staging_is_fully_verified_before_no_replace_rename_and_created_fd_stays_open(self) -> None:
        materializer_source=MATERIALIZER_PATH.read_text(encoding="utf-8")
        publish=function_ast(MATERIALIZER_PATH,"_publish")
        self.assertLess(publish.index("_verify_staging"),publish.index("_rename_no_replace"))
        verify=function_ast(MATERIALIZER_PATH,"_verify_staging")
        for token in ("population_index.json","_collect_tree","payload_sha256","record_count"):
            self.assertIn(token,verify)
        runner_source=(ROOT/"scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        body=runner_source[runner_source.index("def write_new_at"):runner_source.index("def frozen_module")]
        self.assertLess(body.index("os.fsync(parent_fd)"),body.index("reopened,observed=open_relative"))
        self.assertLess(body.index("created_info=os.fstat(created)"),body.index("reopened_info=os.fstat(reopened)"))
        self.assertIn("st_dev",body); self.assertIn("st_ino",body); self.assertTrue(materializer_source)

    @unittest.skipIf(os.name=="nt","POSIX descriptor/mode mutation regression")
    def test_payload_mutated_after_index_is_rejected_before_rename(self) -> None:
        capability,binding=object(),object()
        module=instantiate_for_test(compile(MATERIALIZER_PATH.read_bytes(),str(MATERIALIZER_PATH),"exec"),{"capability":capability,"binding":binding,"consume_attested":lambda pair: binding,"population_parent_fd":3})
        entry=module.materialize_h27_production_population
        publish=next(cell.cell_contents for cell in entry.__closure__ or () if callable(cell.cell_contents) and getattr(cell.cell_contents,"__name__","")=="_publish")
        private=publish.__globals__; verify=private["_verify_staging"]
        identities=tuple(f"record-{index:03d}" for index in range(124))
        descriptors=tuple(SimpleNamespace(identity=identity,fixture_id=identity,candidate_pitch=40,active_pitches=(40,),proposal_hop_end=2,resolution_hop_end=4,cents=0.0,inharmonicity=0.0) for identity in identities)
        private["canonical_h27_record_identities"]=lambda plan: identities
        private["_descriptors"]=lambda plan: descriptors
        plan=SimpleNamespace(specifications={"baseline_waveform_recipes":{identity:{} for identity in identities}})
        waveform=b"\0"*(16640*8); mask=b"\0"*(16640*4)
        payload_sha={"waveform.f64le":hashlib.sha256(waveform).hexdigest(),"sample-valid-mask.u8":hashlib.sha256(mask).hexdigest()}
        records=[]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); os.chmod(root,0o700)
            for descriptor in descriptors:
                directory=root/descriptor.identity; directory.mkdir(mode=0o700)
                (directory/"waveform.f64le").write_bytes(waveform); os.chmod(directory/"waveform.f64le",0o600)
                (directory/"sample-valid-mask.u8").write_bytes(mask); os.chmod(directory/"sample-valid-mask.u8",0o600)
                records.append({"record_identity":descriptor.identity,"record_directory":descriptor.identity,"population_namespace":"H27_SYNTHETIC_V1","payload_sha256":dict(payload_sha),"candidate_pitch":40,"active_pitches":[40],"proposal_hop_end":2,"resolution_hop_end":4,"cents":0.0,"inharmonicity":0.0})
            index_raw=private["_canonical_json_bytes"]({"schema_version":1,"population_namespace":"H27_SYNTHETIC_V1","record_count":124,"records":records})
            (root/"population_index.json").write_bytes(index_raw); os.chmod(root/"population_index.json",0o600)
            (root/identities[0]/"waveform.f64le").write_bytes(waveform+b"x")
            staging_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                with self.assertRaisesRegex(PermissionError,"digest mismatch"):
                    verify(capability,staging_fd,plan,records,index_raw)
            finally: os.close(staging_fd)

if __name__=="__main__": unittest.main()
