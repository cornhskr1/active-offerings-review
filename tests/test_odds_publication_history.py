"""Offline regression for pinned Actions and conditionally skipped deployments."""
import copy
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_odds_deploy_safety as safety


class PublicationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.current = dict(id=13, workflow_id=99, run_number=13, run_attempt=1,
            path=safety.WORKFLOW_PATH, head_branch='main', head_sha='a'*40,
            repository={'full_name':safety.REPOSITORY},
            head_repository={'full_name':safety.REPOSITORY}, event='workflow_run',
            status='in_progress', conclusion=None)
        self.anchor = dict(self.current, id=9, run_number=9, status='completed',
            conclusion='success', updated_at='2026-10-19T01:00:00Z')
        self.skip = dict(self.anchor, id=10, run_number=10, conclusion='skipped',
            updated_at='2026-10-19T02:00:00Z')
        self.failure = dict(self.anchor, id=11, run_number=11, conclusion='failure',
            updated_at='2026-10-19T03:00:00Z')
        self.skipped_job = dict(run_id=10, run_attempt=1, head_branch='main',
            head_sha='a'*40, name='deploy', status='completed', conclusion='skipped',
            steps=[], runner_id=None, runner_name=None, runner_group_id=None,
            runner_group_name=None)
        self.skip_payload = dict(total_count=1,jobs=[self.skipped_job])

    def jobs(self, run_id):
        if run_id==10:return copy.deepcopy(self.skip_payload)
        outcomes = ['success']*12 if run_id==9 else ['success']*3+['failure']+['skipped']*6+['success']*2
        return dict(total_count=1,jobs=[dict(run_id=run_id,run_attempt=1,
            head_branch='main',name='deploy',status='completed',
            conclusion='success' if run_id==9 else 'failure',
            steps=[dict(number=n,name=name,status='completed',conclusion=c)
                for n,name,c in zip([1,2,3,4,5,6,7,8,9,17,18,19],
                    safety.PINNED_RECOVERY_STEPS,outcomes)])])

    def test_pinned_success_skip_and_guard_failure_restore_only_verified_anchor(self):
        runs=[self.anchor,self.skip,self.failure]
        self.assertFalse(safety.permitted(self.current,runs))
        proof=safety.proved_precollection_failures(runs,self.jobs)
        self.assertEqual(proof,{10,11})
        self.assertTrue(safety.permitted(self.current,runs,precollection_failures=proof))
        self.assertEqual(safety.proved_precollection_failures([self.skip,self.failure],self.jobs),set())
        self.assertFalse(safety.permitted(self.current,[self.skip],precollection_failures={10}))
        self.assertFalse(safety.permitted(self.current,runs,precollection_failures={11}))

    def test_current_workflow_pins_are_exact_verified_step_contract(self):
        raw=(ROOT/safety.WORKFLOW_PATH).read_text()
        for index in (2,6,7,8):
            self.assertIn('uses: '+safety.PINNED_RECOVERY_STEPS[index].removeprefix('Run '),raw)
        self.assertEqual(safety.PINNED_RECOVERY_STEPS[9],'Post '+safety.PINNED_RECOVERY_STEPS[2])
        self.assertTrue(safety.successful_publication(self.anchor,self.jobs(9)))
        recovery=self.jobs(9);recovery['jobs'][0]['steps'][5]['conclusion']='skipped'
        self.assertTrue(safety.successful_publication(self.anchor,recovery))
        for index in (2,6,7,8,9):
            changed=self.jobs(9);changed['jobs'][0]['steps'][index]['name']+='0'
            self.assertFalse(safety.successful_publication(self.anchor,changed))
        mixed=self.jobs(9);mixed['jobs'][0]['steps'][2]['name']=safety.DEPLOY_STEPS[2]
        self.assertFalse(safety.successful_publication(self.anchor,mixed))

    def test_skipped_proof_rejects_missing_ambiguous_or_started_jobs(self):
        self.assertTrue(safety.skipped_before_job_start(self.skip,self.skip_payload))
        for payload in (None,{}, {'total_count':0,'jobs':[]},
            {'total_count':True,'jobs':[self.skipped_job]},
            {'total_count':2,'jobs':[self.skipped_job]},
            {'total_count':1,'jobs':[]}, {'total_count':1,'jobs':None}):
            with self.subTest(payload=payload):
                self.assertFalse(safety.skipped_before_job_start(self.skip,payload))
        for key,value in [('run_id',99),('run_id',True),('run_attempt',2),
            ('run_attempt',True),('head_sha','b'*40),('head_branch','other'),
            ('name','other'),('status','in_progress'),('conclusion','success'),
            ('steps',None),('steps',[{'name':'collection','conclusion':'success'}]),
            ('runner_id',1),('runner_name','runner'),('runner_group_id',0),
            ('runner_group_name','GitHub Actions')]:
            p=copy.deepcopy(self.skip_payload);p['jobs'][0][key]=value
            with self.subTest(key=key,value=value):
                self.assertFalse(safety.skipped_before_job_start(self.skip,p))
        for key in self.skipped_job:
            p=copy.deepcopy(self.skip_payload);del p['jobs'][0][key]
            with self.subTest(missing=key):
                self.assertFalse(safety.skipped_before_job_start(self.skip,p))

    def test_skipped_run_identity_must_be_exact_first_attempt(self):
        for key,value in [('id',True),('id',0),('run_attempt',2),('run_attempt',True),
            ('workflow_id','99'),('run_number',None),('status','pending'),
            ('conclusion','cancelled'),('event','push'),('path','other.yml'),
            ('head_branch','other'),('head_sha','main'),('head_sha',None),
            ('repository',{}),('head_repository',None)]:
            run=dict(self.skip,**{key:value})
            with self.subTest(key=key,value=value):
                self.assertFalse(safety.skipped_before_job_start(run,self.skip_payload))
        self.assertFalse(safety.skipped_before_job_start(None,self.skip_payload))

    def test_started_collection_and_unknown_history_remain_blocking(self):
        def jobs(n):
            p=self.jobs(n)
            if n==11:p['jobs'][0]['steps'][5]['conclusion']='failure'
            return p
        runs=[self.anchor,self.skip,self.failure]
        proof=safety.proved_precollection_failures(runs,jobs)
        self.assertEqual(proof,{10})
        self.assertFalse(safety.permitted(self.current,runs,precollection_failures=proof))
        for outcome in ('timed_out','action_required','neutral','unknown'):
            r=dict(self.failure,conclusion=outcome)
            proof=safety.proved_precollection_failures([self.anchor,self.skip,r],self.jobs)
            self.assertFalse(safety.permitted(self.current,[self.anchor,self.skip,r],precollection_failures=proof))
        def unavailable(n):
            if n==10:raise ValueError('unavailable')
            return self.jobs(n)
        with self.assertRaises(ValueError):
            safety.proved_precollection_failures(runs,unavailable)

    def resume_main(self, runs=None, jobs=None, event='workflow_dispatch', resume='true', attempt=1):
        current=dict(self.current,event=event,run_attempt=attempt)
        runs=[self.anchor,self.failure,current] if runs is None else runs
        calls=[]
        fixture=self
        class GitHub:
            def open(self, request, timeout):
                path=request.full_url.split(safety.REPOSITORY)[1];calls.append(path)
                if path=='/actions/runs/13':payload=current
                elif path=='/actions/workflows/99/runs?per_page=100&page=1':
                    payload={'total_count':len(runs),'workflow_runs':runs}
                elif path=='/actions/runs/9/attempts/1/jobs?per_page=100':
                    payload=(jobs or fixture.jobs)(9)
                elif path=='/actions/runs/11/attempts/1/jobs?per_page=100':
                    payload=fixture.jobs(11)
                    # Hosting failure after collection must never be auto-ignored.
                    for step in payload['jobs'][0]['steps'][:8]:step['conclusion']='success'
                    payload['jobs'][0]['steps'][8]['conclusion']='failure'
                else:raise AssertionError('Unexpected endpoint: '+path)
                return io.BytesIO(json.dumps(payload).encode())
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{
            'GITHUB_REPOSITORY':safety.REPOSITORY,'GH_TOKEN':'synthetic-test-token',
            'GITHUB_RUN_ID':'13','GITHUB_EVENT_NAME':event,
            'RESUME_AFTER_REVIEW':resume,'RUNNER_TEMP':temp,
        }), patch.object(safety.urllib.request,'build_opener',return_value=GitHub()):
            path=pathlib.Path(temp)/'odds-recovery-proof.json'
            try:safety.main()
            except ValueError:
                self.assertFalse(path.exists(),'Rejected recovery must not leave a proof')
                raise
            return json.loads(path.read_text()),calls

    def test_reviewed_new_dispatch_restores_only_verified_success_not_failed_artifact(self):
        proof,calls=self.resume_main()
        self.assertEqual(proof,{'repository':safety.REPOSITORY,'current_run_id':13,'anchor_run_id':9})
        self.assertIn('/actions/runs/9/attempts/1/jobs?per_page=100',calls)
        self.assertNotIn('/actions/runs/11/attempts/1/jobs?per_page=100',calls)

    def test_reviewed_resume_without_valid_anchor_cannot_create_proof(self):
        for runs in ([self.failure],[]):
            with self.subTest(runs=runs),self.assertRaises(ValueError):self.resume_main(runs=runs)
        for damage in ('rerun','missing','changed_action','collection_failed','unavailable'):
            def jobs(n):
                if damage=='unavailable':raise ValueError('Jobs unavailable')
                payload=self.jobs(n)
                if damage=='rerun':payload['jobs'][0]['run_attempt']=2
                elif damage=='missing':payload['jobs']=[]
                elif damage=='changed_action':payload['jobs'][0]['steps'][8]['name']+='0'
                else:payload['jobs'][0]['steps'][5]['conclusion']='failure'
                return payload
            # An older success cannot replace a damaged latest-success anchor.
            older=dict(self.anchor,id=8,run_number=8,updated_at='2026-10-18T01:00:00Z')
            with self.subTest(damage=damage),self.assertRaises(ValueError):
                self.resume_main(runs=[older,self.anchor,self.failure],jobs=jobs)

    def test_resume_does_not_clear_automatic_trigger_rerun_or_active_history(self):
        for event,resume,attempt in [('push','true',1),('schedule','true',1),
                ('workflow_run','true',1),('workflow_dispatch','false',1),('workflow_dispatch','true',2)]:
            with self.subTest(event=event,resume=resume,attempt=attempt),self.assertRaises(ValueError):
                self.resume_main(event=event,resume=resume,attempt=attempt)
        for status in ('in_progress','pending','waiting'):
            active=dict(self.failure,status=status,conclusion=None)
            with self.subTest(status=status),self.assertRaises(ValueError):
                self.resume_main(runs=[self.anchor,active])

if __name__=='__main__':unittest.main()
