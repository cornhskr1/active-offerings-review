"""App-owned proof at the actual full-snapshot consumer boundary."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch
from scripts import basketball_catalog_transition as transition
from scripts.snapshot_semantic_guards import validate_change
from tests import test_full_private_snapshot as full
from tests.test_full_private_snapshot import snapshot


class BasketballConsumerTransitionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=full.FullSnapshotTests();self.fixture.setUp();self.addCleanup(self.fixture.temp.cleanup)
        self.old=json.loads(self.fixture.raw[transition.PATH])
        self.old.update(collection_paused=True,stale=True,generated_at='2026-10-24T04:44:31+00:00',
            screening_date='2026-10-23',source_observation_times={'schedule':'2026-10-18T00:00:00Z'},
            verified_u18=[{'name':'Synthetic Athlete'}],catalog_special_rules=[{
                'id':'cbc','catalog_line':'CBC | Men | NO PLAYER PROPOSITION WAGERS',
                'restriction':'NO PLAYER PROPOSITION WAGERS','catalog_source':'Menu 10','catalog_version':'10'}])
        self.catalog=json.loads(self.fixture.raw[transition.CATALOG])
        self.catalog.update(source_label='Menu 11',menu_version='11',sections=[{
            'sport':'NCAA Basketball','lines':['CBC | Men | NO PLAYER PROPOSITION WAGERS']}])
        self.new=deepcopy(self.old)
        self.new['catalog_special_rules'][0].update(catalog_source='Menu 11',catalog_version='11')
        for name,value in [('BEFORE',self.old),('AFTER',self.new),('CATALOG_HASH',self.catalog)]:
            p=patch.object(transition,name,transition.digest(value));p.start();self.addCleanup(p.stop)
        self.prior(transition.PATH,self.old);self.prior(transition.CATALOG,self.catalog)
        self.candidate(transition.PATH,self.new);self.candidate(transition.CATALOG,self.catalog)

    def prior(self,name,value):
        (self.fixture.previous/name).write_text(json.dumps(value));self.fixture.save_previous()

    def candidate(self,name,value):
        raw=json.dumps(value).encode();(self.fixture.bundle/name).write_bytes(raw)
        self.fixture.manifest['files'][name]=hashlib.sha256(raw).hexdigest();self.fixture.save_manifest()

    def test_reviewed_transition_passes_full_consumer_without_mutating_inputs(self):
        old=snapshot(self.fixture.previous);candidate=snapshot(self.fixture.bundle)
        with self.assertRaisesRegex(ValueError,'held observation'):validate_change(self.old,self.new)
        self.fixture.prepare()
        self.assertEqual(self.new,json.loads((self.fixture.preview/transition.PATH).read_text()))
        self.assertEqual(old,snapshot(self.fixture.previous));self.assertEqual(candidate,snapshot(self.fixture.bundle))

    def test_freshened_clocks_rejected_even_with_rehashed_manifest(self):
        for field,value in [('generated_at','2026-11-04T09:00:00Z'),('screening_date','2026-11-04')]:
            with self.subTest(field=field):
                bad=deepcopy(self.new);bad[field]=value;self.candidate(transition.PATH,bad);self.fixture.reject()

    def test_hold_source_age_and_rule_changes_rejected(self):
        for key,value in [('collection_paused',False),('stale',False),('verified_u18',[]),
                          ('source_observation_times',{'schedule':'2026-11-04T00:00:00Z'})]:
            with self.subTest(key=key):
                bad=deepcopy(self.new);bad[key]=value;self.candidate(transition.PATH,bad);self.fixture.reject()
        bad=deepcopy(self.new);bad['catalog_special_rules'][0]['restriction']='ALLOW PROPS'
        self.candidate(transition.PATH,bad);self.fixture.reject()

    def test_catalog_in_candidate_cannot_authorize_transition(self):
        prior=deepcopy(self.catalog);prior['menu_version']='unreviewed'
        self.prior(transition.CATALOG,prior);self.fixture.reject()

    def test_changed_prior_or_replacement_does_not_get_exception(self):
        old=deepcopy(self.old);old['verified_u18']=[];self.prior(transition.PATH,old);self.fixture.reject()

    def test_unchanged_post_transition_passes_normally(self):
        self.prior(transition.PATH,self.new)
        previous={transition.PATH:self.new,transition.CATALOG:self.catalog}
        self.assertIs(previous,transition.retention_baselines(previous,{transition.PATH:self.new}))
        self.fixture.prepare()

    def test_catalog_lines_independently_verified(self):
        catalog=deepcopy(self.catalog);catalog['sections'][0]['lines']=[]
        with patch.object(transition,'CATALOG_HASH',transition.digest(catalog)):
            self.prior(transition.CATALOG,catalog);self.candidate(transition.CATALOG,catalog);self.fixture.reject()

    def test_unknown_other_held_changes_still_rejected(self):
        self.old['another_field']='retained';self.prior(transition.PATH,self.old);self.fixture.reject()

if __name__=='__main__':unittest.main()
