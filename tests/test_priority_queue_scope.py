"""Priority queue uses catalog categories and one authoritative collegiate alert."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text()

def function_source(name):
    start = HTML.index(f"function {name}(")
    end = HTML.find("\nfunction ", start + 1)
    return HTML[start:end if end >= 0 else None]

class PriorityQueueTests(unittest.TestCase):
    def test_catalog_categories_and_queue_scope(self):
        script = """
const assert=require('node:assert/strict');
const CT='America/Chicago';
const mappedCatalogEventForScheduleEvent=item=>item.source_id==='college-football'?{sport:'NCAA Football'}:null;
""" + "\n".join(function_source(n) for n in (
            "ctKey", "eventTime", "normCollegeSport", "reviewSport",
            "isNonWageredNcaaSport", "priorityQueueIncludes")) + """
for(const item of [
  {sport:'Football',league:'NCAA Football'},
  {sport:'Football',league:'Nebraska Collegiate'},
  {sport:'NCAA Football'},
  {sport:'Football',source_id:'college-football'}
])assert.equal(reviewSport(item),'NCAA Football');
assert.equal(reviewSport({sport:'Football',league:'NFL'}),'Football');
assert.equal(reviewSport({sport:"Women's Baseball",school:'Nebraska'}),'NCAA Baseball');
for(const item of [
  {sport:'NCAA Soccer',type:'SCHEDULE COVERAGE GAP'},
  {sport:"Women's Soccer",league:'NCAA Division I Soccer | Women'},
  {sport:'Soccer',school:'Nebraska'}
])assert.equal(priorityQueueIncludes(item),false);
assert.equal(priorityQueueIncludes({sport:'Soccer',league:'Premier League'}),true);
assert.equal(isNonWageredNcaaSport({sport:'Soccer',school:'Nebraska'}),false);
assert.equal(ctKey('2026-10-12'),'2026-10-12');
assert.equal(eventTime('2026-10-12'),'DATE ONLY');
"""
        subprocess.run(["node","-e",script],cwd=ROOT,check=True)

    def test_authoritative_alert_replaces_only_its_source_duplicate(self):
        script = """
const assert=require('node:assert/strict');
const CT='America/Chicago';
const event={school:'Nebraska',sport:'Baseball',date:'2026-10-12',opponent:'Red-White Series: Game 1'};
const visibleCollegeEvents=()=>[event];
const collegeReg=()=>({c:'red'});
const authoritativeCollegeAlerts=()=>[{severity:'RED',sport:'NCAA Baseball',
  event:'Nebraska Baseball vs. Red-White Series: Game 1',start_time:event.date}];
const basketballIntelligenceAlerts=()=>[];
const collegeFuturesAttention=()=>[];
const boxingReviewAlerts=()=>[];
const combatBoutReviewAlerts=()=>[];
const tennisIntelligenceAlerts=()=>[];
const sameAlert=(a,b)=>a.event===b.event;
""" + "\n".join(function_source(n) for n in (
            "ctKey", "normCollegeSport", "reviewSport", "isNonWageredNcaaSport",
            "priorityQueueIncludes", "authoritativeCollegePriorityKey", "attentionCardsForDay")) + """
const pq=[
 {key:authoritativeCollegePriorityKey(event),type:'NOT PERMISSIBLE',sport:'Baseball',league:'Nebraska Collegiate',start_time:event.date,event:'Nebraska vs Red-White Series: Game 1'},
 {key:'other-age-risk',sport:'NCAA Baseball',type:'U18 EXPOSURE',start_time:event.date,event:'Another event'},
 {key:'unmatched-source',sport:'NCAA Baseball',start_time:event.date,event:'Unmatched event'},
 {sport:'NCAA Soccer',start_time:event.date,event:'Soccer'}
];
const cards=attentionCardsForDay(event.date,[],pq);
assert.equal(cards.length,3);
assert.equal(cards.filter(c=>c.event.includes('Red-White')).length,1);
assert(cards.some(c=>c.type==='U18 EXPOSURE'));
assert(cards.some(c=>c.key==='unmatched-source'));
"""
        subprocess.run(["node","-e",script],cwd=ROOT,check=True)

    def test_metrics_count_final_queue(self):
        script = """
const assert=require('node:assert/strict');
const DATA={};
const todayKey=()=> '2026-10-05';
const addDays=(day,n)=>'2026-10-'+String(5+n).padStart(2,'0');
const basketballReviewEvents=()=>[];
const attentionCardsForDay=day=>day==='2026-10-05'?[{severity:'RED'}]:[];
const scheduleCoverageAttention=()=>[{severity:'AMBER',sport:'Soccer'},{severity:'AMBER',sport:'NCAA Soccer'}];
const staleScheduleSourceAttention=()=>[];
const failedScheduleSourceAttention=()=>[];
const heldMatchupAttention=()=>[];
const heldAgeReviewAttention=()=>[];
const priorityQueueIncludes=c=>c.sport!=='NCAA Soccer';
""" + function_source("buildTodayModel").split("let TODAY_MODEL")[0] + """
const model=buildTodayModel();
assert.equal(model.red,1);
assert.equal(model.amber,1);
assert.equal(model.windowCards.length,2);
assert.equal(model.dayCards.size,8);
"""
        subprocess.run(["node","-e",script],cwd=ROOT,check=True)
