"""Exact reviewed Crown/CBI provenance update; no new observation or age evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest
from scripts import basketball_catalog_transition as transition
from scripts.snapshot_semantic_guards import validate_change
from tests import test_full_private_snapshot as full

FIXTURES=Path(__file__).parent/'fixtures/basketball-catalog-nov13'
NOW=datetime(2026,11,16,15,tzinfo=timezone.utc)

class November13TransitionTests(unittest.TestCase):
    def setUp(self):
        self.old,self.new,self.catalog=[json.loads((FIXTURES/name).read_text()) for name in ('before.json','after.json','catalog.json')]

    def test_exact_hashes_and_only_two_provenance_fields_change(self):
        self.assertEqual(tuple(map(transition.digest,(self.old,self.new,self.catalog))),transition.NOVEMBER_13_TRANSITION)
        restored=deepcopy(self.new)
        self.assertEqual([r['id'] for r in self.new['catalog_special_rules']],['cbc','cbi'])
        for old,new,copy in zip(self.old['catalog_special_rules'],self.new['catalog_special_rules'],restored['catalog_special_rules']):
            self.assertEqual(old['catalog_version'],'11.2.26')
            self.assertEqual(new['catalog_version'],'11.13.26')
            for field in transition.PROVENANCE:copy[field]=old[field]
        self.assertEqual(restored,self.old)
        self.assertEqual(self.new['generated_at'],'2026-10-24T04:44:31.416671+00:00')
        self.assertEqual(self.new['screening_date'],'2026-10-23')

    def fixture(self,old=None,new=None,catalog=None):
        f=full.FullSnapshotTests();f.setUp();self.addCleanup(f.temp.cleanup)
        old=self.old if old is None else old;new=self.new if new is None else new;catalog=self.catalog if catalog is None else catalog
        for path,before,after in [(transition.PATH,old,new),(transition.CATALOG,catalog,self.catalog)]:
            (f.previous/path).write_text(json.dumps(before))
            raw=json.dumps(after).encode();(f.bundle/path).write_bytes(raw)
            f.manifest['files'][path]=hashlib.sha256(raw).hexdigest()
        f.save_previous();f.save_manifest();return f

    def test_real_transition_passes_full_consumer_without_mutation(self):
        with self.assertRaisesRegex(ValueError,'held observation'):validate_change(self.old,self.new,now=NOW)
        f=self.fixture();before=full.snapshot(f.previous);candidate=full.snapshot(f.bundle)
        f.prepare(now=NOW)
        self.assertEqual(json.loads((f.preview/transition.PATH).read_text()),self.new)
        self.assertEqual(full.snapshot(f.previous),before);self.assertEqual(full.snapshot(f.bundle),candidate)

    def test_every_other_field_change_fails_even_with_rehashed_candidate(self):
        changes=[('generated_at','2026-11-16T12:00:00Z'),('screening_date','2026-11-16'),('collection_paused',False),('stale',False),('verified_u18',[]),('new_field','unapproved')]
        for key,value in changes:
            with self.subTest(key=key):
                bad=deepcopy(self.new);bad[key]=value
                self.assertIsNone(transition.proven_candidate(self.old,bad,self.catalog))
                f=self.fixture(new=bad)
                with self.assertRaises(ValueError):f.prepare(now=NOW)
                self.assertFalse(f.preview.exists())
        for key,value in [('restriction','ALLOW PROPS'),('catalog_line','Other event'),('catalog_version','11.14.26'),('catalog_source','Other source')]:
            bad=deepcopy(self.new);bad['catalog_special_rules'][0][key]=value
            self.assertIsNone(transition.proven_candidate(self.old,bad,self.catalog))
            f=self.fixture(new=bad)
            with self.assertRaises(ValueError):f.prepare(now=NOW)

    def test_only_trusted_exact_prior_and_catalog_can_authorize(self):
        bad_old=deepcopy(self.old);bad_old['screening_date']='2026-10-22'
        bad_catalog=deepcopy(self.catalog);bad_catalog['menu_version']='11.14.26'
        for old,catalog in [(bad_old,self.catalog),(self.old,bad_catalog)]:
            self.assertIsNone(transition.proven_candidate(old,self.new,catalog))
            f=self.fixture(old=old,catalog=catalog)
            with self.assertRaises(ValueError):f.prepare(now=NOW)
