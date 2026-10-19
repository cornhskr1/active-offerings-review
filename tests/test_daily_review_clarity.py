"""Daily review retains uncertain evidence and separates work without hiding gaps."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text()
SCRIPT = re.search(r'<script>([\s\S]*)</script>', HTML).group(1).split('// interactions')[0]

class DailyReviewClarityTests(unittest.TestCase):
    def run_js(self, body):
        subprocess.run(['node'], input=SCRIPT + '\n' + body, text=True, cwd=ROOT, check=True)

    def test_unknown_event_date_stays_in_today_queue_only(self):
        self.run_js("""
const assert=require('node:assert/strict');
const fs=require('fs');
// Provider snapshots exist only in deployment staging, never in Git fixtures.
for(const [key,path] of Object.entries(FILES))if(key!=='oddsEvents')DATA[key]=JSON.parse(fs.readFileSync(path));
const missing={key:'unknown-date-regression',sport:'Tennis',league:'Professional Tennis',
 type:'AGE EVIDENCE REVIEW',severity:'AMBER',event:'Unknown date',start_time:null,
 age_review_required:true,event_date_missing:true};
DATA.priority.cards.push(missing);
const model=buildTodayModel();
assert.equal(model.windowCards.filter(c=>c.key===missing.key).length,1);
assert.ok(model.dayCards.get(todayKey()).some(c=>c.key===missing.key));
assert.ok(!model.dayCards.get(addDays(todayKey(),1)).some(c=>c.key===missing.key));
""")

    def test_lanes_preserve_every_card_once(self):
        self.run_js("""
const assert=require('node:assert/strict');
renderIssueBoard=cards=>cards.map(c=>`[${c.event}]`).join('');
const market={event:'market-only'},coverage={event:'coverage-only'};
const result=renderReviewLanes([market,coverage],[coverage],[]);
assert.match(result,/Market checks · 1/);
assert.match(result,/Coverage needs attention · 1/);
assert.equal(result.split('[market-only]').length,2);
assert.equal(result.split('[coverage-only]').length,2);
assert.match(result,/not an all-clear/);
""")

    def test_explicit_postponement_remains_coverage_work(self):
        self.run_js("""
const assert=require('node:assert/strict');
DATA.global={sources:[{sport:'Soccer',league:'Chance Liga',ok:true,postponed_fixtures_held:1},
 {sport:'Soccer',league:'Reserve only',ok:true,untimed_or_reserve_fixtures_held:3}]};
const cards=postponedFixtureAttention(todayKey());
assert.equal(cards.length,1);assert.equal(cards[0].type,'POSTPONED FIXTURE');
assert.equal(cards[0].league,'Chance Liga');assert.match(cards[0].event,/1 postponed fixture/);
const rendered=renderIssueBoard(cards,[]);
assert.match(rendered,/1 coverage issue/);assert.doesNotMatch(rendered,/12:00/);
const mixed=renderIssueBoard([...cards,{...cards[0],type:'AGE EVIDENCE REVIEW',event:'Other review',event_date_missing:true}],[]);
assert.doesNotMatch(mixed,/12:00/);
""")

    def test_partial_basketball_fixtures_keep_phase_coverage_attention(self):
        self.run_js("""
const assert=require('node:assert/strict'),fs=require('fs');
// Provider snapshots exist only in deployment staging, never in Git fixtures.
for(const [key,path] of Object.entries(FILES))if(key!=='oddsEvents')DATA[key]=JSON.parse(fs.readFileSync(path));
const ids=new Set(['basketball-euroleague','eurocup-basketball','basketball-womens-euroleague','fiba-bcl']);
const sources=JSON.parse(fs.readFileSync('data/global-schedule-sources.json')).sources.filter(s=>ids.has(s.id));
assert.equal(sources.length,4);
DATA.global={sources:sources.map(s=>({...s,ok:true,events:8}))};
const cards=scheduleCoverageAttention('2026-10-18');
for(const source of sources){
 assert.equal(source.coverage_status,'partial');
 const label=mappedCatalogEventForSource(source.id)?.catalog_event||source.league;
 assert.ok(cards.some(c=>c.league===label&&c.type==='SCHEDULE COVERAGE GAP'),source.id);
}
""")

    def test_each_schedule_feed_is_checked(self):
        self.run_js("""
const assert=require('node:assert/strict');
for(const key of ['global','basketball','college','tennisReview'])DATA[key]={window_start:todayKey(),window_end:addDays(todayKey(),7)};
assert.equal(publishedLoadStatus([['global',true]]).tone,'');
for(const key of ['global','basketball','college','tennisReview']){
 const saved=DATA[key];DATA[key]={window_start:todayKey(),window_end:todayKey()};
 assert.equal(publishedLoadStatus([['global',true]]).tone,'status-warn',key);
 DATA[key]=saved;
}
""")

    def test_returning_to_panel_restores_position_and_repeated_click_keeps_it(self):
        start=HTML.index('const PANEL_SCROLL=');end=HTML.index("document.getElementById('nav').addEventListener",start)
        script="""
const assert=require('node:assert/strict');let current={id:'today'};
const positions=[];const window={scrollY:900,scrollTo:options=>positions.push(options.top)};
const document={querySelector:()=>current,querySelectorAll:()=>[]};
"""+HTML[start:end]+"""
activatePanel({dataset:{panel:'catalog'}});assert.deepEqual(positions,[0]);
current={id:'catalog'};window.scrollY=240;
activatePanel({dataset:{panel:'today'}});assert.deepEqual(positions,[0,900]);
current={id:'today'};window.scrollY=950;
activatePanel({dataset:{panel:'today'}});assert.deepEqual(positions,[0,900]);
"""
        subprocess.run(['node','-e',script],check=True)
