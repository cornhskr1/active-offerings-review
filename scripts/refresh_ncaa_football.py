#!/usr/bin/env python3
from pathlib import Path
import json, datetime, urllib.request, urllib.error, re, html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA / "ncaa-football-sources.json").read_text(encoding="utf-8"))
REVIEW = DATA / "review-data.json"

UA = "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"
HEADERS = {"User-Agent": UA}

FRESHMAN_TERMS = [
    r"\bFr\.\b", r"\bFreshman\b", r"\bTrue Freshman\b",
    r"\breclassif(?:ied|ication)\b", r"\bearly enrollee\b",
    r"\bforgo (?:his|her) senior year\b", r"\bskip(?:ped|s)? (?:his|her) senior year\b"
]

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read(1_500_000)
        return resp.geturl(), raw.decode("utf-8", errors="ignore"), getattr(resp, "status", 200)

def textify(src):
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", src)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s)

def load_review():
    if REVIEW.exists():
        try:
            return json.loads(REVIEW.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema_version":1,"review_window_days":7,"events":[],"u18_matches":[],"restriction_triggers":[],"coverage_alerts":[]}

now = datetime.datetime.now(datetime.timezone.utc)
team_results = []
u18_records = []
coverage_alerts = []
freshman_signals = []

for team in CFG["teams"]:
    result = {
        "sport":"NCAA Football",
        "team":team["team"],
        "division":team.get("division"),
        "conference":team.get("conference"),
        "checked_at":now.isoformat(),
        "schedule":{"url":team["schedule_url"],"ok":False},
        "roster":{"url":team["roster_url"],"ok":False},
        "known_u18":team.get("known_u18",[])
    }

    roster_text = ""
    for key in ("schedule","roster"):
        url = team[f"{key}_url"]
        try:
            final_url, body, status = fetch(url)
            result[key].update({"ok": 200 <= status < 400, "http_status":status, "final_url":final_url})
            if key == "roster":
                roster_text = textify(body)
        except Exception as e:
            result[key].update({"ok":False,"error":str(e)[:180]})

    # Freshman/reclassification discovery signals are NOT age determinations.
    matches = []
    if roster_text:
        for term in FRESHMAN_TERMS:
            if re.search(term, roster_text, re.I):
                matches.append(term)
    result["freshman_discovery_signals"] = len(matches)
    if matches:
        freshman_signals.append({
            "sport":"NCAA Football",
            "team":team["team"],
            "type":"FRESHMAN / RECLASSIFICATION DISCOVERY",
            "status":"REVIEW",
            "message":f"{team['team']} official roster/bio source contains freshman/reclassification indicators. Age verification remains required.",
            "checked_at":now.isoformat()
        })

    for athlete in team.get("known_u18",[]):
        u18_records.append({
            "sport":"NCAA Football",
            "league":"NCAA FBS" if team.get("division")=="FBS" else "NCAA Football",
            "team":team["team"],
            "athlete":athlete["name"],
            "age":athlete["age"],
            "position":athlete.get("position"),
            "status":athlete.get("status","VERIFIED"),
            "evidence_url":athlete.get("evidence_url"),
            "evidence_note":athlete.get("evidence_note"),
            "checked_at":now.isoformat()
        })

    # Coverage stays partial until roster-age screening is actually complete.
    coverage_state = "PARTIAL"
    reasons = []
    if not result["schedule"]["ok"]:
        reasons.append("schedule source unavailable")
    if not result["roster"]["ok"]:
        reasons.append("roster source unavailable")
    reasons.append("full roster DOB/age screening not complete")
    coverage_alerts.append({
        "sport":"NCAA Football",
        "league":"NCAA Football",
        "team":team["team"],
        "coverage_state":coverage_state,
        "schedule_ok":result["schedule"]["ok"],
        "participants_ok":result["roster"]["ok"],
        "age_coverage":"PARTIAL",
        "freshness":"CURRENT" if result["roster"]["ok"] and result["schedule"]["ok"] else "UNVERIFIED",
        "known_u18_count":len(team.get("known_u18",[])),
        "reason":"; ".join(reasons),
        "checked_at":now.isoformat()
    })

    team_results.append(result)

out = {
    "schema_version":1,
    "generated_at":now.isoformat(),
    "sport":"NCAA Football",
    "teams_mapped":len(team_results),
    "teams":team_results,
    "known_u18":u18_records,
    "freshman_discovery_signals":freshman_signals,
    "coverage_alerts":coverage_alerts
}
(DATA / "ncaa-football-data.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

review = load_review()
review["background_checked_at"] = now.isoformat()
review["generated_at"] = now.isoformat()

# Replace only NCAA Football generated records, preserving other adapters.
review["u18_matches"] = [x for x in review.get("u18_matches",[]) if x.get("sport")!="NCAA Football"] + u18_records
review["coverage_alerts"] = [x for x in review.get("coverage_alerts",[]) if x.get("sport")!="NCAA Football"] + coverage_alerts
review["discovery_signals"] = [x for x in review.get("discovery_signals",[]) if x.get("sport")!="NCAA Football"] + freshman_signals

REVIEW.write_text(json.dumps(review, indent=2), encoding="utf-8")
print(json.dumps({
    "generated_at":now.isoformat(),
    "teams_mapped":len(team_results),
    "known_u18":len(u18_records),
    "coverage_alerts":len(coverage_alerts),
    "freshman_discovery_signals":len(freshman_signals)
}))
