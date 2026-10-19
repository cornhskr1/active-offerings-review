from pathlib import Path
import subprocess
import unittest
from copy import deepcopy
from datetime import datetime,timezone
from unittest.mock import patch
from scripts import refresh_official_school_calendars as collector
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text()
class NebraskaSavedReviewTests(unittest.TestCase):
 def test_current_cutoff_state_and_contradiction(self):
  helpers=HTML[HTML.index('function futuresCurrentState('):HTML.index('\nfunction renderCollege()',HTML.index('function futuresCurrentState('))]
  script="""
const assert=require('node:assert/strict');let today='2026-11-02';
const todayKey=()=>today,ctKey=x=>x.slice(0,10),prettyDay=x=>x,esc=x=>String(x),pill=(c,x)=>x;
const DATA={college:{events:[]},collegeFutures:{source_stale:true,programs:[]}};
"""+helpers+"""
const p={school:'Nebraska',sport:"Men's Basketball",source_stale:true,regular_season_futures:{days_to_cutoff:15,color:'green',label:'NOT DUE'},first_regular_season_contest:{date:'2026-11-02',time:'6:30 PM CST',opponent:'Le Moyne'}};
DATA.collegeFutures.programs=[p];const before=JSON.stringify(p);
assert.equal(futuresCurrentState('regular',p).days_to_cutoff,0);
assert.match(futuresCutoffLine('regular',p),/CUTOFF DATE TODAY/);
let rows=collegeFuturesAttention(today);assert.equal(rows.length,1);assert.equal(rows[0].date_only,true);assert.equal(rows[0].start_time,'2026-11-02');assert.match(rows[0].reason,/Saved cutoff evidence/);
today='2026-11-03';assert.equal(futuresCurrentState('regular',p).days_to_cutoff,-1);assert.equal(collegeFuturesAttention(today)[0].severity,'RED');
assert.equal(JSON.stringify(p),before);
today='2026-10-19';p.school='Omaha';p.sport="Women's Basketball";p.first_regular_season_contest={date:'2026-10-21',opponent:'Concordia (Neb.)'};
DATA.college.calendar_events=[{school:p.school,sport:p.sport,date:'2026-10-21',opponent:'Concordia (Neb.)',event_type:'exhibition'}];
assert.equal(futuresCurrentState('regular',p).contradiction,true);
assert.equal(futuresCurrentState('regular',p).days_to_cutoff,null);
rows=collegeFuturesAttention(today);assert.equal(rows.length,1);assert.equal(rows[0].severity,'AMBER');assert.equal(rows[0].event_date_missing,true);assert.match(rows[0].reason,/no replacement/);assert.doesNotMatch(rows[0].reason,/must be disabled before/);
assert.equal(collegeFuturesAttention('2026-10-21').length,0);
DATA.college.calendar_events[0].opponent='Another team';assert.equal(futuresCurrentState('regular',p).contradiction,undefined);
p.first_regular_season_contest.date='2026-02-30';assert.equal(futuresCurrentState('regular',p).days_to_cutoff,null);
"""
  subprocess.run(['node','-e',script],check=True)
 def test_full_projection_preserves_source_evidence_and_terminal_records(self):
  sources=[{'id':str(i),'school':s,'sport':p} for i,(s,p) in enumerate(sorted(collector.EXPECTED))]
  rows=[{'uid':str(i),'date':'2026-10-26','opponent':'Other','status':status,'event_type':'exhibition','source_generated_at':'2026-10-18T00:00:00Z','location':'Lincoln, NE'} for i,status in enumerate(['CONFIRMED','CANCELLED','REMOVED','COMPLETED'])]
  baseline=deepcopy(rows)
  def collect(s,prev,now,get):return {'events':rows if s==sources[0] else [],'source_status':{'ok':True,'fetched_at':'2026-10-18T00:00:00Z'},'cache':{}}
  with patch.object(collector,'collect_school_calendar',side_effect=collect):
   data,_=collector.build_snapshot({'sources':sources},{},{},datetime(2026,10,19,4,tzinfo=timezone.utc))
  self.assertEqual(data['events'],[])
  self.assertEqual(len(data['calendar_events']),4)
  self.assertEqual(rows,baseline)
  self.assertEqual(data['calendar_events'][0]['source_generated_at'],baseline[0]['source_generated_at'])
  self.assertEqual(data['sources'][0]['fetched_at'],'2026-10-18T00:00:00Z')
 def test_failed_missing_cache_retains_full_prior_projection(self):
  sources=[{'id':str(i),'school':s,'sport':p} for i,(s,p) in enumerate(sorted(collector.EXPECTED))]
  first=sources[0]
  row={'uid':'saved-future','school':first['school'],'sport':first['sport'],'date':'2026-11-02','opponent':'Other','status':'CONFIRMED','event_type':'exhibition','location':'Lincoln, NE'}
  old={'events':[],'calendar_events':[row]};baseline=deepcopy(old)
  with patch.object(collector,'collect_school_calendar',return_value={'events':[],'source_status':{'ok':False},'cache':{}}):
   data,_=collector.build_snapshot({'sources':sources},old,{},datetime(2026,10,19,12,tzinfo=timezone.utc))
  self.assertEqual(len(data['calendar_events']),1)
  self.assertTrue(data['calendar_events'][0]['source_stale'])
  self.assertEqual(data['calendar_events'][0]['event_type'],'exhibition')
  self.assertEqual(old,baseline)
 def test_rolling_ui_projection_excludes_terminal_and_preserves_unrelated(self):
  helpers=HTML[HTML.index('function allCollegeEvents('):HTML.index('\nfunction basketballIntelligenceAlerts(')]
  script="""const assert=require('node:assert/strict');const todayKey=()=> '2026-10-19',addDays=()=> '2026-10-26',keyBetween=(d,a,b)=>d>=a&&d<=b,isNonWageredNcaaSport=()=>false,basketballCollegeSupplements=()=>[];
const DATA={college:{calendar_programs:[{school:'Nebraska',sport:"Men's Basketball"}],events:[{school:'Nebraska',sport:"Men's Basketball",date:'2026-10-20',uid:'old'},{school:'Omaha',sport:'Wrestling',date:'2026-10-21',source_stale:true}],calendar_events:['CONFIRMED','CANCELLED','REMOVED','COMPLETED'].map((status,i)=>({school:'Nebraska',sport:"Men's Basketball",uid:String(i),date:'2026-10-26',status,event_type:'exhibition'}))}};
"""+helpers+"""const rows=visibleCollegeEvents();assert.equal(rows.length,2);assert.equal(rows[0].uid,'0');assert.equal(rows[0].event_type,'exhibition');assert.equal(rows[1].source_stale,true);assert.equal(DATA.college.events[0].uid,'old');"""
  subprocess.run(['node','-e',script],check=True)
