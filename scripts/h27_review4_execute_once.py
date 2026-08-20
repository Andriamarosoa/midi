#!/usr/bin/env python3
"""Darwin-only, no-retry H27 Review-4 population materialization."""
from __future__ import annotations

import hashlib, importlib.metadata, json, os, platform, stat, subprocess, sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

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
OPERATIONAL_PARENT_NAME = "review4"
TERMINAL_PARENT_NAME = "review4"
OPERATIONAL_REPOSITORY_PATH = "src/polyphonic/harmonic_censoring_h27_review4_materializer.py"
OPERATIONAL_MODULE_SHA256 = "2ecaabf1e1880688244b06ecb03a9b3eb7831d4659e209aa11e36b7b60948be3"
OPERATIONAL_MODULE_BLOB = "8cdafbd6a08ea893daa2d6f41cb62166bf9162cd"
OPERATIONAL_BINDING_PATH = "configs/harmonic_censoring_h27_review4_materializer_identity_binding.json"
OPERATIONAL_SEAL_PATH = "configs/harmonic_censoring_h27_review4_materializer_external_seal.json"
OPERATIONAL_BINDING_FILE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer_identity_binding.json"
OPERATIONAL_SEAL_FILE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer_external_seal.json"
OPERATIONAL_BINDING_IDENTITY = ("9371d80c75c2cf08ebf2cc33177c05c123c13efa", 5269, "204f61303277b4a813d23a4a6a478d6d33a17893d30a72156e7a7d2574dfb4da")
OPERATIONAL_SEAL_IDENTITY = ("370eaf40be9863ec381061678451a58409264244", 1198, "f396257c040b7d0504336b98384308f76e45a32614efba129eba91c53b55f1de")
AUTHORITY_INSTANCE_ID = "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a"
ACTIVATION_SHA256 = "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2"
EXPECTED_ISSUER_ID = "h27-execution-codex-mac-primary"
EXPECTED_ACTIVATION_ID = None
RECOVERY_PREDECESSOR = None
CONTRACT_PATH = "src/polyphonic/harmonic_censoring_h27_contract.py"

ADMINISTRATIVE_INPUTS = (
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract.json", "2fc615a5f1c45245dd579891b42cfe12feb100aa", 9912, "230249ef9118d43d0d538f8b005178fd123852ddf6ed7ee69e1d76553949b622"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_contract_external_seal.json", "d912a1ebd0fb6818147a0f07da1f6140d9434398", 2786, "9a698340046692eab0e415a6094cdffc7ce36c40ce38382cbe53425f10c6238e"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding.json", "1f41f92b60c541219013bb78d40d38d183b2b80c", 6092, "4621b87709ecf74ed5cb733d1a4470e576b8ea159b48256446b5dd539b0a70e0"),
    ("configs/harmonic_censoring_h27_one_shot_execution_composition_identity_binding_external_seal.json", "cfaf71d625e774cf7294b993b7ea6206b53adc43", 3184, "9e8b20928f233e0910c3bb3c583a4a4686681b91ab8049e89dfe4129c1a5e5e3"),
    ("configs/harmonic_censoring_h27_materialization_activation_contract.json", "2df0e53637cc31d97c01e75b88cb47c2e866c187", 11131, "a1e679e4357552bd88640d3d67a6f17bd9feaad38e8f26e4ed68539f167980c4"),
    ("configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json", "0ef61aa7ada69b619a8e7acd7138151a36496089", 3122, "2174570372df3e8349a425d62ce8e1d084238757fb944968ad8539d9dcabac9d"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json", "e7ff1b71bdd62adf8341dbd824302f1eb57e69c6", 7358, "da96c338d4a99e848ab5fa63d717442c3af27fab6268bb9abae99c1f76321dab"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json", "d34da25095581694ce4ca928734bb9b01d2e357c", 1245, "8bb92ad437331528adf744388e77b445c8477a2e7dcbc87f4b84d602a147102b"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding.json", "e7191b7b27d9339b1f94fc89aec032dd9ad61062", 6032, "0f965e7bce28982d408dfd41054bde59f02c11a5016dc90af483dba6a14b6a1d"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_identity_binding_external_seal.json", "9e89d4d68013193582dee1062c61aaf8dd191ad3", 2848, "664ad640a623f3357226b83985665253b3c37b5c4fc10252223e25e0087def12"),
    ("configs/harmonic_censoring_h27_issuer_authority_claim_capability_boundary_external_review_seal.json", "c33350b3712a179a0e5577e90763ec72f96fd165", 3864, "93b3d86633f979a9521cd93d0e7629956015e279ad61cbbfca579d2857185c6b"),
    ("src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py", "ec61eef88dce7591fd411af230568b1e1d44d62e", 18915, "d3d06f8c087845089094ff71f29d8745581d391784b9bbc40abeb57b0ba42f2f"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json", "a32721107c1ff65697661cfa7a2a235811884fc6", 4609, "a752721a022433ac1d9fddccb29b9e56cbd5c1bc0566762ca50acd2f9b01a9fc"),
    ("configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json", "be17bda1d7da5144758606ed4b4f1b56708ebf3d", 1760, "a7aa1f6d844fb25e2f633db8bd2817f6741bfe194418985c8419bda64573b3be"),
    ("configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json", "d5b852e63676b59a75b938ef17c51f9247dd5e68", 3057, "68751aede0f11ce04763eb7398f4c071db91310c62c9a58c11667b908b58f95f"),
    ("src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py", "79f399359e366781f9526098c98a93cca71b1b49", 32243, "02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70"),
)
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

class OperationalBinding(NamedTuple):
    authority_sha256: str
    claim_sha256: str
    code_git_blob_sha1: str
    invocation_nonce: str
    process_id: int
    code_sha256: str

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
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),f"H27 unsafe directory: {path}"); return fd
def open_subdirectory(parent_fd: int,name: str) -> int:
    require("/" not in name and name not in ("",".",".."),"H27 unsafe subdirectory name")
    fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd); info=os.fstat(fd)
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),"H27 unsafe administrative subdirectory"); return fd
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
    created=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent_fd); reopened=None
    try:
        offset=0
        while offset<len(raw):
            count=os.write(created,raw[offset:]); require(count>0,"H27 incomplete write"); offset+=count
        os.fsync(created); created_info=os.fstat(created)
        require(stat.S_ISREG(created_info.st_mode) and created_info.st_nlink==1 and stat.S_IMODE(created_info.st_mode)==0o600,"H27 created file invariant failed")
        os.fsync(parent_fd); reopened,observed=open_relative(parent_fd,name); reopened_info=os.fstat(reopened)
        require((created_info.st_dev,created_info.st_ino)==(reopened_info.st_dev,reopened_info.st_ino),"H27 durable reopen inode mismatch")
        require(observed==raw and digest(observed)==digest(raw),"H27 durable byte-exact reread failed"); return reopened,observed
    except BaseException:
        if reopened is not None: os.close(reopened)
        raise
    finally: os.close(created)
def frozen_module(name: str,raw: bytes,filename: str,injected=None):
    require(name not in sys.modules,"H27 frozen module name collision")
    module=ModuleType(name); module.__file__=filename; module.__package__=name.rpartition(".")[0]
    for key,value in (injected or {}).items(): setattr(module,key,value)
    sys.modules[name]=module
    try:
        exec(compile(raw,filename,"exec",dont_inherit=True),module.__dict__)
        require(sys.modules.get(name) is module,"H27 frozen module registry drift")
        return module
    finally:
        sys.modules.pop(name,None)

def verify_runtime(contract):
    expected=contract["runtime_exact"]; executable=Path(sys.executable).resolve(strict=True)
    observed={"implementation":platform.python_implementation(),"version":platform.python_version(),"platform_system":platform.system(),"platform_release":platform.release(),"platform_machine":platform.machine(),"resolved_executable":executable.as_posix(),"executable_size_bytes":executable.stat().st_size,"executable_sha256":digest(executable.read_bytes())}
    require(all(observed[k]==expected[k] for k in observed),"H27 exact runtime mismatch")
    require(all(os.environ.get(k)==v for k,v in contract["process_environment_exact"].items()),"H27 process environment mismatch")
    distribution=importlib.metadata.distribution("numpy"); require(distribution.version==expected["numpy_version"],"H27 NumPy version mismatch")
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

def verify_identity(raw: bytes, identity: tuple[str,int,str], message: str) -> None:
    require((git_blob(raw),len(raw),digest(raw))==identity,message)

def parse_frozen_bound_json(contract, frozen_inputs, path):
    return contract.parse_strict_json(frozen_inputs[path], path.as_posix())

def attest_recovery_predecessor():
    if RECOVERY_PREDECESSOR is None:
        return None
    observed={}
    for label,path,expected in RECOVERY_PREDECESSOR:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try: raw=read_fd(fd,0o600)
        finally: os.close(fd)
        value=strict_json(raw)
        for key,wanted in expected.items(): require(value.get(key)==wanted,f"H27 predecessor {label} semantic drift: {key}")
        observed[label]={"path":path.as_posix(),"size_bytes":len(raw),"raw_sha256":digest(raw)}
    return observed

def preclaim():
    require(sys.platform=="darwin" and len(sys.argv)==1,"H27 Darwin zero-argument runner required")
    require(os.environ.get(ACK)=="I_UNDERSTAND_H27_REVIEW4_IS_ONE_SHOT","H27 ACK missing")
    require(git("rev-parse","HEAD").decode().strip()==REQUIRED_HEAD,"H27 HEAD mismatch")
    require(git("symbolic-ref","-q","HEAD",allowed=(0,1))==b"","H27 target must be detached")
    require(git("status","--porcelain=v1","--untracked-files=all")==b"","H27 target dirty")
    frozen={}
    for relative,blob,size,sha in SEALED_COMPONENTS:
        raw=git("cat-file","blob",REQUIRED_HEAD+":"+relative); verify_identity(raw,(blob,size,sha),"H27 component drift: "+relative); frozen[relative]=raw
    administrative=[]
    for relative,blob,size,sha in ADMINISTRATIVE_INPUTS:
        raw=git("cat-file","blob",REQUIRED_HEAD+":"+relative); verify_identity(raw,(blob,size,sha),"H27 administrative chain drift: "+relative)
        administrative.append({"path":relative,"git_blob_sha1":blob,"size_bytes":size,"raw_sha256":sha})
    admin_fd=open_directory(ADMIN); operational_parent=open_subdirectory(admin_fd,OPERATIONAL_PARENT_NAME)
    terminal_parent=os.dup(operational_parent) if TERMINAL_PARENT_NAME==OPERATIONAL_PARENT_NAME else open_subdirectory(admin_fd,TERMINAL_PARENT_NAME)
    operational_fd=os.open(OPERATIONAL_MODULE.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=operational_parent); operational_raw=read_fd(operational_fd,0o400)
    verify_identity(operational_raw,(OPERATIONAL_MODULE_BLOB,len(operational_raw),OPERATIONAL_MODULE_SHA256),"H27 operational identity mismatch")
    operational_code=compile(operational_raw,str(OPERATIONAL_MODULE),"exec",dont_inherit=True)
    binding_fd,binding_raw=open_relative(operational_parent,OPERATIONAL_BINDING_FILE.name,0o400); seal_fd,seal_raw=open_relative(operational_parent,OPERATIONAL_SEAL_FILE.name,0o400)
    os.close(binding_fd); os.close(seal_fd)
    verify_identity(binding_raw,OPERATIONAL_BINDING_IDENTITY,"H27 operational binding identity mismatch"); verify_identity(seal_raw,OPERATIONAL_SEAL_IDENTITY,"H27 operational seal identity mismatch")
    binding_json,seal_json=strict_json(binding_raw),strict_json(seal_raw)
    materializer_identity={"path":OPERATIONAL_REPOSITORY_PATH,"git_blob_sha1":OPERATIONAL_MODULE_BLOB,"size_bytes":len(operational_raw),"raw_sha256":OPERATIONAL_MODULE_SHA256}
    require(binding_json["materializer"]==materializer_identity and binding_json["administrative_chain"]==administrative,"H27 operational binding mismatch")
    require(seal_json["identity_binding"]=={"path":OPERATIONAL_BINDING_PATH,"git_blob_sha1":OPERATIONAL_BINDING_IDENTITY[0],"size_bytes":OPERATIONAL_BINDING_IDENTITY[1],"raw_sha256":OPERATIONAL_BINDING_IDENTITY[2]} and seal_json["materializer"]==materializer_identity,"H27 operational seal mismatch")
    activation_parent=open_subdirectory(admin_fd,"activation"); activation_fd,activation_raw=open_relative(activation_parent,ACTIVATION.name); os.close(activation_parent)
    require(digest(activation_raw)==ACTIVATION_SHA256,"H27 activation digest mismatch"); activation=strict_json(activation_raw)
    require(activation.get("authority_instance_id")==AUTHORITY_INSTANCE_ID and activation.get("single_use") is True and activation.get("consumed") is False and activation.get("issuer_id")==EXPECTED_ISSUER_ID,"H27 activation semantics mismatch")
    if EXPECTED_ACTIVATION_ID is not None: require(activation.get("activation_id")==EXPECTED_ACTIVATION_ID,"H27 activation id mismatch")
    authority_parent=open_subdirectory(admin_fd,"authority"); claim_parent=open_subdirectory(admin_fd,"claims"); population_parent=open_subdirectory(admin_fd,"population"); os.close(admin_fd)
    for parent,name in ((authority_parent,AUTHORITY.name),(claim_parent,CLAIM.name),(population_parent,FINAL_NAME),(population_parent,STAGING_NAME),(terminal_parent,TERMINAL.name)):
        try: os.stat(name,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise FileExistsError("H27 one-shot destination preexists: "+name)
    activation_contract=strict_json(git("cat-file","blob",REQUIRED_HEAD+":configs/harmonic_censoring_h27_materialization_activation_contract.json")); verify_runtime(activation_contract)
    contract=frozen_module("h27_frozen_contract",frozen[CONTRACT_PATH],CONTRACT_PATH); frozen_inputs={}
    for path,blob in contract.REVIEWED_GIT_BLOBS.items():
        raw=git("cat-file","blob",REQUIRED_HEAD+":"+path.as_posix()); require(git_blob(raw)==blob,"H27 frozen scientific input drift: "+path.as_posix()); frozen_inputs[path]=raw
    def frozen_bound_json(repository,path):
        require(Path(repository)==TARGET,"H27 frozen plan repository mismatch"); require(path in frozen_inputs,"H27 unbound frozen plan input")
        return parse_frozen_bound_json(contract,frozen_inputs,path)
    contract._bound_json=frozen_bound_json
    predecessor=attest_recovery_predecessor()
    return (activation,activation_contract,contract,operational_code,operational_raw,administrative,activation_fd,operational_fd,authority_parent,claim_parent,population_parent,operational_parent,terminal_parent,predecessor)

def attested_consumer(capability,binding,activation_fd,operational_fd,authority_fd,claim_fd):
    request=yield
    require(type(request) is tuple and len(request)==2 and request[0] is capability and request[1] is binding,"H27 exact capability/binding pair required")
    require(os.getpid()==binding.process_id,"H27 process drift")
    require(digest(read_fd(activation_fd,0o600))==ACTIVATION_SHA256,"H27 activation drift after claim")
    code_raw=read_fd(operational_fd,0o400)
    require(digest(code_raw)==binding.code_sha256 and git_blob(code_raw)==binding.code_git_blob_sha1,"H27 code drift after claim")
    require(digest(read_fd(authority_fd,0o600))==binding.authority_sha256,"H27 authority drift after claim")
    require(digest(read_fd(claim_fd,0o600))==binding.claim_sha256,"H27 claim drift after claim")
    yield binding

def consume_and_run(state):
    (activation,activation_contract,contract,operational_code,operational_raw,administrative,activation_fd,operational_fd,authority_parent,claim_parent,population_parent,operational_parent,terminal_parent,predecessor)=state
    nonce=str(activation["invocation_nonce"])
    authority={"schema_version":1,"authority_type":"h27_review4_materialization_authority","authority_instance_id":AUTHORITY_INSTANCE_ID,"activation":{"raw_sha256":ACTIVATION_SHA256,"issuer_identity":activation["issuer_id"]},"invocation_nonce":nonce,"required_head":REQUIRED_HEAD,"population_namespace":"H27_SYNTHETIC_V1","expected_counts":{"total":124,"baseline":17,"p2":107},"fixed_destinations":{"final":(POPULATION_PARENT/FINAL_NAME).as_posix(),"staging":(POPULATION_PARENT/STAGING_NAME).as_posix()},"runtime_exact":activation_contract["runtime_exact"],"process_environment_exact":activation_contract["process_environment_exact"],"sealed_h27_inputs":activation_contract["sealed_h27_inputs"],"sealed_administrative_inputs":administrative,"sealed_components":[{"path":path,"git_blob_sha1":blob,"size_bytes":size,"raw_sha256":sha} for path,blob,size,sha in SEALED_COMPONENTS],"materializer":{"git_blob_sha1":OPERATIONAL_MODULE_BLOB,"size_bytes":len(operational_raw),"raw_sha256":OPERATIONAL_MODULE_SHA256},"operational_identity_binding":{"git_blob_sha1":OPERATIONAL_BINDING_IDENTITY[0],"size_bytes":OPERATIONAL_BINDING_IDENTITY[1],"raw_sha256":OPERATIONAL_BINDING_IDENTITY[2]},"operational_external_seal":{"git_blob_sha1":OPERATIONAL_SEAL_IDENTITY[0],"size_bytes":OPERATIONAL_SEAL_IDENTITY[1],"raw_sha256":OPERATIONAL_SEAL_IDENTITY[2]},"predecessor_consumed_attestation":predecessor,"single_use":True,"science_authorized":False,"locked_test_used":False}
    authority_fd,authority_raw=write_new_at(authority_parent,AUTHORITY.name,canonical(authority))
    claim={"schema_version":1,"claim_type":"h27_review4_materialization_consumed","activation_sha256":ACTIVATION_SHA256,"authority_sha256":digest(authority_raw),"materializer_blob":OPERATIONAL_MODULE_BLOB,"materializer_sha256":OPERATIONAL_MODULE_SHA256,"operational_binding_sha256":OPERATIONAL_BINDING_IDENTITY[2],"operational_seal_sha256":OPERATIONAL_SEAL_IDENTITY[2],"runtime_process_id":os.getpid(),"invocation_nonce":nonce,"fixed_destinations":authority["fixed_destinations"],"retry_allowed":False,"consumed":True}
    claim_fd,claim_raw=write_new_at(claim_parent,CLAIM.name,canonical(claim))
    capability=object(); binding=OperationalBinding(digest(authority_raw),digest(claim_raw),OPERATIONAL_MODULE_BLOB,nonce,os.getpid(),OPERATIONAL_MODULE_SHA256)
    consumer=attested_consumer(capability,binding,activation_fd,operational_fd,authority_fd,claim_fd); next(consumer)
    name="h27_frozen_materializer"; materializer=ModuleType(name)
    materializer.__file__=str(OPERATIONAL_MODULE); materializer.__package__="src.polyphonic"
    materializer._H27_FROZEN_CONTRACT=contract
    materializer._H27_BOUNDARY_SESSION={"capability":capability,"binding":binding,"consume_attested":consumer.send,"population_parent_fd":population_parent}
    require(name not in sys.modules,"H27 frozen operational module name already occupied")
    sys.modules[name]=materializer
    try: exec(operational_code,materializer.__dict__)
    finally:
        if sys.modules.get(name) is materializer: del sys.modules[name]
    records,index_raw=materializer.materialize_h27_production_population(contract.load_h27_dormant_plan,TARGET)
    plan=contract.load_h27_dormant_plan(TARGET); terminal=reconcile(contract,plan,population_parent,records,index_raw)
    terminal_fd,_=write_new_at(terminal_parent,TERMINAL.name,canonical(terminal)); os.close(terminal_fd); return terminal

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
        info=os.stat(name,dir_fd=fd,follow_symlinks=False); require(not stat.S_ISLNK(info.st_mode),"H27 tree symlink forbidden"); relative=prefix+name
        if stat.S_ISDIR(info.st_mode):
            require(stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),"H27 tree directory invariant failed")
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try: files.update(collect_tree(child,relative+"/"))
            finally: os.close(child)
        else:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600 and info.st_uid==os.getuid(),"H27 tree file invariant failed"); files.add(relative)
    return files

def reconcile(contract,plan,population_parent,expected_records,expected_index_raw):
    final_fd=os.open(FINAL_NAME,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=population_parent); index_fd,index_raw=open_relative(final_fd,"population_index.json"); os.close(index_fd)
    require(index_raw==expected_index_raw,"H27 final index differs from pre-rename staging verification"); index=strict_json(index_raw); records=index.get("records")
    require(records==list(expected_records) and index.get("record_count")==124 and len(records)==124,"H27 exact index reconciliation failed")
    expected=list(contract.canonical_h27_record_identities(plan)); identities=[r.get("record_identity") for r in records]
    require(identities==expected and len(set(identities))==124,"H27 identity/order mismatch")
    grid_counts={"P2_GAIN_V1":9,"P2_PHASE_V1":12,"P2_NOISE_V1":12,"P2_ZERO_CONTEXT_BOUNDARY_V1":4,"P2_CENTS_INHARMONICITY_V1":18,"P2_PERMUTATION_V1":32,"P2_RUNTIME_V1":8,"P2_HOP_SHIFT_V1":12}
    require(all(sum(str(value).startswith("p2/"+grid+"/") for value in identities)==count for grid,count in grid_counts.items()),"H27 exact eight-grid distribution mismatch")
    expected_files={"population_index.json"}
    for row in records:
        identity=row["record_identity"]; record_fd=open_chain(final_fd,identity)
        try:
            for name,sha in row["payload_sha256"].items():
                fd,raw=open_relative(record_fd,name); os.close(fd); require(digest(raw)==sha,"H27 final payload digest mismatch")
                require((name.endswith("waveform.f64le") and len(raw)==133120) or (name=="sample-valid-mask.u8" and len(raw)==66560 and set(raw)<={0,1}),"H27 final payload invariant failed"); expected_files.add(identity+"/"+name)
        finally: os.close(record_fd)
    require(collect_tree(final_fd)==expected_files,"H27 exhaustive final tree mismatch"); os.close(final_fd)
    return {"status":"H27_REVIEW4_TERMINAL_SUCCESS","control_plane_verified":True,"constructor_gate_replayed":False,"publisher_replayed":False,"authority_instance_id":AUTHORITY_INSTANCE_ID,"materializer_authority_consumed":True,"materializer_invoked_once":True,"p0_executed":False,"p1_executed":False,"p2_executed":False,"p0_complete":False,"p1_complete":False,"p2_complete":False,"baseline_population_materialized":True,"p2_population_materialized":True,"population_reconciled":True,"population_namespace":"H27_SYNTHETIC_V1","total_records":124,"unique_records":124,"baseline_records":17,"p2_records":107,"population_index_sha256":digest(index_raw),"data_preparation_complete":True,"global_reconciliation_pass":True,"predecessor_consumed_attested":RECOVERY_PREDECESSOR is not None,"science_executed":False,"locked_test_opened":False,"training_executed":False,"review4_closed":True}

def main() -> int:
    terminal=consume_and_run(preclaim()); print(json.dumps(terminal,sort_keys=True,separators=(",",":"))); return 0
if __name__=="__main__": raise SystemExit(main())
