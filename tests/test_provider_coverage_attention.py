"""One active shared provider gap should create one review issue, not one per identity."""

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProviderCoverageAttentionTests(unittest.TestCase):
    def test_coverage_issue_is_not_presented_as_scheduled_noon_event(self):
        html = (ROOT / "index.html").read_text()
        start = html.index("function renderIssueBoard(")
        end = html.index("\nfunction renderUpcomingSportBoard(", start)
        script = """
const assert=require('node:assert/strict');
const pill=(_,label)=>label;
const esc=value=>String(value??'');
const reviewLeagueLabel=(_,league)=>league;
const regionForAttentionCard=card=>card.region;
const regionLeagueLabel=(_,league)=>league;
const esportsGameLabel=()=>'';
const prettyDay=()=>{throw Error('coverage gap has no fixture date')};
const eventTime=()=>{throw Error('coverage gap has no fixture time')};
const ctKey=()=>{throw Error('coverage gap has no fixture date')};
""" + html[start:end] + """
const htmlOut=renderIssueBoard([{severity:'AMBER',type:'SCHEDULE COVERAGE GAP',
  sport:'Rugby',league:'New Zealand Rugby competitions',region:'New Zealand',
  event:'3 approved competitions · shared fixture feed gap',
  start_time:'2026-09-26T12:00:00-05:00',reason:'No dependable feed'}],[]);
assert.match(htmlOut,/1 coverage issue/);
assert.doesNotMatch(htmlOut,/1 event|12:00/);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_nz_rugby_three_current_gaps_are_one_issue(self):
        html = (ROOT / "index.html").read_text()
        names = ("exactSeasonStatus", "annualSeasonStatus", "eventSourceIds",
                 "mappedSeasonStatus", "groupedActiveCoverageGaps")
        functions = []
        for name in names:
            start = html.index(f"function {name}(")
            end = html.find("\nfunction ", start + 1)
            functions.append(html[start:end if end >= 0 else None])
        script = """
const assert=require('node:assert/strict');
const fs=require('node:fs');
const DATA={seasonMap:JSON.parse(fs.readFileSync('data/catalog-season-map.json')),
  coverage:JSON.parse(fs.readFileSync('data/priority2-coverage-inventory.json')),
  global:JSON.parse(fs.readFileSync('data/global-schedule.json'))};
function todayKey(){return '2026-09-26'}
function isNonWageredNcaaSport(){return false}
""" + "\n".join(functions) + """
const cards=groupedActiveCoverageGaps('2026-09-26');
const nz=cards.filter(card=>card.league==='New Zealand Rugby competitions');
assert.equal(nz.length,1);
assert.match(nz[0].event,/3 approved competitions/);
for(const name of ['National Provincial Championship','Heartland Championship','Farah Palmer Cup'])
  assert(nz[0].reason.includes(name));
assert(cards.length<10,'current shared gaps must remain a small provider-level queue');
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_active_shared_gaps_group_and_inactive_or_single_sources_do_not(self):
        html = (ROOT / "index.html").read_text()
        start = html.index("function groupedActiveCoverageGaps(")
        end = html.index("\nfunction scheduleCoverageAttention(", start)
        script = """
const assert=require('node:assert/strict');
const source=(id,coverage_status)=>({id,source_type:'coverage-gap',sport:'Rugby',
  league:id,region:'New Zealand',official_schedule_url:'https://www.provincial.rugby/',coverage_status});
const DATA={global:{sources:[source('rugby-nzr'),source('rugby-other'),source('already-alerted','missing')]},
  seasonMap:{sports:[{groups:[{events:[
    {key:'npc',season_status:'in'}, {key:'heartland',season_status:'in'},
    {key:'fpc',season_status:'out'}, {key:'single',season_status:'in'},
    {key:'already-one',season_status:'in'}, {key:'already-two',season_status:'in'}
  ]}]}]},coverage:{identities:[
    {identity_key:'npc',sport:'Rugby',league:'NPC',coverage_state:'ADAPTER_GAP',sources:[{id:'rugby-nzr',type:'coverage-gap'}]},
    {identity_key:'heartland',sport:'Rugby',league:'Heartland',coverage_state:'ADAPTER_GAP',sources:[{id:'rugby-nzr',type:'coverage-gap'}]},
    {identity_key:'fpc',sport:'Rugby',league:'FPC',coverage_state:'ADAPTER_GAP',sources:[{id:'rugby-nzr',type:'coverage-gap'}]},
    {identity_key:'single',sport:'Rugby',league:'Single',coverage_state:'ADAPTER_GAP',sources:[{id:'rugby-other',type:'coverage-gap'}]},
    {identity_key:'already-one',sport:'Rugby',league:'One',coverage_state:'ADAPTER_GAP',sources:[{id:'already-alerted',type:'coverage-gap'}]},
    {identity_key:'already-two',sport:'Rugby',league:'Two',coverage_state:'ADAPTER_GAP',sources:[{id:'already-alerted',type:'coverage-gap'}]}
  ]}};
function mappedSeasonStatus(event){return event.season_status}
function isNonWageredNcaaSport(){return false}
""" + html[start:end] + """
const cards=groupedActiveCoverageGaps('2026-09-26');
assert.equal(cards.length,1);
assert.equal(cards[0].league,'rugby-nzr');
assert.match(cards[0].event,/2 approved competitions/);
assert.match(cards[0].reason,/NPC; Heartland/);
assert.doesNotMatch(cards[0].reason,/FPC|Single/);
assert.equal(cards[0].start_time,'2026-09-26T12:00:00-05:00');
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
