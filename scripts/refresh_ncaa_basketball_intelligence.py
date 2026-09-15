#!/usr/bin/env python3
from pathlib import Path
import datetime, json, re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()

SCHEDULE_PATH = DATA / "ncaa-basketball.json"
KNOWN_PATH = DATA / "known-u18.json"
RULES_PATH = DATA / "ncaa-basketball-rules.json"
OUT_PATH = DATA / "ncaa-basketball-intelligence.json"

schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8")) if SCHEDULE_PATH.exists() else {"events":[]}
known = json.loads(KNOWN_PATH.read_text(encoding="utf-8")) if KNOWN_PATH.exists() else {"records":[]}
rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))

def norm(v):
    s = str(v or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def team_match(registry_team, event_team):
    a, b = norm(registry_team), norm(event_team)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    # Common school-name equivalences that should not require mascot text.
    aliases = {
        "usc": {"usc", "southern california"},
        "uconn": {"uconn", "connecticut"},
        "unc": {"unc", "north carolina"},
        "lsu": {"lsu", "louisiana state"},
        "smu": {"smu", "southern methodist"},
        "tcu": {"tcu", "texas christian"},
        "ucf": {"ucf", "central florida"},
        "byu": {"byu", "brigham young"},
    }
    for vals in aliases.values():
        if a in vals and b in vals:
            return True
    return False

def event_text(ev):
    fields = [
        ev.get("name"), ev.get("league"), ev.get("status_detail"),
        ev.get("round_description"), ev.get("source_url"),
        ev.get("championship_id"), ev.get("bracket_id")
    ]
    return " ".join(str(x or "") for x in fields).lower()

verified_u18 = []
for rec in known.get("records", []):
    if norm(rec.get("sport")) != "basketball":
        continue
    if str(rec.get("status") or "").upper() not in ("VERIFIED", "VERIFIED U18"):
        continue
    verified_u18.append({
        "sport": "Basketball",
        "league": rec.get("league"),
        "team": rec.get("team"),
        "athlete": rec.get("athlete"),
        "age": rec.get("age"),
        "age_label": rec.get("age_label"),
        "status": "VERIFIED U18",
        "source": known.get("source", "Known U18 registry")
    })

events = [
    e for e in schedule.get("events", [])
    if str(e.get("status") or "").upper() != "COMPLETED"
]

active_exposures = []
for ev in events:
    matches = []
    for rec in verified_u18:
        if team_match(rec.get("team"), ev.get("home")) or team_match(rec.get("team"), ev.get("away")):
            matches.append({
                "athlete": rec.get("athlete"),
                "team": rec.get("team"),
                "age": rec.get("age"),
                "age_label": rec.get("age_label")
            })
    if matches:
        active_exposures.append({
            "event_id": ev.get("id"),
            "contest_id": ev.get("contest_id"),
            "league": ev.get("league"),
            "division": ev.get("division"),
            "gender": ev.get("gender"),
            "event": ev.get("name"),
            "home": ev.get("home"),
            "away": ev.get("away"),
            "start_time": ev.get("start_time"),
            "severity": rules["u18"]["severity"],
            "reason": "Known verified U18 athlete is rostered to a team in this scheduled NCAA basketball event.",
            "staff_action": rules["u18"]["staff_action"],
            "athletes": matches
        })

special_restrictions = []
for ev in events:
    text = event_text(ev)
    for rule in rules.get("special_events", []):
        aliases = [str(a).lower() for a in rule.get("aliases", [])]
        if not any(a and a in text for a in aliases):
            continue
        special_restrictions.append({
            "event_id": ev.get("id"),
            "contest_id": ev.get("contest_id"),
            "league": ev.get("league"),
            "division": ev.get("division"),
            "gender": ev.get("gender"),
            "event": ev.get("name"),
            "start_time": ev.get("start_time"),
            "tournament": rule.get("name"),
            "restriction": rule.get("restriction"),
            "severity": rule.get("severity", "AMBER"),
            "reason": f'{rule.get("name")} · {rule.get("restriction")}',
            "staff_action": rule.get("staff_action")
        })

out = {
    "schema_version": 1,
    "generated_at": NOW.isoformat(),
    "screening_date": TODAY.isoformat(),
    "sport": "NCAA Basketball",
    "method": "Registry-first event matching plus explicit special-tournament metadata detection.",
    "verified_u18_count": len(verified_u18),
    "verified_u18": verified_u18,
    "active_exposure_count": len(active_exposures),
    "active_exposures": active_exposures,
    "special_restriction_count": len(special_restrictions),
    "special_restrictions": special_restrictions,
    "events_screened": len(events),
    "notes": rules.get("principles", [])
}

OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({
    "verified_u18": len(verified_u18),
    "active_u18_exposures": len(active_exposures),
    "special_restrictions": len(special_restrictions),
    "events_screened": len(events)
}))
