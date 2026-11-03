"""Saved collegiate location evidence is displayed conservatively without changing the feed."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text()


class CollegeLocationDisplayTests(unittest.TestCase):
    def test_verified_venue_and_red_review_preserve_distinct_states(self):
        rules = HTML[HTML.index("function collegeReg("):HTML.index("\nfunction futuresCurrentState(")]
        render = HTML[HTML.index("function renderCollege(){"):HTML.index("\nfunction restrictionColor(")]
        script = r"""
const assert=require('node:assert/strict');
const event={school:'Nebraska',sport:"Women's Basketball",opponent:'Western Illinois',date:'2026-11-07',time:'2:00 PM CT',location:'Pinnacle Bank Arena',played_in_nebraska:false,site_color:'amber',site_test:'MANUAL LOCATION REVIEW',site:'HOME',source_stale:true,source_url:'https://huskers.com/sports/womens-basketball/schedule'};
const unknown={...event,opponent:'Unknown venue opponent',location:'Memorial Stadium',site:'HOME',source_stale:false};
const away={...event,opponent:'Xavier',location:'Cincinnati, OH',site_color:'green',site_test:'OK · OUTSIDE NEBRASKA',site:'AWAY',source_stale:false};
const events=[event,unknown,away],before=JSON.stringify(events);
const nodes={collegeSchool:{value:'all'},collegeStatus:{value:'all'},collegeSource:{},collegeGrid:{}};
const document={getElementById:id=>nodes[id]},DATA={college:{sources:[]}};
const visibleCollegeEvents=()=>events,renderCollegeFutures=()=>{};
const esc=x=>String(x??''),pill=(color,label)=>'<span class="'+color+'">'+label+'</span>',fmtDateTime=()=>'',prettyDay=x=>x;
""" + rules + render + r"""
assert.equal(collegeReg(event).test,'NOT PERMISSIBLE');
assert.equal(collegeReg(event).c,'red');
assert.equal(collegeReg({...event,location:'  PINNACLE   BANK ARENA '}).c,'red');
assert.match(collegeReg(event).location,/Lincoln, Nebraska/);
assert.equal(collegeReg({...event,location:'Pinnacle Bank Arena Annex'}).c,'amber');
assert.equal(collegeReg({...event,location_conflict_reason:'Conflicting state evidence'}).test,'MANUAL REVIEW');
assert.equal(collegeReg({...unknown,site_color:undefined,site_test:undefined}).c,'amber');
assert.equal(collegeReg({...unknown,location:''}).displayColor,'red');
assert.equal(collegeReg(away).test,'LOCATION CHECK ONLY');
renderCollege();
const cards=[...nodes.collegeGrid.innerHTML.matchAll(/<article[^>]*>[\s\S]*?<\/article>/g)].map(x=>x[0]);
assert.equal(cards.length,3);
const home=cards.find(x=>x.includes('Western Illinois'));
const review=cards.find(x=>x.includes('Unknown venue opponent'));
const outside=cards.find(x=>x.includes('Xavier'));
assert.match(home,/college-card red/);
assert.match(home,/<span class="red">NOT PERMISSIBLE/);
assert.match(home,/Pinnacle Bank Arena · Lincoln, Nebraska/);
assert.match(home,/Verified venue location/);
assert.match(home,/SAVED SOURCE — VERIFY/);
assert.match(review,/college-card red/);
assert.match(review,/<span class="red">MANUAL REVIEW/);
assert.doesNotMatch(review,/NOT PERMISSIBLE/);
assert.match(outside,/college-card green/);
assert.match(nodes.collegeGrid.innerHTML,/1 not permissible · 1 review/);
nodes.collegeStatus.value='amber';renderCollege();
assert.match(nodes.collegeGrid.innerHTML,/Unknown venue opponent/);
assert.doesNotMatch(nodes.collegeGrid.innerHTML,/Western Illinois|Xavier/);
nodes.collegeStatus.value='red';renderCollege();
assert.match(nodes.collegeGrid.innerHTML,/Western Illinois/);
assert.doesNotMatch(nodes.collegeGrid.innerHTML,/Unknown venue opponent|Xavier/);
assert.equal(JSON.stringify(events),before);
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


if __name__ == "__main__":
    unittest.main()
