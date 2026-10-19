"""Prevent retrying provider collection after an uncertain/failed deployment.

Uses only the workflow's ephemeral, read-only GitHub token. Never reads the
provider key. The Pages concurrency lock must remain workflow-wide.
"""
import json,os,urllib.request,urllib.error
from datetime import datetime,timezone
REPOSITORY='cornhskr1/active-offerings-review'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Redirect rejected')
def permitted(current,runs,resume=False):
 if (not isinstance(current,dict) or current.get('path')!='.github/workflows/deploy-pages.yml'
     or current.get('head_branch')!='main' or not isinstance(current.get('id'),int)
     or not isinstance(current.get('workflow_id'),int) or not isinstance(current.get('run_number'),int)):
  return False
 if not isinstance(runs,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),int)
      or r.get('workflow_id')!=current['workflow_id'] or r.get('head_branch')!='main'
      or not isinstance(r.get('run_number'),int) for r in runs):return False
 if current.get('run_attempt')!=1:return False
 prior=[r for r in runs if r['id']!=current['id'] and r.get('status')!='queued']
 if not prior:return current['run_number']==1
 if any(r.get('status')!='completed' for r in prior):return False
 try:
  stamps=[datetime.fromisoformat(run['updated_at'].replace('Z','+00:00')) for run in prior]
  if any(stamp.tzinfo is None or stamp>datetime.now(timezone.utc) for stamp in stamps):return False
  latest=max(stamps)
 except (KeyError,ValueError,TypeError,AttributeError):return False
 if resume:return True  # New owner-reviewed dispatch only, never a rerun.
 return all(run.get('conclusion')=='success' for run,stamp in zip(prior,stamps) if stamp==latest)

def all_runs(get_page):
 result=[];seen=set();expected=None
 for page in range(1,101):
  payload=get_page(page)
  if not isinstance(payload,dict) or not isinstance(payload.get('total_count'),int) or not isinstance(payload.get('workflow_runs'),list):
   raise ValueError('Workflow history unavailable')
  if expected is None:expected=payload['total_count']
  if payload['total_count']!=expected:raise ValueError('Workflow history changed during verification')
  rows=payload['workflow_runs']
  if not rows and len(result)<expected:raise ValueError('Truncated workflow history')
  for row in rows:
   if not isinstance(row,dict) or not isinstance(row.get('id'),int) or row['id'] in seen:raise ValueError('Ambiguous workflow history')
   seen.add(row['id']);result.append(row)
  if len(result)==expected:return result
  if len(result)>expected:raise ValueError('Workflow history count mismatch')
 raise ValueError('Workflow history exceeds verification limit')
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
 runs=all_runs(lambda page:get('/actions/workflows/'+str(workflow)+'/runs?per_page=100&page='+str(page)))
 resume=os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and os.environ.get('RESUME_AFTER_REVIEW')=='true'
 if not permitted(current,runs,resume):raise ValueError('Previous deployment was not confirmed successful. Review the failure before explicitly resuming collection.')
if __name__=='__main__':
 try:main()
 except Exception:
  raise SystemExit('Collection blocked: deployment history is failed, uncertain, or unavailable. Review before resuming; no provider request was made.')
