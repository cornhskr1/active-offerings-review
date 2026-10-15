"""Reviewed age evidence supersedes historic U18 labels without deleting history."""
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text()


def evidence(status="verified_dob", dob="2000-01-01"):
    row = {"status": status, "checked_at": "2026-10-14", "sources": [],
           "review": {"id": "fixture-review"}}
    if status == "verified_dob":
        row["dob"] = dob
    return row


def js_function(name):
    start = HTML.index(f"function {name}(")
    end = HTML.find("\nfunction ", start + 1)
    return HTML[start:end if end >= 0 else None]


class ReviewedAgeConsumerTests(unittest.TestCase):
    def run_script(self, name, inputs, output):
        # Exercise each collector without touching the checkout's published data.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "data").mkdir()
            for script in (name, "athlete_age_evidence.py", "catalog_identity.py"):
                shutil.copy(ROOT / "scripts" / script, root / "scripts" / script)
            for filename, data in inputs.items():
                (root / "data" / filename).write_text(json.dumps(data))
            subprocess.run(["python3", "-B", str(root / "scripts" / name)],
                           cwd=root, check=True, capture_output=True, text=True)
            return json.loads((root / "data" / output).read_text())

    def records(self, sport, team, league):
        year = dt.datetime.now(ZoneInfo("America/Chicago")).year
        base = {"sport": sport, "team": team, "league": league, "status": "VERIFIED U18", "age": 17}
        return [
            {**base, "athlete": "Adult Player", "age_evidence": evidence()},
            {**base, "athlete": "Unknown Player", "age_evidence": evidence("unknown")},
            {**base, "athlete": "Conflict Player", "age_evidence": evidence("conflicting_dob")},
            {**base, "athlete": "Age Only Player", "age_evidence": evidence("age_only")},
            {**base, "athlete": "Birthday Player", "age_evidence": evidence(dob=f"{year-17}-01-01")},
            {**base, "athlete": "Legacy Player"},
        ]

    def test_soccer_queue_requires_verified_u18_on_event_date(self):
        year = dt.datetime.now(ZoneInfo("America/Chicago")).year
        records = self.records("Soccer", "Test FC", "Test League")
        events = [{"id": str(index), "sport": "Soccer", "league": "Test League",
                   "name": "Test FC vs Other FC", "status": "UPCOMING", "start_time": value}
                  for index, value in enumerate((
                      f"{year}-12-31T12:00:00-06:00", f"{year+1}-01-01T12:00:00-06:00",
                      f"{year+1}-01-01T01:00:00Z", "invalid", f"{year}-12-31T23:30:00-12:00"))]
        result = self.run_script("refresh_priority_queue.py", {
            "known-u18.json": {"records": records}, "global-schedule.json": {"events": events}
        }, "priority-queue.json")
        cards = {row["key"]: row for row in result["cards"]}
        self.assertEqual(set(cards["event|0"]["confirmed_u18_athletes"]), {"Birthday Player", "Legacy Player"})
        self.assertEqual(cards["event|1"]["confirmed_u18_athletes"], ["Legacy Player"])
        self.assertEqual(cards["event|2"]["confirmed_u18_athletes"], ["Legacy Player"])
        self.assertEqual(cards["event|3"]["confirmed_u18_athletes"], ["Legacy Player"])
        self.assertEqual(set(cards["event|4"]["confirmed_u18_athletes"]), {"Birthday Player", "Legacy Player"})
        for index in (0, 1, 2, 4):
            self.assertNotIn("Adult Player", cards[f"event|{index}"]["athletes"])
            self.assertEqual(set(cards[f"event|{index}"]["age_review_athletes"]),
                             {"Unknown Player", "Conflict Player", "Age Only Player"})
        self.assertTrue(cards["event|3"]["event_date_missing"])
        self.assertIn("Birthday Player", cards["event|3"]["age_review_athletes"])

    def test_soccer_uncertainty_and_missing_event_date_are_amber(self):
        base = {"sport": "Soccer", "team": "Test FC", "league": "Test League", "status": "VERIFIED U18"}
        for value, age_evidence in (("2026-10-14", evidence("age_only")),
                                    ("2026-10-14", evidence("conflicting_dob")),
                                    ("2026-10-14", evidence("unknown")),
                                    ("invalid", evidence(dob="2009-01-01")),
                                    ("10/14/2026", evidence(dob="2009-01-01")),
                                    (None, evidence(dob="2009-01-01"))):
            with self.subTest(date=value, status=age_evidence["status"]):
                output = self.run_script("refresh_priority_queue.py", {
                    "known-u18.json": {"records": [{**base, "athlete": "Review Player", "age_evidence": age_evidence}]},
                    "global-schedule.json": {"events": [{"id": "review", "sport": "Soccer", "league": "Test League",
                        "name": "Test FC vs Other FC", "status": "UPCOMING", "start_time": value}]}
                }, "priority-queue.json")
                self.assertEqual(len(output["cards"]), 1)
                self.assertEqual(output["cards"][0]["severity"], "AMBER")
                self.assertEqual(output["cards"][0]["type"], "AGE EVIDENCE REVIEW")

    def test_football_uses_reviewed_identity_instead_of_stale_u18_feed(self):
        athlete = 'Ethan "Boobie" Feaster'
        dates = ["2027-05-22T23:30:00-12:00", "2027-05-23T00:30:00Z", "2027-05-24", None, "ambiguous"]
        output = self.run_script("refresh_priority_queue.py", {
            "known-u18.json": {"records": [{"sport": "Football", "team": "USC",
                "athlete": "Ethan “Boobie” Feaster", "age_evidence": evidence(dob="2009-05-23")}]},
            "ncaa-football-data.json": {"known_u18": [{"team": "USC", "athlete": athlete, "age": 17}]},
            "global-schedule.json": {"events": [{"id": str(index), "sport": "Football", "league": "NCAA Football",
                "name": "USC vs Other College", "status": "UPCOMING", "start_time": value}
                for index, value in enumerate(dates)]}
        }, "priority-queue.json")
        cards = {row["key"]: row for row in output["cards"]}
        self.assertEqual(set(cards), {"event|0", "event|3", "event|4"})
        self.assertEqual(cards["event|0"]["severity"], "RED")
        for key in ("event|3", "event|4"):
            self.assertEqual(cards[key]["severity"], "AMBER")
            self.assertTrue(cards[key]["event_date_missing"])
            self.assertEqual(cards[key]["age_review_athletes"], [athlete])

    def test_basketball_cache_corrects_stale_u18_and_preserves_evidence(self):
        records = self.records("Basketball", "Test College", "NCAA Men")
        records[0].update(last_verified="2025-01-02", aliases=["A. Player"], official_player_id="fixture:1")
        old = [{"player_id": str(i), "gender": "Men", "team": "Test College", "athlete": row["athlete"],
                "status": "VERIFIED U18", "dob": "2012-01-01", "verified_at": "2025-02-03"}
               for i, row in enumerate(records)]
        output = self.run_script("refresh_ncaa_basketball_age_cache.py", {
            "known-u18.json": {"records": records},
            "ncaa-basketball-age-cache.json": {"records": old},
            "ncaa-basketball-rosters.json": {"teams": [{"gender": "Men", "team": "Test College",
                "athletes": [{"id": str(i), "name": row["athlete"], "age": 17} for i, row in enumerate(records)]}]}
        }, "ncaa-basketball-age-cache.json")
        rows = {row["athlete"]: row for row in output["records"]}
        adult = rows["Adult Player"]
        self.assertEqual(adult["status"], "VERIFIED 18+")
        self.assertEqual(adult["dob"], "2000-01-01")
        self.assertEqual(adult["age_evidence"], records[0]["age_evidence"])
        self.assertEqual(adult["last_verified"], "2025-01-02")
        self.assertEqual(adult["verified_at"], "2025-02-03")
        self.assertEqual(adult["aliases"], ["A. Player"])
        self.assertEqual(adult["official_player_id"], "fixture:1")
        for name in ("Unknown Player", "Conflict Player", "Age Only Player"):
            self.assertEqual(rows[name]["status"], "TARGETED REVIEW")
            self.assertIsNone(rows[name]["dob"])
            self.assertIsNone(rows[name]["calculated_age"])
            self.assertNotIn("KNOWN U18", rows[name]["priority_reasons"])
        self.assertEqual(rows["Legacy Player"]["status"], "VERIFIED U18")
        self.assertEqual(output["summary"]["age_review"], 3)

    def test_basketball_event_alerts_recheck_birthday(self):
        year = dt.datetime.now(ZoneInfo("America/Chicago")).year
        records = self.records("Basketball", "Test College", "NCAA Men")
        events = [{"id": str(index), "division": "Division I", "gender": "Men", "status": "UPCOMING",
                   "name": "Test College vs Other College", "home": "Test College", "away": "Other College",
                   "start_time": value}
                  for index, value in enumerate((f"{year}-12-31", f"{year+1}-01-01",
                                                 f"{year+1}-01-01T01:00:00Z", "invalid"))]
        output = self.run_script("refresh_ncaa_basketball_intelligence.py", {
            "known-u18.json": {"records": records}, "ncaa-basketball.json": {"events": events},
            "ncaa-basketball-rules.json": {"u18": {"severity": "RED", "staff_action": "Review"}},
            "ncaa-basketball-rosters.json": {"teams": [{"gender": "Men", "team": "Test College",
                "athletes": [{"name": row["athlete"]} for row in records]}]}
        }, "ncaa-basketball-intelligence.json")
        self.assertEqual({row["athlete"] for row in output["verified_u18"]}, {"Birthday Player", "Legacy Player"})
        alerts = {row["event_id"]: row for row in output["active_exposures"]}
        self.assertEqual({row["athlete"] for row in alerts["0"]["athletes"]}, {"Birthday Player", "Legacy Player"})
        self.assertEqual([row["athlete"] for row in alerts["1"]["athletes"]], ["Legacy Player"])
        self.assertEqual([row["athlete"] for row in alerts["2"]["athletes"]], ["Legacy Player"])
        self.assertEqual([row["athlete"] for row in alerts["3"]["athletes"]], ["Legacy Player"])
        reviews = {row["event_id"]: row for row in output["age_reviews"]}
        for index in ("0", "1", "2"):
            self.assertEqual({row["athlete"] for row in reviews[index]["athletes"]},
                             {"Unknown Player", "Conflict Player", "Age Only Player"})
            self.assertEqual(reviews[index]["severity"], "AMBER")
        self.assertTrue(reviews["3"]["event_date_missing"])
        self.assertIn("Birthday Player", {row["athlete"] for row in reviews["3"]["athletes"]})

    def test_public_registry_keeps_history_and_separates_review_dates(self):
        script = """
const assert=require('node:assert/strict');
const todayKey=()=> '2026-10-15';
const DATA={known:{records:[{athlete:'General Adult',sport:'Soccer',age:17,
 age_evidence:{status:'verified_dob',dob:'2000-01-01',checked_at:'2026-10-14'}}]},
 tennisRegistry:{records:[{name:'Historic Player',official_player_id:'itf:123',aliases:['H. Player'],
 last_verified:'2025-01-02',age_evidence:{status:'verified_dob',dob:'2008-10-15',checked_at:'2026-10-14',review:{id:'r'}}}],verified_u18:[]},
 tennisCache:{records:{one:{name:'H. Player',official_player_id:'itf:123',age:17,age_status:'VERIFIED U18'},
 two:{name:'Uncertain Player',age:17,age_status:'VERIFIED U18',age_evidence:{status:'age_only',checked_at:'2026-10-14'}}}}};
const elements={};const document={getElementById:id=>(elements[id]??={innerHTML:'',value:''})};
const esc=value=>String(value??'');const pill=(color,label)=>`<span class="${color}">${label}</span>`;
""" + "\n".join(js_function(name) for name in (
            "registryNameKey", "tennisRegistryIdentity", "registryAgeSummary", "preferredRegistryName",
            "combinedKnownU18Rows", "u18LastVerifiedLabel", "renderU18")) + r"""
const rows=combinedKnownU18Rows().rows;
assert.equal(rows.length,3);
const historic=rows.find(r=>r.official_player_id==='itf:123');
assert.equal(historic.last_verified,'2025-01-02');
assert.equal(historic.age_evidence.checked_at,'2026-10-14');
assert.equal(registryAgeSummary(historic,'2026-10-14').status,'VERIFIED U18');
assert.equal(registryAgeSummary(historic,'2026-10-15').status,'VERIFIED 18+');
assert.equal(registryAgeSummary(rows.find(r=>r.athlete==='Uncertain Player')).age,null);
assert.equal(registryAgeSummary({age_evidence:{status:'verified_dob',dob:'2008-02-30'}}).status,'AGE UNVERIFIED');
const leapBorn={age_evidence:{status:'verified_dob',dob:'2008-02-29'}};
assert.equal(registryAgeSummary(leapBorn,'2026-02-27').status,'VERIFIED U18');
assert.equal(registryAgeSummary(leapBorn,'2026-02-28').status,'BIRTHDAY REVIEW');
assert.equal(registryAgeSummary(leapBorn,'2026-03-01').status,'VERIFIED 18+');
renderU18();
assert.match(elements.u18Groups.innerHTML,/VERIFIED 18\+ · HISTORICAL/);
assert.match(elements.u18Groups.innerHTML,/AGE ONLY/);
assert.match(elements.u18Groups.innerHTML,/Evidence checked: 2026-10-14/);
assert.match(elements.u18Groups.innerHTML,/Last verified: 2025-01-02/);
assert.match(elements.u18RegistryMetrics.innerHTML,/>0<\/b><span>current verified U18/);
elements.u18Search.value='H. Player';renderU18();
assert.match(elements.u18Groups.innerHTML,/Historic Player/);
assert.doesNotMatch(elements.u18Groups.innerHTML,/General Adult/);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_missing_date_reviews_remain_visible_without_inventing_event_date(self):
        script = """
const assert=require('node:assert/strict');
const CT='America/Chicago';const todayKey=()=> '2026-10-15';
const DATA={basketballIntel:{age_reviews:[{event:'Review Game',start_time:null,event_date_missing:true,
 athletes:[{athlete:'Review Player',team:'Test College'}]}]}};
const visibleCollegeEvents=()=>[];const authoritativeCollegeAlerts=()=>[];
const authoritativeCollegePriorityKey=()=>'';
const collegeFuturesAttention=()=>[];const boxingReviewAlerts=()=>[];
const combatBoutReviewAlerts=()=>[];const tennisIntelligenceAlerts=()=>[];
const sameAlert=(a,b)=>a.event===b.event;const priorityQueueIncludes=()=>true;
""" + "\n".join(js_function(name) for name in (
            "ctKey", "basketballIntelligenceAlerts", "attentionCardsForDay")) + """
const basketball=basketballIntelligenceAlerts('2026-10-15');
assert.equal(basketball.length,1);assert.equal(basketball[0].severity,'AMBER');
assert.equal(basketball[0].start_time,null);
const soccer={event:'Soccer review',start_time:'invalid',age_review_required:true,event_date_missing:true,severity:'AMBER'};
const cards=attentionCardsForDay('2026-10-15',[],[soccer]);
assert.equal(cards.length,2);
assert.equal(attentionCardsForDay('2026-10-16',[],[soccer]).length,0);
DATA.basketballIntel.active_exposures=[{event:'Review Game',start_time:'2026-10-15',athletes:[]}];
const mixed=attentionCardsForDay('2026-10-15',[],[]);
assert.equal(mixed.length,2);
assert(mixed.some(card=>card.severity==='RED'));
assert(mixed.some(card=>card.severity==='AMBER'));
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_mixed_red_card_labels_each_uncertain_athlete_review_only(self):
        script = """
const assert=require('node:assert/strict');
const reviewSport=c=>c.sport,reviewLeagueLabel=(c,l)=>l,regionForAttentionCard=()=>'',regionLeagueLabel=(r,l)=>l;
const esc=value=>String(value??''),pill=(color,label)=>`<span>${label}</span>`,esportsGameLabel=()=>'';
const ctKey=value=>String(value||'').slice(0,10),eventTime=()=> '12:00';
const prettyDay=value=>{if(!value)throw new Error('Missing date must not be formatted');return value};
""" + js_function("renderIssueBoard") + r"""
const mixed={sport:'Soccer',league:'Test League',event:'Shared match',severity:'RED',start_time:'2026-10-15',
 athletes:['Confirmed Player','Uncertain Player'],confirmed_u18_athletes:['Confirmed Player'],age_review_athletes:['Uncertain Player']};
const html=renderIssueBoard([mixed],[]);
assert.match(html,/Confirmed Player \(verified U18\)/);
assert.match(html,/Uncertain Player \(age review only\)/);
assert.doesNotMatch(html,/Uncertain Player \(verified U18\)/);
const missing=renderIssueBoard([{...mixed,severity:'AMBER',start_time:null,event_date_missing:true}],[]);
assert.match(missing,/Event date unresolved/);
assert.doesNotMatch(missing,/1969|1970/);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_actual_board_date_helpers_do_not_crash_or_invent_missing_dates(self):
        script = """
const assert=require('node:assert/strict');
const CT='America/Chicago';
const reviewSport=c=>c.sport,reviewLeagueLabel=(c,l)=>l,regionForAttentionCard=()=>'',regionLeagueLabel=(r,l)=>l;
const esc=value=>String(value??''),pill=(color,label)=>`<span>${label}</span>`,esportsGameLabel=()=>'';
""" + "\n".join(js_function(name) for name in ("ctKey", "prettyDay", "eventTime", "renderIssueBoard")) + """
const base={sport:'Soccer',league:'Test League',event:'Age review',severity:'AMBER',athletes:['Review Player'],age_review_athletes:['Review Player']};
for(const start_time of [null,undefined,'','invalid','10/15/2026','2026-02-30','2026-10-15Tinvalid']){
  for(const flag of [{},{event_date_missing:true}]){
    const html=renderIssueBoard([{...base,start_time,...flag}],[]);
    assert.match(html,/Event date unresolved/);
    assert.doesNotMatch(html,/1969|1970|Invalid Date|undefined/);
    assert.match(html,/Review Player/);
  }
}
const flagged=renderIssueBoard([{...base,start_time:'2026-10-15',event_date_missing:true}],[]);
assert.match(flagged,/Event date unresolved/);
const valid=renderIssueBoard([{...base,start_time:'2026-10-15T12:00:00-05:00'}],[]);
assert.doesNotMatch(valid,/Event date unresolved/);
assert.match(valid,/Oct 15/);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
