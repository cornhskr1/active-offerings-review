"""Synthetic no-network producer tests; meaningful held screening changes stay visible."""
import ast
import copy
import json
from pathlib import Path
import unittest
from scripts.snapshot_semantic_guards import validate_change

SOURCE=Path(__file__).resolve().parents[1]/'scripts/refresh_ncaa_basketball_intelligence.py'
class HeldBasketballClockTests(unittest.TestCase):
    def setUp(self):
        tree=ast.parse(SOURCE.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='preserve_unchanged_held_screening_clock')
        namespace={'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),namespace)
        self.retain=namespace['preserve_unchanged_held_screening_clock']
        self.previous={'generated_at':'2026-10-23T01:00:00Z','screening_date':'2026-10-22','collection_paused':True,'stale':True,
            'source_observation_times':{'schedule':'2026-10-18T00:00:00Z'},'verified_u18':[{'id':'synthetic-1','name':'Synthetic Athlete'}],
            'verified_u18_count':1,'active_exposure_count':0,'active_exposures':[],'catalog_special_rules':['synthetic rule']}
        self.candidate=copy.deepcopy(self.previous);self.candidate.update(generated_at='2026-10-24T01:00:00Z',screening_date='2026-10-23')
    def test_identical_held_payload_retains_both_clocks_and_passes_unchanged_guard(self):
        before=copy.deepcopy(self.candidate)
        for _ in range(3):
            result=self.retain(self.previous,self.candidate);self.assertEqual(self.previous,result);validate_change(self.previous,result)
        self.assertEqual(before,self.candidate)
    def test_independent_registry_rules_and_screening_changes_are_not_suppressed(self):
        for key,value in [('verified_u18',[{'id':'synthetic-2','name':'Different Synthetic Athlete'}]),
                          ('catalog_special_rules',['reviewed new rule']),('active_exposure_count',1),
                          ('source_observation_times',{'schedule':'2026-10-19T00:00:00Z'})]:
            changed=copy.deepcopy(self.candidate);changed[key]=value
            with self.subTest(key=key):
                self.assertEqual(changed,self.retain(self.previous,changed))
                with self.assertRaises(ValueError):validate_change(self.previous,changed)
    def test_unheld_or_missing_prior_does_not_freeze_fresh_screening(self):
        for previous in (None,{},dict(self.previous,collection_paused=False)):
            self.assertEqual(self.candidate,self.retain(previous,self.candidate))
        candidate=dict(self.candidate,collection_paused=False)
        self.assertEqual(candidate,self.retain(self.previous,candidate))
    def test_type_changes_and_missing_clocks_are_not_disguised(self):
        candidate=dict(self.candidate,verified_u18_count=True)
        self.assertEqual(candidate,self.retain(self.previous,candidate))
        previous=dict(self.previous);del previous['screening_date']
        self.assertEqual(self.candidate,self.retain(previous,self.candidate))

    def test_new_screening_day_age_transition_is_not_frozen(self):
        from scripts.athlete_age_evidence import age_on,age_status_on
        record={'age_evidence':{'status':'verified_dob','dob':'2008-10-24'}}
        self.assertEqual(17,age_on(record,'2026-10-23'))
        self.assertEqual(18,age_on(record,'2026-10-24'))
        self.assertNotEqual(age_status_on(record,'2026-10-23'),age_status_on(record,'2026-10-24'))
        changed=copy.deepcopy(self.candidate)
        changed.update(screening_date='2026-10-24',verified_u18=[],verified_u18_count=0)
        result=self.retain(self.previous,changed)
        self.assertEqual(changed,result)
        self.assertEqual('2026-10-24',result['screening_date'])
        with self.assertRaises(ValueError):validate_change(self.previous,result)
