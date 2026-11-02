import copy, datetime as dt, json, unittest
from scripts.api_sports_nba_preflight import collect, inspect_payload, ENDPOINT, SOURCE_ID
NOW=dt.datetime(2026,11,2,3,tzinfo=dt.timezone.utc)
SOURCE={'id':SOURCE_ID,'source_type':'api-sports-nba-preflight','endpoint':ENDPOINT,'coverage_status':'pending-fixture-review'}
def payload():
 return {'get':'games/','parameters':{'league':'standard','season':'2026'},'errors':[],'results':1,'response':[{'id':12345,'league':'standard','season':2026,'stage':2,'date':{'start':'2026-11-03T00:30:00.000Z'},'status':{'short':1},'teams':{'visitors':{'id':2,'name':'Boston Celtics'},'home':{'id':4,'name':'Brooklyn Nets'}},'officials':['OMIT PERSONNEL'],'logo':'DO NOT FETCH'}]}
class Response:
 status_code=200
 headers={'x-ratelimit-requests-limit':'100','x-ratelimit-requests-remaining':'99'}
 def json(self):return payload()
class Preflight(unittest.TestCase):
 def check(self,response=None,previous=None,key='synthetic-private-key',source=None,now=NOW):
  calls=[]
  def get(*args,**kwargs):calls.append((args,kwargs));return response or Response()
  r=collect(source or SOURCE,previous or {},now,key,get)
  if key:self.assertNotIn(key,json.dumps(r))
  return r,calls
 def test_single_request_no_emission_no_unowned_fields(self):
  r,c=self.check();self.assertEqual(len(c),1);self.assertFalse(r['ok']);self.assertEqual(r['events'],0);self.assertTrue(r['review_required'])
  self.assertEqual(r['preflight_evidence']['catalog_identity_key'],'basketball-us-nba');self.assertNotIn('OMIT',json.dumps(r));self.assertNotIn('DO NOT',json.dumps(r))
  self.assertEqual(c[0][1]['params'],{'league':'standard','season':'2026'});self.assertFalse(c[0][1]['allow_redirects']);self.assertEqual(c[0][1]['timeout'],25)
 def test_missing_key_and_endpoint_never_request(self):
  for key in ('','bad\nkey',' padded '):self.assertEqual(self.check(key=key)[1],[])
  self.assertEqual(self.check(source={**SOURCE,'endpoint':'https://foreign.test'})[1],[])
 def test_rolling_receipt_and_clock_rollback(self):
  r,_=self.check()
  for now in (NOW,NOW+dt.timedelta(hours=23,minutes=59),NOW-dt.timedelta(hours=1)):
   result,c=self.check(previous=r,now=now);self.assertEqual(c,[]);self.assertEqual(result['api_attempted_at'],r['api_attempted_at']);self.assertEqual(result['checked_at'],r['checked_at'])
  self.assertEqual(len(self.check(previous=r,now=NOW+dt.timedelta(hours=24))[1]),1)
  self.assertEqual(self.check(previous={'api_attempted_at':'bad'})[1],[])
 def test_http_quota_and_exception_no_secret_leak(self):
  for status in (302,401,403,429,500):
   response=Response();response.status_code=status;r,c=self.check(response);self.assertNotIn('preflight_evidence',r);self.assertEqual(len(c),1);self.assertIn('api_attempted_at',r)
  for headers in ({},{'x-ratelimit-requests-limit':'7500','x-ratelimit-requests-remaining':'7499'},{'x-ratelimit-requests-limit':'100','x-ratelimit-requests-remaining':'100'}):
   response=Response();response.headers=headers;self.assertNotIn('preflight_evidence',self.check(response)[0])
  def fail(*a,**kw):raise RuntimeError('synthetic-private-key raw-body')
  r=collect(SOURCE,{},NOW,'synthetic-private-key',fail);self.assertNotIn('synthetic-private-key',json.dumps(r));self.assertNotIn('raw-body',json.dumps(r));self.assertEqual(r['requests_this_run'],1)
 def test_adverse_payload_rejects_entire_evidence(self):
  cases=[]
  for key,value in [('errors',{'plan':'secret reflected'}),('response',[]),('results',2),('parameters',{'league':'Africa','season':'2026'})]:
   x=payload();x[key]=value;cases.append(x)
  for key,value in [('season',2025),('league','vegas'),('stage',None),('id',True),('status',{'short':99}),('date',{'start':'2026-11-03T00:30:00'})]:
   x=payload();x['response'][0][key]=value;cases.append(x)
  x=payload();x['response']*=2;x['results']=2;cases.append(x)
  for side in ('home','visitors'):
   x=payload();x['response'][0]['teams'][side]['name']='Unknown Youth Team';cases.append(x)
  for x in cases:
   with self.subTest(x=x),self.assertRaises((ValueError,TypeError)):inspect_payload(x,2026,NOW)
 def test_past_only_naive_clock_and_nonmutation(self):
  x=payload();before=copy.deepcopy(x);inspect_payload(x,2026,NOW);self.assertEqual(x,before)
  with self.assertRaises(ValueError):inspect_payload(x,2026,NOW+dt.timedelta(days=9))
  with self.assertRaises(ValueError):self.check(now=NOW.replace(tzinfo=None))
 def test_config_does_not_claim_usable_route(self):
  from pathlib import Path
  d=json.loads((Path(__file__).resolve().parents[1]/'data/global-schedule-sources.json').read_text())
  s=next(x for x in d['sources'] if x['id']==SOURCE_ID);self.assertEqual(s['coverage_status'],'pending-fixture-review');self.assertNotIn('scope_source_ids',s);self.assertEqual(s['endpoint'],ENDPOINT)
class CollectorBranch(unittest.TestCase):
 def test_actual_driver_branch_records_only_diagnostics(self):
  import ast
  from pathlib import Path
  text=(Path(__file__).resolve().parents[1]/'scripts/refresh_global_schedule.py').read_text()
  tree=ast.parse(text)
  branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="source.get('source_type') == 'api-sports-nba-preflight'")
  module=ast.Module(body=branch.body[:-1],type_ignores=[])
  calls=[]
  class Requests:
   @staticmethod
   def get(*a,**kw):calls.append((a,kw));return Response()
  class Env:
   @staticmethod
   def get(k,default):return 'synthetic-private-key'
  class OS:environ=Env()
  env={'source':SOURCE,'previous_schedule':{'sources':[]},'source_status':[],'NOW_UTC':NOW,'os':OS(),'requests':Requests(),'collect_api_sports_nba_preflight':collect,'events':[]}
  exec(compile(module,'driver','exec'),env)
  self.assertEqual(len(calls),1);self.assertEqual(env['events'],[]);self.assertFalse(env['source_status'][0]['ok'])
  self.assertNotIn('synthetic-private-key',json.dumps(env['source_status']))

if __name__=='__main__':unittest.main()
