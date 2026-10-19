"""Rendered catalog health distinguishes source reachability from fixture coverage."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text()
HELPERS = HTML[HTML.index("let CATALOG_HEALTH_FILTER='all';"):HTML.index('// interactions')]


class CatalogSourceBadgeTests(unittest.TestCase):
    def run_js(self, body):
        subprocess.run(['node', '-e', """
const assert=require('node:assert/strict');
const DATA={global:{sources:[],generated_at:'2026-10-18'}};
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;');
const fmtDateTime=x=>x;
const regionLeagueLabel=(_,league)=>league;
const host={innerHTML:''};
const document={getElementById:()=>host};
""" + HELPERS + body], cwd=ROOT, check=True)

    def test_rendered_states_filters_and_counts_share_one_classification(self):
        self.run_js("""
const make=(id,source_type,coverage_status,ok=true)=>({id,league:id,sport:'Test',
  source_type,coverage_status,ok,event_count:0,official_schedule_url:'https://example.org/schedule'});
DATA.global.sources=[
 make('gap','coverage-gap'),make('gap-legacy','coverage-gap','legacy-name'),
 make('window','official-event-window','complete'),make('window-partial','official-event-window','partial-window'),
 make('partial','fixture-adapter','partial'),make('partial-round','fixture-adapter','partial-next-round'),
 make('complete','fixture-adapter','complete'),make('unknown','fixture-adapter'),
 make('error','fixture-adapter','partial',false),make('gap-error','coverage-gap','pending',false),
 make('window-error','official-event-window','complete',false),
 make('manual','tennis-intelligence','current-published-events',false),
 {...make('excluded','fixture-adapter','complete'),approved_catalog:false}
];
DATA.global.sources[0].source_note='Exact gap warning <retain>.';
DATA.global.sources[2].source_note='Exact date-only warning.';
const expected={gap:'setup','gap-legacy':'setup',window:'window','window-partial':'window',
 partial:'partial','partial-round':'partial',complete:'connected',unknown:'connected',
 error:'source','gap-error':'source','window-error':'source',manual:'manual'};
const labels={setup:'NOT CONNECTED',window:'DATES ONLY',partial:'PARTIAL SCHEDULE',
 connected:'SOURCE CHECKED',source:'SOURCE NEEDS CHECK',manual:'SAVED EVIDENCE'};
assert.equal(catalogCoverageHealth().length,12);
for(const row of catalogCoverageHealth()){
 assert.equal(row.state,expected[row.source.id]);
 const rendered=catalogEntryHealthHtml('Test',[],[row.source.id]);
 assert(rendered.includes(labels[row.state]),row.source.id);
 assert(rendered.includes('https://example.org/schedule'));
 assert.doesNotMatch(rendered,/>CONNECTED</);
 for(const filter of Object.keys(labels)){
  CATALOG_HEALTH_FILTER=filter;
  assert.equal(catalogEntryMatchesHealth('Test',[],[row.source.id]),filter===row.state);
 }
}
assert.match(catalogEntryHealthHtml('Test',[],['gap']),/Exact gap warning &lt;retain>/);
assert.match(catalogEntryHealthHtml('Test',[],['window']),/Exact date-only warning/);
assert.match(catalogEntryHealthHtml('Test',[],['unknown']),/does not establish complete season coverage/);
assert.match(catalogEntryHealthHtml('Test',[],['manual']),/age does not create an automated alert/);
CATALOG_HEALTH_FILTER='all';
assert(catalogEntryMatchesHealth('Test',[],['unknown']));
renderCatalogHealth();
for(const [label,count] of [['Source checks passed',2],['Sources need setup',2],['Dates only',2],
 ['Partial coverage',2],['Source errors',3],['Manual evidence',1]])assert(host.innerHTML.includes(`${label}: ${count}`));
""")

    def test_published_gap_and_date_sources_never_render_as_successful_fixture_sources(self):
        self.run_js("""
const fs=require('node:fs');
DATA.global=JSON.parse(fs.readFileSync('data/global-schedule.json'));
for(const row of catalogCoverageHealth()){
 if(row.source.source_type==='coverage-gap')assert(['setup','source'].includes(row.state),row.source.id);
 if(row.source.source_type==='official-event-window')assert(['window','source'].includes(row.state),row.source.id);
 if(String(row.source.coverage_status).startsWith('partial')&&row.source.source_type!=='official-event-window')
  assert(['partial','source','setup'].includes(row.state),row.source.id);
}
""")


if __name__ == '__main__':
    unittest.main()
