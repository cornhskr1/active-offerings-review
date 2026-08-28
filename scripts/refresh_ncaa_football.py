#!/usr/bin/env python3
from pathlib import Path
import json, datetime, urllib.request, urllib.error, re, html, time
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG_PATH = DATA / "ncaa-football-sources.json"
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))
REVIEW = DATA / "review-data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"
}

FRESHMAN_TERMS = [
    r"\bFreshman\b", r"\bTrue Freshman\b",
    r"\breclassif(?:ied|ication)\b", r"\bearly enrollee\b",
    r"\bforgo (?:his|her) senior year\b", r"\bskip(?:ped|s)? (?:his|her) senior year\b"
]

def fetch(url, timeout=18, max_bytes=650000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        text = raw.decode("utf-8", errors="ignore")
        return {
            "ok": 200 <= getattr(resp,"status",200) < 400,
            "status": getattr(resp,"status",200),
            "final_url": resp.geturl(),
            "content_type": resp.headers.get("Content-Type",""),
            "text": text
        }

def page_text(src):
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", src)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s)

def validate_football_page(result, kind):
    if not result or not result.get("ok"):
        return False
    txt = page_text(result.get("text","")).lower()
    url = result.get("final_url","").lower()
    # Conservative content validation to avoid marking generic homepages as mapped.
    football = "football" in txt or "football" in url
    if kind == "schedule":
        specific = "schedule" in txt or "schedule" in url
    else:
        specific = "roster" in txt or "roster" in url
    return football and specific

def discover(root, kind, candidates):
    attempts = []
    for path in candidates:
        url = root.rstrip("/") + path
        try:
            r = fetch(url)
            valid = validate_football_page(r, kind)
            attempts.append({"url":url,"http_status":r.get("status"),"final_url":r.get("final_url"),"valid":valid})
            if valid:
                return {
                    "ok":True,
                    "url":r["final_url"],
                    "http_status":r["status"],
                    "text":r["text"],
                    "attempts":attempts
                }
        except Exception as e:
            attempts.append({"url":url,"valid":False,"error":str(e)[:120]})
    return {"ok":False,"url":None,"attempts":attempts}

def load_review():
    if REVIEW.exists():
        try:
            return json.loads(REVIEW.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema_version":1,"review_window_days":7,"events":[],"u18_matches":[],"restriction_triggers":[],"coverage_alerts":[]}

now = datetime.datetime.now(datetime.timezone.utc)
results=[]
alerts=[]
known=[]
signals=[]
mapped_full=0
mapped_partial=0
unresolved=0

for team in CFG["teams"]:
    roots = team.get("candidate_roots",[])
    best_schedule = {"ok":False}
    best_roster = {"ok":False}
    chosen_root = None

    for root in roots:
        schedule = discover(root, "schedule", CFG["path_candidates"]["schedule"])
        roster = discover(root, "roster", CFG["path_candidates"]["roster"])

        if schedule["ok"] or roster["ok"]:
            chosen_root = root
            if schedule["ok"]: best_schedule = schedule
            if roster["ok"]: best_roster = roster

        if schedule["ok"] and roster["ok"]:
            break

    if best_schedule["ok"] and best_roster["ok"]:
        mapping_status="AUTO-MAPPED"
        mapped_full += 1
    elif best_schedule["ok"] or best_roster["ok"]:
        mapping_status="PARTIAL"
        mapped_partial += 1
    else:
        mapping_status="UNRESOLVED"
        unresolved += 1

    roster_text = page_text(best_roster.get("text","")) if best_roster.get("ok") else ""
    freshman_hits = []
    if roster_text:
        for term in FRESHMAN_TERMS:
            if re.search(term, roster_text, re.I):
                freshman_hits.append(term)

    if freshman_hits:
        signals.append({
            "sport":"NCAA Football",
            "team":team["team"],
            "type":"FRESHMAN / RECLASSIFICATION DISCOVERY",
            "status":"REVIEW",
            "message":f"{team['team']} roster source contains freshman/reclassification indicators. Age verification remains required.",
            "checked_at":now.isoformat()
        })

    for a in team.get("known_u18",[]):
        known.append({
            "sport":"NCAA Football",
            "league":"NCAA FBS",
            "team":team["team"],
            "athlete":a["name"],
            "age":a["age"],
            "position":a.get("position"),
            "status":a.get("status","VERIFIED"),
            "evidence_url":a.get("evidence_url"),
            "evidence_note":a.get("evidence_note"),
            "checked_at":now.isoformat()
        })

    # Persist discovered mapping into config for future runs.
    team["mapped"] = mapping_status in ("AUTO-MAPPED","PARTIAL")
    team["mapping_status"] = mapping_status
    team["last_mapping_check"] = now.isoformat()
    if chosen_root:
        team["official_root"] = chosen_root
    if best_schedule["ok"]:
        team["schedule_url"] = best_schedule["url"]
    if best_roster["ok"]:
        team["roster_url"] = best_roster["url"]

    coverage = "PARTIAL" if mapping_status=="AUTO-MAPPED" else mapping_status
    age_coverage = "PARTIAL" if best_roster["ok"] else "UNMAPPED"

    alert = {
        "sport":"NCAA Football",
        "league":"NCAA FBS",
        "team":team["team"],
        "conference":team.get("conference"),
        "division":"FBS",
        "mapped": mapping_status in ("AUTO-MAPPED","PARTIAL"),
        "mapping_status":mapping_status,
        "schedule_ok":bool(best_schedule["ok"]),
        "participants_ok":bool(best_roster["ok"]),
        "age_coverage":age_coverage,
        "freshness":"CURRENT" if best_schedule["ok"] and best_roster["ok"] else "UNVERIFIED",
        "known_u18_count":len(team.get("known_u18",[])),
        "coverage_state":coverage,
        "reason":"full roster DOB/age screening not complete" if best_roster["ok"] else "official roster mapping unresolved",
        "checked_at":now.isoformat()
    }
    alerts.append(alert)
    results.append({
        "team":team["team"],
        "conference":team.get("conference"),
        "mapping_status":mapping_status,
        "official_root":team.get("official_root"),
        "schedule_url":team.get("schedule_url"),
        "roster_url":team.get("roster_url"),
        "freshman_discovery_signals":len(freshman_hits)
    })

# Save discovered URLs back to source registry.
CFG["last_auto_map_run"] = now.isoformat()
CFG_PATH.write_text(json.dumps(CFG, indent=2), encoding="utf-8")

out = {
    "schema_version":3,
    "generated_at":now.isoformat(),
    "sport":"NCAA Football",
    "scope":"FBS auto-mapping inventory",
    "teams_total":len(results),
    "teams_mapped":mapped_full,
    "teams_partial":mapped_partial,
    "teams_unmapped":unresolved,
    "known_u18":known,
    "freshman_discovery_signals":signals,
    "coverage_alerts":alerts,
    "teams":results,
    "conference_counts":{}
}
for t in CFG["teams"]:
    c=t.get("conference","Unknown")
    out["conference_counts"][c]=out["conference_counts"].get(c,0)+1

(DATA/"ncaa-football-data.json").write_text(json.dumps(out,indent=2),encoding="utf-8")

review=load_review()
review["background_checked_at"]=now.isoformat()
review["generated_at"]=now.isoformat()
review["u18_matches"]=[x for x in review.get("u18_matches",[]) if x.get("sport")!="NCAA Football"]+known
review["coverage_alerts"]=[x for x in review.get("coverage_alerts",[]) if x.get("sport")!="NCAA Football"]+alerts
review["discovery_signals"]=[x for x in review.get("discovery_signals",[]) if x.get("sport")!="NCAA Football"]+signals
REVIEW.write_text(json.dumps(review,indent=2),encoding="utf-8")

print(json.dumps({
    "generated_at":now.isoformat(),
    "teams_total":len(results),
    "auto_mapped":mapped_full,
    "partial":mapped_partial,
    "unresolved":unresolved,
    "known_u18":len(known)
}))
