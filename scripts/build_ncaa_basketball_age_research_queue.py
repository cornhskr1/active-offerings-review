#!/usr/bin/env python3
from pathlib import Path
import datetime, json, re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CACHE_PATH = DATA / "ncaa-basketball-age-cache.json"
SCHEDULE_PATH = DATA / "ncaa-basketball.json"
SOURCES_PATH = DATA / "ncaa-basketball-age-sources.json"
OUT_PATH = DATA / "ncaa-basketball-age-research-queue.json"

NOW = datetime.datetime.now(datetime.timezone.utc)

if not CACHE_PATH.exists():
    raise SystemExit("Missing data/ncaa-basketball-age-cache.json")

cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8")) if SCHEDULE_PATH.exists() else {"events":[]}
sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8")) if SOURCES_PATH.exists() else {"local_priority":[]}

def norm(v):
    s = str(v or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# Build active/upcoming team set from current Today + 7 basketball feed.
active_teams = set()
for ev in schedule.get("events", []):
    if str(ev.get("status") or "").upper() == "COMPLETED":
        continue
    for field in ("home","away"):
        if ev.get(field):
            active_teams.add(norm(ev[field]))

# Build official local source map.
local_sources = {}
for school in sources.get("local_priority", []):
    for alias in school.get("aliases", []):
        local_sources[norm(alias)] = school

def local_source_for(team, gender):
    school = local_sources.get(norm(team))
    if not school:
        return None
    return school.get("men_roster") if gender == "Men" else school.get("women_roster")

def in_today_plus_7(team):
    nt = norm(team)
    return nt in active_teams

queue = []

for rec in cache.get("records", []):
    status = str(rec.get("status") or "").upper()

    # Verified players stay in the persistent cache but do not need new research.
    if status in ("VERIFIED U18","VERIFIED 18+"):
        continue

    reasons = list(rec.get("priority_reasons") or [])
    score = 0

    if "KNOWN U18" in reasons:
        score += 1000

    if "NEBRASKA PRIORITY" in reasons:
        score += 800

    today7 = in_today_plus_7(rec.get("team"))
    if today7:
        score += 600
        reasons.append("TODAY+7")

    if "FRESHMAN" in reasons:
        score += 400

    if status == "AGE REVIEW":
        score += 200
    elif status == "UNRESOLVED":
        score += 50

    # Stable tiebreaker favors younger class signals and then alphabetic order.
    queue.append({
        "priority_score": score,
        "priority_reasons": sorted(set(reasons)),
        "gender": rec.get("gender"),
        "conference": rec.get("conference"),
        "team": rec.get("team"),
        "athlete": rec.get("athlete"),
        "player_id": rec.get("player_id"),
        "class": rec.get("class"),
        "position": rec.get("position"),
        "status": status,
        "official_roster_source": local_source_for(rec.get("team"), rec.get("gender")),
        "evidence_source": rec.get("evidence_source"),
        "evidence_url": rec.get("evidence_url"),
        "last_researched": rec.get("last_researched")
    })

queue.sort(key=lambda x:(
    -int(x.get("priority_score") or 0),
    x.get("gender") or "",
    x.get("conference") or "",
    x.get("team") or "",
    x.get("athlete") or ""
))

summary = {
    "queue_total": len(queue),
    "known_u18": sum(1 for x in queue if "KNOWN U18" in x.get("priority_reasons", [])),
    "nebraska_priority": sum(1 for x in queue if "NEBRASKA PRIORITY" in x.get("priority_reasons", [])),
    "today_plus_7": sum(1 for x in queue if "TODAY+7" in x.get("priority_reasons", [])),
    "freshmen": sum(1 for x in queue if "FRESHMAN" in x.get("priority_reasons", [])),
    "age_review": sum(1 for x in queue if x.get("status") == "AGE REVIEW"),
    "unresolved": sum(1 for x in queue if x.get("status") == "UNRESOLVED"),
    "top_priority_1000_plus": sum(1 for x in queue if (x.get("priority_score") or 0) >= 1000),
    "top_priority_800_plus": sum(1 for x in queue if (x.get("priority_score") or 0) >= 800),
}

out = {
    "schema_version": 1,
    "generated_at": NOW.isoformat(),
    "method": "Priority-ranked NCAA Division I basketball age research queue.",
    "priority_order": [
        "KNOWN U18",
        "NEBRASKA PRIORITY",
        "TODAY+7",
        "FRESHMAN",
        "AGE REVIEW",
        "UNRESOLVED"
    ],
    "summary": summary,
    "queue": queue
}

OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(summary))
