"""Institution identities, not shared mascots or host cities, anchor restrictions."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text()
def function(name):
    start=HTML.index('function '+name+'(')
    return HTML[start:HTML.index('\nfunction ',start+1)]

class CollegiateIdentityTests(unittest.TestCase):
    def test_institution_participants_and_collegiate_scope(self):
        script="""
const assert=require('node:assert/strict');
const CT='America/Chicago';
"""+'\n'.join(function(n) for n in ['ctKey','normCollegeSport','collegeAliases','collegeTeamKey','collegeGender','matchesCollegeEvent'])+"""
const college=(school='Omaha',sport="Women's Volleyball")=>({school,sport,date:'2026-10-24',location:'Omaha, Neb. / Baxter Arena'});
const event=(name,extra={})=>({name,sport:'NCAA Volleyball',league:'NCAA Volleyball',start_time:'2026-10-24T18:00Z',...extra});
assert.equal(matchesCollegeEvent(event('North Alabama Lions at UT Arlington Mavericks'),college()),false);
assert.equal(matchesCollegeEvent(event('Dallas Mavericks at Houston Rockets',{sport:'Basketball',league:'NBA'}),college('Omaha',"Men's Basketball")),false);
assert.equal(matchesCollegeEvent(event('Omaha Mavericks at Houston Rockets',{sport:'Basketball',league:'NBA'}),college('Omaha',"Men's Basketball")),false);
for(const name of ['Mavericks at Other Team','Bluejays at Other Team','Huskers at Other Team','UNO at Other Team','Nebraska Wesleyan at Other Team','Nebraska Kearney at Other Team']) {
 for(const school of ['Omaha','Nebraska','Creighton']) assert.equal(matchesCollegeEvent(event(name),college(school)),false,name+' / '+school);
}
assert.equal(matchesCollegeEvent(event('UConn Huskies at Creighton Bluejays',{location:'Omaha, Nebraska'}),college()),false);
assert.equal(matchesCollegeEvent(event('UConn Huskies at Creighton Bluejays',{location:'Omaha, Nebraska'}),college('Nebraska')),false);
for(const [school,name] of [['Omaha','North Dakota Fighting Hawks at Omaha Mavericks'],['Nebraska','UCLA Bruins at Nebraska Cornhuskers'],['Creighton','UConn Huskies at Creighton Bluejays']]) assert.equal(matchesCollegeEvent(event(name),college(school)),true);
assert.equal(matchesCollegeEvent(event('Omaha at St. Thomas',{sport:'NCAA Soccer',league:'Division I Soccer | Men'}),college('Omaha',"Women's Soccer")),false);
assert.equal(matchesCollegeEvent(event('Omaha at St. Thomas',{sport:'NCAA Soccer',league:'Division I Soccer | Women'}),college('Omaha',"Women's Soccer")),true);
assert.equal(matchesCollegeEvent(event('Omaha Mavericks at Other Team',{sport:'NCAA Beach Volleyball'}),college()),false);
assert.equal(matchesCollegeEvent(event('Omaha Mavericks at Other Team',{gender:'Men'}),college()),false);
assert.equal(matchesCollegeEvent(event('Omaha Mavericks at Other Team',{start_time:'2026-10-25T18:00Z'}),college()),false);
assert.equal(matchesCollegeEvent(event('Other Team at Omaha Mavericks',{source_endpoint:'https://example.org/mens-college-volleyball/scoreboard'}),college()),false);
"""
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)

    def test_published_screenshot_collisions_and_real_restrictions(self):
        script="""
const assert=require('node:assert/strict');
const CT='America/Chicago';
// Frozen public-name reproductions, independent of rolling feed dates.
const globals=[{"name": "Dallas Mavericks at Houston Rockets", "sport": "Basketball", "league": "NBA", "start_time": "2026-10-22T00:30Z", "source_id": "nba", "location": "Toyota Center (Houston) · Houston, TX"}, {"name": "Providence Friars at Creighton Bluejays", "sport": "NCAA Volleyball", "league": "NCAA Volleyball", "start_time": "2026-10-23T23:00Z", "source_id": "ncaa-volleyball", "location": "D.J. Sokol Arena · Omaha, Nebraska"}, {"name": "North Alabama Lions at UT Arlington Mavericks", "sport": "NCAA Volleyball", "league": "NCAA Volleyball", "start_time": "2026-10-24T18:00Z", "source_id": "ncaa-volleyball", "location": "College Park Center · Arlington, Texas"}, {"name": "North Dakota Fighting Hawks at Omaha Mavericks", "sport": "NCAA Volleyball", "league": "NCAA Volleyball", "start_time": "2026-10-24T18:00Z", "source_id": "ncaa-volleyball", "location": "Baxter Arena · Omaha, Nebraska"}, {"name": "USC Trojans at Nebraska Cornhuskers", "sport": "NCAA Volleyball", "league": "NCAA Volleyball", "start_time": "2026-10-25T01:00Z", "source_id": "ncaa-volleyball", "location": "Bob Devaney Center · Lincoln, Nebraska"}];
const colleges=[{"school": "Creighton", "sport": "Women's Soccer", "date": "2026-10-21", "opponent": "Connecticut", "location": "Omaha, Neb. (Morrison Stadium)", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Omaha", "sport": "Women's Basketball", "date": "2026-10-21", "opponent": "Concordia (Neb.)", "location": "Omaha, Neb. / Sapp Fieldhouse", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Nebraska", "sport": "Swimming & Diving", "date": "2026-10-23", "opponent": "Minnesota", "location": "Vermillion, S.D. / The Natatorium", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Nebraska", "sport": "Swimming & Diving", "date": "2026-10-23", "opponent": "South Dakota", "location": "Vermillion, S.D. / The Natatorium", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Creighton", "sport": "Volleyball", "date": "2026-10-23", "opponent": "Providence", "location": "Omaha, Neb. (Wayne and Eileen Ryan Athletic Center and D.J. Sokol Arena)", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Nebraska", "sport": "Women's Basketball", "date": "2026-10-23", "opponent": "Wayne State", "location": "Pinnacle Bank Arena", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Omaha", "sport": "Hockey", "date": "2026-10-23", "opponent": "Lindenwood", "location": "St. Charles, MO", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Creighton", "sport": "Men's Basketball", "date": "2026-10-23", "opponent": "Minnesota", "location": "Omaha, Neb. (CHI Health Center Omaha)", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Nebraska", "sport": "Women's Tennis", "date": "2026-10-23", "opponent": "TCU Jae Foundation Battle of the Boot", "location": "Fort Worth, Texas", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Omaha", "sport": "Men's Tennis", "date": "2026-10-23", "opponent": "MAC Indoor Championship", "location": "Muncie, IN", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Omaha", "sport": "Volleyball", "date": "2026-10-24", "opponent": "North Dakota", "location": "Omaha, Neb. / Baxter Arena", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Omaha", "sport": "Men's Soccer", "date": "2026-10-24", "opponent": "St. Thomas", "location": "St. Paul, Minn.", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Omaha", "sport": "Women's Soccer", "date": "2026-10-24", "opponent": "St. Thomas", "location": "St. Paul, Minn.", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Creighton", "sport": "Women's Basketball", "date": "2026-10-24", "opponent": "Missouri", "location": "Overland Park, Kan. (Johnson County CC)", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Omaha", "sport": "Hockey", "date": "2026-10-24", "opponent": "Lindenwood", "location": "St. Charles, MO", "played_in_nebraska": false, "site_test": "OK · OUTSIDE NEBRASKA", "site_color": "green"}, {"school": "Creighton", "sport": "Men's Soccer", "date": "2026-10-24", "opponent": "Butler", "location": "Omaha, Neb. (Morrison Stadium)", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Nebraska", "sport": "Volleyball", "date": "2026-10-24", "opponent": "USC", "location": "Lincoln, Neb. / Bob Devaney Sports Center", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Creighton", "sport": "Women's Tennis", "date": "2026-10-24", "opponent": "Bluejay/Maverick Invite", "location": "Omaha, Neb. (Koch Family Tennis Center)", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}, {"school": "Omaha", "sport": "Women's Tennis", "date": "2026-10-24", "opponent": "Omaha/Creighton Invite", "location": "Omaha, NE / KOCH TENNIS CENTER", "played_in_nebraska": true, "site_test": "NOT PERMISSIBLE", "site_color": "red"}];
const visibleCollegeEvents=()=>colleges.map(c=>({...c}));
const reviewSport=c=>'NCAA '+c.sport;
"""+'\n'.join(function(n) for n in ['ctKey','normCollegeSport','collegeAliases','collegeTeamKey','collegeGender','matchesCollegeEvent','collegeMatchForGlobal','collegeReg','authoritativeCollegeAlerts'])+"""
for(const name of ['Dallas Mavericks at Houston Rockets','North Alabama Lions at UT Arlington Mavericks']) {
 const event=globals.find(e=>e.name===name);assert(event,'regression fixture missing');
 assert.equal(collegeMatchForGlobal(event),null,name);
 assert(!authoritativeCollegeAlerts(ctKey(event.start_time),globals).some(a=>a.event===name));
}
for(const [school,name] of [['Omaha','North Dakota Fighting Hawks at Omaha Mavericks'],['Nebraska','USC Trojans at Nebraska Cornhuskers'],['Creighton','Providence Friars at Creighton Bluejays']]) {
 const event=globals.find(e=>e.name===name);assert(event);
 const matched=collegeMatchForGlobal(event);assert.equal(matched?.school,school);
 assert.equal(collegeReg(matched).c,'red');
 assert(authoritativeCollegeAlerts(ctKey(event.start_time),globals).some(a=>a.event===name&&a.severity==='RED'));
}
const basketball=colleges.find(c=>c.school==='Omaha'&&c.date==='2026-10-21'&&c.sport.includes('Basketball'));
assert(basketball);assert(authoritativeCollegeAlerts('2026-10-21',globals).some(a=>a.event.includes('Omaha')&&a.severity==='RED'),'unmatched authoritative event must remain protected');
const real=globals.find(e=>e.name==='North Dakota Fighting Hawks at Omaha Mavericks');
const original=collegeMatchForGlobal(real);
colleges.push({...original,opponent:'Different opponent',location:'Different venue'});
assert.equal(collegeMatchForGlobal(real),null,'ambiguous college schedule must not enrich global event');
const held=authoritativeCollegeAlerts('2026-10-24',globals);
assert(!held.some(a=>a.event===real.name));
assert(held.some(a=>a.event.includes('Different opponent')&&a.severity==='RED'));
colleges.pop();
const duplicate={...real,name:'Other opponent at Omaha Mavericks'};
assert(!authoritativeCollegeAlerts('2026-10-24',[...globals,duplicate]).some(a=>a.event===real.name||a.event===duplicate.name),'ambiguous global matchups retain standalone authoritative alerts');
"""
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)
