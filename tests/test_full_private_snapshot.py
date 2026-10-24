"""Synthetic structural coverage for all writer outputs, never live collection."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.prepare_full_private_preview import _contract,read_full_snapshot,prepare_full_preview


def snapshot(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


class FullSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.site=self.root/'site';self.site.mkdir()
        (self.site/'index.html').write_text('<html>synthetic</html>')
        (self.site/'data').mkdir();(self.site/'data/unchanged.json').write_text('{"keep":true}')
        for name in ('known-u18.json','catalog-season-map.json'):
            (self.site/'data'/name).write_text('{"synthetic_app_owned":true}')
        self.before=snapshot(self.site)
        self.bundle=self.root/'bundle';self.bundle.mkdir();self.preview=self.root/'preview'
        self.spec=_contract();self.raw={}
        samples={'str':'synthetic','int':1,'bool':False,'dict':{},'list':[],'NoneType':None,'float':1.0}
        for name,rule in self.spec['outputs'].items():
            if rule['root_type']=='text':raw=b'synthetic non-public evidence'
            elif rule['root_type']=='pdf':raw=b'%PDF-1.7\nsynthetic structural fixture, not a parsed PDF'
            else:
                obj={k:copy.deepcopy(samples[t]) for k,t in rule['required_types'].items()}
                for k in obj:
                    if k.endswith('_at') or k.endswith('_seen') or k=='last_verified':obj[k]='2026-10-01T00:00:00Z'
                    if k in ('url','href','endpoint') or k.endswith('_url'):obj[k]='https://example.test/synthetic'
                if rule.get('schema_version') is not None:obj['schema_version']=rule['schema_version']
                raw=json.dumps(obj).encode()
            self.raw[name]=raw;path=self.bundle/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            if rule['public']:
                prior=self.site/name;prior.parent.mkdir(parents=True,exist_ok=True);prior.write_bytes(raw)
        self.before=snapshot(self.site)
        self.manifest={'schema_version':2,'contract':'complete-collector-snapshot/v1','app_commit':self.spec['app_commit'],
                       'files':{k:hashlib.sha256(v).hexdigest() for k,v in self.raw.items()},
                       'configuration':{'target_app_commit':self.spec['app_commit'],
                           'families':{k:{'applied_app_commit':None,'pending_configuration':True} for k in self.spec['family_outputs']}}}
        self.save_manifest()
        self.previous=self.root/'previous';self.previous.mkdir()
        for name,rule in self.spec['outputs'].items():
            if rule['public']:
                path=self.previous/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.raw[name])
        self.kw=dict(previous_publication=self.previous,trusted_publication_run_id=12345,expected_previous_snapshot_sha256='',expected_data_commit='d'*40,fetched_data_commit='d'*40,expected_app_commit='a'*40,staged_app_commit='a'*40)
        self.save_previous()

    def save_previous(self):
        manifest={'schema_version':1,'contract':'public-data-snapshot/v1','app_commit':'a'*40,'data_commit':'c'*40,
                  'data_contract_app_commit':self.spec['app_commit'],'configuration':self.manifest['configuration'],'publisher_run_id':12344,
                  'files':{name:hashlib.sha256((self.previous/name).read_bytes()).hexdigest() for name,rule in self.spec['outputs'].items() if rule['public']}}
        raw=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()+b'\n'
        (self.previous/'manifest.json').write_bytes(raw);self.kw['expected_previous_snapshot_sha256']=hashlib.sha256(raw).hexdigest()

    def save_manifest(self):(self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
    def prepare(self,**changes):return prepare_full_preview(self.site,self.bundle,self.preview,**dict(self.kw,**changes))
    def reject(self):
        with self.assertRaises((ValueError,OSError)):self.prepare()
        self.assertFalse(self.preview.exists());self.assertEqual(self.before,snapshot(self.site))
        self.assertFalse(list(self.root.glob('.full-private-preview-*')))

    def test_complete_snapshot_covers_all_writers_but_not_semantic_approval(self):
        self.assertEqual(len(self.spec['family_outputs']),17)
        self.assertEqual(set().union(*(set(v) for v in self.spec['family_outputs'].values())),set(self.spec['outputs']))
        self.assertEqual(len(self.spec['outputs']),32)
        receipt=self.prepare()
        self.assertFalse(receipt['production_enabled']);self.assertTrue(receipt['pending_configuration'])
        self.assertEqual(receipt['contract_app_commit'],self.spec['app_commit'])
        self.assertEqual(receipt['target_app_commit'],'a'*40)
        self.assertEqual(len(receipt['public_files']),31)
        self.assertEqual(receipt['semantic_review_required'],[])
        self.assertIn('protected prior-publication',receipt['validation_scope'])
        self.assertFalse((self.preview/'BASKETBALL_COVERAGE_STATUS.md').exists())
        self.assertFalse((self.preview/'manifest.json').exists())
        self.assertEqual(self.before,snapshot(self.site))
        for name in receipt['public_files']:self.assertEqual(self.raw[name],(self.preview/name).read_bytes())

    def test_pending_configuration_is_not_claimed_when_same_revision(self):
        receipt=self.prepare(expected_app_commit=self.spec['app_commit'],staged_app_commit=self.spec['app_commit'])
        self.assertFalse(receipt['contract_revision_pending'])
        self.assertTrue(receipt['pending_configuration'])
        self.assertFalse(receipt['applied_configuration_verified'])
        self.assertFalse(receipt['production_enabled'])

    def test_incomplete_or_extra_snapshot_and_wrong_identity_rejected(self):
        for changes in ({'app_commit':'e'*40},{'schema_version':True},{'contract':'unknown'}):
            old=copy.deepcopy(self.manifest);self.manifest.update(changes);self.save_manifest();self.reject();self.manifest=old
        self.save_manifest()
        key=next(iter(self.raw));path=self.bundle/key;raw=path.read_bytes();path.unlink();self.reject();path.write_bytes(raw)
        extra=self.bundle/'payload.py';extra.write_text('must never execute');self.reject();extra.unlink()
        self.manifest['files']['../escape.py']='0'*64;self.save_manifest();self.reject()

    def test_family_config_provenance_must_not_hide_pending_updates(self):
        family=next(iter(self.spec['family_outputs']))
        state=self.manifest['configuration']['families'][family]
        for change in ({'pending_configuration':False},{'pending_configuration':1},
                       {'applied_app_commit':'main'}):
            old=copy.deepcopy(state);state.update(change);self.save_manifest();self.reject();state.clear();state.update(old)
        del self.manifest['configuration']['families'][family];self.save_manifest();self.reject()

    def test_trusted_prior_holds_identity_evidence_and_url_boundary(self):
        cases=[('data/ncaa-basketball-age-cache.json',{'collection_paused':True,'stale':True},{}),
               ('data/tennis-u18-registry.json',{'records':[{'official_player_id':'itf:synthetic','age_evidence':{'review':{'id':'synthetic-reviewed'},'status':'verified_dob','dob':'2009-01-02'}}]},{}),
               ('data/global-schedule.json',{}, {'source_url':'javascript:alert(1)'}),
               ('data/global-schedule.json',{}, {'generated_at':'2999-01-01T00:00:00Z'})]
        for name,prior_changes,new_changes in cases:
            original=json.loads(self.raw[name]);prior=copy.deepcopy(original);prior.update(prior_changes)
            new=copy.deepcopy(original);new.update(new_changes)
            (self.previous/name).write_text(json.dumps(prior));self.save_previous();self.before=snapshot(self.site)
            raw=json.dumps(new).encode();(self.bundle/name).write_bytes(raw)
            self.manifest['files'][name]=hashlib.sha256(raw).hexdigest();self.save_manifest()
            self.reject()
            (self.previous/name).write_bytes(self.raw[name]);self.save_previous();self.before=snapshot(self.site)
            (self.bundle/name).write_bytes(self.raw[name]);self.manifest['files'][name]=hashlib.sha256(self.raw[name]).hexdigest();self.save_manifest()

    def test_tamper_and_unknown_shapes_rejected(self):
        key='data/status.json';path=self.bundle/key
        for raw in (self.raw[key]+b' ',b'{"generated_at":"x"}',b'{"generated_at":NaN}'):
            path.write_bytes(raw)
            if raw!=self.raw[key]+b' ':self.manifest['files'][key]=hashlib.sha256(raw).hexdigest();self.save_manifest()
            self.reject()

    def test_bool_not_integer_and_pdf_signature_required(self):
        key='data/status.json';obj=json.loads(self.raw[key]);obj['source_count']=True
        raw=json.dumps(obj).encode();(self.bundle/key).write_bytes(raw)
        self.manifest['files'][key]=hashlib.sha256(raw).hexdigest();self.save_manifest();self.reject()
        (self.bundle/key).write_bytes(self.raw[key]);self.manifest['files'][key]=hashlib.sha256(self.raw[key]).hexdigest()
        key='data/catalog-current.pdf';raw=b'not a PDF';(self.bundle/key).write_bytes(raw)
        self.manifest['files'][key]=hashlib.sha256(raw).hexdigest();self.save_manifest();self.reject()

    def test_symlinks_and_directory_alias_rejected(self):
        key='data/status.json';path=self.bundle/key;path.unlink();path.symlink_to(self.site/'data/unchanged.json');self.reject()
        path.unlink();path.write_bytes(self.raw[key]);other=self.root/'other';other.mkdir()
        for base in (self.site,self.bundle):
            with self.assertRaises(ValueError):prepare_full_preview(self.site,self.bundle,other/'..'/base.name/'nested',**self.kw)
            self.assertFalse((base/'nested').exists())

    def test_existing_last_good_and_copy_failure_preserved(self):
        with patch('scripts.prepare_full_private_preview.shutil.copytree',side_effect=OSError('synthetic failure')):self.reject()
        self.prepare();before=snapshot(self.preview)
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(before,snapshot(self.preview));self.assertEqual(self.before,snapshot(self.site))

    def test_snapshot_contract_not_from_data_and_source_identity_bound(self):
        (self.bundle/'contract.json').write_text(json.dumps(self.spec));self.reject()
        (self.bundle/'contract.json').unlink()
        for changes in ({'fetched_data_commit':'e'*40},{'expected_data_commit':'main'},{'staged_app_commit':'b'*40}):
            with self.assertRaises(ValueError):self.prepare(**changes)
            self.assertFalse(self.preview.exists())


    def test_preview_cannot_mutate_previous_publication(self):
        before=snapshot(self.previous)
        for destination in (self.previous/'new',self.root/'site'/'..'/'previous'/'new'):
            with self.subTest(destination=str(destination)):
                self.preview=destination
                with self.assertRaises(ValueError):self.prepare()
                self.assertEqual(before,snapshot(self.previous))
                self.assertEqual(self.before,snapshot(self.site))

if __name__=='__main__':unittest.main()
