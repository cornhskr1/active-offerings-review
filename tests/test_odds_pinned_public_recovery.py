"""Recovery is bound to one proved publication; no live/provider calls in tests."""
import copy
import hashlib
import json
import pathlib
import unittest
from unittest.mock import patch
from tests import test_full_snapshot_adapters as adapters
from scripts.recover_pinned_public_snapshot import restore_pinned_public,ORIGIN,NoRedirect
from scripts.restore_public_snapshot import restore_snapshot
from scripts.public_data_snapshot import POINTER

class PinnedPublicRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f=adapters.AdapterTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.checkpoint={'schema_version':1,'repository':'cornhskr1/active-offerings-review','origin':ORIGIN,
            'anchor_run_id':12344,'anchor_head_sha':'a'*40,'snapshot_sha256':self.f.public['snapshot_sha256'],
            'odds_sha256':hashlib.sha256(self.f.odds).hexdigest(),'odds_observed_at':'2026-10-01T00:00:00Z','skip_provider_collection':True}
        self.output=self.f.f.root/'pinned'
    def get(self,path,limit):
        raw=(self.f.f.site/path).read_bytes();self.assertLessEqual(len(raw),limit);return raw
    def test_exact_bytes_recovered_with_mandatory_collection_skip(self):
        receipt,odds=restore_pinned_public(self.f.run,self.output,self.checkpoint,self.get)
        self.assertTrue(receipt['pinned_public_recovery']);self.assertEqual(odds,self.f.odds)
        self.assertEqual((self.output/'manifest.json').read_bytes(),(self.f.f.site/'data/complete-snapshots'/self.checkpoint['snapshot_sha256']/'manifest.json').read_bytes())
    def test_wrong_anchor_origin_hash_or_skip_rejected(self):
        for change in ({'anchor_run_id':12343},{'anchor_head_sha':'b'*40},{'origin':'https://other/'},
                       {'snapshot_sha256':'0'*64},{'odds_sha256':'0'*64},{'skip_provider_collection':False}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                restore_pinned_public(self.f.run,self.output,dict(self.checkpoint,**change),self.get)
            self.assertFalse(self.output.exists())
    def test_corrupt_file_or_provider_state_cannot_pass(self):
        for target in ('data/odds-api-events.json','manifest.json','data/catalog-live.json'):
            def get(path,limit):
                raw=self.get(path,limit)
                return raw+b' ' if path.endswith(target) else raw
            with self.subTest(target=target),self.assertRaises(ValueError):
                restore_pinned_public(self.f.run,self.output,self.checkpoint,get)
            self.assertFalse(self.output.exists())
    def test_even_reviewed_hash_cannot_release_hold(self):
        odds=json.loads(self.f.odds);odds['collector_state']['halted']=False;raw=json.dumps(odds).encode()
        cp=dict(self.checkpoint,odds_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            restore_pinned_public(self.f.run,self.output,cp,lambda p,l:raw if p=='data/odds-api-events.json' else self.get(p,l))
    def test_pointer_change_and_redirect_fail_closed(self):
        reads=0
        def get(p,l):
            nonlocal reads
            if p==POINTER:
                reads+=1
                if reads==2:return b'{}'
            return self.get(p,l)
        with self.assertRaises(ValueError):restore_pinned_public(self.f.run,self.output,self.checkpoint,get)
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_only_missing_or_expired_artifact_enters_reviewed_recovery(self):
        def evidence(p):
            if p.endswith('/artifacts?per_page=100'):return {'total_count':0,'artifacts':[]}
            return self.f.get_public(p)
        with patch('scripts.recover_pinned_public_snapshot.restore_pinned_public',return_value=({'pinned_public_recovery':True},self.f.odds)) as recover:
            result=restore_snapshot(self.f.proof,12345,self.output,get=evidence,get_archive=lambda _:self.fail(),public_recovery_checkpoint=self.checkpoint)
            self.assertTrue(result[0]['pinned_public_recovery']);recover.assert_called_once()
        self.f.jobs['jobs'][0]['steps'][8]['conclusion']='failure'
        with patch('scripts.recover_pinned_public_snapshot.restore_pinned_public') as recover,self.assertRaises(ValueError):
            restore_snapshot(self.f.proof,12345,self.output,get=evidence,get_archive=lambda _:self.fail(),public_recovery_checkpoint=self.checkpoint)
        recover.assert_not_called()
    def test_malformed_inventory_never_falls_back(self):
        for inventory in ({}, {'total_count':1,'artifacts':[]}, {'total_count':2,'artifacts':[self.f.metadata]*2}):
            def evidence(p):return inventory if p.endswith('/artifacts?per_page=100') else self.f.get_public(p)
            with patch('scripts.recover_pinned_public_snapshot.restore_pinned_public') as recover,self.assertRaises(ValueError):
                restore_snapshot(self.f.proof,12345,self.output,get=evidence,get_archive=lambda _:self.fail(),public_recovery_checkpoint=self.checkpoint)
            recover.assert_not_called()
    def test_workflow_skip_and_retention_contract(self):
        raw=(pathlib.Path(__file__).resolve().parents[1]/'.github/workflows/deploy-pages.yml').read_text()
        self.assertIn("if: steps.stage.outputs.recovered != 'true'",raw)
        self.assertIn('retention-days: 30',raw)
        self.assertIn('--public-recovery-checkpoint migration/activation/pages-public-recovery-20261115.json',raw)

if __name__=='__main__':unittest.main()
