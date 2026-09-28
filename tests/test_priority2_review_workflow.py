"""The Review Today catalog index and bulk exception report share the full inventory."""

import json
import subprocess
import unittest
from pathlib import Path

from scripts.report_priority2_exceptions import cohorts


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
INVENTORY = json.loads((ROOT / "data" / "priority2-coverage-inventory.json").read_text())


class Priority2ReviewWorkflowTests(unittest.TestCase):
    def test_bulk_report_covers_exceptions_without_multiplying_identity_total(self):
        groups = cohorts(INVENTORY)
        soccer_gaps = next(g for g in groups if (g["kind"], g["state"], g["sport"]) == ("coverage", "ADAPTER_GAP", "Soccer"))
        self.assertEqual(185, soccer_gaps["count"])
        self.assertEqual(185, len(set(soccer_gaps["identity_keys"])))
        self.assertEqual(61, next(g["count"] for g in groups if (g["kind"], g["state"], g["sport"]) == ("season", "PARTIAL_WINDOW", "Soccer")))
        self.assertEqual(731, len(INVENTORY["identities"]))

    def test_catalog_stays_in_its_own_tab(self):
        today = HTML[HTML.index('<section class="panel active" id="today"'):HTML.index('<section class="panel" id="catalog"')]
        self.assertNotIn('todayCatalogSearch', today)
        self.assertNotIn('Full Catalog Coverage', today)
        self.assertIn('id="catalogHealth"', HTML)
        self.assertIn('id="catalogSearch"', HTML)
        self.assertNotIn('renderCatalogCoverageIndex', HTML)
        today_render = HTML[HTML.index('function renderToday()'):HTML.index('function collegeReg(')]
        self.assertNotIn('OK · NO REVIEW', today_render)
        self.assertNotIn('coverage index', today_render.lower())
        self.assertIn("document.getElementById('todayDays').innerHTML=TODAY_MODEL.sportBoard;", today_render)
        self.assertIn('${dayEvents.length} scheduled', today_render)

    def test_stale_tennis_calendars_make_one_issue_and_label_cards(self):
        start = HTML.index("function staleScheduleSourceAttention(")
        end = HTML.index("\nfunction buildTodayModel(", start)
        script = """
const assert=require('node:assert/strict');
const DATA={tennis:{generated_at:'2026-09-16T11:31:56Z'}};
""" + HTML[start:end] + """
const events=Array.from({length:27},(_,i)=>({sport:'Tennis',
  source_id:`tennis-source-${i%5}`,source_stale:true}));
events.push({sport:'Motorsports',source_id:'other',source_stale:true});
const cards=staleScheduleSourceAttention(events,'2026-09-27');
assert.equal(cards.length,1);
assert.equal(cards[0].type,'STALE SCHEDULE SOURCE');
assert.match(cards[0].event,/5 stale feeds · 27 affected tournament cards/);
assert.match(cards[0].reason,/2026-09-16/);
assert.equal(staleScheduleSourceAttention([],'2026-09-27').length,0);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)
        today_render = HTML[HTML.index('function renderUpcomingSportBoard('):HTML.index('function collegeReg(')]
        self.assertEqual(2, today_render.count("e.source_stale?' · STALE SOURCE — VERIFY':''") +
                         today_render.count("event.source_stale?' · STALE SOURCE — VERIFY':''"))
        workflow = (ROOT / ".github/workflows/refresh-tennis-intelligence.yml").read_text()
        self.assertIn('cron: "11 11 * * *"', workflow)

    def test_past_due_ncaa_futures_alert_occurs_once(self):
        start = HTML.index("function collegeFuturesAttention(")
        end = HTML.index("\nfunction renderCollege(", start)
        script = """
const assert=require('node:assert/strict');
const DATA={collegeFutures:{programs:[{school:'Nebraska',sport:'Football',
  regular_season_futures:{days_to_cutoff:-1},
  first_regular_season_contest:{date:'2026-09-25',time:'12:00',opponent:'Visitor'}}]}};
function todayKey(){return '2026-09-26'}
function ctKey(value){return value.slice(0,10)}
function prettyDay(value){return value}
""" + HTML[start:end] + """
assert.equal(collegeFuturesAttention('2026-09-26').length,1);
for(const day of ['2026-09-27','2026-09-28','2026-09-29'])
  assert.equal(collegeFuturesAttention(day).length,0);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_three_review_views_defer_queue_and_keep_collapse_state(self):
        start = HTML.index("let TODAY_MODEL=null;")
        end = HTML.index("\nfunction collegeReg(", start)
        script = """
const assert=require('node:assert/strict');
const DATA={basketball:{},basketballIntel:{},tennisReview:{summary:{}}};
let TODAY_VIEW='date';
const elements=new Map();
const element=id=>elements.get(id)||elements.set(id,{innerHTML:'',textContent:'',hidden:false,
  dataset:{},classList:{add(){},remove(){}},setAttribute(){},value:''}).get(id);
const buttons=['attention','date','sport'].map(todayView=>({dataset:{todayView},
  classList:{toggle(){}},setAttribute(){},textContent:''}));
const document={getElementById:element,querySelector(){return buttons[0]},querySelectorAll(){return buttons}};
let builds=0,dayCalls=0,queueCalls=0,sportCalls=0;
function buildTodayModel(){builds++;return{global:{},start:'2026-09-26',end:'2026-10-03',events:[],pqCards:[],
  coverageAlerts:[],red:1,amber:2,dayCards:new Map(),windowCards:null,queueRendered:false,dateHtml:null,sportBoard:null}}
function todayKey(){return '2026-09-26'}
function addDays(_,i){return `2026-09-${String(26+i).padStart(2,'0')}`}
function attentionCardsForDay(){dayCalls++;return[]}
function renderIssueBoard(){queueCalls++;return'issue-board'}
function renderUpcomingSportBoard(){sportCalls++;return'sport-board'}
function fmtDateTime(){return''}
function esc(value){return String(value)}
function prettyDay(value){return value}
function regionLeagueLabel(value){return value}
""" + HTML[start:end] + """
renderToday();
assert.equal(builds,1);
assert.equal(queueCalls,0);
assert.equal(element('todayAlerts').hidden,true);
TODAY_VIEW='sport';renderToday();
assert.equal(builds,1);
assert.equal(sportCalls,1);
assert.equal(element('todayDays').innerHTML,'sport-board');
assert.equal(queueCalls,0);
TODAY_VIEW='attention';renderToday();
assert.equal(queueCalls,1);
assert.equal(element('todayAlerts').hidden,false);
assert.equal(element('todayAlerts').open,true);
element('todayAlerts').open=false;
TODAY_VIEW='date';renderToday();
TODAY_VIEW='attention';renderToday();
assert.equal(queueCalls,1);
assert.equal(builds,1);
assert.equal(element('todayAlerts').open,false);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_ncaa_basketball_attention_uses_one_sport_group(self):
        helper = HTML[HTML.index("function normCollegeSport("):HTML.index("function isNonWageredNcaaSport(")]
        board = HTML[HTML.index("function renderIssueBoard("):HTML.index("function renderUpcomingSportBoard(")]
        script = """
const assert=require('node:assert/strict');
function reviewLeagueLabel(_,label){return label}
function regionForAttentionCard(){return 'United States'}
function pill(_,label){return label}
function esc(value){return String(value)}
function regionLeagueLabel(region,league){return `${region} — ${league}`}
function esportsGameLabel(){return ''}
function ctKey(value){return String(value).slice(0,10)}
function prettyDay(value){return value}
function eventTime(){return '12:00'}
""" + helper + board + """
const cards=[
  {sport:"Men's Basketball",school:'Nebraska',league:'NCAA Men',severity:'AMBER',event:'Men'},
  {sport:"Women's Basketball",type:'NEBRASKA COLLEGIATE',league:'NCAA Women',severity:'AMBER',event:'Women'},
  {sport:'NCAA Basketball',league:'NCAA Division II',severity:'AMBER',event:'DII'},
  {sport:'Basketball',league:'WNBA',severity:'AMBER',event:'Pro'}
];
const html=renderIssueBoard(cards,[]);
assert.equal((html.match(/class="issue-sport-name">NCAA Basketball/g)||[]).length,1);
assert.equal((html.match(/class="issue-sport-name">Basketball/g)||[]).length,1);
assert.doesNotMatch(html,/class="issue-sport-name">(?:Men's|Women's) Basketball/);
assert.match(html,/NCAA Men/);
assert.match(html,/NCAA Women/);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
