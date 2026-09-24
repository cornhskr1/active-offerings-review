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

class ReviewTodayDivisionTests(unittest.TestCase):
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
