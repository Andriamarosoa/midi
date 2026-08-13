from __future__ import annotations
import datetime,hashlib,json,re
from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as m
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as a
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as p
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant as r
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as b
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as g
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as q
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as c
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuance_artifact_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuance_artifact_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def sixty_four(chain):
 ec=json.loads((ROOT/chain[0]['path']).read_bytes());roots=ec['reviewed_and_sealed_destination_contract_chain'];db=json.loads((ROOT/roots[2]['path']).read_bytes());dc=json.loads((ROOT/db['reviewed_contract']['path']).read_bytes());dr=dc['reviewed_and_sealed_dormant_boundary'];old=json.loads((ROOT/dc['transitive_identity_source']['path']).read_bytes());ar=old['upstream_roots'];e=json.loads((ROOT/ar[0]['path']).read_bytes());f=[e['reviewed_contract'],e['contract_external_seal'],*e['reviewed_and_sealed_dormant_publication_simulator']];o=json.loads((ROOT/e['transitive_upstream_binding']['path']).read_bytes())['upstream_entries'];return [*roots,*dr,*ar,*f,*o]
class TestContract(unittest.TestCase):
 def setUp(self):self.c=json.loads(C.read_bytes());self.s=json.loads(S.read_bytes())
 def test_72(self):
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_one_shot_authority_chain'];ac=json.loads((ROOT/roots[0]['path']).read_bytes());execroots=ac['reviewed_and_sealed_execution_authorization_chain'];entries=[*roots,*execroots,*sixty_four(execroots)];self.assertEqual(len(entries),72);self.assertEqual(len({x['path'] for x in entries}),72)
  for x in entries:chk(self,x)
  manifest=[{k:x[k] for k in ('path','git_blob_sha1','size_bytes','raw_sha256')} for x in sorted(entries,key=lambda x:x['path'])]
  raw=(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n').encode()
  schema=self.c['future_artifact_schema'];self.assertEqual(len(raw),schema['predecessor_manifest_canonicalization']['manifest_size_bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),schema['fields']['predecessor_manifest_sha256']['exact_value'])
 def test_closed_and_edges(self):
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='issuance_artifact_contract_exists',k)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_canonical(self):
  for raw in (C.read_bytes(),S.read_bytes()):self.assertNotIn(b'\r',raw);self.assertTrue(raw.endswith(b'\n'))
 def test_closed_schema_and_adversarial_values(self):
  s=self.c['future_artifact_schema'];order=s['field_order'];self.assertTrue(s['closed_schema']);self.assertFalse(s['additional_fields_allowed']);self.assertEqual(order,list(s['fields']))
  f=s['fields'];nonce='ab'*32;issuer=f['issuer_id']['exact_value'];dest=f['destination_path']['exact_value'];pm=f['predecessor_manifest_sha256']['exact_value'];digest=hashlib.sha256((issuer+'\n'+nonce+'\n'+dest+'\n'+pm).encode()).hexdigest()
  good={'schema_version':1,'artifact_id':'h27-authority-'+digest,'issuer_id':issuer,'invocation_nonce':nonce,'issued_at_utc':'2026-08-13T12:34:56Z','destination_path':dest,'single_use':True,'predecessor_identity_count':72,'predecessor_manifest_sha256':pm}
  self.assertEqual(list(good),order);datetime.datetime.strptime(good['issued_at_utc'],'%Y-%m-%dT%H:%M:%SZ');self.assertRegex(good['invocation_nonce'],f['invocation_nonce']['regex']);self.assertRegex(good['predecessor_manifest_sha256'],f['predecessor_manifest_sha256']['regex'])
  bad=[{**good,'extra':1},{**good,'issuer_id':'other'},{**good,'invocation_nonce':'A'*64},{**good,'issued_at_utc':'2026-02-30T12:00:00Z'},{**good,'single_use':False},{**good,'predecessor_identity_count':True},{**good,'predecessor_manifest_sha256':'0'*64},{**good,'artifact_id':'h27-authority-'+'0'*64}]
  def valid(x):
   if list(x)!=order or set(x)!=set(order) or type(x['schema_version']) is not int or x['schema_version']!=1 or x['issuer_id']!=issuer or not re.fullmatch(f['invocation_nonce']['regex'],x['invocation_nonce']) or x['destination_path']!=dest or x['single_use'] is not True or type(x['predecessor_identity_count']) is not int or x['predecessor_identity_count']!=72 or x['predecessor_manifest_sha256']!=pm:return False
   try:datetime.datetime.strptime(x['issued_at_utc'],'%Y-%m-%dT%H:%M:%SZ')
   except (TypeError,ValueError):return False
   expected='h27-authority-'+hashlib.sha256((issuer+'\n'+x['invocation_nonce']+'\n'+dest+'\n'+pm).encode()).hexdigest();return x['artifact_id']==expected
  self.assertTrue(valid(good))
  for x in bad:self.assertFalse(valid(x))
if __name__=='__main__':unittest.main()
