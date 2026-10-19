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

    def test_time_conflict_is_one_candidate_and_visible_coverage_work(self):
        self.run_js("""
const assert=require('node:assert/strict');
const e={id:'canonical',name:'Away at Home',sport:'Football',league:'Synthetic',start_time:'2026-10-20T00:20:00Z',
 odds_observation:{catalog_identity_key:'synthetic',observed_at:'2026-10-19T00:00:00Z'},
 schedule_time_conflict:{canonical_start_time:'2026-10-20T00:20:00Z',provider_start_time:'2026-10-20T00:22:00Z'}};
const cards=scheduleTimeConflictAttention([e]);assert.equal(cards.length,1);assert.equal(cards[0].time_label,'TIME CONFLICT');
const detail=oddsObservationHtml(e);assert.match(detail,/TIME CONFLICT/);assert.match(detail,/7:20 PM/);assert.match(detail,/7:22 PM/);assert.match(detail,/neither kickoff is confirmed/);
const board=renderIssueBoard(cards,[e]);assert.match(board,/TIME CONFLICT/);assert.match(board,/Neither time is selected/);
""")

    def test_legacy_source_key_is_exact_unique_and_preserves_preseason_scope(self):
        self.run_js("""
const assert=require('node:assert/strict'),fs=require('fs');
for(const [key,path] of Object.entries(FILES))if(key!=='oddsEvents')DATA[key]=JSON.parse(fs.readFileSync(path));
assert.equal(oddsIdentityForScheduleEvent({source_id:'nfl',season_stage:'REGULAR SEASON'}),'football-us-nfl');
assert.equal(oddsIdentityForScheduleEvent({source_id:'mlb',season_stage:'PRESEASON'}),'baseball-us-mlb-spring-training');
assert.equal(oddsIdentityForScheduleEvent({source_id:'not-mapped',name:'NFL'}),null);
const nfl=DATA.oddsMap.mappings.find(m=>m.catalog_identity_key==='football-us-nfl');DATA.oddsMap.mappings.push({...nfl,provider_key:'synthetic-ambiguous'});
assert.equal(oddsIdentityForScheduleEvent({source_id:'nfl'}),null);
""")

    def test_current_provider_first_without_irrelevant_paused_source_commentary(self):
        self.run_js(r"""
const assert=require('node:assert/strict');
const now=new Date().toISOString();
DATA.seasonMap={source_mappings:[{key:'synthetic-id',source_id:'legacy'}]};
DATA.oddsMap={mappings:[{provider_key:'synthetic',catalog_identity_key:'synthetic-id',sport:'Basketball',league:'Synthetic League'}]};
DATA.oddsEvents={sources:[{provider_key:'synthetic',status:'ok',observed_at:now,stale:false}]};
ODDS_SESSION={events:[{catalog_identity_key:'synthetic-id',observed_at:now,source_stale:false}]};
DATA.global={sources:[{id:'legacy',sport:'Basketball',league:'Synthetic League',ok:false,collection_paused:true,endpoint:'https://site.api.espn.com/example',official_schedule_url:'https://example.org/official',errors:['Permission required: ESPN automated collection is paused pending access review.']} ]};
let html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy']);
assert.match(html,/The Odds API · Schedule data available/);assert.match(html,/PARTIAL SCHEDULE/);assert.match(html,/1 event observed/);assert.match(html,/Partial coverage only/);assert.match(html,/https:\/\/example.org\/official/);assert.doesNotMatch(html,/SOURCE ISSUE|ESPN|PAUSED/);assert.match(html,/Approval basis:/);assert.match(html,/Information source:/);assert.match(html,/Coverage:/);
DATA.oddsMap.mappings.push({provider_key:'other',catalog_identity_key:'other-id',sport:'Basketball',league:'Other'});html=catalogEntryHealthHtml('Basketball',['synthetic-id','other-id'],['legacy']);assert.match(html,/PAUSED/);DATA.oddsMap.mappings.pop();
DATA.global.sources.push({...DATA.global.sources[0],id:'unreplaced'});html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy','unreplaced']);assert.match(html,/PAUSED/);DATA.global.sources.pop();
DATA.oddsEvents.sources[0].stale=true;html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy']);assert.match(html,/STALE SCHEDULE/);assert.match(html,/ESPN/);assert.match(html,/PAUSED/);assert.doesNotMatch(html,/Schedule data available/);
DATA.oddsEvents.sources[0].stale=false;DATA.oddsEvents.sources[0].observed_at='2020-01-01T00:00:00Z';html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy']);assert.match(html,/STALE SCHEDULE/);assert.match(html,/PAUSED/);
DATA.oddsEvents.sources[0].observed_at=now;ODDS_SESSION.events=[];html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy']);assert.match(html,/NO CURRENT EVENTS/);assert.match(html,/PAUSED/);assert.doesNotMatch(html,/Schedule data available/);
DATA.oddsEvents.sources[0].status='not_active_in_directory';html=catalogEntryHealthHtml('Basketball',['synthetic-id'],['legacy']);assert.match(html,/SOURCE NEEDS ATTENTION/);
""")
