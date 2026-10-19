import hashlib,io,json,sys,tarfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import recover_verified_pages_cache as r
class RecoveryTests(unittest.TestCase):
 def archive(self,members):
  tar=io.BytesIO()
  with tarfile.open(fileobj=tar,mode='w') as t:
   for name,body,kind in members:
    item=tarfile.TarInfo(name);item.size=len(body);item.type=kind;t.addfile(item,io.BytesIO(body) if kind==tarfile.REGTYPE else None)
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('artifact.tar',tar.getvalue())
  return out.getvalue()
 def body(self):
  return json.dumps({'provider':'The Odds API','schema_version':1,'observed_at':'2026-10-19T03:20:40Z','events':[],'collector_state':{'schema_version':1,'sources':{},'directory':{},'halted':True,'stopped_at':'2026-10-19T03:00:00Z'}}).encode()
 def test_exact_bytes_preserve_halt_and_dates(self):
  body=self.body();raw=self.archive([('./data/odds-api-events.json',body,tarfile.REGTYPE)])
  self.assertEqual(r.read_cache_archive(raw,hashlib.sha256(raw).hexdigest()),body)
  with self.assertRaises(ValueError):r.read_cache_archive(raw,'bad')
 def test_missing_duplicate_link_and_malformed_rejected(self):
  good=('data/odds-api-events.json',self.body(),tarfile.REGTYPE)
  for members in [[],[good,good],[('data/odds-api-events.json',b'',tarfile.SYMTYPE)],[('data/odds-api-events.json',b'{}',tarfile.REGTYPE)]]:
   raw=self.archive(members)
   with self.assertRaises(ValueError):r.read_cache_archive(raw,hashlib.sha256(raw).hexdigest())
 def test_provenance_and_anchor_fail_before_download(self):
  calls=[]
  with self.assertRaises(ValueError):r.recover({},123,lambda url:calls.append(url))
  self.assertEqual(calls,[])
  good={'id':r.ARTIFACT,'name':'github-pages','expired':False,'digest':'sha256:'+r.DIGEST,'workflow_run':{'id':r.RUN,'repository_id':1349023164,'head_branch':'main','head_sha':'d9008dba9613ad931349a78dc1e436a145303214'}}
  self.assertTrue(r.validate_metadata(good))
  for key,value in [('expired',True),('id',1),('digest','wrong')]:self.assertFalse(r.validate_metadata({**good,key:value}))
 def test_staging_restores_exact_bytes_and_signals_no_collection(self):
  import tempfile,subprocess,runpy,urllib.error,os
  from unittest.mock import patch
  import stage_odds_pages as stage_module
  class Missing:
   def open(self,url,timeout):
    if url.endswith('.json'):raise urllib.error.HTTPError(url,404,'missing',{},None)
    return io.BytesIO(b'Upcoming Event Review data/odds-api-events.json')
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'repo';root.mkdir();subprocess.run(['git','init','-q',str(root)],check=True)
   (root/'index.html').write_text('site');subprocess.run(['git','add','index.html'],cwd=root,check=True)
   proof={'repository':r.REPO,'current_run_id':123,'anchor_run_id':r.RUN}
   (Path(temp)/'odds-recovery-proof.json').write_text(json.dumps(proof));output=Path(temp)/'outputs'
   with patch.dict(os.environ,{'RUNNER_TEMP':temp,'GITHUB_RUN_ID':'123','GITHUB_OUTPUT':str(output)}),patch.object(sys,'argv',['stage','--root',str(root),'--stage',temp+'/site','--previous',temp+'/previous.json']),patch('urllib.request.build_opener',return_value=Missing()),patch.object(r,'recover',return_value=self.body()) as recover:
    runpy.run_path(str(ROOT/'scripts/stage_odds_pages.py'),run_name='__main__')
   recover.assert_called_once_with(proof,123)
   self.assertEqual((Path(temp)/'site/data/odds-api-events.json').read_bytes(),self.body())
   self.assertEqual(output.read_text(),'recovered=true\n')
   self.assertTrue(json.loads((Path(temp)/'previous.json').read_text())['collector_state']['halted'])
 def test_only_one_pages_publisher_and_recovery_skips_collection(self):
  files=list((ROOT/'.github/workflows').glob('*.yml'))
  writers=[p.name for p in files if 'actions/deploy-pages@' in p.read_text()]
  self.assertEqual(writers,['deploy-pages.yml'])
  workflow=(ROOT/'.github/workflows/deploy-pages.yml').read_text()
  self.assertIn("if: steps.stage.outputs.recovered != 'true'",workflow)
  self.assertIn('Update NRGC Catalog',workflow)
  self.assertNotIn('pages: write',(ROOT/'.github/workflows/update-catalog.yml').read_text())
