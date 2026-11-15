import copy
import sys
import pathlib
import unittest
import urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import wait_pages_artifact as ready
import check_odds_deploy_safety as safety

class ArtifactReadinessTests(unittest.TestCase):
    def setUp(self):
        self.artifact = dict(id=5, name='github-pages', expired=False, size_in_bytes=10,
                            workflow_run=dict(id=9, head_branch='main', head_sha='a'*40))
        self.good = dict(total_count=1, artifacts=[self.artifact])
    def check(self, payload):
        return ready.artifact_ready(payload, 5, 9, 'a'*40)
    def test_exact_artifact(self):
        self.assertTrue(self.check(self.good))
    def test_visibility_delay_retries_only_read(self):
        responses = iter([dict(total_count=0, artifacts=[]), self.good])
        waits=[]
        ready.wait_for_artifact(lambda: next(responses), 5, 9, 'a'*40, waits.append)
        self.assertEqual(waits, [10])
    def test_absence_is_bounded(self):
        waits=[]
        with self.assertRaises(ValueError):
            ready.wait_for_artifact(lambda:dict(total_count=0,artifacts=[]),5,9,'a'*40,waits.append)
        self.assertEqual(waits,[10]*6)
    def test_reject_wrong_identity_expired_empty_duplicate_truncated(self):
        for changes in (dict(id=6),dict(name='other'),dict(expired=True),dict(size_in_bytes=0),
                        dict(workflow_run=dict(id=10,head_branch='main',head_sha='a'*40)),
                        dict(workflow_run=dict(id=9,head_branch='other',head_sha='a'*40)),
                        dict(workflow_run=dict(id=9,head_branch='main',head_sha='b'*40))):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.check(dict(total_count=1,artifacts=[dict(self.artifact,**changes)]))
        for payload in ({},dict(total_count=2,artifacts=[self.artifact]),dict(total_count=2,artifacts=[self.artifact]*2)):
            with self.assertRaises(ValueError): self.check(payload)
    def test_transient_api_only(self):
        for code in (404,429,500,502,503,504):
            calls=[]
            def fetch():
                calls.append(1)
                if len(calls)==1: raise urllib.error.HTTPError('https://api.github.com',code,'transient',{},None)
                return self.good
            ready.wait_for_artifact(fetch,5,9,'a'*40,lambda _:None)
            self.assertEqual(len(calls),2)
        for code in (401,403):
            def fetch(): raise urllib.error.HTTPError('https://api.github.com',code,'denied',{},None)
            with self.assertRaises(urllib.error.HTTPError):
                ready.wait_for_artifact(fetch,5,9,'a'*40,lambda _:self.fail('must not retry denial'))
    def test_new_history_profile_requires_readiness_success(self):
        run=dict(id=9,run_attempt=1,status='completed',conclusion='success')
        numbers=[1,2,3,4,5,6,7,8,9,10,18,19,20]
        steps=[dict(name=n,number=i,status='completed',conclusion='success') for n,i in zip(safety.READY_RECOVERY_STEPS,numbers)]
        job=dict(run_id=9,run_attempt=1,head_branch='main',name='deploy',status='completed',conclusion='success',steps=steps)
        payload=dict(total_count=1,jobs=[job])
        self.assertTrue(safety.successful_publication(run,payload))
        for conclusion in ('skipped','failure'):
            changed=copy.deepcopy(payload);changed['jobs'][0]['steps'][8]['conclusion']=conclusion
            self.assertFalse(safety.successful_publication(run,changed))
        failed=dict(run,conclusion='failure');job['conclusion']='failure';steps[8]['conclusion']='failure';steps[9]['conclusion']='skipped'
        self.assertFalse(safety.precollection_failure(failed,payload))
    def test_precollection_still_proved_new_profile(self):
        run=dict(id=9,run_attempt=1,status='completed',conclusion='failure')
        outcomes=['success']*3+['failure']+['skipped']*7+['success']*2
        steps=[dict(name=n,number=i,status='completed',conclusion=o) for n,i,o in zip(safety.READY_RECOVERY_STEPS,[1,2,3,4,5,6,7,8,9,10,18,19,20],outcomes)]
        job=dict(run_id=9,run_attempt=1,head_branch='main',name='deploy',status='completed',conclusion='failure',steps=steps)
        self.assertTrue(safety.precollection_failure(run,dict(total_count=1,jobs=[job])))

if __name__=='__main__': unittest.main()
