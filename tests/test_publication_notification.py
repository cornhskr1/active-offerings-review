import base64
import copy
import hashlib
import unittest
from pathlib import Path
from scripts import verify_publication_notification as n
ROOT=Path(__file__).resolve().parents[1]
class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.raw=b'fixed historical manifest';self.digest=hashlib.sha256(self.raw).hexdigest()
        self.env=dict(NOTIFICATION_DATA_COMMIT='a'*40,NOTIFICATION_MANIFEST_SHA256=self.digest,
            GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REF='refs/heads/main',GITHUB_RUN_ATTEMPT='1',NOTIFICATION_RESUME='false')
        self.candidate=dict(data_commit='b'*40,manifest_sha256='c'*64)
        blob=hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest()
        self.compare='/compare/'+'a'*40+'...'+'b'*40+'?per_page=1'
        self.tree='/git/trees/'+'a'*40+'?recursive=1';self.blob='/git/blobs/'+blob
        self.responses={self.compare:dict(status='ahead',base_commit={'sha':'a'*40},merge_base_commit={'sha':'a'*40},ahead_by=2,behind_by=0),
            self.tree:dict(truncated=False,tree=[dict(path='published/current/manifest.json',type='blob',mode='100644',sha=blob,size=len(self.raw))]),
            self.blob:dict(sha=blob,encoding='base64',size=len(self.raw),content=base64.b64encode(self.raw).decode())}
        self.calls=[]
    def get(self,path):self.calls.append(path);return self.responses[path]
    def verify(self):return n.verify(n.inputs(self.env),self.candidate,self.get)
    def test_no_notification_preserves_scheduled_path(self):
        self.assertIsNone(n.inputs({}));n.verify(None,{},self.get);self.assertEqual(self.calls,[])
    def test_same_commit_requires_exact_fetched_manifest(self):
        self.candidate={'data_commit':'a'*40,'manifest_sha256':self.digest};self.verify();self.assertEqual(self.calls,[])
        self.candidate['manifest_sha256']='0'*64
        with self.assertRaises(ValueError):self.verify()
    def test_stale_notification_binds_newer_exact_candidate_without_rollback(self):
        before=copy.deepcopy(self.candidate);self.verify();self.assertEqual(self.candidate,before)
        self.assertEqual(self.calls,[self.compare,self.tree,self.blob])
        self.assertFalse(any('main' in c for c in self.calls))
    def test_incomplete_pair_rerun_resume_non_dispatch_wrong_branch_rejected(self):
        for key,value in [('NOTIFICATION_DATA_COMMIT',''),('NOTIFICATION_MANIFEST_SHA256',''),
            ('NOTIFICATION_DATA_COMMIT','A'*40),('NOTIFICATION_MANIFEST_SHA256','x'*64),
            ('GITHUB_EVENT_NAME','schedule'),('GITHUB_REF','refs/heads/other'),
            ('GITHUB_RUN_ATTEMPT','2'),('NOTIFICATION_RESUME','true')]:
            self.setUp();self.env[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):n.inputs(self.env)
    def test_diverged_ancestry_incomplete_tree_symlink_and_tampering_block(self):
        for damage in ('diverged','base','merge','behind','tree','duplicate','symlink','blob','digest'):
            self.setUp()
            if damage=='diverged':self.responses[self.compare]['status']='diverged'
            elif damage in ('base','merge'):self.responses[self.compare]['base_commit' if damage=='base' else 'merge_base_commit']['sha']='d'*40
            elif damage=='behind':self.responses[self.compare]['behind_by']=1
            elif damage=='tree':self.responses[self.tree]['truncated']=True
            elif damage=='duplicate':self.responses[self.tree]['tree']*=2
            elif damage=='symlink':self.responses[self.tree]['tree'][0]['mode']='120000'
            elif damage=='blob':self.responses[self.blob]['content']=base64.b64encode(b'tampered').decode()
            else:self.env['NOTIFICATION_MANIFEST_SHA256']='0'*64
            with self.subTest(damage=damage),self.assertRaises(ValueError):self.verify()
    def test_no_new_steps_or_resume_override_and_verify_before_staging(self):
        raw=(ROOT/'.github/workflows/deploy-pages.yml').read_text()
        self.assertIn('!inputs.notification_data_commit && !inputs.notification_manifest_sha256 && inputs.resume_after_review',raw)
        self.assertIn('cancel-in-progress: false',raw)
        code=(ROOT/'scripts/restore_public_snapshot.py').read_text()
        self.assertLess(code.index('notification = inputs()'),code.index('private=fetch_candidate'))
        self.assertLess(code.index('private=fetch_candidate'),code.index('verify(notification,private,private_get)'))
        self.assertLess(code.index('verify(notification,private,private_get)'),code.index("stage(root,work/'current-app')"))
        self.assertIn('prepare_full_preview(',code)

if __name__=='__main__':unittest.main()
