from __future__ import annotations
import json
import hashlib
from pathlib import Path
from unittest import mock
import unittest
from src.polyphonic import harmonic_censoring_h27_real_publication_one_shot_authority_issuer as issuer

NONCE='ab'*32;STAMP='2026-08-13T12:34:56Z'
def probe(nonce:str)->issuer.H27EffectFreeIssuerProbe:
 raw=issuer._canonical_artifact_bytes(issuer._ISSUER_ID,nonce,STAMP,issuer._DESTINATION);return issuer.H27EffectFreeIssuerProbe(False,False,False,hashlib.sha256(raw).hexdigest())
def invoke(nonce:str=NONCE,p:object=None):return issuer.issue_h27_real_publication_one_shot_authority(issuer_id=issuer._ISSUER_ID,invocation_nonce=nonce,issued_at_utc=STAMP,destination_path=issuer._DESTINATION,probe=probe(nonce) if p is None else p)
class TestIssuer(unittest.TestCase):
 def setUp(self):
  with issuer._NONCE_LOCK:issuer._USED_NONCES.clear()
 def test_success_is_canonical_and_effect_free(self):
  result=invoke();self.assertEqual(result.verified_identities,78);self.assertIsNone(result.destination_path);self.assertEqual((result.issuance_artifact_exists,result.authority_exists,result.claim_exists,result.capability_exists),(False,False,False,False));self.assertEqual((result.filesystem_effects,result.science_invocations),(0,0));value=json.loads(result.canonical_bytes);self.assertEqual(tuple(value),issuer._FIELD_ORDER);self.assertEqual(value['issuer_id'],issuer._ISSUER_ID);self.assertTrue(value['single_use']);self.assertEqual(value['predecessor_identity_count'],72);self.assertEqual(value['predecessor_manifest_sha256'],issuer._PREDECESSOR_MANIFEST_SHA256);self.assertTrue(result.canonical_bytes.endswith(b'\n'));self.assertNotIn(b'\r',result.canonical_bytes)
 def test_78_identities_precede_input_and_probe_logic(self):
  with mock.patch.object(issuer,'_verify_seventy_eight_inputs',side_effect=PermissionError('drift')):
   with self.assertRaises(PermissionError):invoke()
 def test_each_dependency_is_verified_before_parse(self):
  original_verify=issuer._verify_exact;original_json=issuer._verified_json;verified=set();parsed=[]
  def observe(relative,*rest):raw=original_verify(relative,*rest);verified.add(str(relative));return raw
  def guarded(item):value=original_json(item);self.assertIn(item['path'],verified);parsed.append(item['path']);return value
  with mock.patch.object(issuer,'_verify_exact',side_effect=observe),mock.patch.object(issuer,'_verified_json',side_effect=guarded):issuer._verify_seventy_eight_inputs()
  self.assertGreater(len(parsed),8)
 def test_invalid_inputs_fail_before_nonce_consumption(self):
  cases=({'issuer_id':'h26-execution-codex-mac-primary'},{'invocation_nonce':'A'*64},{'issued_at_utc':'2026-02-30T12:00:00Z'},{'destination_path':'/tmp/wrong'})
  for changed in cases:
   args={'issuer_id':issuer._ISSUER_ID,'invocation_nonce':NONCE,'issued_at_utc':STAMP,'destination_path':issuer._DESTINATION,'probe':probe(NONCE)};args.update(changed)
   with self.assertRaises((ValueError,PermissionError)):issuer.issue_h27_real_publication_one_shot_authority(**args)
   with issuer._NONCE_LOCK:self.assertNotIn(NONCE,issuer._USED_NONCES)
 def test_probe_is_closed_immutable_data_and_nonce_is_one_shot(self):
  with self.assertRaises(PermissionError):invoke(p=object())
  for changed in ({'destination_observed':True},{'create_attempted':True},{'write_attempted':True},{'expected_canonical_sha256':'0'*64}):
   with issuer._NONCE_LOCK:issuer._USED_NONCES.clear()
   values={'destination_observed':False,'create_attempted':False,'write_attempted':False,'expected_canonical_sha256':probe(NONCE).expected_canonical_sha256};values.update(changed)
   with self.assertRaises(PermissionError):invoke(p=issuer.H27EffectFreeIssuerProbe(**values))
  with issuer._NONCE_LOCK:issuer._USED_NONCES.clear()
  invoke()
  with self.assertRaises(PermissionError):invoke()
 def test_custom_objects_are_rejected_before_magic_methods_can_execute(self):
  class ExecutableValue:
   def _execute(self,*args,**kwargs):raise AssertionError('custom code executed')
   __eq__=__ne__=__str__=__repr__=__hash__=__add__=__radd__=_execute
  bad=ExecutableValue()
  for field in ('issuer_id','invocation_nonce','issued_at_utc','destination_path'):
   args={'issuer_id':issuer._ISSUER_ID,'invocation_nonce':NONCE,'issued_at_utc':STAMP,'destination_path':issuer._DESTINATION,'probe':probe(NONCE)};args[field]=bad
   with self.assertRaises(TypeError):issuer.issue_h27_real_publication_one_shot_authority(**args)
  for field in ('destination_observed','create_attempted','write_attempted','expected_canonical_sha256'):
   values={'destination_observed':False,'create_attempted':False,'write_attempted':False,'expected_canonical_sha256':probe(NONCE).expected_canonical_sha256};values[field]=bad
   with self.assertRaises(TypeError):invoke(p=issuer.H27EffectFreeIssuerProbe(**values))
  with issuer._NONCE_LOCK:self.assertNotIn(NONCE,issuer._USED_NONCES)
 def test_source_has_no_real_filesystem_or_science_api(self):
  source=Path(issuer.__file__).read_text(encoding='utf-8')
  for forbidden in ('os.open','O_EXCL','write_bytes','open(','fsync','rename(','import numpy','tensorflow','Callable'):
   self.assertNotIn(forbidden,source)
if __name__=='__main__':unittest.main()
