import copy
import sys
import pathlib
import unittest
import urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import check_odds_deploy_safety as safety

class ArtifactReadinessTests(unittest.TestCase):
    def test_javascript_artifact_contract(self):
        import subprocess
        root=pathlib.Path(__file__).resolve().parents[1]
        subprocess.run(['node','--test','tests/odds_artifact_readiness.test.cjs'],cwd=root,check=True)
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
