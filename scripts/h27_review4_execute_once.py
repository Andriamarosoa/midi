#!/usr/bin/env python3
"""Darwin-only, no-retry H27 Review-4 population materialization."""
from __future__ import annotations

import hashlib, importlib.metadata, json, os, platform, stat, subprocess, sys
from pathlib import Path
from types import ModuleType

ACK = "H27_REVIEW4_MATERIALIZATION_EXECUTE"
TARGET = Path("/Users/amcarene/midi-worker/repository")
REQUIRED_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
ADMIN = Path("/Users/amcarene/h27-admin")
ACTIVATION = ADMIN / "activation/h27-materialization-v1.json"
AUTHORITY = ADMIN / "authority/h27-materialization-v1.json"
CLAIM = ADMIN / "claims/h27-synthetic-v1.consumed.json"
TERMINAL = ADMIN / "review4/h27-review4-terminal.json"
POPULATION_PARENT = ADMIN / "population"
FINAL_NAME, STAGING_NAME = "h27-synthetic-v1", ".h27-synthetic-v1.staging"
OPERATIONAL_MODULE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer.py"
OPERATIONAL_REPOSITORY_PATH = "src/polyphonic/harmonic_censoring_h27_review4_materializer.py"
OPERATIONAL_MODULE_SHA256 = "8941ed24443aff54fd0ec331e74efb87b71b045e352e0a9ce19a379a31b9650a"
OPERATIONAL_MODULE_BLOB = "dab34b25b09e13aac2d46712e688aae2426fcd56"
OPERATIONAL_BINDING_PATH = "configs/harmonic_censoring_h27_review4_materializer_identity_binding.json"
OPERATIONAL_SEAL_PATH = "configs/harmonic_censoring_h27_review4_materializer_external_seal.json"
OPERATIONAL_BINDING_FILE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer_identity_binding.json"
OPERATIONAL_SEAL_FILE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer_external_seal.json"
OPERATIONAL_BINDING_IDENTITY = ("14eb7ffa320ae99a1fd3f70c56afc73c75ee5adc",1512,"1f495b010b86f9c47c3c95d56c1aa887ec9d22f8ab857b221a98be88f3e07cc6")
OPERATIONAL_SEAL_IDENTITY = ("28093a9511670f18fdb8b7aba7f6f57bb23ce69d",1118,"3a330d160de20354670e1d9d849a38bd82dd5b3368790307a1533e94a9032347")
AUTHORITY_INSTANCE_ID = "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a"
ACTIVATION_SHA256 = "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2"
CONTRACT_PATH = "src/polyphonic/harmonic_censoring_h27_contract.py"
SEALED_COMPONENTS = (
 (CONTRACT_PATH,"0499b33a2762851d2a1fafa40b9c4976cea767e8",12183,"34daaf2a8a2cbfc33d8ed8c8ce2a6552abb08bc30642759c8733ffda1dbb56d9"),
 ("src/polyphonic/harmonic_censoring_h27_engine.py","d21c60e5a96cba5ba6d90dacedd49b8b1eaa5635",24030,"a5403a675ebff4a61dfefed36f21fd529f940eb82fe466569e77e4d9ab007eb7"),
 ("src/polyphonic/harmonic_censoring_h27_materializer_dormant.py","394f25a51f854cf629ef184694c4dcf1a45904b8",12949,"90950664e764f6b982df3a44fd08bd534ecb190b3d7019cc49cc60b57a1c3eb7"),
 ("src/polyphonic/harmonic_censoring_h27_production_materializer_dormant.py","d3a903acfa67daf822d50aab005b88943a8c18fa",22223,"1d4b0b651c2c916a1a1bcd71578aa263074290c90fd381be867b77ef46cc0a25"),
 ("src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py","79f399359e366781f9526098c98a93cca71b1b49",32243,"02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70"),
 ("src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py","ec61eef88dce7591fd411af230568b1e1d44d62e",18915,"d3d06f8c087845089094ff71f29d8745581d391784b9bbc40abeb57b0ba42f2f"),
 ("src/polyphonic/harmonic_censoring_h27_one_shot_execution_composition_dormant.py","c57dbd4ccd6f9ef9b75e3698580ca14d66d74682",7289,"6e2ccf317e071eed583b85995c11c386dfc5b306bb9a3b4c283dbf2fe0c6c9bb"),
 ("src/polyphonic/harmonic_censoring_h27_recomputer.py","4949137f5a827e436c92b361f36f66b6f0312bcb",22456,"4411e27fb1c2e9846f9e5688e90cb6bcc8d1d9bfd0fd12726ffd510e9f1a286a"),
)

def require(ok: bool, message: str) -> None:
    if not ok: raise PermissionError(message)
def digest(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def git_blob(raw: bytes) -> str: return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(value: object) -> bytes:
    return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()
def strict_json(raw: bytes) -> dict[str,object]:
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,"H27 duplicate JSON key"); out[key]=value
        return out
    value=json.loads(raw.decode(),object_pairs_hook=pairs,parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    require(type(value) is dict,"H27 JSON root must be object"); return value
def git(*args: str, allowed=(0,)) -> bytes:
    env={k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
    result=subprocess.run(["git","--no-optional-locks","--no-replace-objects","-c","core.hooksPath=/dev/null","-C",str(TARGET),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,env=env)
    require(result.returncode in allowed,"H27 Git preflight failed: "+repr(args)); return result.stdout

def open_directory(path: Path) -> int:
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); info=os.fstat(fd)
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),f"H27 unsafe directory: {path}")
    return fd
def open_subdirectory(parent_fd: int,name: str) -> int:
    require("/" not in name and name not in ("",".",".."),"H27 unsafe subdirectory name")
    fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd); info=os.fstat(fd)
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),"H27 unsafe administrative subdirectory")
    return fd
def read_fd(fd: int, mode: int|None=None) -> bytes:
    os.lseek(fd,0,os.SEEK_SET); before=os.fstat(fd)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1,"H27 regular single-link file required")
    if mode is not None: require(stat.S_IMODE(before.st_mode)==mode,"H27 file mode drift")
    chunks=[]
    while True:
        chunk=os.read(fd,1024*1024)
        if not chunk: break
        chunks.append(chunk)
    after=os.fstat(fd)
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),"H27 file changed while read")
    return b"".join(chunks)
def open_relative(parent_fd: int,name: str,mode=0o600):
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent_fd)
    try: return fd,read_fd(fd,mode)
    except BaseException: os.close(fd); raise
def write_new_at(parent_fd: int,name: str,raw: bytes):
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
    try:
        offset=0
        while offset<len(raw):
            count=os.write(fd,raw[offset:]); require(count>0,"H27 incomplete write"); offset+=count
        os.fsync(fd)
    finally: os.close(fd)
    os.fsync(parent_fd); check,observed=open_relative(parent_fd,name)
    require(observed==raw,"H27 durable byte-exact reread failed"); return check,observed
def frozen_module(name: str,raw: bytes,filename: str,injected=None):
    module=ModuleType(name); module.__file__=filename; module.__package__=name.rpartition(".")[0]
    for key,value in (injected or {}).items(): setattr(module,key,value)
    exec(compile(raw,filename,"exec",dont_inherit=True),module.__dict__); return module

def verify_runtime(contract):
    expected=contract["runtime_exact"]; executable=Path(sys.executable).resolve(strict=True)
    observed={"implementation":platform.python_implementation(),"version":platform.python_version(),"platform_system":platform.system(),"platform_release":platform.release(),"platform_machine":platform.machine(),"resolved_executable":executable.as_posix(),"executable_size_bytes":executable.stat().st_size,"executable_sha256":digest(executable.read_bytes())}
    require(all(observed[k]==expected[k] for k in observed),"H27 exact runtime mismatch")
    require(all(os.environ.get(k)==v for k,v in contract["process_environment_exact"].items()),"H27 process environment mismatch")
    distribution=importlib.metadata.distribution("numpy")
    require(distribution.version==expected["numpy_version"],"H27 NumPy version mismatch")
    matches={"numpy":[],"blas":[]}
    for relative in distribution.files or ():
        candidate=Path(distribution.locate_file(relative)).resolve(strict=True)
        if not candidate.is_file(): continue
        size=candidate.stat().st_size
        if size not in (expected["numpy_multiarray_size_bytes"],expected["blas_library_size_bytes"]): continue
        raw=candidate.read_bytes(); sha=digest(raw)
        if size==expected["numpy_multiarray_size_bytes"] and sha==expected["numpy_multiarray_sha256"]: matches["numpy"].append(candidate)
        if size==expected["blas_library_size_bytes"] and sha==expected["blas_library_sha256"]: matches["blas"].append(candidate)
    require(len(matches["numpy"])==len(matches["blas"])==1 and "openblas" in matches["blas"][0].name.lower(),"H27 NumPy/OpenBLAS identity mismatch")

def preclaim():
    require(sys.platform=="darwin" and len(sys.argv)==1,"H27 Darwin zero-argument runner required")
    require(os.environ.get(ACK)=="I_UNDERSTAND_H27_REVIEW4_IS_ONE_SHOT","H27 ACK missing")
    require(git("rev-parse","HEAD").decode().strip()==REQUIRED_HEAD,"H27 HEAD mismatch")
    require(git("symbolic-ref","-q","HEAD",allowed=(0,1))==b"","H27 target must be detached")
    require(git("status","--porcelain=v1","--untracked-files=all")==b"","H27 target dirty")
    frozen={}
    for relative,blob,size,sha in SEALED_COMPONENTS:
        raw=git("cat-file","blob",REQUIRED_HEAD+":"+relative)
        require((git_blob(raw),len(raw),digest(raw))==(blob,size,sha),"H27 component drift: "+relative); frozen[relative]=raw
    admin_fd=open_directory(ADMIN); review_parent=open_subdirectory(admin_fd,"review4")
    operational_fd=os.open(OPERATIONAL_MODULE.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=review_parent); materializer_git=read_fd(operational_fd,0o400)
    require((git_blob(materializer_git),digest(materializer_git))==(OPERATIONAL_MODULE_BLOB,OPERATIONAL_MODULE_SHA256),"H27 operational identity mismatch")
    binding_fd=os.open(OPERATIONAL_BINDING_FILE.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=review_parent); binding_raw=read_fd(binding_fd,0o400); os.close(binding_fd)
    seal_fd=os.open(OPERATIONAL_SEAL_FILE.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=review_parent); seal_raw=read_fd(seal_fd,0o400); os.close(seal_fd)
    require((git_blob(binding_raw),len(binding_raw),digest(binding_raw))==OPERATIONAL_BINDING_IDENTITY,"H27 operational binding identity mismatch")
    require((git_blob(seal_raw),len(seal_raw),digest(seal_raw))==OPERATIONAL_SEAL_IDENTITY,"H27 operational seal identity mismatch")
    binding,seal=strict_json(binding_raw),strict_json(seal_raw)
    require(binding["materializer"]["git_blob_sha1"]==OPERATIONAL_MODULE_BLOB and binding["materializer"]["raw_sha256"]==OPERATIONAL_MODULE_SHA256,"H27 binding mismatch")
    require(seal["identity_binding"]["git_blob_sha1"]==git_blob(binding_raw) and seal["materializer"]["git_blob_sha1"]==OPERATIONAL_MODULE_BLOB,"H27 seal mismatch")
    activation_parent=open_subdirectory(admin_fd,"activation"); activation_fd,activation_raw=open_relative(activation_parent,ACTIVATION.name); os.close(activation_parent)
    require(digest(activation_raw)==ACTIVATION_SHA256,"H27 activation digest mismatch"); activation=strict_json(activation_raw)
    require(activation.get("authority_instance_id")==AUTHORITY_INSTANCE_ID and activation.get("single_use") is True and activation.get("consumed") is False and activation.get("issuer_id")=="h27-execution-codex-mac-primary","H27 activation semantics mismatch")
    authority_parent=open_subdirectory(admin_fd,"authority"); claim_parent=open_subdirectory(admin_fd,"claims")
    population_parent=open_subdirectory(admin_fd,"population"); os.close(admin_fd)
    for parent,name in ((authority_parent,AUTHORITY.name),(claim_parent,CLAIM.name),(population_parent,FINAL_NAME),(population_parent,STAGING_NAME),(review_parent,TERMINAL.name)):
        try: os.stat(name,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise FileExistsError("H27 one-shot destination preexists: "+name)
    operational_raw=materializer_git
    activation_contract=strict_json(git("cat-file","blob",REQUIRED_HEAD+":configs/harmonic_censoring_h27_materialization_activation_contract.json")); verify_runtime(activation_contract)
    contract=frozen_module("h27_frozen_contract",frozen[CONTRACT_PATH],CONTRACT_PATH)
    frozen_inputs={}
    for path,blob in contract.REVIEWED_GIT_BLOBS.items():
        raw=git("cat-file","blob",REQUIRED_HEAD+":"+path.as_posix())
        require(git_blob(raw)==blob,"H27 frozen scientific input drift: "+path.as_posix())
        frozen_inputs[path]=raw
    def frozen_bound_json(repository,path):
        require(Path(repository)==TARGET,"H27 frozen plan repository mismatch")
        require(path in frozen_inputs,"H27 unbound frozen plan input")
        return contract.parse_strict_json(frozen_inputs[path])
    contract._bound_json=frozen_bound_json
    materializer=frozen_module("h27_frozen_materializer",operational_raw,str(OPERATIONAL_MODULE),{"_H27_FROZEN_CONTRACT":contract})
    critical_names=("_require_capability","_validate_session_before_consumption","_render_record","_write_new","_rename_no_replace","_publish","materialize_h27_production_population","H27ProductionMaterializationCapability","H27Review4CapabilityBinding","H27Review4Session")
    critical_objects={name:getattr(materializer,name) for name in critical_names}
    return activation,activation_contract,contract,materializer,critical_objects,activation_fd,operational_fd,authority_parent,claim_parent,population_parent,review_parent

def attested_consumer(capability,binding,operational_fd,authority_fd,claim_fd):
    request=yield
    require(type(request) is tuple and len(request)==2 and request[0] is capability and request[1] is binding,"H27 exact capability/binding pair required")
    require(os.getpid()==binding.process_id,"H27 process drift")
    require(digest(read_fd(operational_fd,0o400))==binding.code_identity_sha256,"H27 code drift after claim")
    require(digest(read_fd(authority_fd,0o600))==binding.authority_sha256,"H27 authority drift after claim")
    require(digest(read_fd(claim_fd,0o600))==binding.claim_sha256,"H27 claim drift after claim")
    yield binding

def consume_and_run(state):
    activation,activation_contract,contract,materializer,critical_objects,activation_fd,operational_fd,authority_parent,claim_parent,population_parent,review_parent=state
    nonce=str(activation["invocation_nonce"])
    authority={"schema_version":1,"authority_type":"h27_review4_materialization_authority","authority_instance_id":AUTHORITY_INSTANCE_ID,"activation":{"raw_sha256":ACTIVATION_SHA256,"issuer_identity":activation["issuer_id"]},"invocation_nonce":nonce,"required_head":REQUIRED_HEAD,"population_namespace":"H27_SYNTHETIC_V1","expected_counts":{"total":124,"baseline":17,"p2":107},"fixed_destinations":{"final":(POPULATION_PARENT/FINAL_NAME).as_posix(),"staging":(POPULATION_PARENT/STAGING_NAME).as_posix()},"runtime_exact":activation_contract["runtime_exact"],"process_environment_exact":activation_contract["process_environment_exact"],"sealed_h27_inputs":activation_contract["sealed_h27_inputs"],"sealed_components":[{"path":path,"git_blob_sha1":blob,"size_bytes":size,"raw_sha256":sha} for path,blob,size,sha in SEALED_COMPONENTS],"materializer":{"git_blob_sha1":OPERATIONAL_MODULE_BLOB,"raw_sha256":OPERATIONAL_MODULE_SHA256},"operational_identity_binding":{"git_blob_sha1":OPERATIONAL_BINDING_IDENTITY[0],"raw_sha256":OPERATIONAL_BINDING_IDENTITY[2]},"operational_external_seal":{"git_blob_sha1":OPERATIONAL_SEAL_IDENTITY[0],"raw_sha256":OPERATIONAL_SEAL_IDENTITY[2]},"single_use":True,"science_authorized":False,"locked_test_used":False}
    authority_fd,authority_raw=write_new_at(authority_parent,AUTHORITY.name,canonical(authority))
    claim={"schema_version":1,"claim_type":"h27_review4_materialization_consumed","activation_sha256":ACTIVATION_SHA256,"authority_sha256":digest(authority_raw),"materializer_blob":OPERATIONAL_MODULE_BLOB,"materializer_sha256":OPERATIONAL_MODULE_SHA256,"operational_binding_sha256":OPERATIONAL_BINDING_IDENTITY[2],"operational_seal_sha256":OPERATIONAL_SEAL_IDENTITY[2],"runtime_process_id":os.getpid(),"invocation_nonce":nonce,"fixed_destinations":authority["fixed_destinations"],"retry_allowed":False,"consumed":True}
    claim_fd,claim_raw=write_new_at(claim_parent,CLAIM.name,canonical(claim))
    capability=object.__new__(materializer.H27ProductionMaterializationCapability)
    binding=materializer.H27Review4CapabilityBinding(digest(authority_raw),digest(claim_raw),OPERATIONAL_MODULE_BLOB,nonce,os.getpid(),OPERATIONAL_MODULE_SHA256)
    consumer=attested_consumer(capability,binding,operational_fd,authority_fd,claim_fd); next(consumer)
    session=materializer.H27Review4Session(capability,binding,consumer.send,authority_fd,claim_fd,population_parent)
    require(all(getattr(materializer,name,None) is value for name,value in critical_objects.items()),"H27 frozen materializer rebinding detected")
    critical_objects["materialize_h27_production_population"](session,contract.load_h27_dormant_plan,TARGET)
    plan=contract.load_h27_dormant_plan(TARGET); terminal=reconcile(contract,materializer,plan,population_parent)
    write_new_at(review_parent,TERMINAL.name,canonical(terminal)); return terminal

def open_chain(root_fd,relative):
    current=os.dup(root_fd)
    try:
        for part in relative.split("/"):
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current); os.close(current); current=child
        return current
    except BaseException: os.close(current); raise

def collect_tree(fd,prefix=""):
    files=set()
    for name in os.listdir(fd):
        info=os.stat(name,dir_fd=fd,follow_symlinks=False)
        require(not stat.S_ISLNK(info.st_mode),"H27 tree symlink forbidden")
        relative=prefix+name
        if stat.S_ISDIR(info.st_mode):
            require(stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),"H27 tree directory invariant failed")
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try: files.update(collect_tree(child,relative+"/"))
            finally: os.close(child)
        else:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600 and info.st_uid==os.getuid(),"H27 tree file invariant failed")
            files.add(relative)
    return files

def reconcile(contract,materializer,plan,population_parent):
    final_fd=os.open(FINAL_NAME,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=population_parent)
    index_fd,index_raw=open_relative(final_fd,"population_index.json"); os.close(index_fd); index=strict_json(index_raw); records=index.get("records")
    require(type(records) is list and index.get("record_count")==124 and len(records)==124,"H27 index count mismatch")
    expected=list(contract.canonical_h27_record_identities(plan)); identities=[r.get("record_identity") for r in records]
    require(identities==expected and len(set(identities))==124,"H27 identity/order mismatch")
    grid_counts={"P2_GAIN_V1":9,"P2_PHASE_V1":12,"P2_NOISE_V1":12,"P2_ZERO_CONTEXT_BOUNDARY_V1":4,"P2_CENTS_INHARMONICITY_V1":18,"P2_PERMUTATION_V1":32,"P2_RUNTIME_V1":8,"P2_HOP_SHIFT_V1":12}
    require(all(sum(str(value).startswith("p2/"+grid+"/") for value in identities)==count for grid,count in grid_counts.items()),"H27 exact eight-grid distribution mismatch")
    fields=("record_identity","record_directory","population_namespace","payload_sha256","candidate_pitch","active_pitches","proposal_hop_end","resolution_hop_end","cents","inharmonicity")
    descriptors={d.identity:d for d in materializer._descriptors(plan)}; recipes=plan.specifications["baseline_waveform_recipes"]
    expected_files={"population_index.json"}; alternates=0
    for row in records:
        identity=row["record_identity"]; descriptor=descriptors[identity]
        require(tuple(row)==fields and row["record_directory"]==identity,"H27 row schema/directory mismatch")
        require((row["candidate_pitch"],tuple(row["active_pitches"]),row["proposal_hop_end"],row["resolution_hop_end"],row["cents"],row["inharmonicity"])==(descriptor.candidate_pitch,descriptor.active_pitches,descriptor.proposal_hop_end,descriptor.resolution_hop_end,descriptor.cents,descriptor.inharmonicity),"H27 derived metadata mismatch")
        record_fd=open_chain(final_fd,identity)
        try:
            payloads=row["payload_sha256"]; names=set(payloads)
            require(names in ({"waveform.f64le","sample-valid-mask.u8"},{"waveform.f64le","sample-valid-mask.u8","alternate-waveform.f64le"}),"H27 payload set mismatch")
            require(("alternate-waveform.f64le" in names)==(descriptor.fixture_id not in recipes),"H27 alternate payload outside planned collision")
            alternates += int("alternate-waveform.f64le" in names)
            for name,sha in payloads.items():
                fd,raw=open_relative(record_fd,name); os.close(fd); require(digest(raw)==sha,"H27 payload digest mismatch")
                require((name.endswith("waveform.f64le") and len(raw)==133120) or (name=="sample-valid-mask.u8" and len(raw)==66560 and set(raw)<={0,1}),"H27 payload invariant failed")
                expected_files.add(identity+"/"+name)
        finally: os.close(record_fd)
    require(alternates==sum(d.fixture_id not in recipes for d in descriptors.values()),"H27 alternate collision count mismatch")
    observed=collect_tree(final_fd)
    require(observed==expected_files,"H27 exhaustive tree mismatch"); os.close(final_fd)
    return {"status":"H27_REVIEW4_TERMINAL_SUCCESS","control_plane_verified":True,"constructor_gate_replayed":False,"publisher_replayed":False,"authority_instance_id":AUTHORITY_INSTANCE_ID,"materializer_authority_consumed":True,"materializer_invoked_once":True,"p0_executed":False,"p1_executed":False,"p2_executed":False,"p0_complete":False,"p1_complete":False,"p2_complete":False,"baseline_population_materialized":True,"p2_population_materialized":True,"population_reconciled":True,"population_namespace":"H27_SYNTHETIC_V1","total_records":124,"unique_records":124,"baseline_records":17,"p2_records":107,"population_index_sha256":digest(index_raw),"data_preparation_complete":True,"global_reconciliation_pass":True,"science_executed":False,"locked_test_opened":False,"training_executed":False,"review4_closed":True}

def main() -> int:
    terminal=consume_and_run(preclaim()); print(json.dumps(terminal,sort_keys=True,separators=(",",":"))); return 0
if __name__=="__main__": raise SystemExit(main())
