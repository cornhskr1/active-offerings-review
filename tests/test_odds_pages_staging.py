import io,json,pathlib,tempfile,unittest,urllib.error,sys,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from stage_odds_pages import recover_previous,stage,PRODUCTION,MAX_BYTES
class Opener:
 def __init__(self,values):self.values=iter(values);self.calls=[]
 def open(self,url,timeout):
  self.calls.append(url);value=next(self.values)
  if isinstance(value,Exception):raise value
  return io.BytesIO(value)
class StagingTests(unittest.TestCase):
 def test_only_prior_public_location(self):
  o=Opener([])
  with self.assertRaises(ValueError):recover_previous('https://example.com/cache',o)
  self.assertEqual(o.calls,[])
 def test_first_deployment_only(self):
  error=urllib.error.HTTPError(PRODUCTION,404,'not found',{},None)
  o=Opener([error,b'<html>Upcoming Event Review</html>'])
  self.assertIsNone(recover_previous(PRODUCTION+'data/odds-api-events.json',o))
  o=Opener([error,b'Upcoming Event Review data/odds-api-events.json'])
  with self.assertRaises(ValueError):recover_previous(PRODUCTION+'data/odds-api-events.json',o)
 def test_cache_failure_never_resets_halt(self):
  for data in [b'{}',b'bad json',b'x'*(MAX_BYTES+1)]:
   with self.assertRaises(ValueError):recover_previous(PRODUCTION+'data/odds-api-events.json',Opener([data]))
  data={'schema_version':1,'provider':'The Odds API','collector_state':{'halted':True}}
  self.assertTrue(recover_previous(PRODUCTION+'data/odds-api-events.json',Opener([json.dumps(data).encode()]))['collector_state']['halted'])
 def test_only_tracked_files_staged(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)/'repo';root.mkdir();subprocess.run(['git','init','-q',str(root)],check=True)
   (root/'index.html').write_text('public');(root/'untracked-secret').write_text('synthetic-not-secret')
   subprocess.run(['git','add','index.html'],cwd=root,check=True)
   output=pathlib.Path(temp)/'site';stage(root,output)
   self.assertEqual((output/'index.html').read_text(),'public');self.assertFalse((output/'untracked-secret').exists());self.assertFalse((output/'.git').exists())
 def test_main_only_secret_and_no_git_data_write(self):
  s=(ROOT/'.github/workflows/deploy-pages.yml').read_text()
  self.assertIn('17 */3 * * *',s);self.assertIn("github.ref == 'refs/heads/main'",s)
  self.assertIn('ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}',s)
  self.assertIn('runner.temp }}/active-offerings-site',s)
  for forbidden in ['git push','git commit','pull_request_target','/odds?','/scores?'] :self.assertNotIn(forbidden,s)

from check_odds_deploy_safety import permitted,all_runs
class DeploySafetyTests(unittest.TestCase):
 def test_failed_or_uncertain_previous_run_blocks_retry(self):
  current={'id':10,'workflow_id':99,'path':'.github/workflows/deploy-pages.yml','head_branch':'main','run_attempt':1,'run_number':10}
  previous={'id':9,'workflow_id':99,'run_started_at':'2026-10-19T00:00:00Z','updated_at':'2026-10-19T00:01:00Z','head_branch':'main','run_number':9,'status':'completed','conclusion':'success'}
  self.assertTrue(permitted(current,[previous]))
  for conclusion in ['failure','cancelled','timed_out',None]:
   self.assertFalse(permitted(current,[{**previous,'conclusion':conclusion}]))
  self.assertFalse(permitted(current,[{**previous,'status':'in_progress'}]))
  self.assertFalse(permitted(current,[previous,{**previous,'id':8,'run_number':8,'run_started_at':'2026-10-19T01:00:00Z','updated_at':'2026-10-19T01:01:00Z','conclusion':'failure'}]))
  self.assertFalse(permitted(current,[]))
  self.assertFalse(permitted(current,[{**previous,'workflow_id':100}]))
  self.assertFalse(permitted(current,[{'id':9}]))
  self.assertFalse(permitted({**current,'head_branch':'other'},[previous],resume=True))
  self.assertFalse(permitted({**current,'run_attempt':2},[previous]))
  self.assertFalse(permitted({**current,'run_attempt':2},[previous],resume=True))
  self.assertFalse(permitted(current,[previous,{**previous,'id':11,'run_number':11,'run_started_at':'2026-10-19T01:00:00Z','updated_at':'2026-10-19T01:01:00Z','conclusion':'failure'}]))
  self.assertTrue(permitted({**current,'run_number':1},[]))
  self.assertTrue(permitted(current,[{**previous,'conclusion':'failure'}],resume=True))
 def test_safety_guard_precedes_secret_step(self):
  s=(ROOT/'.github/workflows/deploy-pages.yml').read_text()
  self.assertLess(s.index('check_odds_deploy_safety.py'),s.index('ODDS_API_KEY:'))
  self.assertIn('group: pages',s);self.assertIn('cancel-in-progress: false',s)

 def test_complete_history_required(self):
  pages={1:{'total_count':2,'workflow_runs':[{'id':1}]},2:{'total_count':2,'workflow_runs':[{'id':2}]}}
  self.assertEqual(len(all_runs(lambda page:pages[page])),2)
  with self.assertRaises(ValueError):all_runs(lambda page:pages[1] if page==1 else {'total_count':2,'workflow_runs':[]})
  with self.assertRaises(ValueError):all_runs(lambda page:pages[1])

 def test_reverse_completion_order_and_ambiguous_timestamps(self):
  current={'id':102,'workflow_id':99,'path':'.github/workflows/deploy-pages.yml','head_branch':'main','run_attempt':1,'run_number':102}
  success={'id':101,'workflow_id':99,'head_branch':'main','run_number':101,'status':'completed','conclusion':'success','run_started_at':'2026-10-19T01:00:00Z','updated_at':'2026-10-19T01:02:00Z'}
  failure={**success,'id':100,'run_number':100,'run_started_at':'2026-10-19T00:59:00Z','updated_at':'2026-10-19T01:03:00Z','conclusion':'failure'}
  self.assertFalse(permitted(current,[success,failure]))
  self.assertFalse(permitted(current,[success,{**failure,'updated_at':success['updated_at']}]))
  self.assertFalse(permitted(current,[{**success,'updated_at':'2999-01-01T00:00:00Z'}]))
  self.assertFalse(permitted(current,[{**success,'updated_at':'bad'}]))

from check_odds_deploy_safety import stable_runs,precollection_failure,proved_precollection_failures,HistoryChanged
class DeployHistoryRecoveryTests(unittest.TestCase):
 def fixture(self):
  current={'id':12,'workflow_id':99,'path':'.github/workflows/deploy-pages.yml','head_branch':'main','run_attempt':1,'run_number':12}
  success={**current,'id':9,'status':'completed','conclusion':'success','updated_at':'2026-10-19T03:00:00Z'}
  failed={**success,'id':10,'conclusion':'failure','updated_at':'2026-10-19T04:00:00Z'}
  names=['Set up job','Checkout latest main','Run actions/setup-python@v5','Verify previous deployment before any provider collection','Stage public site and recover last event snapshot','Refresh zero-quota event observations only','Run actions/configure-pages@v5','Run actions/upload-pages-artifact@v3','Run actions/deploy-pages@v4','Post Run actions/setup-python@v5','Post Checkout latest main','Complete job']
  steps=[{'number':([1,2,3,4,5,6,7,8,9,17,18,19][i]),'name':name,'status':'completed','conclusion':'success' if i<3 or i>9 else 'failure' if i==3 else 'skipped'} for i,name in enumerate(names)]
  return current,success,failed,{'total_count':1,'jobs':[{'run_id':10,'run_attempt':1,'head_branch':'main','name':'deploy','status':'completed','conclusion':'failure','steps':steps}]}
 def test_history_restart_is_complete_and_bounded(self):
  calls=[];attempt=0
  def page(n):
   nonlocal attempt
   calls.append(n)
   if n==1:attempt+=1
   if attempt==1:return {'total_count':2 if n==1 else 3,'workflow_runs':[{'id':n}]}
   return {'total_count':3,'workflow_runs':[{'id':n}]}
  self.assertEqual([r['id'] for r in stable_runs(page)],[1,2,3]);self.assertEqual(calls,[1,2,1,2,3])
  count=0
  def unstable(n):
   nonlocal count
   count+=1
   return {'total_count':2 if n==1 else 3,'workflow_runs':[{'id':n}]}
  with self.assertRaises(HistoryChanged):stable_runs(unstable)
  self.assertEqual(count,6)
  with self.assertRaises(ValueError):stable_runs(lambda n:{'total_count':2,'workflow_runs':[{'id':1}]})
 def test_proved_failure_requires_successful_anchor_and_all_failures(self):
  current,success,failed,payload=self.fixture()
  second={**failed,'id':11,'updated_at':'2026-10-19T05:00:00Z'}
  def jobs(run_id):
   p=json.loads(json.dumps(payload));p['jobs'][0]['run_id']=run_id
   if run_id==9:
    p['jobs'][0]['conclusion']='success'
    for step in p['jobs'][0]['steps']:step['conclusion']='success'
   return p
  runs=[success,failed,second];proof=proved_precollection_failures(runs,jobs)
  self.assertEqual(proof,{10,11});self.assertTrue(permitted(current,runs,precollection_failures=proof))
  self.assertFalse(permitted(current,runs,precollection_failures={11}))
  self.assertFalse(permitted(current,[failed],precollection_failures={10}))
  self.assertFalse(permitted(current,[success,{**second,'status':'in_progress'}],precollection_failures={11}))
 def test_ambiguous_or_collector_stage_failures_never_recover(self):
  current,success,failed,payload=self.fixture()
  self.assertTrue(precollection_failure(failed,payload))
  for mutate in [lambda p:p.update(total_count=2),lambda p:p['jobs'][0].update(run_attempt=2),lambda p:p['jobs'][0]['steps'][0].update(number=2),lambda p:p['jobs'][0].update(run_id=999),lambda p:p['jobs'][0]['steps'].pop(),lambda p:p['jobs'][0]['steps'][5].update(conclusion='success'),lambda p:p['jobs'][0]['steps'][5].update(conclusion='failure'),lambda p:p['jobs'][0]['steps'][5].update(status='in_progress'),lambda p:p['jobs'][0]['steps'].insert(0,{'name':'Unknown task','status':'completed','conclusion':'success'}),lambda p:p['jobs'][0]['steps'][10].update(conclusion='failure')]:
   p=json.loads(json.dumps(payload));mutate(p);self.assertFalse(precollection_failure(failed,p))
  for fields in [{'run_attempt':2},{'conclusion':'cancelled'},{'conclusion':'timed_out'}]:self.assertFalse(precollection_failure({**failed,**fields},payload))
  self.assertFalse(precollection_failure(failed,{}))
 def test_anchor_must_really_publish_not_skip_or_rerun(self):
  current,success,failed,payload=self.fixture()
  def skipped_anchor(run_id):
   p=json.loads(json.dumps(payload));p['jobs'][0]['run_id']=run_id
   if run_id==9:
    p['jobs'][0]['conclusion']='success'
    for step in p['jobs'][0]['steps']:step['conclusion']='skipped'
   return p
  self.assertEqual(proved_precollection_failures([success,failed],skipped_anchor),set())
  self.assertEqual(proved_precollection_failures([{**success,'run_attempt':2},failed],skipped_anchor),set())
  self.assertEqual(proved_precollection_failures([{**success,'updated_at':'invalid'},failed],skipped_anchor),set())
