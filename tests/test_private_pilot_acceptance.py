"""Synthetic only: protected app pilot boundary, not a production cutover test."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.prepare_private_pilot_preview import prepare_preview

NOW=datetime(2026,10,24,2,0,tzinfo=timezone.utc)
OLD='2026-10-24T01:00:00+00:00'
NEW='2026-10-24T01:59:00+00:00'


def bundle(root,status,review):
    (root/'data').mkdir(parents=True,exist_ok=True)
    hashes={}
    for name,obj in [('data/status.json',status),('data/review-data.json',review)]:
        raw=json.dumps(obj).encode();(root/name).write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    (root/'manifest.json').write_text(json.dumps({'schema_version':1,'files':hashes}))


def snapshot(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


class PilotAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.site=self.root/'site';self.candidate=self.root/'candidate';self.out=self.root/'preview'
        self.status={'generated_at':OLD,'source_count':2,'healthy_count':1,'sources':[
            {'id':'public','name':'Public synthetic','priority':'HIGH','url':'https://example.test/','ok':True,'checked_at':OLD,'http_status':200},
            {'id':'itf','name':'Held synthetic','priority':'HIGH','url':'https://www.itftennis.com/','ok':False,'checked_at':None,'http_status':None,
             'access_status':'permission_required','collection_paused':True,'stale':True}]}
        self.review={'schema_version':1,'generated_at':'2026-10-20T00:00:00+00:00','background_checked_at':OLD,
            'events':[{'id':'synthetic-event','count':1}],'u18_matches':[],'restriction_triggers':[],'coverage_alerts':[]}
        bundle(self.site,self.status,self.review)
        (self.site/'manifest.json').unlink()
        (self.site/'index.html').write_text('<html>synthetic site</html>')
        self.before=snapshot(self.site)
        self.status['generated_at']=NEW;self.status['sources'][0]['checked_at']=NEW
        self.review['background_checked_at']=NEW;self.save()
        self.kw=dict(now=NOW,max_age_seconds=21600,expected_data_commit='d'*40,
            fetched_data_commit='d'*40,expected_app_commit='a'*40,staged_app_commit='a'*40)

    def save(self):bundle(self.candidate,self.status,self.review)
    def run_preview(self,**changes):return prepare_preview(self.site,self.candidate,self.out,**dict(self.kw,**changes))
    def reject(self,**changes):
        with self.assertRaises((ValueError,OSError)):self.run_preview(**changes)
        self.assertFalse(self.out.exists());self.assertEqual(snapshot(self.site),self.before)
        self.assertFalse(list(self.root.glob('.private-preview-*')))

    def test_valid_candidate_retains_event_time_and_binds_revision_receipt(self):
        receipt=self.run_preview()
        self.assertEqual(receipt['contract'],'public-source-status/v1')
        self.assertFalse(receipt['production_enabled'])
        self.assertEqual(receipt['data_commit'],'d'*40)
        self.assertEqual(snapshot(self.site),self.before)
        new=json.loads((self.out/'data/review-data.json').read_text())
        self.assertEqual(new['generated_at'],'2026-10-20T00:00:00+00:00')
        self.assertEqual(new['events'],self.review['events'])
        self.assertEqual((self.out/'index.html').read_bytes(),self.before['index.html'])
        self.assertFalse((self.out/'manifest.json').exists())
        self.assertFalse((self.out/'receipt.json').exists())

    def test_last_good_existing_preview_never_replaced(self):
        self.run_preview();before=snapshot(self.out)
        self.status['healthy_count']=0;self.save()
        with self.assertRaises(ValueError):self.run_preview()
        self.assertEqual(before,snapshot(self.out));self.assertEqual(self.before,snapshot(self.site))

    def test_revision_identity_and_explicit_policy(self):
        for changes in ({'expected_data_commit':'main'},{'fetched_data_commit':'e'*40},
            {'staged_app_commit':'b'*40},{'expected_app_commit':None},
            {'max_age_seconds':True},{'max_age_seconds':0},{'max_age_seconds':86401},
            {'now':NOW.replace(tzinfo=None)}):
            with self.subTest(changes=changes):self.reject(**changes)

    def test_future_stale_naive_regressed_or_mismatched_time(self):
        for stamp in ('2026-10-23T01:00:00Z','2026-10-24T03:00:00Z',
            '2026-10-24T01:59:00','bad',None,'2026-10-24T00:59:00Z'):
            self.status['generated_at']=stamp;self.review['background_checked_at']=stamp;self.save()
            with self.subTest(stamp=stamp):self.reject()
        self.status['generated_at']=NEW;self.review['background_checked_at']=OLD;self.save();self.reject()

    def test_source_check_age_is_absolute_not_two_accumulated_windows(self):
        self.status["generated_at"]="2026-10-24T01:00:00Z"
        self.review["background_checked_at"]="2026-10-24T01:00:00Z"
        self.status["sources"][0]["checked_at"]="2026-10-23T19:01:00Z"
        self.save();self.reject()

    def test_exact_freshness_boundary(self):
        # At one minute old, inclusive60s accepted;59s rejects, no current time globals.
        self.reject(max_age_seconds=59)
        self.run_preview(max_age_seconds=60)

    def test_event_owned_fields_and_nested_types_preserved(self):
        for field,value in [('events',[]),('generated_at',NEW),('schema_version',True),('coverage_alerts',{})]:
            prior=copy.deepcopy(self.review);self.review[field]=value;self.save();self.reject();self.review=prior
        self.review['events'][0]['count']=True;self.save();self.reject()

    def test_sources_counts_types_urls_and_publisher_hold(self):
        mutations=[lambda s:s.update(source_count=True),lambda s:s.update(internal_secret='unexpected'),
            lambda s:s['sources'][0].update(unreviewed='unexpected'),lambda s:s['sources'][0].update(name='Changed'),lambda s:s.update(healthy_count=2),
            lambda s:s['sources'].pop(),lambda s:s['sources'].append(copy.deepcopy(s['sources'][0])),
            lambda s:s['sources'][0].update(id='other'),lambda s:s['sources'][0].update(access_status='allowed'),lambda s:s['sources'][0].update(ok='true'),
            lambda s:s['sources'][0].update(http_status=500),lambda s:s['sources'][0].update(url='https://other.test'),
            lambda s:s['sources'][1].update(access_status='allowed'),lambda s:s['sources'][1].update(ok=True),
            lambda s:s['sources'][1].update(collection_paused=False),lambda s:s['sources'][1].update(checked_at=NEW)]
        for mutation in mutations:
            prior=copy.deepcopy(self.status);mutation(self.status);self.save();self.reject();self.status=prior

    def test_tampering_missing_extra_and_linked_inputs(self):
        p=self.candidate/'data/status.json';raw=p.read_bytes();p.write_bytes(raw+b' ');self.reject();p.write_bytes(raw)
        p.unlink();self.reject();p.write_bytes(raw)
        extra=self.candidate/'execute.py';extra.write_text('raise AssertionError("must not execute")');self.reject();extra.unlink()
        p.unlink();p.symlink_to(self.site/'data/status.json');self.reject();p.unlink();p.write_bytes(raw)
        linked=self.site/'external';linked.symlink_to(self.candidate,target_is_directory=True)
        with self.assertRaises(ValueError):self.run_preview()
        linked.unlink()
        self.out.symlink_to(self.site,target_is_directory=True)
        with self.assertRaises(ValueError):self.run_preview()
        self.assertEqual(snapshot(self.site),self.before)

    def test_duplicate_and_nonfinite_json_rejected_even_matching_digest(self):
        p=self.candidate/'data/status.json'
        for raw in (b'{"sources":[],"sources":[]}',b'{"sources":NaN}'):
            p.write_bytes(raw);manifest=json.loads((self.candidate/'manifest.json').read_text())
            manifest['files']['data/status.json']=hashlib.sha256(raw).hexdigest()
            (self.candidate/'manifest.json').write_text(json.dumps(manifest));self.reject()

    def test_copy_failure_cleans_partial_preview_and_preserves_last_good(self):
        with patch('scripts.prepare_private_pilot_preview.shutil.copytree',side_effect=OSError('synthetic disk failure')):
            self.reject()

    def test_validated_bytes_are_not_reread_after_staging(self):
        import shutil
        original=shutil.copytree
        candidate_bytes=(self.candidate/'data/status.json').read_bytes()
        def mutate_then_copy(*args,**kwargs):
            (self.candidate/'data/status.json').write_text('{"untrusted":"changed after verification"}')
            return original(*args,**kwargs)
        with patch('scripts.prepare_private_pilot_preview.shutil.copytree',side_effect=mutate_then_copy):self.run_preview()
        self.assertEqual(candidate_bytes,(self.out/'data/status.json').read_bytes())

    def test_dotdot_alias_cannot_stage_inside_trusted_site(self):
        other=self.root/"other";other.mkdir()
        for root in (self.site,self.candidate):
            alias=other/".."/root.name/"nested"
            with self.assertRaises(ValueError):prepare_preview(self.site,self.candidate,alias,**self.kw)
            self.assertFalse((root/"nested").exists())
        self.assertEqual(self.before,snapshot(self.site))

    def test_preview_nested_in_inputs_rejected(self):
        for root in (self.site,self.candidate):
            with self.assertRaises(ValueError):prepare_preview(self.site,self.candidate,root/'nested',**self.kw)
            self.assertFalse((root/'nested').exists())

if __name__=='__main__':unittest.main()
