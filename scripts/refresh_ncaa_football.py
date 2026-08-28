#!/usr/bin/env python3
from pathlib import Path
import json, datetime, urllib.request, urllib.error, re, html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA / "ncaa-football-sources.json").read_text(encoding="utf-8"))
REVIEW = DATA / "review-data.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}

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
mapped_count = 0
team_results = []
coverage_alerts = []
u18_records = []
signals = []

for team in CFG["teams"]:
    mapped = bool(team.get("mapped"))
    if mapped:
        mapped_count += 1

    result = {
        "sport": "NCAA Football",
        "team": team["team"],
        "conference": team.get("conference"),
        "division": team.get("division","FBS"),
        "mapped": mapped,
        "checked_at": now.isoformat(),
        "schedule": {"url": team.get("schedule_url"), "ok": False},
        "roster": {"url": team.get("roster_url"), "ok": False},
        "known_u18": team.get("known_u18", [])
    }

    roster_text = ""
    if mapped:
        for key in ("schedule","roster"):
            url = result[key].get("url")
            if not url:
                continue
            try:
                final_url, body, status = fetch(url)
                result[key].update({"ok": 200 <= status < 400, "http_status": status, "final_url": final_url})
                if key == "roster":
                    roster_text = textify(body)
            except Exception as e:
                result[key].update({"ok": False, "error": str(e)[:180]})

    matches = []
    if roster_text:
        for term in FRESHMAN_TERMS:
            if re.search(term, roster_text, re.I):
                matches.append(term)
    result["freshman_discovery_signals"] = len(matches)
    if matches:
        signals.append({
            "sport": "NCAA Football",
            "team": team["team"],
            "type": "FRESHMAN / RECLASSIFICATION DISCOVERY",
            "status": "REVIEW",
            "message": f"{team['team']} roster/bio source contains freshman or reclassification indicators. Age verification remains required.",
            "checked_at": now.isoformat()
        })

    for athlete in team.get("known_u18", []):
        u18_records.append({
            "sport": "NCAA Football",
            "league": "NCAA FBS",
            "team": team["team"],
            "athlete": athlete["name"],
            "age": athlete["age"],
            "position": athlete.get("position"),
            "status": athlete.get("status","VERIFIED"),
            "evidence_url": athlete.get("evidence_url"),
            "evidence_note": athlete.get("evidence_note"),
            "checked_at": now.isoformat()
        })

    if mapped:
        coverage_state = "PARTIAL"
        reason = "full roster DOB/age screening not complete"
        if not result["schedule"]["ok"]:
            reason = "schedule source unavailable; " + reason
        if not result["roster"]["ok"]:
            reason = "roster source unavailable; " + reason
        schedule_ok = result["schedule"]["ok"]
        participants_ok = result["roster"]["ok"]
        freshness = "CURRENT" if schedule_ok and participants_ok else "UNVERIFIED"
        age_coverage = "PARTIAL"
    else:
        coverage_state = "UNMAPPED"
        reason = "team is loaded in NCAA Football inventory but live schedule/roster mapping has not been added yet"
        schedule_ok = False
        participants_ok = False
        freshness = "UNVERIFIED"
        age_coverage = "UNMAPPED"

    coverage_alerts.append({
        "sport": "NCAA Football",
        "league": "NCAA FBS",
        "team": team["team"],
        "conference": team.get("conference"),
        "division": team.get("division","FBS"),
        "mapped": mapped,
        "schedule_ok": schedule_ok,
        "participants_ok": participants_ok,
        "age_coverage": age_coverage,
        "freshness": freshness,
        "known_u18_count": len(team.get("known_u18",[])),
        "coverage_state": coverage_state,
        "reason": reason,
        "checked_at": now.isoformat()
    })
    team_results.append(result)

out = {
    "schema_version": 2,
    "generated_at": now.isoformat(),
    "sport": "NCAA Football",
    "scope": CFG.get("scope","FBS inventory"),
    "teams_total": len(team_results),
    "teams_mapped": mapped_count,
    "teams_unmapped": len(team_results) - mapped_count,
    "teams": team_results,
    "known_u18": u18_records,
    "freshman_discovery_signals": signals,
    "coverage_alerts": coverage_alerts,
    "conference_counts": {}
}
for t in team_results:
    c = t.get("conference","Unknown")
    out["conference_counts"][c] = out["conference_counts"].get(c,0) + 1

(DATA / "ncaa-football-data.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

review = load_review()
review["background_checked_at"] = now.isoformat()
review["generated_at"] = now.isoformat()
review["u18_matches"] = [x for x in review.get("u18_matches",[]) if x.get("sport") != "NCAA Football"] + u18_records
review["coverage_alerts"] = [x for x in review.get("coverage_alerts",[]) if x.get("sport") != "NCAA Football"] + coverage_alerts
review["discovery_signals"] = [x for x in review.get("discovery_signals",[]) if x.get("sport") != "NCAA Football"] + signals
REVIEW.write_text(json.dumps(review, indent=2), encoding="utf-8")

print(json.dumps({
    "generated_at": now.isoformat(),
    "teams_total": len(team_results),
    "teams_mapped": mapped_count,
    "teams_unmapped": len(team_results) - mapped_count,
    "known_u18": len(u18_records)
}))
