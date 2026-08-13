from __future__ import annotations
import hashlib,json
from pathlib import Path
from unittest import mock
import unittest
from src.polyphonic import harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor as ctor

NONCE='cd'*32;STAMP='2026-08-13T12:34:56Z'
def sealed():return dict(ctor._SEALED_VALUES)
def probe(nonce=NONCE):
 raw=ctor._canonical_artifact_bytes(ctor._ISSUER_ID,STAMP,nonce,ctor._DESTINATION,sealed());return ctor.H27EffectFreeConstructorProbe(True,True,True,False,False,False,False,hashlib.sha256(raw).hexdigest())
def invoke(nonce=NONCE,p=None):return ctor.construct_h27_real_publication_authority_instance_artifact(issuer_id=ctor._ISSUER_ID,issued_at_utc=STAMP,invocation_nonce=nonce,canonical_destination_path=ctor._DESTINATION,sealed_chain_identity=sealed(),probe=probe(nonce) if p is None else p)
class TestConstructor(unittest.TestCase):
 def test_success_is_canonical_and_effect_free(self):
  result=invoke();value=json.loads(result.canonical_bytes);self.assertEqual(result.verified_identities,98);self.assertEqual(tuple(value),ctor._TOP_LEVEL_FIELDS);self.assertEqual(tuple(value['sealed_chain_identity']),ctor._SEALED_FIELDS);self.assertEqual(value['sealed_chain_identity'],ctor._SEALED_VALUES);self.assertTrue(value['single_use']);self.assertFalse(value['consumed']);self.assertEqual(value['authority_instance_id'],result.authority_instance_id);self.assertRegex(result.authority_instance_id,r'^[0-9a-f]{64}$');self.assertEqual((result.persistent_reservation_performed,result.destination_path,result.authority_instance_artifact_exists,result.authority_instance_exists,result.filesystem_effects,result.science_invocations),(False,None,False,False,0,0));self.assertTrue(result.canonical_bytes.endswith(b'\n'));self.assertNotIn(b'\r',result.canonical_bytes)
 def test_exact_derivation(self):
  value=json.loads(invoke().canonical_bytes);s=value['sealed_chain_identity'];expected=hashlib.sha256('\0'.join((ctor._NAMESPACE,ctor._ISSUER_ID,STAMP,NONCE,ctor._DESTINATION,s['contract_raw_sha256'],s['binding_raw_sha256'])).encode('ascii')).hexdigest();self.assertEqual(value['authority_instance_id'],expected)
 def test_98_identities_precede_runtime_inputs(self):
  class Explosive:
   def boom(self,*a,**k):raise AssertionError('runtime input touched')
   __str__=__repr__=__eq__=__ne__=__hash__=boom
  with mock.patch.object(ctor,'_verify_ninety_eight_inputs',side_effect=PermissionError('drift')):
   with self.assertRaises(PermissionError):ctor.construct_h27_real_publication_authority_instance_artifact(issuer_id=Explosive(),issued_at_utc=Explosive(),invocation_nonce=Explosive(),canonical_destination_path=Explosive(),sealed_chain_identity=Explosive(),probe=Explosive())
 def test_each_dependency_is_verified_before_parse(self):
  original_verify=ctor._verify_exact;original_json=ctor._verified_json;verified=set();parsed=[]
  def observe(relative,*rest):raw=original_verify(relative,*rest);verified.add(str(relative));return raw
  def guarded(item):value=original_json(item);self.assertIn(item['path'],verified);parsed.append(item['path']);return value
  with mock.patch.object(ctor,'_verify_exact',side_effect=observe),mock.patch.object(ctor,'_verified_json',side_effect=guarded):ctor._verify_ninety_eight_inputs()
  self.assertGreater(len(parsed),10)
 def test_invalid_values_and_order_fail_closed(self):
  cases=({'issuer_id':'wrong'},{'issued_at_utc':'2026-02-30T12:00:00Z'},{'invocation_nonce':'A'*64},{'canonical_destination_path':'/tmp/wrong'})
  for change in cases:
   args={'issuer_id':ctor._ISSUER_ID,'issued_at_utc':STAMP,'invocation_nonce':NONCE,'canonical_destination_path':ctor._DESTINATION,'sealed_chain_identity':sealed(),'probe':probe()};args.update(change)
   with self.assertRaises(ValueError):ctor.construct_h27_real_publication_authority_instance_artifact(**args)
  reversed_sealed=dict(reversed(tuple(sealed().items())))
  with self.assertRaises(ValueError):ctor.construct_h27_real_publication_authority_instance_artifact(issuer_id=ctor._ISSUER_ID,issued_at_utc=STAMP,invocation_nonce=NONCE,canonical_destination_path=ctor._DESTINATION,sealed_chain_identity=reversed_sealed,probe=probe())
 def test_probe_requires_registry_availability_and_zero_effects(self):
  base={'persistent_registry_checked':True,'identity_available':True,'nonce_available':True,'reservation_attempted':False,'destination_observed':False,'create_attempted':False,'write_attempted':False,'expected_canonical_sha256':probe().expected_canonical_sha256}
  with self.assertRaises(PermissionError):invoke(p=object())
  for changed in ({'persistent_registry_checked':False},{'identity_available':False},{'nonce_available':False},{'reservation_attempted':True},{'destination_observed':True},{'create_attempted':True},{'write_attempted':True},{'expected_canonical_sha256':'0'*64}):
   values=dict(base);values.update(changed)
   with self.assertRaises(PermissionError):invoke(p=ctor.H27EffectFreeConstructorProbe(**values))
 def test_custom_objects_rejected_before_magic_methods(self):
  class Explosive:
   def boom(self,*a,**k):raise AssertionError('magic method executed')
   __str__=__repr__=__eq__=__ne__=__hash__=__iter__=boom
  bad=Explosive()
  for field in ('issuer_id','issued_at_utc','invocation_nonce','canonical_destination_path','sealed_chain_identity'):
   args={'issuer_id':ctor._ISSUER_ID,'issued_at_utc':STAMP,'invocation_nonce':NONCE,'canonical_destination_path':ctor._DESTINATION,'sealed_chain_identity':sealed(),'probe':probe()};args[field]=bad
   with self.assertRaises(TypeError):ctor.construct_h27_real_publication_authority_instance_artifact(**args)
  values={'persistent_registry_checked':True,'identity_available':True,'nonce_available':True,'reservation_attempted':False,'destination_observed':False,'create_attempted':False,'write_attempted':False,'expected_canonical_sha256':probe().expected_canonical_sha256};values['identity_available']=bad
  with self.assertRaises(TypeError):invoke(p=ctor.H27EffectFreeConstructorProbe(**values))
 def test_source_has_no_publication_or_science_api(self):
  source=Path(ctor.__file__).read_text(encoding='utf-8')
  for forbidden in ('os.open','O_EXCL','write_bytes','fsync','rename(','replace(','import numpy','tensorflow','subprocess','socket'):
   self.assertNotIn(forbidden,source)
if __name__=='__main__':unittest.main()
