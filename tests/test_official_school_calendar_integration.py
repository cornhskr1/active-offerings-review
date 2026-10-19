from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import unittest
from unittest.mock import patch
from scripts import refresh_official_school_calendars as module

ROOT = Path(__file__).resolve().parents[1]

class SchoolCalendarIntegrationTests(unittest.TestCase):
    def config(self):
        return {'sources': [{'id':str(i),'school':school,'sport':sport} for i,(school,sport) in enumerate(sorted(module.EXPECTED))]}

    def test_exact_sixteen_inventory(self):
        config=self.config();config['sources'].append({'id':'bad','school':'Omaha','sport':'Football'})
        with self.assertRaises(ValueError):module.build_snapshot(config,{}, {},datetime.now(timezone.utc))

    def test_location_requires_state_not_home_or_ambiguous_venue(self):
        for location in ['Memorial Stadium','Lincoln','Omaha','Nebraska at Iowa']:
            self.assertEqual(module.classify_location({'location':location,'site':'HOME'})['site_color'],'amber',location)
        self.assertEqual(module.classify_location({'location':'Lincoln, Neb.','site':'UNKNOWN'})['site_color'],'red')
        self.assertEqual(module.classify_location({'location':'Lincoln, NE'})['site_color'],'red')
        self.assertEqual(module.classify_location({'location':'Overland Park, Kan.','site':'HOME'})['site_color'],'green')
        self.assertEqual(module.classify_location({'location':'Memorial Stadium, Champaign, IL'})['site_color'],'green')

    def test_cancelled_removed_not_reintroduced_and_unrelated_saved_stale(self):
        config=self.config();first=config['sources'][0];now=datetime(2026,10,19,1,tzinfo=timezone.utc)
        old={'events':[{'school':'Nebraska','sport':'Wrestling','date':'2026-10-20','opponent':'Other','time':'TBA'}]}
        baseline=deepcopy(old)
        def collect(source,previous,now,get):
            rows=[]
            if source==first:
                rows=[{'uid':str(i),'date':'2026-10-20','opponent':'Other','location':'Omaha, Neb.','status':status} for i,status in enumerate(['CONFIRMED','CANCELLED','REMOVED','COMPLETED'])]
            return {'events':rows,'source_status':{'ok':True},'cache':{}}
        with patch.object(module,'collect_school_calendar',side_effect=collect):
            result,cache=module.build_snapshot(config,old,{},now)
        self.assertEqual(len(result['events']),2)
        self.assertTrue(next(e for e in result['events'] if e['sport']=='Wrestling')['source_stale'])
        self.assertEqual(old,baseline)
        self.assertEqual(len(result['calendar_programs']),16)

    def test_failed_initial_calendar_retains_saved_exact_program(self):
        config=self.config();first=config['sources'][0];now=datetime(2026,10,19,1,tzinfo=timezone.utc)
        event={'school':first['school'],'sport':first['sport'],'date':'2026-10-18','opponent':'Other','location':'Omaha, Neb.','time':'TBA'}
        with patch.object(module,'collect_school_calendar',return_value={'events':[],'source_status':{'ok':False,'error':'Unavailable'},'cache':{}}):
            result,_=module.build_snapshot(config,{'events':[event]}, {},now)
        self.assertEqual(len(result['events']),1)
        self.assertTrue(result['events'][0]['source_stale'])
        self.assertEqual(result['events'][0]['date'],'2026-10-18')

    def test_futures_preserved_not_recomputed(self):
        old={'generated_at':'2026-10-01','programs':[{'school':'Nebraska','first_regular_season_contest':{'date':'2026-11-02'}}]}
        baseline=deepcopy(old);new=module.retain_futures(old)
        self.assertEqual(old,baseline)
        self.assertEqual(new['generated_at'],old['generated_at'])
        self.assertEqual(new['programs'][0]['first_regular_season_contest'],old['programs'][0]['first_regular_season_contest'])
        self.assertTrue(new['source_stale'])

    def test_workflow_collects_only_offered_calendars_not_legacy_html_or_rosters(self):
        text=(ROOT/'.github/workflows/refresh-nebraska-collegiate.yml').read_text()
        self.assertIn('python3 scripts/refresh_official_school_calendars.py',text)
        self.assertNotIn('python3 scripts/refresh_nebraska_collegiate.py',text)
        self.assertNotIn('python3 scripts/refresh_nebraska_collegiate_futures.py',text)
        self.assertIn('data/official-school-calendar-cache.json',text)

    def test_calendar_owned_basketball_suppresses_saved_espn_resurrection(self):
        html=(ROOT/'index.html').read_text()
        start=html.index('function normTeamName(');end=html.index('\nfunction basketballIntelligenceAlerts(',start)
        script='''const assert=require('node:assert/strict');
const normCollegeSport=s=>String(s).toLowerCase().replace(/women.s|men.s/g,'').trim();
const collegeGender=e=>/women/i.test(e.gender||e.sport||'')?'women':'men';
const ctKey=s=>s.slice(0,10);const eventTime=()=> 'TBA';
const DATA={college:{calendar_programs:[{school:'Nebraska',sport:"Men's Basketball"}],events:[]},basketball:{events:[{division:'Division I',start_time:'2026-10-20T18:00:00Z',home:'Nebraska',away:'Other',gender:'Men'}]}};
'''+html[start:end]+'''
assert.equal(basketballCollegeSupplements().length,0);
DATA.college.calendar_programs=[];
assert.equal(basketballCollegeSupplements().length,1);
'''
        subprocess.run(['node','-e',script],check=True,cwd=ROOT)

if __name__=='__main__':unittest.main()
