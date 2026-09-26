"""Review Today must evaluate each division's coverage independently."""

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def function_source(name):
    start = HTML.index(f"function {name}(")
    end = HTML.find("\nfunction ", start + 1)
    return HTML[start:end if end >= 0 else None]


class ReviewTodayDivisionTests(unittest.TestCase):
    def test_beach_continental_cup_scope_holds_remain_visible_out_of_season(self):
        script = """
const assert=require('node:assert/strict');
const fs=require('node:fs');
const DATA={
  global:JSON.parse(fs.readFileSync('data/global-schedule.json')),
  seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json'))
};
function todayKey(){return '2026-09-26'}
function sourceCatalogMapping(){return null}
"""
        script += "\n".join(function_source(name) for name in (
            "exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
            "mappedSeasonStatus", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const holds=scheduleCoverageAttention('2026-09-26').filter(card=>
  card.sport==='Volleyball' && card.type==='SCOPE/CALENDAR HOLD' &&
  card.league.startsWith('FIVB Beach Volleyball Continental Cup |'));
assert.equal(holds.length,2);
assert(holds.every(card=>/Do not substitute/.test(card.reason)));
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_supercopa_calendar_holds_remain_visible_with_configured_gap_sources(self):
        script = """
const assert=require('node:assert/strict');
const fs=require('node:fs');
const DATA={
  global:JSON.parse(fs.readFileSync('data/global-schedule.json')),
  seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json'))
};
function todayKey(){return '2026-09-26'}
function sourceCatalogMapping(){return null}
"""
        script += "\n".join(function_source(name) for name in (
            "exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
            "mappedSeasonStatus", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const holds=scheduleCoverageAttention('2026-09-26').filter(card=>
  card.sport==='Volleyball'&&card.type==='SCOPE/CALENDAR HOLD'&&card.league.startsWith('Brazilian Supercopa'));
assert.equal(holds.length,2);
assert(holds.some(card=>card.league==='Brazilian Supercopa | Men'&&/October 23/.test(card.reason)));
assert(holds.some(card=>card.league==='Brazilian Supercopa | Women'&&/October 16/.test(card.reason)));
assert(holds.every(card=>card.source_url==='https://cbv.com.br/volei-de-quadra/supercopa'));
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_retired_beach_tour_holds_remain_visible_out_of_season(self):
        script = """
const assert=require('node:assert/strict');
const fs=require('node:fs');
const DATA={
  global:JSON.parse(fs.readFileSync('data/global-schedule.json')),
  seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json'))
};
function todayKey(){return '2026-09-26'}
function sourceCatalogMapping(){return null}
"""
        script += "\n".join(function_source(name) for name in (
            "exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
            "mappedSeasonStatus", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const cards=scheduleCoverageAttention('2026-09-26');
const holds=cards.filter(card=>card.sport==='Volleyball'&&card.type==='SCOPE/CALENDAR HOLD'&&card.league.startsWith('Beach Volleyball World Tour'));
assert.equal(holds.length,4);
assert(holds.some(card=>card.league==='Beach Volleyball World Tour | Men'&&/replaced/.test(card.reason)));
assert(holds.some(card=>card.league==='Beach Volleyball World Tour Championships | Women'&&/Do not substitute/.test(card.reason)));
assert(!cards.some(card=>card.league==='Beach Pro Tour | Women'&&card.type==='SCOPE/CALENDAR HOLD'));
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_ncaa_section_holds_and_fbs_adapter_gap_are_visible(self):
        script = """
const assert=require('node:assert/strict');
const fs=require('node:fs');
const DATA={
  global:JSON.parse(fs.readFileSync('data/global-schedule.json')),
  seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json'))
};
function todayKey(){return '2026-09-26'}
function sourceCatalogMapping(){return null}
"""
        script += "\n".join(function_source(name) for name in (
            "exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
            "mappedSeasonStatus", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const cards=scheduleCoverageAttention('2026-09-26');
const holds=cards.filter(card=>card.sport.startsWith('NCAA ')&&card.type==='SCOPE/CALENDAR HOLD');
assert.equal(holds.length,7);
assert(holds.some(card=>card.league==='Division I Swimming | Women'&&/diving does not inherit approval/.test(card.reason)));
assert(holds.some(card=>card.league==='College Basketball Invitational (CBI) | Men'));
const fbs=cards.find(card=>card.league==='Division I Football Bowl Subdivision (FBS)');
assert(fbs);
assert.equal(fbs.type,'SCHEDULE COVERAGE GAP');
assert.equal(fbs.source_url,'https://www.ncaa.com/scoreboard/football/fbs');
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_partial_fiba_window_stays_visible_without_false_out_of_season_label(self):
        script = """
const assert=require('node:assert/strict');
const DATA={global:{sources:[{
  id:'basketball-fiba-world-cup-men',sport:'Basketball',
  league:'FIBA Basketball World Cup | Men',region:'International',
  coverage_status:'missing',official_schedule_url:'https://www.fiba.basketball/'
}]},seasonMap:{source_mappings:[],catalog_event_mappings:[],sports:[{
  sport:'Basketball',groups:[{country:'International',events:[{
    catalog_event:'FIBA Basketball World Cup | Men and Women',
    coverage_children:[{
      label:'FIBA Basketball World Cup | Men',source_id:'basketball-fiba-world-cup-men',
      season_start_date:'2027-08-27',season_end_date:'2027-09-12',
      season_window_complete:false
    }]
  }]}]
}]}};
function todayKey(){return '2026-09-24'}
function sourceCatalogMapping(){return null}
"""
        script += "\n".join(function_source(name) for name in (
            "exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
            "mappedSeasonStatus", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const child=DATA.seasonMap.sports[0].groups[0].events[0].coverage_children[0];
assert.equal(mappedSeasonStatus(child),null);
assert.equal(mappedSeasonStatus({...child,season_window_complete:true}),'out');
const cards=scheduleCoverageAttention('2026-09-24');
assert.equal(cards.length,1);
assert.match(cards[0].reason,/partial season calendar/);
assert.equal(cards[0].source_url,'https://www.fiba.basketball/');
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_chile_league_and_cup_render_as_distinct_coverage_warnings(self):
        script = """
const assert=require('node:assert/strict');
const DATA={global:{sources:[
  {id:'chile-lnb',sport:'Basketball',league:'Liga Nacional de Basquetbol de Chile (LNB)',region:'Chile',coverage_status:'missing'},
  {id:'chile-copa',sport:'Basketball',league:'Copa Chile',region:'Chile',coverage_status:'missing'}
]},seasonMap:{source_mappings:[],catalog_event_mappings:[],sports:[{
  sport:'Basketball',groups:[{country:'Chile',events:[
    {catalog_event:'Liga Nacional de Basquetbol de Chile (LNB) | Men',source_id:'chile-lnb',test_status:'in'},
    {catalog_event:'Copa Chile | Men',source_id:'chile-copa',test_status:'in'}
  ]}]
}]}};
function sourceCatalogMapping(){return null}
function mappedSeasonStatus(value){return value.test_status}
"""
        script += "\n".join(function_source(name) for name in (
            "eventSourceIds", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const cards=scheduleCoverageAttention('2026-09-24');
assert.deepEqual(cards.map(card=>card.league).sort(),[
  'Copa Chile | Men','Liga Nacional de Basquetbol de Chile (LNB) | Men'
]);
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_pending_fiba_3x3_womens_scope_stays_visible_in_review_today(self):
        script = """
const assert=require('node:assert/strict');
const DATA={global:{sources:[{
  id:'basketball-fiba-3x3-tour-men',sport:'Basketball',
  league:'FIBA 3x3 World Tour | Men',coverage_status:'current-published-events'
}]},seasonMap:{source_mappings:[],catalog_event_mappings:[],sports:[{
  sport:'Basketball',groups:[{country:'International',events:[{
    catalog_event:'FIBA 3x3 World Tour | Men and Women',coverage_children:[
      {label:'FIBA 3x3 World Tour | Men',source_id:'basketball-fiba-3x3-tour-men',test_status:'in'},
      {label:'FIBA 3x3 World Tour | Women',test_status:null}
    ]
  }]}]
}]}};
function sourceCatalogMapping(){return null}
function mappedSeasonStatus(value){return value.test_status}
"""
        script += "\n".join(function_source(name) for name in (
            "eventSourceIds", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const cards=scheduleCoverageAttention('2026-09-25');
assert.equal(cards.length,1);
assert.equal(cards[0].league,'FIBA 3x3 World Tour | Women');
assert.equal(cards[0].type,'SEASON COVERAGE GAP');
assert.match(cards[0].reason,/no verified current season dates/);
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_mixed_parent_does_not_hide_womens_coverage(self):
        script = """
const assert=require('node:assert/strict');
const DATA={
  global:{sources:[{
    id:'women-fixture',sport:'Soccer',league:'Serie A | Women',
    region:'Italy',coverage_status:'missing',
    official_schedule_url:'https://example.org/women/schedule'
  }]},
  seasonMap:{source_mappings:[],catalog_event_mappings:[],sports:[
    {sport:'Soccer',groups:[{country:'Italy',governing_body:'FIGC',events:[{
      catalog_event:'Serie A | Men and Women',test_status:'mixed',
      coverage_children:[
        {label:'Serie A | Men',source_id:'men-fixture',test_status:'out'},
        {label:'Serie A | Women',source_id:'women-fixture',test_status:'in'}
      ]
    }]}]},
    {sport:'Basketball',groups:[{country:'International',events:[{
      catalog_event:'Cup | Men and Women',test_status:'mixed',
      coverage_children:[
        {label:'Cup | Men',test_status:'out'},
        {label:'Cup | Women',test_status:'in'}
      ]
    }]}]}
  ]}
};
function sourceCatalogMapping(){return null}
function mappedSeasonStatus(value){return value.test_status}
"""
        script += "\n".join(function_source(name) for name in (
            "eventSourceIds", "mappedCatalogEventForSource",
            "uncoveredMappedEvents", "scheduleCoverageAttention",
        ))
        script += """
const mapped=mappedCatalogEventForSource('women-fixture');
assert.equal(mapped.catalog_event,'Serie A | Women');
assert.equal(mappedSeasonStatus(mapped),'in');
const cards=scheduleCoverageAttention('2026-09-26');
assert(cards.some(card=>card.league==='Serie A | Women' &&
  card.source_url==='https://example.org/women/schedule'));
assert(cards.some(card=>card.league==='Cup | Women'));
assert(!cards.some(card=>card.league==='Serie A | Men'));
assert(!cards.some(card=>card.league==='Cup | Men'));
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


if __name__ == "__main__":
    unittest.main()
