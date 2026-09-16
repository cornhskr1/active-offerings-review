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
ROSTERS_PATH = DATA / "ncaa-basketball-rosters.json"
CATALOG_PATH = DATA / "catalog-live.json"
OUT_PATH = DATA / "ncaa-basketball-intelligence.json"

schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8")) if SCHEDULE_PATH.exists() else {"events":[]}
known = json.loads(KNOWN_PATH.read_text(encoding="utf-8")) if KNOWN_PATH.exists() else {"records":[]}
rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
rosters = json.loads(ROSTERS_PATH.read_text(encoding="utf-8")) if ROSTERS_PATH.exists() else {"teams":[]}
catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else {"sections":[]}

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


def athlete_match(a, b):
    return norm(a) == norm(b) and bool(norm(a))

def rostered_verified_u18(rec, gender=None):
    """Return True only when the verified registry athlete is present on the current active roster."""
    for team in rosters.get("teams", []):
        if gender and team.get("gender") and str(team.get("gender")) != str(gender):
            continue
        if not team_match(rec.get("team"), team.get("team")):
            continue
        for athlete in team.get("athletes") or []:
            if athlete_match(rec.get("athlete"), athlete.get("name")):
                return True
    return False

def event_text(ev):
    # Restriction detection uses event metadata only. Do not use source URLs or
    # opaque IDs because incidental strings can create false tournament matches.
    fields = [
        ev.get("name"),
        ev.get("league"),
        ev.get("status_detail"),
        ev.get("round_description"),
        ev.get("tournament"),
        ev.get("tournament_name"),
        ev.get("series_name"),
        ev.get("season_type"),
        ev.get("notes"),
    ]
    return " ".join(str(x or "") for x in fields).lower()


def alias_in_text(alias, text):
    """Token-safe alias match. Full names match literally; short aliases require word boundaries."""
    a = str(alias or "").strip().lower()
    if not a:
        return False
    if len(a) <= 4 and " " not in a:
        return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text) is not None
    return a in text


def ncaa_basketball_catalog_lines():
    for section in catalog.get("sections", []):
        if norm(section.get("sport")) == "ncaa basketball":
            return [str(x) for x in section.get("lines", [])]
    return []


def catalog_special_rules():
    """
    Regulatory truth comes from the current approved catalog.
    Only build a CBI/CBC rule when the current catalog explicitly contains
    the event, Men's scope, and NO PLAYER PROPOSITION WAGERS restriction.
    """
    lines = ncaa_basketball_catalog_lines()
    configured = {str(r.get("id") or ""): r for r in rules.get("special_events", [])}
    wanted = [
        ("cbc", "College Basketball Crown", ["college basketball crown", "cbc"]),
        ("cbi", "College Basketball Invitational", ["college basketball invitational", "cbi"]),
    ]

    out = []
    for rule_id, canonical, aliases in wanted:
        matched_line = None
        for line in lines:
            low = line.lower()
            if canonical.lower() not in low:
                continue
            if "men" not in low:
                continue
            if "no player proposition wagers" not in low:
                continue
            matched_line = line
            break
        if not matched_line:
            continue

        base = configured.get(rule_id, {})
        out.append({
            "id": rule_id,
            "name": canonical,
            "aliases": aliases,
            "gender": "Men",
            "restriction": "NO PLAYER PROPOSITION WAGERS",
            "severity": base.get("severity", "AMBER"),
            "staff_action": base.get(
                "staff_action",
                f"Confirm no player proposition wagers are offered for the {canonical} event."
            ),
            "catalog_line": matched_line,
            "catalog_source": catalog.get("source_label"),
            "catalog_version": catalog.get("menu_version"),
        })
    return out


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
    and str(e.get("division") or "") == "Division I"
]

active_exposures = []
roster_matched_verified_u18 = []
roster_unmatched_verified_u18 = []

for rec in verified_u18:
    # League carries the men's/women's lane in the registry.
    league_text = str(rec.get("league") or "").lower()
    rec_gender = "Women" if "women" in league_text else "Men" if "men" in league_text else None
    if rostered_verified_u18(rec, rec_gender):
        roster_matched_verified_u18.append(rec)
    else:
        roster_unmatched_verified_u18.append(rec)

for ev in events:
    matches = []
    for rec in roster_matched_verified_u18:
        league_text = str(rec.get("league") or "").lower()
        rec_gender = "Women" if "women" in league_text else "Men" if "men" in league_text else None
        if rec_gender and ev.get("gender") and str(ev.get("gender")) != rec_gender:
            continue
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
            "reason": "Verified U18 athlete is matched to the current roster of a team in this scheduled NCAA basketball event.",
            "staff_action": rules["u18"]["staff_action"],
            "athletes": matches
        })

special_restrictions = []
catalog_rules = catalog_special_rules()

for ev in events:
    # Catalog restriction applies only to Men's Division I basketball.
    if str(ev.get("division") or "") != "Division I":
        continue
    if str(ev.get("gender") or "") != "Men":
        continue

    text = event_text(ev)

    for rule in catalog_rules:
        aliases = rule.get("aliases", [])
        if not any(alias_in_text(a, text) for a in aliases):
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
            "staff_action": rule.get("staff_action"),
            "catalog_line": rule.get("catalog_line"),
            "catalog_source": rule.get("catalog_source"),
            "catalog_version": rule.get("catalog_version"),
            "detection_method": "Explicit tournament metadata matched to current approved catalog restriction."
        })

out = {
    "schema_version": 1,
    "generated_at": NOW.isoformat(),
    "screening_date": TODAY.isoformat(),
    "sport": "NCAA Basketball",
    "method": "Roster-matched U18 screening plus catalog-validated explicit special-tournament metadata detection.",
    "verified_u18_count": len(verified_u18),
    "verified_u18": verified_u18,
    "roster_matched_verified_u18_count": len(roster_matched_verified_u18),
    "roster_matched_verified_u18": roster_matched_verified_u18,
    "roster_unmatched_verified_u18_count": len(roster_unmatched_verified_u18),
    "roster_unmatched_verified_u18": roster_unmatched_verified_u18,
    "active_exposure_count": len(active_exposures),
    "active_exposures": active_exposures,
    "catalog_special_rules_count": len(catalog_rules),
    "catalog_special_rules": catalog_rules,
    "special_restriction_count": len(special_restrictions),
    "special_restrictions": special_restrictions,
    "events_screened": len(events),
    "notes": rules.get("principles", [])
}

OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({
    "verified_u18_registry": len(verified_u18),
    "roster_matched_verified_u18": len(roster_matched_verified_u18),
    "active_u18_exposures": len(active_exposures),
    "special_restrictions": len(special_restrictions),
    "events_screened": len(events)
}))
