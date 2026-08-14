from __future__ import annotations
import hashlib,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
BINDING=ROOT/'configs/harmonic_censoring_h27_creator_leaf_creation_contract_identity_binding.json'
SEAL=ROOT/'configs/harmonic_censoring_h27_creator_leaf_creation_contract_identity_binding_external_seal.json'
def blob(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def check(t,i):
 raw=(ROOT/i['path']).read_bytes();t.assertEqual((i['git_blob_sha1'],i['size_bytes'],i['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
class TestBinding(unittest.TestCase):
 @classmethod
 def setUpClass(c): c.r=BINDING.read_bytes();c.sr=SEAL.read_bytes();c.b=json.loads(c.r);c.s=json.loads(c.sr)
 def test_five_exact_identities(self):
  for raw in (self.r,self.sr):self.assertNotIn(b'\r',raw);self.assertTrue(raw.endswith(b'\n'))
  check(self,self.s['identity_binding']);ids=[self.b['reviewed_contract'],self.b['contract_external_seal'],*self.b['reviewed_admin_root_creator_chain']];self.assertEqual((len(ids),len({i['path'] for i in ids})),(5,5));[check(self,i) for i in ids]
 def test_closed_binding(self):
  self.assertEqual(self.b['transitive_identity_binding'],{'combined_unique_path_count':5,'all_five_identities_must_be_rehashed':True,'duplicates_forbidden':True,'path_or_identity_drift_forbidden':True})
  self.assertEqual(self.b['bound_future_creator_leaf'],{'platform_exact':'darwin','acknowledgement_environment_exact':'H27_CREATOR_LEAF_CREATE_EXECUTE=1','arguments_forbidden':True,'parent_path_exact':'/Users/amcarene/h27-admin','parent_expected_device_exact':16777233,'parent_expected_inode_exact':1445438,'parent_fd_and_named_entry_must_match_terminal_identity':True,'target_leaf_exact':'creator','target_path_exact':'/Users/amcarene/h27-admin/creator','static_preflight_count':4,'one_shot_creation_step_count':7,'creation_rule_count':14})
  self.assertEqual(self.b['preserved_future_runner_boundary'],{'future_runner_requirement_count':7,'distinct_later_commit_required':True,'external_review_pass_required':True,'exact_identity_binding_required':True,'external_identity_binding_seal_required':True,'execution_from_exact_reviewed_git_blob_bytes_only':True,'current_checkout_or_worktree_file_fallback_forbidden':True,'runner_forbidden_in_current_stage':True})
  self.assertEqual((self.s['bound_unique_path_count'],self.s['future_parent_path_exact'],self.s['future_parent_expected_device_exact'],self.s['future_parent_expected_inode_exact'],self.s['future_acknowledgement_environment_exact'],self.s['static_preflight_count'],self.s['one_shot_creation_step_count'],self.s['creation_rule_count'],self.s['future_runner_requirement_count']),(5,'/Users/amcarene/h27-admin',16777233,1445438,'H27_CREATOR_LEAF_CREATE_EXECUTE=1',4,7,14,7))
 def test_dormant(self):
  true={'contract_exists','contract_externally_reviewed','contract_externally_sealed','identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in true,k)
  self.assertEqual(self.b['preserved_authority_state'],{'admin_root_creation_authority_terminally_consumed':True,'admin_root_creator_retry_forbidden':True,'publisher_authorization_consumed':False,'publisher_final_or_staging_observed':False})
  for k in ('identity_binding_externally_reviewed','identity_binding_externally_sealed','runner_exists','creator_leaf_observed','creator_leaf_created','publisher_final_or_staging_observed','source_published','creator_entrypoint_executed','registry_opened','control_bundle_created','science_or_locked_test'):self.assertIs(self.s[k],False,k)
if __name__=='__main__':unittest.main()
