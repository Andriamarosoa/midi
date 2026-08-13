from __future__ import annotations
import hashlib,json
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
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_implementation_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_implementation_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def sixty_four(chain):
 ec=json.loads((ROOT/chain[0]['path']).read_bytes());roots=ec['reviewed_and_sealed_destination_contract_chain'];db=json.loads((ROOT/roots[2]['path']).read_bytes());dc=json.loads((ROOT/db['reviewed_contract']['path']).read_bytes());dr=dc['reviewed_and_sealed_dormant_boundary'];old=json.loads((ROOT/dc['transitive_identity_source']['path']).read_bytes());ar=old['upstream_roots'];e=json.loads((ROOT/ar[0]['path']).read_bytes());f=[e['reviewed_contract'],e['contract_external_seal'],*e['reviewed_and_sealed_dormant_publication_simulator']];o=json.loads((ROOT/e['transitive_upstream_binding']['path']).read_bytes())['upstream_entries'];return [*roots,*dr,*ar,*f,*o]
class TestContract(unittest.TestCase):
 def setUp(self):self.c=json.loads(C.read_bytes());self.s=json.loads(S.read_bytes())
 def test_76_exact_identities(self):
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_issuance_artifact_contract_chain'];artifact_contract=json.loads((ROOT/roots[0]['path']).read_bytes());authority_roots=artifact_contract['reviewed_and_sealed_one_shot_authority_chain'];authority=json.loads((ROOT/authority_roots[0]['path']).read_bytes());execroots=authority['reviewed_and_sealed_execution_authorization_chain'];entries=[*roots,*authority_roots,*execroots,*sixty_four(execroots)];self.assertEqual(len(entries),76);self.assertEqual(len({x['path'] for x in entries}),76)
  for x in entries:chk(self,x)
 def test_future_boundary_is_exact_and_absent(self):
  f=self.c['future_issuer_implementation'];self.assertEqual(f['implementation_path'],'src/polyphonic/harmonic_censoring_h27_real_publication_one_shot_authority_issuer.py');self.assertEqual(f['public_entrypoint'],'issue_h27_real_publication_one_shot_authority');self.assertFalse(f['implementation_exists']);self.assertFalse(f['implementation_authorized']);self.assertFalse(f['invocation_authorized']);self.assertTrue(f['fake_or_in_memory_adapter_tests_only']);self.assertTrue(f['separate_real_issuance_authorization_required']);self.assertTrue(all(self.c['mandatory_fail_closed_requirements'].values()))
 def test_only_contract_creation_is_authorized(self):
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='issuer_implementation_contract_exists',k)
  for k,v in self.c['authorization'].items():self.assertIs(v,k=='contract_and_external_seal_creation_authorized',k)
  self.assertTrue(self.c['dependency_graph']['acyclic']);self.assertFalse(self.c['dependency_graph']['self_hash_present']);self.assertFalse(self.c['dependency_graph']['historical_back_reference_present']);self.assertEqual(self.c['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_canonical(self):
  for raw in (C.read_bytes(),S.read_bytes()):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
if __name__=='__main__':unittest.main()
