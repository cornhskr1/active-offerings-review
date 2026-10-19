"""Offline F1 presentation, licensing, exact health binding and UI regressions."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text()
SCRIPT = re.search(r'<script>([\s\S]*)</script>', HTML).group(1).split('// interactions')[0]


class JolpicaF1UiTests(unittest.TestCase):
    def run_js(self, body, ui=False):
        setup = r'''
const assert=require('node:assert/strict');
const JolpicaF1=require('./assets/jolpica-f1.js');
const CatalogHealthSummary=require('./assets/catalog-health-summary.js');
const now='2026-10-19T10:00:00Z';
const sample={schema_version:1,provider:'Jolpica-F1',source_id:'jolpica-f1',catalog_identity_key:'motorsports-intl-f1',dataset_scope:'isolated_jolpica_f1_only',observed_at:now,window_start:'2026-10-19T05:00:00Z',window_end:'2026-10-27T05:00:00Z',source_health:{status:'partial'},collector_state:{halted:false},license:{id:'CC-BY-NC-SA-4.0',url:'https://creativecommons.org/licenses/by-nc-sa/4.0/',source_url:'https://github.com/jolpica/jolpica-f1',terms_url:'https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md',attribution:'F1 schedule data: Jolpica-F1',changes:'Selected race schedule facts; normalized dates and filtered review window.',notice:'Provided without warranty; Jolpica does not endorse this tool.'},events:[{id:'jolpica-f1:2026:19:americas',source_id:'jolpica-f1',catalog_identity_key:'motorsports-intl-f1',season:'2026',round:19,circuit_id:'americas',circuit:'Circuit of the Americas',name:'United States Grand Prix',locality:'Austin',country:'USA',date:'2026-10-25',start_time:'2026-10-25T19:00:00Z',date_only:false,status:'UNKNOWN',source_stale:false,observed_at:now,coverage_complete:false,license_id:'CC-BY-NC-SA-4.0',source_url:'https://api.jolpi.ca/ergast/f1/current/races/'}]};
const copy=x=>JSON.parse(JSON.stringify(x));
'''
        subprocess.run(['node'], input=(SCRIPT if ui else '') + '\n' + setup + body,
                       text=True, cwd=ROOT, check=True)

    def test_exact_identity_license_and_unknown_fields(self):
        self.run_js(r'''
const before=JSON.stringify(sample);const snapshot=JolpicaF1.project(sample,now);
assert.equal(JSON.stringify(sample),before);assert.equal(snapshot.events[0].status,'UNKNOWN');
assert.equal(snapshot.events[0].coverage_complete,false);assert.equal(snapshot.current,true);
assert.deepEqual(snapshot.license,sample.license);
const injected=copy(sample);Object.assign(injected.events[0],{participants:['Driver'],age:25,catalog_approved:true,season_start:'01-01'});
const clean=JolpicaF1.project(injected,now).events[0];for(const key of ['participants','age','catalog_approved','season_start'])assert.equal(key in clean,false);
for(const mutate of [x=>x.catalog_identity_key='motorsports-intl-formula-e',x=>x.events[0].catalog_identity_key='motorsports-intl-formula-e',x=>x.license.id='MIT',x=>x.events[0].status='SCHEDULED',x=>x.observed_at='2026-10-20T00:00:00Z',x=>x.events.push(copy(x.events[0])),x=>x.events[0].start_time=null]){const bad=copy(sample);mutate(bad);assert.throws(()=>JolpicaF1.project(bad,now));}
for(const state of [undefined,null,'false',[],{}, {halted:'false'},{halted:null},{halted:0}]){const bad=copy(sample);bad.collector_state=state;assert.throws(()=>JolpicaF1.project(bad,now));}
const day=copy(sample);day.events[0].start_time=null;day.events[0].date_only=true;
assert.equal(JolpicaF1.project(day,now).events[0].start_time,'2026-10-25');
''')

    def test_staleness_pause_health_and_non_mutating_repeated_merge(self):
        self.run_js(r'''
const snapshot=JolpicaF1.project(sample,now);
const coverage={identities:[{identity_key:JolpicaF1.IDENTITY,source_ids:['official-f1']},{identity_key:'formula-e',source_ids:['official-f1']}]};
const globalData={window_start:'2026-10-19',window_end:'2026-10-26',sources:[{id:'official-f1',source_type:'official-event-window',endpoint:'https://formula1.com',ok:true,checked_at:now}],events:[{id:'reference',source_id:'official-f1',catalog_identity_key:JolpicaF1.IDENTITY,start_time:'2026-10-25',date_only:true,name:'F1 season window'}]};
const before=JSON.stringify({coverage,globalData});
const input={coverage:JolpicaF1.coverage(coverage,snapshot),global:JolpicaF1.global(globalData,snapshot),now};
const summary=CatalogHealthSummary.build(input);assert.equal(summary.totals.fresh_events,1);assert.equal(summary.rows[0].fresh_event_count,1);assert.equal(summary.rows[1].fresh_event_count,0);assert.equal(summary.rows[0].reference_event_count,1);
assert.equal(JSON.stringify({coverage,globalData}),before);
assert.equal(JolpicaF1.global(input.global,snapshot).events.length,2);
const stale=JolpicaF1.project(sample,'2026-10-20T10:00:01Z');assert.equal(stale.current,false);assert.equal(stale.events[0].source_stale,true);
for(const status of ['stale','paused']){const held=copy(sample);held.source_health.status=status;const s=JolpicaF1.project(held,now);assert.equal(s.current,false);assert.equal(s.events[0].source_stale,true);}
const empty=copy(sample);empty.events=[];const s=JolpicaF1.project(empty,now);assert.equal(s.current,true);assert.equal(s.events.length,0);assert.equal(s.source.coverage_status,'partial');
''')

    def test_healthy_empty_uses_only_f1_source_window(self):
        self.run_js(r"""
const empty=copy(sample);empty.events=[];const snapshot=JolpicaF1.project(empty,now);
const coverage={identities:[{identity_key:JolpicaF1.IDENTITY,source_ids:[]},{identity_key:'other',source_ids:['other-source']}]};
const globalData={window_start:'2026-10-01',window_end:'2026-10-08',sources:[{id:'other-source',endpoint:'https://other.example/schedule',ok:true,checked_at:now,window_start:sample.window_start,window_end:sample.window_end}],events:[]};
const before=JSON.stringify(globalData);
const input={coverage:JolpicaF1.coverage(coverage,snapshot),global:JolpicaF1.global(globalData,snapshot),now,windowStart:'2026-10-19',windowEnd:'2026-10-26'};
const rows=CatalogHealthSummary.build(input).rows;
assert.equal(rows[0].state,'healthy_empty');assert.equal(rows[0].healthy_source_count,1);assert.equal(rows[0].fresh_event_count,0);
assert.equal(rows[1].state,'inactive_unknown');assert.equal(rows[1].healthy_source_count,0);
assert.equal(JSON.stringify(globalData),before);assert.equal(input.global.window_start,'2026-10-01');assert.equal(input.global.window_end,'2026-10-08');
const narrow=copy(sample);narrow.events=[];narrow.window_end='2026-10-20T05:00:00Z';const short=JolpicaF1.project(narrow,now);
const wideGlobal={...globalData,window_start:'2026-10-19',window_end:'2026-10-26'};
assert.equal(CatalogHealthSummary.build({...input,global:JolpicaF1.global(wideGlobal,short)}).rows[0].state,'inactive_unknown');
""")

    def test_exclusive_f1_window_end_and_central_dst(self):
        self.run_js(r"""
const empty=copy(sample);empty.events=[];const snapshot=JolpicaF1.project(empty,now);
assert.equal(snapshot.source.window_start,'2026-10-19');assert.equal(snapshot.source.window_end,'2026-10-26');assert.equal(empty.window_end,'2026-10-27T05:00:00Z');
const coverage={identities:[{identity_key:JolpicaF1.IDENTITY,source_ids:[]}]};
const health=(s,at,start,end)=>CatalogHealthSummary.build({coverage:JolpicaF1.coverage(coverage,s),global:JolpicaF1.global({window_start:start,window_end:end,sources:[],events:[]},s),now:at,windowStart:start,windowEnd:end}).rows[0].state;
assert.equal(health(snapshot,now,'2026-10-19','2026-10-26'),'healthy_empty');
assert.equal(health(snapshot,now,'2026-10-19','2026-10-27'),'inactive_unknown');
const dst=copy(empty);dst.observed_at='2026-11-01T10:00:00Z';dst.window_start='2026-11-01T05:00:00Z';dst.window_end='2026-11-09T06:00:00Z';
const fall=JolpicaF1.project(dst,dst.observed_at);assert.equal(fall.source.window_start,'2026-11-01');assert.equal(fall.source.window_end,'2026-11-08');assert.equal(dst.window_end,'2026-11-09T06:00:00Z');
assert.equal(health(fall,dst.observed_at,'2026-11-01','2026-11-08'),'healthy_empty');assert.equal(health(fall,dst.observed_at,'2026-11-01','2026-11-09'),'inactive_unknown');
""")

    def test_ui_license_location_and_catalog_invariants(self):
        self.run_js(r'''
DATA.seasonMap=JSON.parse(require('node:fs').readFileSync('data/catalog-season-map.json','utf8'));
const before=JSON.stringify(DATA.seasonMap);F1_SNAPSHOT=JolpicaF1.project(sample,now);
const notice=f1SourceHtml();assert.match(notice,/CC BY-NC-SA 4.0/);assert.match(notice,/Modifications:/);assert.match(notice,/noncommercial, share alike/);assert.match(notice,/does not endorse/);assert.match(notice,/not wagering approval/);
const event=F1_SNAPSHOT.events[0];assert.match(f1EventHtml(event),/Austin/);assert.match(f1EventHtml(event),/Race status UNKNOWN/);assert.match(f1EventHtml(event),/ages unknown/);
const board=renderUpcomingSportBoard([event]);assert.match(board,/United States Grand Prix/);assert.match(board,/Jolpica-F1/);assert.match(board,/Data-use terms/);assert.match(board,/Circuit of the Americas/);
const identity=oddsCatalogIdentity('motorsports-intl-f1');assert.equal(identity.source_id,'motorsports-f1');assert.equal(JSON.stringify(DATA.seasonMap),before);
F1_SNAPSHOT=null;F1_LOAD_ERROR='Invalid snapshot';assert.match(f1SourceHtml(),/Invalid snapshot/);
''', ui=True)

    def test_review_today_reference_is_not_a_second_race(self):
        self.run_js(r"""
F1_SNAPSHOT=JolpicaF1.project(sample,now);todayKey=()=> '2026-10-19';
DATA.global={sources:[{id:'motorsports-f1',source_type:'official-event-window'}],events:[{id:'window',source_id:'motorsports-f1',name:'F1 dates',start_time:'2026-10-25',date_only:true,status:'UNKNOWN'}]};
basketballReviewEvents=()=>[];attentionCardsForDay=()=>[];
scheduleCoverageAttention=staleScheduleSourceAttention=failedScheduleSourceAttention=heldMatchupAttention=heldAgeReviewAttention=postponedFixtureAttention=scheduleTimeConflictAttention=()=>[];
const before=JSON.stringify(DATA.global);const model=buildTodayModel();assert.equal(model.events.length,1);assert.equal(model.events[0].source_id,'jolpica-f1');assert.equal(model.events[0].status,'UNKNOWN');assert.equal(model.global.sources.length,2);assert.equal(JSON.stringify(DATA.global),before);
assert.equal(buildTodayModel().events.length,1);
""", ui=True)

    def test_default_by_date_render_includes_license_and_unknowns(self):
        self.run_js(r"""
F1_SNAPSHOT=JolpicaF1.project(sample,now);todayKey=()=> '2026-10-19';
const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',dataset:{},classList:{toggle(){}},setAttribute(){}});return nodes.get(id);};
global.document={getElementById:node,querySelector:node,querySelectorAll:()=>[]};
renderOddsSessionStatus=()=>{};reviewFeedWindows=()=>[];collegeMatchForGlobal=()=>null;
TODAY_MODEL={start:todayKey(),end:'2026-10-26',global:{},events:F1_SNAPSHOT.events,pqCards:[],coverageAlerts:[],red:0,amber:0,dateHtml:null};
assert.equal(TODAY_VIEW,'date');renderToday();const html=node('todayDays').innerHTML;
assert.match(html,/United States Grand Prix/);assert.match(html,/Circuit of the Americas/);assert.match(html,/Austin/);assert.match(html,/Race status UNKNOWN/);assert.match(html,/Entrants and ages unknown/);
assert.match(html,/CC BY-NC-SA 4.0/);assert.match(html,/Data-use terms/);assert.match(html,/Modifications:/);assert.match(html,/noncommercial, share alike/);assert.match(html,/does not endorse/);
assert.equal((html.match(/Modifications:/g)||[]).length,1);
renderToday();assert.equal(node('todayDays').innerHTML,html);
TODAY_VIEW='sport';renderToday();TODAY_VIEW='date';renderToday();assert.equal(node('todayDays').innerHTML,html);
""", ui=True)

    def test_rendered_catalog_card_uses_validated_exact_f1_source(self):
        self.run_js(r"""
DATA.seasonMap=JSON.parse(require('node:fs').readFileSync('data/catalog-season-map.json','utf8'));
todayKey=()=> '2026-10-19';DATA.global={sources:[],events:[]};const before=JSON.stringify({map:DATA.seasonMap,global:DATA.global});
const f1=oddsCatalogIdentity('motorsports-intl-f1'),formulaE=oddsCatalogIdentity('motorsports-intl-formula-e');
F1_SNAPSHOT=JolpicaF1.project(sample,now);
assert.ok(eventSourceIds(f1).includes('jolpica-f1'));assert.ok(!eventSourceIds(formulaE).includes('jolpica-f1'));
const valid=renderMappedCatalogEvents([f1],'Motorsports');assert.match(valid,/PARTIAL SCHEDULE/);assert.match(valid,/Jolpica-F1/);assert.doesNotMatch(valid,/NOT CONNECTED/);assert.match(valid,/Season progress/);
F1_SNAPSHOT=JolpicaF1.project(sample,'2026-10-20T11:00:00Z');
const stale=renderMappedCatalogEvents([f1],'Motorsports');assert.match(stale,/SOURCE NEEDS CHECK/);assert.match(stale,/SAVED EVIDENCE — VERIFY/);assert.doesNotMatch(stale,/NOT CONNECTED/);
F1_SNAPSHOT=null;
assert.ok(!eventSourceIds(f1).includes('jolpica-f1'));
const absent=renderMappedCatalogEvents([f1],'Motorsports');assert.match(absent,/NOT CONNECTED/);assert.doesNotMatch(absent,/PARTIAL SCHEDULE/);
assert.equal(JSON.stringify({map:DATA.seasonMap,global:DATA.global}),before);
""", ui=True)

    def test_exact_official_f1_link_not_formula_e(self):
        import json
        from scripts.build_catalog_official_sources import EVENT_URL_OVERRIDES
        registry = json.loads((ROOT / "data/catalog-official-sources.json").read_text())
        rows = {row["key"]: row for row in registry["events"]}
        self.assertEqual(rows["motorsports-intl-f1"]["official_url"], "https://www.formula1.com/en/racing/2026")
        self.assertEqual(EVENT_URL_OVERRIDES["motorsports-intl-f1"], "https://www.formula1.com/en/racing/2026")
        self.assertIn("fiaformulae.com", rows["motorsports-intl-formula-e"]["official_url"])

    def test_static_integration(self):
        self.assertLess(HTML.index('assets/jolpica-f1.js'), HTML.index('const DATA={}'))
        self.assertIn("f1:'data/jolpica-f1-events.json'", HTML)
        self.assertIn("event.key==='motorsports-intl-f1'?f1SourceHtml()", HTML)
        self.assertIn('JolpicaF1.coverage(DATA.coverage,F1_SNAPSHOT)', HTML)
        self.assertNotIn('api.jolpi.ca', HTML)


if __name__ == '__main__':
    unittest.main()
