"""Prevent retrying provider collection after an uncertain/failed deployment.

Uses only the workflow's ephemeral, read-only GitHub token. Never reads the
provider key. The Pages concurrency lock must remain workflow-wide.
"""
import json,os,re,urllib.request,urllib.error
from datetime import datetime,timezone
REPOSITORY='cornhskr1/active-offerings-review'
WORKFLOW_PATH='.github/workflows/deploy-pages.yml'
# Audited workflow-wide, literal `pages` lock with cancel-in-progress: false.
# Review the serialization contract before updating this pin after a YAML edit.
SERIALIZED_WORKFLOW_BLOB='eaae3f7f1ad34cfbaaacd9a3ab22a089ef617429'
class HistoryChanged(ValueError):
 pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Redirect rejected')
def permitted(current,runs,resume=False,precollection_failures=frozenset(),pending_runs=frozenset()):
 if (not isinstance(current,dict) or current.get('path')!='.github/workflows/deploy-pages.yml'
     or current.get('head_branch')!='main' or not isinstance(current.get('id'),int)
     or not isinstance(current.get('workflow_id'),int) or not isinstance(current.get('run_number'),int)):
  return False
 if not isinstance(runs,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),int)
      or r.get('workflow_id')!=current['workflow_id'] or r.get('head_branch')!='main'
      or not isinstance(r.get('run_number'),int) for r in runs):return False
 if current.get('run_attempt')!=1:return False
 prior=[r for r in runs if r['id']!=current['id'] and r.get('status')!='queued'
        and not (r.get('status')=='pending' and r['id'] in pending_runs)]
 if not prior:return current['run_number']==1
 if any(r.get('status')!='completed' for r in prior):return False
 try:
  stamps=[datetime.fromisoformat(run['updated_at'].replace('Z','+00:00')) for run in prior]
  if any(stamp.tzinfo is None or stamp>datetime.now(timezone.utc) for stamp in stamps):return False
  latest=max(stamps)
 except (KeyError,ValueError,TypeError,AttributeError):return False
 if resume:return True  # New owner-reviewed dispatch only, never a rerun.
 # Only independently proved no-collection failures/cancellations may be removed from the
 # completion history. A successful published anchor must still remain.
 checked=[(run,stamp) for run,stamp in zip(prior,stamps)
          if not (run['id'] in precollection_failures and run.get('conclusion') in ('failure','cancelled'))]
 if not checked:return False
 latest=max(stamp for _,stamp in checked)
 return all(run.get('conclusion')=='success' for run,stamp in checked if stamp==latest)

def all_runs(get_page):
 result=[];seen=set();expected=None
 for page in range(1,101):
  payload=get_page(page)
  if not isinstance(payload,dict) or not isinstance(payload.get('total_count'),int) or not isinstance(payload.get('workflow_runs'),list):
   raise ValueError('Workflow history unavailable')
  if expected is None:expected=payload['total_count']
  if payload['total_count']!=expected:raise HistoryChanged('Workflow history changed during verification')
  rows=payload['workflow_runs']
  if not rows and len(result)<expected:raise ValueError('Truncated workflow history')
  for row in rows:
   if not isinstance(row,dict) or not isinstance(row.get('id'),int) or row['id'] in seen:raise ValueError('Ambiguous workflow history')
   seen.add(row['id']);result.append(row)
  if len(result)==expected:return result
  if len(result)>expected:raise ValueError('Workflow history count mismatch')
 raise ValueError('Workflow history exceeds verification limit')
def stable_runs(get_page):
 # New queued deployments can arrive during pagination. Restart the WHOLE
 # read, never combine pages from different totals or ignore uncertain rows.
 for attempt in range(3):
  try:return all_runs(get_page)
  except HistoryChanged:
   if attempt==2:raise

def serialized_pending_runs(current,runs,get_run,get_jobs,get_workflow,workflow_sha,workflow_ref):
 # `pending` is GitHub's workflow-concurrency waiting state, not a prior failure.
 # Empty jobs alone are a racy observation. Prove the immutable workflow at BOTH
 # execution commits uses the same audited workflow-wide lock, which prevents a
 # successor from starting while this run is active, even after our last read.
 pending=[r for r in runs if r.get('id')!=current.get('id') and r.get('status')=='pending']
 if not pending:return set()
 def identity(run):
  return (isinstance(run,dict) and all(type(run.get(k)) is int and run[k]>0 for k in ('id','workflow_id','run_number','run_attempt'))
          and run['run_attempt']==1 and 'conclusion' in run and run.get('path')==WORKFLOW_PATH
          and run.get('head_branch')=='main' and isinstance(run.get('repository'),dict)
          and run['repository'].get('full_name')==REPOSITORY
          and isinstance(run.get('head_repository'),dict) and run['head_repository'].get('full_name')==REPOSITORY
          and run.get('event') in ('push','schedule','workflow_dispatch','workflow_run')
          and isinstance(run.get('head_sha'),str) and re.fullmatch('[0-9a-f]{40}',run['head_sha']) is not None)
 def same_run(a,b):
  return identity(b) and all(a.get(k)==b.get(k) for k in ('id','workflow_id','run_number','run_attempt','path','head_branch','head_sha','event'))
 def active(run):return run.get('status')=='in_progress' and run.get('conclusion') is None
 def audited(sha):
  payload=get_workflow(sha)
  return (isinstance(payload,dict) and payload.get('type')=='file'
          and payload.get('path')==WORKFLOW_PATH and payload.get('sha')==SERIALIZED_WORKFLOW_BLOB)
 if (not identity(current) or not active(current) or workflow_sha!=current['head_sha']
     or workflow_ref!=REPOSITORY+'/'+WORKFLOW_PATH+'@refs/heads/main'
     or not audited(workflow_sha)):return set()
 result=set()
 for run in pending:
  if (not identity(run) or run['workflow_id']!=current['workflow_id']
      or run['run_number']<=current['run_number'] or run.get('conclusion') is not None
      or not audited(run['head_sha'])):continue
  payload=get_jobs(run['id'])
  if not (isinstance(payload,dict) and type(payload.get('total_count')) is int
          and payload['total_count']==0 and isinstance(payload.get('jobs'),list) and payload['jobs']==[]):continue
  latest=get_run(run['id'])
  if not same_run(run,latest):continue
  # Replacement of the pending slot may cancel it during verification. The
  # pinned attempt had no jobs, and the fixed lock rules out a start in between.
  if ((latest.get('status')=='pending' and latest.get('conclusion') is None)
      or (latest.get('status')=='completed' and latest.get('conclusion')=='cancelled')):
   result.add(run['id'])
 latest_current=get_run(current['id'])
 return result if same_run(current,latest_current) and active(latest_current) else set()

DEPLOY_STEPS=['Set up job','Checkout latest main','Run actions/setup-python@v5',
 'Verify previous deployment before any provider collection','Stage public site and recover last event snapshot',
 'Refresh zero-quota event observations only','Run actions/configure-pages@v5',
 'Run actions/upload-pages-artifact@v3','Run actions/deploy-pages@v4',
 'Post Run actions/setup-python@v5','Post Checkout latest main','Complete job']
RECOVERY_STEPS=DEPLOY_STEPS.copy()
RECOVERY_STEPS[4]='Stage site with pinned verified-cache recovery'
def verified_job_steps(run,payload):
 if run.get('run_attempt')!=1 or run.get('status')!='completed':return None
 if not isinstance(payload,dict) or payload.get('total_count')!=1:return None
 jobs=payload.get('jobs')
 if not isinstance(jobs,list) or len(jobs)!=1:return None
 job=jobs[0]
 if (not isinstance(job,dict) or job.get('run_id')!=run['id'] or job.get('run_attempt')!=1
     or job.get('head_branch')!='main' or job.get('name')!='deploy' or job.get('status')!='completed'
     or job.get('conclusion')!=run.get('conclusion')):return None
 steps=job.get('steps')
 if not isinstance(steps,list) or len(steps)!=len(DEPLOY_STEPS):return None
 if any(not isinstance(step,dict) or step.get('status')!='completed' for step in steps):return None
 if [step.get('name') for step in steps] not in (DEPLOY_STEPS,RECOVERY_STEPS):return None
 if [step.get('number') for step in steps]!=[1,2,3,4,5,6,7,8,9,17,18,19]:return None
 return [step.get('conclusion') for step in steps]

def precollection_failure(run,payload):
 if run.get('conclusion')!='failure':return False
 outcomes=verified_job_steps(run,payload)
 return bool(outcomes and ((outcomes[:4]==['success','success','success','failure'] and outcomes[4:9]==['skipped']*5) or (outcomes[:5]==['success']*4+['failure'] and outcomes[5:9]==['skipped']*4)) and all(x in ('success','skipped') for x in outcomes[9:]))

def cancelled_before_job_start(run,payload):
 # A first-attempt run cancelled while waiting for the Pages lock has no jobs.
 # The authenticated attempt-1 jobs response must prove absence, not omit it.
 # Re-runs are excluded: an empty latest attempt cannot clear earlier API use.
 return (isinstance(run,dict) and type(run.get('run_attempt')) is int
         and run['run_attempt']==1 and run.get('status')=='completed'
         and run.get('conclusion')=='cancelled' and isinstance(payload,dict)
         and type(payload.get('total_count')) is int and payload['total_count']==0
         and isinstance(payload.get('jobs'),list) and payload['jobs']==[])

def successful_publication(run,payload):
 outcomes=verified_job_steps(run,payload)
 if run.get('conclusion')!='success' or not outcomes:return False
 recovery=payload['jobs'][0]['steps'][4]['name']==RECOVERY_STEPS[4]
 return outcomes==['success']*12 or (recovery and outcomes==['success']*5+['skipped']+['success']*6)

def proved_precollection_failures(runs,get_jobs):
 # Inspect only failures/cancellations newer than the latest success. Older history remains
 # intact and uncertain states are still rejected by permitted().
 try:
  completed=[(r,datetime.fromisoformat(r['updated_at'].replace('Z','+00:00'))) for r in runs if r.get('status')=='completed']
  if any(stamp.tzinfo is None or stamp>datetime.now(timezone.utc) for _,stamp in completed):return set()
 except (KeyError,ValueError,TypeError,AttributeError):return set()
 successful=[stamp for r,stamp in completed if r.get('conclusion')=='success']
 if not successful:return set()
 latest=max(successful)
 anchors=[r for r,stamp in completed if stamp==latest and r.get('conclusion')=='success']
 if not anchors or not all(successful_publication(r,get_jobs(r['id'])) for r in anchors):return set()
 result=set()
 for run,stamp in completed:
  if run.get('conclusion') in ('failure','cancelled') and stamp>=latest:
   payload=get_jobs(run['id'])
   if precollection_failure(run,payload) or cancelled_before_job_start(run,payload):result.add(run['id'])
 return result

def main():
 if os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:raise ValueError('Repository mismatch')
 token=os.environ.get('GH_TOKEN','')
 if not token:raise ValueError('GitHub workflow verification unavailable')
 run_id=os.environ.get('GITHUB_RUN_ID','')
 if not run_id.isdigit():raise ValueError('Invalid workflow identity')
 opener=urllib.request.build_opener(NoRedirect())
 def get(path):
  request=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
  with opener.open(request,timeout=20) as response:raw=response.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('Workflow response too large')
  return json.loads(raw)
 current=get('/actions/runs/'+run_id)
 if current.get('id')!=int(run_id) or current.get('repository',{}).get('full_name')!=REPOSITORY:raise ValueError('Current run mismatch')
 workflow=current.get('workflow_id')
 if not isinstance(workflow,int):raise ValueError('Workflow identity missing')
 runs=stable_runs(lambda page:get('/actions/workflows/'+str(workflow)+'/runs?per_page=100&page='+str(page)))
 pending=serialized_pending_runs(current,runs,
  lambda identity:get('/actions/runs/'+str(identity)),
  lambda identity:get('/actions/runs/'+str(identity)+'/attempts/1/jobs?per_page=100'),
  lambda sha:get('/contents/'+WORKFLOW_PATH+'?ref='+sha),
  os.environ.get('GITHUB_WORKFLOW_SHA'),os.environ.get('GITHUB_WORKFLOW_REF'))
 resume=os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and os.environ.get('RESUME_AFTER_REVIEW')=='true'
 # Pin the jobs read to attempt 1. A concurrent re-run must not make an empty
 # latest attempt hide jobs from the attempt whose history we are verifying.
 proved=proved_precollection_failures(runs,lambda failed_id:get('/actions/runs/'+str(failed_id)+'/attempts/1/jobs?per_page=100')) if not resume else set()
 if not permitted(current,runs,resume,proved,pending):raise ValueError('Previous deployment was not confirmed successful. Review the failure before explicitly resuming collection.')
 if pending:print('Verified '+str(len(pending))+' never-started deployment(s) waiting for the same Pages lock.')
 # Artifact restoration is allowed only from the exact verified publication anchor.
 if not resume:
  anchors=[r for r in runs if r.get('status')=='completed' and r.get('conclusion')=='success']
  anchor=max(anchors,key=lambda r:datetime.fromisoformat(r['updated_at'].replace('Z','+00:00'))) if anchors else None
  if anchor and successful_publication(anchor,get('/actions/runs/'+str(anchor['id'])+'/attempts/1/jobs?per_page=100')):
   from pathlib import Path
   Path(os.environ['RUNNER_TEMP'],'odds-recovery-proof.json').write_text(json.dumps({'repository':REPOSITORY,'current_run_id':int(run_id),'anchor_run_id':anchor['id']}))
if __name__=='__main__':
 try:main()
 except Exception:
  raise SystemExit('Collection blocked: deployment history is failed, uncertain, or unavailable. Review before resuming; no provider request was made.')

