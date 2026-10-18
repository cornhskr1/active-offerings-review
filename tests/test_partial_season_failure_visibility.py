"""Unknown or partial calendars must not suppress failed-source warnings."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text()

def function(name):
    start = HTML.index('function ' + name + '(')
    end = HTML.index('\nfunction ', start + 1)
    return HTML[start:end]

class PartialSeasonFailureVisibilityTests(unittest.TestCase):
    def test_unknown_and_partial_failures_visible_without_season_claim(self):
        script = """
const assert=require('node:assert/strict');
const source=(id,extra={})=>({id,sport:'Rugby',region:'International',ok:false,
  approved_catalog:true,source_type:'official-fixtures',coverage_status:'partial',
  official_schedule_url:'https://springboks.rugby/match-centre/',errors:['HTTP 504'],...extra});
const DATA={global:{sources:[source('usa'),source('currie-first'),source('currie-premier'),
 source('unknown'),source('offseason'),source('unapproved',{approved_catalog:false}),
 source('gap',{source_type:'coverage-gap'}),source('healthy',{ok:true})]}};
const mapped={usa:{catalog_event:'USA Women',season_window_complete:false,test_status:'in'},
 'currie-first':{catalog_event:'Currie Cup',season_window_complete:false,test_status:'out'},
 'currie-premier':{catalog_event:'Currie Cup',season_window_complete:false,test_status:'out'},
 unknown:{catalog_event:'Unknown dates'},offseason:{catalog_event:'Verified offseason',test_status:'out'},
 unapproved:{catalog_event:'Not approved'},gap:{catalog_event:'Gap'},healthy:{catalog_event:'Healthy'}};
const mappedCatalogEventForSource=id=>mapped[id];
const isNonWageredNcaaSport=()=>false;
const exactSeasonStatus=event=>event.test_status||null;
const annualSeasonStatus=()=>null;
const eventSourceIds=()=>[];
const todayKey=()=> '2026-10-18';
""" + function('mappedSeasonStatus') + '\n' + function('failedScheduleSourceAttention') + """
assert.equal(mappedSeasonStatus(mapped.usa),null);
assert.equal(mappedSeasonStatus(mapped['currie-first']),null);
assert.equal(mappedSeasonStatus(mapped.unknown),null);
assert.equal(mappedSeasonStatus(mapped.offseason),'out');
const cards=failedScheduleSourceAttention([],'2026-10-18');
assert.equal(cards.length,1);
assert.equal(cards[0].type,'SCHEDULE SOURCE FAILED');
assert.match(cards[0].event,/3 approved competitions · 4 failed source checks/);
assert.match(cards[0].reason,/USA Women; Currie Cup; Unknown dates/);
assert.match(cards[0].reason,/HTTP 504/);
assert.match(cards[0].reason,/does not establish whether the competition is in season/);
assert.doesNotMatch(cards[0].reason,/Verified offseason|Not approved|Healthy|Gap/);
assert.equal(mappedSeasonStatus(mapped.usa),null,'warning must not mutate season classification');
"""
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)

    def test_published_saru_failures_have_one_shared_visible_warning(self):
        script = """
const assert=require('node:assert/strict'); const fs=require('node:fs');
const DATA={global:JSON.parse(fs.readFileSync('data/global-schedule.json')),
 seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json'))};
const isNonWageredNcaaSport=()=>false;
const todayKey=()=> '2026-10-18';
""" + '\n'.join(function(n) for n in ['exactSeasonStatus','annualSeasonStatus','eventSourceIds',
 'sourceCatalogMapping','mappedSeasonStatus','mappedCatalogEventForSource','failedScheduleSourceAttention']) + """
// Use published identities/configuration, with deterministic transport failure.
DATA.global.sources=DATA.global.sources.filter(s=>['rugby-usa','rugby-saru-currie-first','rugby-saru-currie-premier'].includes(s.id)).map(s=>({...s,ok:false,events:0,errors:['HTTP 504']}));
const cards=failedScheduleSourceAttention([],'2026-10-18');
assert.equal(cards.length,1);
assert.match(cards[0].event,/2 approved competitions · 3 failed source checks/);
assert.match(cards[0].reason,/Women’s USA Rugby Events/);
assert.match(cards[0].reason,/Currie Cup/);
assert.equal(mappedSeasonStatus(mappedCatalogEventForSource('rugby-usa')),null);
"""
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)

if __name__ == '__main__':
    unittest.main()
