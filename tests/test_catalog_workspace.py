"""Read-only catalog navigation, uncertain seasons, aliases, ages and exact schedule scope."""
import json
import re
import subprocess
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text()
SCRIPT = re.search(r'<script>([\s\S]*)</script>', HTML).group(1).split('// interactions')[0]

class CatalogWorkspaceTests(unittest.TestCase):
    def test_season_timing_distinguishes_exact_upcoming_annual_and_held_dates(self):
        self.js("""
const dated={season_start_date:'2026-10-01',season_end_date:'2026-12-01',last_verified:'2026-09-20'};
assert.equal(C.timing(dated,'2026-11-01').status,'in');assert.equal(C.timing(dated,'2026-11-01').progress,51);
assert.equal(C.timing(dated,'2026-09-29').status,'upcoming');assert.equal(C.timing(dated,'2026-09-29').days,2);
assert.equal(C.timing(dated,'2026-12-02').status,'out');
for(const event of [{season_start:'10-01',season_end:'06-30'}, {...dated,last_verified:null},{...dated,season_hold:true},{...dated,season_window_complete:false},{...dated,season_start_date:'2026-02-30'},{...dated,last_verified:'2027-01-01'},{...dated,nonseasonal:true}]){
 assert.equal(C.timing(event,'2026-11-01').status,'unknown');assert.equal(C.timing(event,'2026-11-01').progress,null);
}
assert.equal(C.timing(dated,'2027-11-01').status,'unknown');
assert.equal(C.timing({season_start_date:'2026-11-01',season_end_date:'2026-11-01',last_verified:'2026-10-01'},'2026-11-01').progress,null);
""")

    def test_season_cards_preserve_division_scope_restrictions_and_escape_text(self):
        self.js("""
todayKey=()=> '2026-11-02';
const row={id:'parent',name:'League <A>',sport:'Basketball',group:{},aliases:[{name:'Alias <A>'}],restrictions:['NO <PROPS>'],event:{coverage_children:[{key:'men',label:'Men',season_start_date:'2026-10-01',season_end_date:'2027-01-01',last_verified:'2026-09-30'},{key:'women',label:'Women',season_window:'March–June',season_start:'03-01',season_end:'06-30'}]}};
assert.equal(catalogSeasonMatches(row,'in'),true);assert.equal(catalogSeasonMatches(row,'unknown'),true);assert.equal(catalogSeasonMatches(row,'upcoming'),false);
const html=catalogSeasonCard(row);assert.match(html,/Men/);assert.match(html,/Women/);assert.match(html,/Typical season window/);
assert.equal((html.match(/role="progressbar"/g)||[]).length,1);
assert.match(html,/NO &lt;PROPS&gt;/);assert.match(html,/League &lt;A&gt;/);assert.match(html,/Alias &lt;A&gt;/);
assert.doesNotMatch(catalogTimingHtml({season_start:'10-01',season_end:'06-30'}),/progressbar/);
""",ui=True)

    def test_reliability_counts_exact_entries_and_keeps_gaps_separate_from_approval(self):
        self.js("""
mappedCatalogEventForScheduleEvent=e=>({key:e.catalog_identity_key});
const rows=[{id:'one',sport:'A',name:'One',event:{key:'one'}},{id:'two',sport:'A',name:'Two',event:{key:'two'}}];
TODAY_MODEL={global:{sources:[]},events:[{id:'a',name:'A',sport:'A',catalog_identity_key:'one',source_stale:true,start_time:'2026-11-02'}, {id:'b',name:'B',sport:'A',catalog_identity_key:'one',observed_at:'2026-11-02T12:00:00Z',start_time:'2026-11-03'}]};
DATA.oddsEvents={collector_state:{halted:true}};
CATALOG_BROWSER.entry='all';CATALOG_BROWSER.date='tomorrow';CATALOG_BROWSER.attention=true;
const html=catalogReliabilityHtml(rows);
assert.match(html,/1 of 2 catalog entries/);assert.match(html,/1 event flagged/);assert.match(html,/provider is paused/);assert.match(html,/Unlisted events may still be taking place/);
CATALOG_BROWSER.entry='two';const empty=catalogReliabilityHtml(rows);
assert.match(empty,/0 of 1 catalog entries/);assert.doesNotMatch(empty,/not approved|No events taking place|fully covered/i);
assert.equal(catalogObservation({observed_at:'invalid'}),null);
assert.equal(catalogObservationLabel({}),'Observation date unavailable');
const options=catalogCompetitionOptions([{id:'x',sport:'Soccer',name:'League <one>',group:{}},{id:'y',sport:'Basketball',name:'NBA',group:{}}],'All sports');
assert.match(options,/<optgroup label="Soccer">/);assert.match(options,/League &lt;one&gt;/);assert.match(options,/<optgroup label="Basketball">/);
assert.match(catalogAliasPreview({name:'National Basketball Association',aliases:[{name:'NBA'}]}),/Also listed as NBA/);
""",ui=True)

    def test_olympics_overview_restores_full_official_program_and_review_groups(self):
        self.js("""
todayKey=()=> '2026-11-02';
const html=catalogOlympicsOverview();
assert.equal(CATALOG_BROWSER.olympicEdition,'summer-2028');
assert.match(html,/Next Games/);assert.match(html,/Los Angeles 2028/);assert.match(html,/French Alps 2030/);
assert.match(html,/Jul 10, 2028/);assert.match(html,/Jul 30, 2028/);
for(const name of DATA.olympicsSummer.disciplines.map(x=>x.name))assert.ok(html.includes(esc(name)),name);
for(const label of ['APPROVED — SCHEDULED','SCHEDULED — NOT APPROVED','SCOPE REVIEW REQUIRED','APPROVED — NOT SCHEDULED'])assert.ok(html.includes(label),label);
const query=catalogOlympicsOverview('Artistic Gymnastics');
assert.match(query,/SCHEDULED — NOT APPROVED/);assert.match(query,/Artistic Gymnastics/);
assert.equal((query.match(/<article class="olympic-program-card/g)||[]).length,1);
assert.match(catalogOlympicsOverview('not-a-real-discipline'),/No matching Olympic disciplines/);
""",ui=True)

    def test_olympics_defaults_to_next_games_and_keeps_pending_dates_explicit(self):
        self.js("""
todayKey=()=> '2029-01-01';
const html=catalogOlympicsOverview();
assert.equal(CATALOG_BROWSER.olympicEdition,'winter-2030');
assert.match(html,/Detailed discipline schedule pending/);
assert.match(html,/Nordic Combined/);assert.match(html,/Not on confirmed program/);
assert.match(html,/SCOPE REVIEW REQUIRED/);
const card=renderOlympicProgramCard({...DATA.olympicsWinter.disciplines[0],approval_status:'approved-scheduled',games_start_date:'2030-02-01',games_end_date:'2030-02-17',schedule_detail_status:'detailed-schedule-pending'});
assert.ok(!card.includes('Feb 1, 2030'));assert.match(card,/Detailed discipline schedule pending/);
""",ui=True)

    def test_new_unmapped_olympic_discipline_requires_review_and_escapes_display(self):
        self.js("""
todayKey=()=> '2026-11-02';
DATA.olympicsSummer.disciplines.push({id:'new-unmapped',name:'New <discipline>'});
const html=catalogOlympicsOverview('New <discipline>');
assert.match(html,/New &lt;discipline&gt;/);assert.ok(!html.includes('New <discipline>'));
assert.match(html,/SCOPE REVIEW REQUIRED/);assert.match(html,/not yet mapped to the catalog/);
""",ui=True)

    def test_board_date_filters_use_central_calendar_and_seven_inclusive_days(self):
        self.js("""
todayKey=()=> '2026-10-31';
const nfl=DATA.seasonMap.sports.find(x=>x.sport==='Football').groups.flatMap(x=>x.events).find(x=>x.source_id==='nfl');
const row={id:nfl.key,sport:'Football',name:nfl.catalog_event,event:nfl};
const event=(id,start_time)=>({id,start_time,sport:'Football',name:id,catalog_identity_key:nfl.key});
TODAY_MODEL={global:{sources:[]},events:[event('today','2026-11-01T03:00:00Z'),event('tomorrow','2026-11-01T07:30:00Z'),event('last','2026-11-06T18:00:00Z'),event('outside','2026-11-07T18:00:00Z'),event('unknown','2026-11-02T12:00:00')]};
assert.deepEqual(catalogBoardRows([row],'today').map(x=>x.event.id),['today']);
assert.deepEqual(catalogBoardRows([row],'tomorrow').map(x=>x.event.id),['tomorrow']);
assert.deepEqual(catalogBoardRows([row],'week').map(x=>x.event.id),['today','tomorrow','last']);
assert.equal(catalogBoardNeedsAttention({}, {restrictions:[]}),false);
assert.equal(catalogBoardNeedsAttention({source_stale:true}, {restrictions:[]}),true);
assert.equal(catalogBoardNeedsAttention({}, {restrictions:['NO FREE FIGHTS']}),true);
assert.equal(catalogBoardNeedsAttention({requires_bout_review:true}, {restrictions:[]}),true);
""",ui=True)

    def test_event_board_uses_exact_identity_and_excludes_reference_windows(self):
        self.js("""
const nfl=DATA.seasonMap.sports.find(x=>x.sport==='Football').groups.flatMap(x=>x.events).find(x=>x.source_id==='nfl');
const row={id:nfl.key,sport:'Football',name:nfl.catalog_event,event:nfl};
const event={id:'one',sport:'Football',name:'A at B',catalog_identity_key:nfl.key,start_time:'2026-11-03T01:00:00Z'};
TODAY_MODEL={global:{sources:[{id:'calendar',source_type:'official-event-window'}]},events:[event,{...event,id:'wrong',catalog_identity_key:'other'},{...event,id:'reference',reference_only:true},{...event,id:'calendar',source_id:'calendar'}]};
assert.deepEqual(catalogBoardRows([row]).map(x=>x.event.id),['one']);
assert.equal(catalogBoardRows([row,{...row}]).length,0);
assert.equal(catalogBoardDate(event),'2026-11-02');
assert.equal(catalogBoardDate({start_time:'2026-11-03T01:00:00'}),'');
assert.match(catalogBoardFlags(event,{restrictions:[]}),/Catalog linked/);
assert.match(catalogBoardFlags({...event,source_stale:true},{restrictions:['NO FREE FIGHTS']}),/Saved schedule/);
""",ui=True)

    def test_november_catalog_preserves_new_approvals_and_bkfc_restriction(self):
        self.js("""
assert.equal(DATA.catalog.menu_version,'11.2.26');
assert.ok(DATA.catalog.restrictions.some(x=>/BKFC.*NO FREE FIGHTS/.test(x.text)));
const rows=C.build({catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:'2026-11-02',role:catalogLineRole});
const afl=rows.find(x=>x.id==='aussie-rules-afl-catalog');
assert.equal(afl.event.coverage_children.length,2);
assert.equal(afl.event.coverage_children[1].source_id,undefined);
assert.equal(rows.find(x=>x.id==='tennis-davis-cup-men').status,'unknown');
const bkfc=rows.find(x=>x.id==='boxing-bkfc');
assert.ok(bkfc.restrictions.includes('NO FREE FIGHTS'));
assert.ok(!bkfc.restrictions.some(x=>/North America/.test(x)));
""",ui=True)

    def test_age_views_live_inside_catalog_without_separate_tab(self):
        self.assertNotIn('data-panel="u18"', HTML)
        self.assertNotIn('<section class="panel" id="u18">', HTML)
        catalog = HTML[HTML.index('<section class="panel active" id="catalog">'):HTML.index('<footer')]
        for key in ['catalogAgeDirectory', 'u18Search', 'u18Groups', 'catalogAgeParking', 'catalogFootballAge', 'catalogBasketballAge']:
            self.assertIn(f'id="{key}"', catalog)

    def test_soccer_and_tennis_age_records_remain_accessible(self):
        self.js("""
const current=catalogBrowserU18();
for(const sport of ['Soccer','Tennis']){
 const records=current.filter(x=>x.sport===sport);assert.ok(records.length>0,sport);
 const html=catalogBrowserSportDetails(sport);
 assert.equal((html.match(/class="registry-athlete"/g)||[]).length,records.length);
 for(const record of records)assert.ok(html.includes(esc(record.athlete)),record.athlete);
}
""",ui=True)

    def test_identity_projection_preserves_all_735_keys_and_child_scope(self):
        self.js("""
const parents=[];
for(const sport of DATA.seasonMap.sports)for(const group of sport.groups||[])for(const event of group.events||[])parents.push({id:event.key,name:event.catalog_event,sport:sport.sport,event,group,aliases:[],restrictions:event.restrictions||[],notes:event.notes||[],kind:'mapped'});
const rows=C.identityRows(parents,DATA.identities,'2026-11-02');
assert.equal(rows.length,735);assert.deepEqual(rows.map(x=>x.id).sort(),DATA.identities.competitions.map(x=>x.identity_key).sort());
const synthetic=C.identityRows([{id:'p',name:'Parent',sport:'Sport',group:{country:'Z'},restrictions:['Parent rule'],notes:[],kind:'mapped',event:{season_start_date:'2026-01-01',coverage_children:[{key:'a',label:'A',restrictions:['A rule']},{key:'b',label:'B'}]}}],{competitions:[{identity_key:'a',aliases:[{name:'Only A'}]},{identity_key:'b',aliases:[{name:'Only B'}]}]},'2026-11-02');
assert.deepEqual(synthetic[0].restrictions,['Parent rule','A rule']);assert.deepEqual(synthetic[1].restrictions,['Parent rule']);
assert.equal(synthetic[0].aliases[0].name,'Only A');assert.equal(synthetic[1].aliases[0].name,'Only B');assert.equal(synthetic[0].event.season_start_date,undefined);
assert.equal(C.matchEvent(synthetic[0],{catalog_identity_key:'b'},{key:'b'}),false);
assert.equal(C.u18Placement({league_mapping:{status:'verified',catalog_identity_key:'b',evidence_url:'https://example.org'}},synthetic).leagueId,'b');
""",ui=True)

    def test_country_hierarchy_and_flags_do_not_invent_national_scope(self):
        self.js("""
const rows=[{id:'b',sport:'Soccer',name:'Beta',group:{country:'Germany',governing_body:'DFB'}},{id:'a',sport:'Soccer',name:'Alpha',group:{country:'Germany',governing_body:'DFB'}},{id:'c',sport:'Soccer',name:'C',group:{country:'Argentina',governing_body:'AFA'}}];
const groups=C.hierarchy(rows);assert.equal(groups[0].country,'Argentina');assert.deepEqual(groups[1].rows.map(x=>x.id),['a','b']);
assert.match(catalogCountryFlag('Germany'),/country-flags.svg#de/);assert.equal(catalogCountryFlag('International'),'');assert.equal(catalogCountryFlag('Europe'),'');
assert.equal(CATALOG_BROWSER.status,'all');
""",ui=True)

    def js(self, body, ui=False):
        pre = "const assert=require('node:assert/strict'),fs=require('node:fs'),C=require('./assets/catalog-workspace.js');\n"
        if ui:
            pre += SCRIPT + "\nconst CatalogWorkspace=C;\n" + (ROOT/'assets/catalog-workspace-view.js').read_text() + "\n"
            pre += "for(const [key,path] of Object.entries(FILES)){try{DATA[key]=JSON.parse(fs.readFileSync(path));}catch{}}\n"
        result = subprocess.run(['node'],input=pre+body,cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)

    def test_exact_dates_survive_missing_empty_failed_or_held_schedule(self):
        self.js("""
const e={key:'a',source_id:'s',season_start_date:'2026-10-01',season_end_date:'2027-03-01'};
for(const sources of [[],[{id:'s',ok:true,events:0}],[{id:'s',ok:false}],[{id:'s',collection_paused:true}]])assert.equal(C.season(e,'2026-11-01',sources),'in');
assert.equal(C.season({...e,season_start_date:'2026-01-01',season_end_date:'2026-03-01'},'2026-11-01'),'out');
""")

    def test_absence_recurring_and_old_dates_are_not_current_season_confirmation(self):
        self.js("""
for(const e of [{},{source_id:'s'},{season_start:'10-01',season_end:'03-01'},{season_start_date:'2025-01-01',season_end_date:'2025-03-01'},{season_status:'in'},{season_start_date:'2026-02-30',season_end_date:'2026-11-02'}])assert.equal(C.season(e,'2026-11-01',[{id:'s',ok:true,events:0}]),'unknown');
assert.equal(C.season({season_start_date:'2026-01-01',season_end_date:'2026-02-01',source_id:'s'},'2026-11-01',[{id:'s',coverage_status:'last-published-event-window'}]),'unknown');
""")

    def test_hold_partial_and_mixed_child_seasons_are_not_collapsed(self):
        self.js("""
const e={season_start_date:'2026-10-01',season_end_date:'2027-03-01'};
for(const key of ['season_hold','nonseasonal'])assert.equal(C.season({...e,[key]:true},'2026-11-01'),'unknown');
assert.equal(C.season({...e,season_window_complete:false},'2026-11-01'),'unknown');
assert.equal(C.season({coverage_children:[e,{season_start_date:'2026-01-01',season_end_date:'2026-03-01'}]},'2026-11-01'),'unknown');
""")

    def test_all_catalog_parents_children_and_original_restrictions_retained(self):
        self.js("""
const input={catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:'2026-11-01',sources:[],notes:catalogSportNotes(DATA.catalog),role:catalogLineRole};
const before=JSON.stringify(input);const rows=C.build(input);
for(const sport of DATA.seasonMap.sports)for(const group of sport.groups||[])for(const e of group.events||[]){
 const row=rows.find(x=>x.id===e.key);assert.ok(row,e.key);assert.equal(row.name,e.catalog_event);assert.deepEqual(row.event.coverage_children,e.coverage_children);for(const rule of e.restrictions||[])assert.ok(row.restrictions.includes(rule));
}
assert.equal(new Set(rows.map(x=>x.id)).size,rows.length);assert.equal(C.filter(rows).length,rows.length);assert.equal(rows.filter(x=>x.sport==='Basketball').length,76);
assert.equal(JSON.stringify(input),before);
const olympic=C.build({catalog:{sections:[{sport:'Olympics',lines:[]}]},seasonMap:{sports:[{sport:'Olympics',editions:[{key:'summer',crosswalk:[{catalog_event:'Cycling',restrictions:['RULE A']},{catalog_event:'Cycling',restrictions:['RULE B']}]}]}]},today:'2026-11-01'});
assert.equal(olympic.length,1);assert.deepEqual(olympic[0].restrictions,['RULE A','RULE B']);
for(const s of DATA.catalog.sections)assert.ok(catalogBrowserSportDetails(s.sport).includes(esc(s.lines[0])));
""",ui=True)

    def test_filters_partition_catalog_and_combine_with_restrictions(self):
        self.js("""
const rows=['in','unknown','out'].flatMap(status=>[true,false].map(restricted=>({id:status+restricted,sport:'A',search:'league alias',status,restrictions:restricted?['NO PROPS']:[]})));
assert.deepEqual(C.counts(rows),{all:6,in:2,unknown:2,out:2});
assert.deepEqual(C.counts(rows,{restricted:true}),{all:3,in:1,unknown:1,out:1});
assert.equal(C.filter(rows,{query:'alias',status:'unknown',restricted:true}).length,1);
assert.equal(C.filter(rows,{query:'absent'}).length,0);assert.equal(C.filter(rows,{status:'all'}).length,6);
""")

    def test_aliases_keep_operator_scope_and_are_searchable(self):
        self.js("""
const rows=C.build({catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:'2026-11-01',role:catalogLineRole});
assert.equal(C.filter(rows,{query:'Liga ARCO'}).some(x=>x.id==='baseball-mx-lmp'),true);
const match=C.filter(rows,{query:'NCAAB'}).find(x=>x.sport==='NCAA Basketball');assert.ok(match);
const alias=match.aliases.find(x=>x.name==='NCAAB');assert.equal(catalogAliasLabel(alias),'FanDuel');assert.match(alias.scope_note,/only in that operator context/);
assert.equal(catalogAliasLabel({name:'A',name_type:'operator'}),'Operator not recorded');
assert.equal(catalogAliasLabel({name:'NHL',name_type:'source label'}),'Source label');
""",ui=True)

    def test_new_unmapped_catalog_entry_remains_visible(self):
        self.js("""
const catalog={sections:[{sport:'Sport',lines:['Existing','New competition']} ]};
const seasonMap={sports:[{sport:'Sport',catalog_snapshot_lines:['Existing'],groups:[{events:[{key:'existing',catalog_event:'Existing'}]}]}]};
const rows=C.build({catalog,seasonMap,today:'2026-11-01'});assert.equal(rows.length,2);assert.equal(rows.find(x=>x.name==='New competition').status,'unknown');
""")

    def test_unmapped_u18_cannot_disappear_or_gain_inferred_affiliation(self):
        self.js("""
const rows=[{id:'atp',sport:'Tennis',name:'ATP',event:{}}];
for(const record of [{sport:'Tennis',league:'ATP'},{sport:'Tennis',catalog_identity_key:'atp'},{sport:'Tennis',league_mapping:{status:'verified',catalog_identity_key:'atp'}},{sport:'Tennis',league_mapping:{status:'pending',catalog_identity_key:'atp',evidence_url:'https://example.org'}}])assert.deepEqual(C.u18Placement(record,rows),{sport:'Tennis',leagueId:null});
const verified={sport:'Tennis',league_mapping:{status:'verified',catalog_identity_key:'atp',evidence_url:'https://example.org'}};assert.deepEqual(C.u18Placement(verified,rows),{sport:'Tennis',leagueId:'atp'});assert.equal(C.u18Placement(verified,[]).sport,'Tennis');
""")

    def test_every_current_athlete_reachable_at_sport_level_with_evidence(self):
        self.js("""
const rows=combinedKnownU18Rows().rows;const before=JSON.stringify(rows);const current=catalogBrowserU18();
assert.equal(current.length,rows.filter(x=>registryAgeSummary(x,todayKey()).status!=='VERIFIED 18+').length);
for(const record of current){const place=C.u18Placement(record,[]);assert.ok(place.sport);const text=catalogBrowserSportDetails(place.sport);assert.ok(text.includes(esc(record.athlete)));assert.match(catalogBrowserAthlete(record),/Last verified:/);}
assert.equal(JSON.stringify(rows),before);
""",ui=True)

    def test_exact_identity_match_and_distinct_children(self):
        self.js("""
const row={id:'one',sport:'A',name:'League',event:{coverage_children:[{key:'one-men'}]}};
assert.ok(C.matchEvent(row,{catalog_identity_key:'one-men'},{key:'one-men'}));
assert.ok(!C.matchEvent(row,{catalog_identity_key:'two'},{key:'two',catalog_event:'League',sport:'B'}));
assert.ok(!C.matchEvent(row,{catalog_identity_key:'two'},{key:'two',catalog_event:'League',sport:'A'}));
assert.ok(!C.matchEvent(row,{}, {key:'two',parent_catalog_event:'League',sport:'A'}));
assert.ok(C.matchEvent(row,{}, {catalog_event:'League',sport:'A'}));
assert.ok(!C.matchEvent(row,{source_id:'shared'},null));
""")

    def test_central_time_dst_and_missing_times(self):
        self.js("""
assert.equal(C.eventDate({start_time:'2026-11-01T06:30:00Z'}).time,'1:30 AM CDT');
assert.equal(C.eventDate({start_time:'2026-11-01T07:30:00Z'}).time,'1:30 AM CST');
assert.equal(C.eventDate({start_time:'2026-03-08T07:30:00Z'}).time,'1:30 AM CST');
assert.equal(C.eventDate({start_time:'2026-03-08T08:30:00Z'}).time,'3:30 AM CDT');
assert.deepEqual(C.eventDate({start_time:'2026-11-01',date_only:true}),{date:'2026-11-01',time:'Time not published'});
assert.equal(C.eventDate({start_time:'2026-11-01T12:00:00'}).time,'Time not published');
assert.equal(C.eventDate({}).time,'Time not published');
""")

    def test_untrusted_display_values_are_escaped(self):
        self.js("""
const html=catalogBrowserAthlete({athlete:'<img src=x onerror=alert(1)>',sport:'Tennis',source_url:'javascript:alert(1)',evidence:'<script>bad</script>',age_evidence:{status:'unknown'}});
assert.ok(!html.includes('<img'));assert.ok(!html.includes('<script>'));assert.ok(!html.includes('href="javascript:'));assert.ok(html.includes('&lt;img'));
""",ui=True)

    def test_existing_functions_are_used_for_real_progress_and_safeguards(self):
        view=(ROOT/'assets/catalog-workspace-view.js').read_text()
        self.assertIn('const seasonBlock=e=>catalogTimingHtml(e)',view)
        self.assertIn('combinedKnownU18Rows()',view)
        self.assertIn('registryAgeSummary(x,todayKey())',view)
        self.assertIn('TODAY_MODEL||buildTodayModel()',view)
        self.assertIn('catalogEntryHealthHtml',view)
        self.assertNotIn('localStorage',view)
        self.assertNotIn('sessionStorage',view)
        self.assertNotIn('fetch(',view)
        self.assertIn('data-panel="college"',HTML)
        self.assertIn('id="collegeFuturesGrid"',HTML)
