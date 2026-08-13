from __future__ import annotations
import json
from pathlib import Path
from unittest import mock
import unittest
from src.polyphonic import harmonic_censoring_h27_real_publication_one_shot_authority_issuer as issuer

NONCE='ab'*32;STAMP='2026-08-13T12:34:56Z'
def adapters(calls:list[str])->issuer.H27EffectFreeIssuerAdapters:
 def absent(path:str)->bool:calls.append('absent');return path==issuer._DESTINATION
 def create(path:str,raw:bytes)->tuple[bool,bool]:calls.append('create');return (False,False)
 def finalize(raw:bytes)->bytes:calls.append('finalize');return raw
 return issuer.H27EffectFreeIssuerAdapters(absent,create,finalize)
def invoke(a:issuer.H27EffectFreeIssuerAdapters):return issuer.issue_h27_real_publication_one_shot_authority(issuer_id=issuer._ISSUER_ID,invocation_nonce=NONCE,issued_at_utc=STAMP,destination_path=issuer._DESTINATION,adapters=a)
class TestIssuer(unittest.TestCase):
 def test_success_is_canonical_and_effect_free(self):
  calls=[];result=invoke(adapters(calls));self.assertEqual(calls,['absent','create','finalize']);self.assertEqual(result.verified_identities,78);self.assertIsNone(result.destination_path);self.assertEqual((result.issuance_artifact_exists,result.authority_exists,result.claim_exists,result.capability_exists),(False,False,False,False));self.assertEqual((result.filesystem_effects,result.science_invocations),(0,0));value=json.loads(result.canonical_bytes);self.assertEqual(tuple(value),issuer._FIELD_ORDER);self.assertEqual(value['issuer_id'],issuer._ISSUER_ID);self.assertTrue(value['single_use']);self.assertEqual(value['predecessor_identity_count'],72);self.assertEqual(value['predecessor_manifest_sha256'],issuer._PREDECESSOR_MANIFEST_SHA256);self.assertTrue(result.canonical_bytes.endswith(b'\n'));self.assertNotIn(b'\r',result.canonical_bytes)
 def test_78_identities_precede_any_adapter(self):
  callbacks=issuer.H27EffectFreeIssuerAdapters(mock.Mock(),mock.Mock(),mock.Mock())
  with mock.patch.object(issuer,'_verify_seventy_eight_inputs',side_effect=PermissionError('drift')):
   with self.assertRaises(PermissionError):invoke(callbacks)
  for callback in callbacks:callback.assert_not_called()
 def test_invalid_inputs_fail_before_adapters(self):
  cases=({'issuer_id':'h26-execution-codex-mac-primary'},{'invocation_nonce':'A'*64},{'issued_at_utc':'2026-02-30T12:00:00Z'},{'destination_path':'/tmp/wrong'})
  for changed in cases:
   callbacks=issuer.H27EffectFreeIssuerAdapters(mock.Mock(),mock.Mock(),mock.Mock());args={'issuer_id':issuer._ISSUER_ID,'invocation_nonce':NONCE,'issued_at_utc':STAMP,'destination_path':issuer._DESTINATION,'adapters':callbacks};args.update(changed)
   with self.assertRaises((ValueError,PermissionError)):issuer.issue_h27_real_publication_one_shot_authority(**args)
   for callback in callbacks:callback.assert_not_called()
 def test_effect_claims_and_byte_mutation_fail(self):
  replacements=({'attest_destination_unobserved':mock.Mock(return_value=False)},{'simulate_create_exclusive':mock.Mock(return_value=(True,False))},{'simulate_create_exclusive':mock.Mock(return_value=(False,True))},{'finalize_in_memory':mock.Mock(return_value=b'changed')})
  for replacement in replacements:
   with self.assertRaises(PermissionError):invoke(adapters([])._replace(**replacement))
 def test_source_has_no_real_filesystem_or_science_api(self):
  source=Path(issuer.__file__).read_text(encoding='utf-8')
  for forbidden in ('os.open','O_EXCL','write_bytes','open(','fsync','rename(','import numpy','tensorflow'):
   self.assertNotIn(forbidden,source)
if __name__=='__main__':unittest.main()
