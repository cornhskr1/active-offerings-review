"""Offline transport/publication integration; all GitHub/provider calls synthetic."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import unittest
import zipfile
from tests import test_full_private_snapshot as full_fixture
from scripts.fetch_full_private_candidate import fetch_candidate
from scripts.restore_public_snapshot import restore_snapshot,_archive_files,require_activation
from scripts.public_data_snapshot import build_public_snapshot,POINTER,SNAPSHOT_ROOT
from scripts.prepare_full_private_preview import prepare_full_preview
from scripts.check_odds_deploy_safety import PINNED_RECOVERY_STEPS


def gitblob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.f=full_fixture.FullSnapshotTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.responses={};self.calls=[];self.private_commit='d'*40
        self.rebuild_private()
        self.public=build_public_snapshot(self.f.site,app_commit='a'*40,data_commit='b'*40,
            data_contract_app_commit=self.f.spec['app_commit'],configuration_state=self.f.manifest['configuration'],publisher_run_id=12344)
        self.odds=json.dumps({'schema_version':1,'provider':'The Odds API','events':[],
            'observed_at':'2026-10-01T00:00:00Z','collector_state':{'schema_version':1,'sources':{},'directory':{},'halted':True}}).encode()
        (self.f.site/'data/odds-api-events.json').write_bytes(self.odds)
        self.run={'id':12344,'path':'.github/workflows/deploy-pages.yml','head_sha':'a'*40,
            'head_branch':'main','repository':{'full_name':'cornhskr1/active-offerings-review'},
            'run_attempt':1,'status':'completed','conclusion':'success'}
        self.jobs={'total_count':1,'jobs':[{'run_id':12344,'run_attempt':1,'head_branch':'main',
            'name':'deploy','status':'completed','conclusion':'success',
            'steps':[{'number':number,'name':name,'status':'completed','conclusion':'success'}
                     for number,name in zip([1,2,3,4,5,6,7,8,9,17,18,19],PINNED_RECOVERY_STEPS)]}]}
        self.proof={'repository':'cornhskr1/active-offerings-review','current_run_id':12345,'anchor_run_id':12344}
        self.archive=self.make_archive();self.reset_metadata()

    def rebuild_private(self):
        tree=[]
        for path in self.f.bundle.rglob('*'):
            if not path.is_file():continue
            raw=path.read_bytes();sha=gitblob(raw);name=path.relative_to(self.f.bundle).as_posix()
            tree.append({'path':'published/current/'+name,'type':'blob','mode':'100644','size':len(raw),'sha':sha})
            self.responses['/git/blobs/'+sha]={'sha':sha,'encoding':'base64','size':len(raw),'content':base64.b64encode(raw).decode()}
        self.responses['/commits/main']={'sha':self.private_commit}
        self.responses['/git/trees/'+self.private_commit+'?recursive=1']={'truncated':False,'tree':tree}

    def get_private(self,path):self.calls.append(path);return copy.deepcopy(self.responses[path])
    def make_archive(self,legacy=False,extra=None):
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w') as tar:
            for path in self.f.site.rglob('*'):
                if not path.is_file():continue
                name=path.relative_to(self.f.site).as_posix()
                if legacy and (name==POINTER or name.startswith(SNAPSHOT_ROOT+'/')):continue
                raw=path.read_bytes();entry=tarfile.TarInfo('./'+name);entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
            if extra is not None:tar.addfile(extra,io.BytesIO(b'x'*extra.size))
        result=io.BytesIO()
        with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('artifact.tar',buffer.getvalue())
        return result.getvalue()
    def reset_metadata(self):
        self.metadata={'id':77,'name':'github-pages','expired':False,'digest':'sha256:'+hashlib.sha256(self.archive).hexdigest(),
            'workflow_run':{'id':12344,'head_branch':'main','head_sha':'a'*40}}
    def get_public(self,path):
        if path=='/actions/runs/12344':return copy.deepcopy(self.run)
        if path=='/actions/runs/12344/attempts/1/jobs?per_page=100':return copy.deepcopy(self.jobs)
        if path=='/actions/runs/12344/artifacts?per_page=100':return {'total_count':1,'artifacts':[copy.deepcopy(self.metadata)]}
        raise AssertionError('Unexpected evidence endpoint '+path)
    def restore(self,**kw):
        return restore_snapshot(self.proof,12345,self.f.root/'restored',get=self.get_public,
            get_archive=lambda identity:self.archive,**kw)
    def checkpoint(self):
        raw=(self.f.site/SNAPSHOT_ROOT/self.public['snapshot_sha256']/'manifest.json').read_bytes()
        return {'repository':self.proof['repository'],'anchor_run_id':12344,'artifact_id':77,
            'artifact_sha256':self.metadata['digest'][7:],'public_manifest':json.loads(raw),
            'public_snapshot_sha256':hashlib.sha256(raw).hexdigest()}

    def test_complete_fetch_to_proven_publication_to_preview(self):
        candidate=self.f.root/'fetched'
        private=fetch_candidate(candidate,get=self.get_private)
        previous,odds=self.restore()
        receipt=prepare_full_preview(self.f.site,candidate,self.f.preview,
            expected_data_commit=private['data_commit'],fetched_data_commit=private['data_commit'],
            expected_app_commit='a'*40,staged_app_commit='a'*40,
            previous_publication=self.f.root/'restored',expected_previous_snapshot_sha256=previous['snapshot_sha256'],
            trusted_publication_run_id=12345)
        self.assertEqual(len(receipt['public_files']),31);self.assertEqual(odds,self.odds)
        self.assertIs(json.loads(odds)['collector_state']['halted'],True)
        self.assertNotIn('BASKETBALL_COVERAGE_STATUS.md',receipt['public_files'])
        self.assertEqual(self.calls.count('/commits/main'),1)
        self.assertTrue(all('/contents/' not in path for path in self.calls))

    def test_binary_pdf_over_one_megabyte_uses_verified_git_blob(self):
        name='data/catalog-current.pdf';raw=b'%PDF-1.7\n'+b'x'*1_100_000
        (self.f.bundle/name).write_bytes(raw);self.f.manifest['files'][name]=hashlib.sha256(raw).hexdigest();self.f.save_manifest();self.rebuild_private()
        fetch_candidate(self.f.root/'large',get=self.get_private)
        self.assertEqual((self.f.root/'large'/name).read_bytes(),raw)

    def test_private_missing_extra_symlink_truncated_hash_and_size_fail_closed(self):
        key='/git/trees/'+self.private_commit+'?recursive=1'
        for mutate in (lambda t:t.update(truncated=True),lambda t:t['tree'].pop(),
                       lambda t:t['tree'].append(dict(t['tree'][0],path='published/current/evil.py')),
                       lambda t:t['tree'][0].update(mode='120000'),lambda t:t['tree'][0].update(size=0)):
            original=copy.deepcopy(self.responses[key]);mutate(self.responses[key])
            with self.assertRaises(ValueError):fetch_candidate(self.f.root/'rejected',get=self.get_private)
            self.assertFalse((self.f.root/'rejected').exists());self.responses[key]=original
        entry=self.responses[key]['tree'][0];self.responses['/git/blobs/'+entry['sha']]['content']=base64.b64encode(b'tampered').decode()
        with self.assertRaises(ValueError):fetch_candidate(self.f.root/'rejected',get=self.get_private)
        self.assertFalse((self.f.root/'rejected').exists())

    def test_anchor_failure_rerun_wrong_artifact_or_private_fallback_rejected(self):
        for fields in ({'conclusion':'failure'},{'run_attempt':2},{'head_branch':'other'}):
            original=copy.deepcopy(self.run);self.run.update(fields)
            with self.assertRaises(ValueError):self.restore()
            self.run=original
        self.metadata['workflow_run']['id']=999
        with self.assertRaises(ValueError):self.restore()
        self.assertFalse((self.f.root/'restored').exists())

    def test_initial_bootstrap_requires_exact_checkpoint_never_auto_fallback(self):
        self.archive=self.make_archive(legacy=True);self.reset_metadata()
        with self.assertRaises(ValueError):self.restore()
        checkpoint=self.checkpoint();receipt,odds=self.restore(checkpoint=checkpoint)
        self.assertEqual(receipt['snapshot_sha256'],self.public['snapshot_sha256']);self.assertEqual(odds,self.odds)

    def test_expired_artifact_requires_exact_retained_bytes_and_checkpoint(self):
        self.metadata['expired']=True
        with self.assertRaises(ValueError):self.restore()
        with self.assertRaises(ValueError):self.restore(retained_archive=self.archive)
        checkpoint=self.checkpoint();checkpoint['anchor_run_id']=999
        with self.assertRaises(ValueError):self.restore(checkpoint=checkpoint,retained_archive=self.archive)
        receipt,_=self.restore(checkpoint=self.checkpoint(),retained_archive=self.archive)
        self.assertEqual(receipt['anchor_run_id'],12344)

    def test_archive_traversal_links_and_corruption_rejected(self):
        for name,kind in (('../escape',tarfile.REGTYPE),('linked',tarfile.SYMTYPE)):
            extra=tarfile.TarInfo(name);extra.type=kind;extra.size=0;raw=self.make_archive(extra=extra)
            with self.assertRaises(ValueError):_archive_files(raw,hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):_archive_files(self.archive,'0'*64)

    def test_no_activation_checkpoint_is_shipped_or_inferred(self):
        with self.assertRaises((ValueError,OSError)):require_activation(self.f.site)
        root=Path(__file__).resolve().parents[1]
        self.assertFalse((root/'migration/activation/pages.json').exists())
        self.assertFalse((root/'migration/activation/pages-bootstrap.json').exists())
        plan=json.loads((root/'migration/pages-activation-plan.json').read_text())
        raw=(root/plan['template']).read_bytes()
        self.assertEqual(gitblob(raw),plan['required_guard_workflow_blob'])
        live=(root/'.github/workflows/deploy-pages.yml').read_bytes()
        self.assertNotEqual(gitblob(live),plan['required_guard_workflow_blob'])
        self.assertIn(b'refresh_odds_api_events.py --config data/odds-api-catalog-mappings.json',raw)
        self.assertIn(b'group: pages\n  cancel-in-progress: false',raw)

if __name__=='__main__':unittest.main()

class TransportTests(unittest.TestCase):
    def test_private_read_token_not_redirected_and_path_fixed(self):
        from unittest.mock import patch
        from scripts.fetch_full_private_candidate import github_getter,NoRedirect
        calls=[]
        class Opener:
            def open(self,request,timeout):
                calls.append(request);return io.BytesIO(b'{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}')
        with patch('scripts.fetch_full_private_candidate.urllib.request.build_opener',return_value=Opener()):
            get=github_getter('synthetic-private-token');get('/commits/main')
            with self.assertRaises(ValueError):get('https://evil.test/credentials')
        self.assertEqual(len(calls),1)
        self.assertTrue(calls[0].full_url.startswith('https://api.github.com/repos/cornhskr1/active-offerings-data/'))
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_pages_archive_signed_download_never_forwards_token(self):
        import urllib.error
        from unittest.mock import patch
        from scripts.restore_public_snapshot import transports
        calls=[]
        class Opener:
            def open(self,request,timeout):
                calls.append(request)
                if len(calls)==1:raise urllib.error.HTTPError(request.full_url,302,'redirect',
                    {'Location':'https://results.blob.core.windows.net/artifact?signature=synthetic'},None)
                return io.BytesIO(b'archive')
        with patch('scripts.restore_public_snapshot.urllib.request.build_opener',return_value=Opener()):
            _,archive=transports('synthetic-github-token');self.assertEqual(archive(77),b'archive')
        self.assertEqual(calls[0].get_header('Authorization'),'Bearer synthetic-github-token')
        self.assertIsNone(calls[1].get_header('Authorization'))
