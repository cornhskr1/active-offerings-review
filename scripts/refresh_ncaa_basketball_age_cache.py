#!/usr/bin/env python3
from pathlib import Path
import datetime, json, re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ROSTER_PATH = DATA / "ncaa-basketball-rosters.json"
CACHE_PATH = DATA / "ncaa-basketball-age-cache.json"
KNOWN_U18_PATH = DATA / "known-u18.json"

NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.date()

if not ROSTER_PATH.exists():
    raise SystemExit("Missing data/ncaa-basketball-rosters.json")

rosters = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))

if CACHE_PATH.exists():
    try:
        old_cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        old_cache = {"records":[]}
else:
    old_cache = {"records":[]}

if KNOWN_U18_PATH.exists():
    try:
        known_u18 = json.loads(KNOWN_U18_PATH.read_text(encoding="utf-8"))
    except Exception:
        known_u18 = {"records":[]}
else:
    known_u18 = {"records":[]}

def norm(v):
    s = str(v or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def parse_dob(v):
    if not v:
        return None
    text = str(v).strip()
    for candidate in (text[:10], text):
        try:
            return datetime.date.fromisoformat(candidate[:10])
        except Exception:
            pass
    return None

def calc_age(dob, on_date):
    if not dob:
        return None
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))

def roster_key(gender, team, athlete):
    return f"{gender}|{team}|{athlete}"

# Existing cache indexed by stable ESPN player id when possible, then fallback roster key.
old_by_id = {}
old_by_key = {}
for rec in old_cache.get("records", []):
    if rec.get("player_id"):
        old_by_id[str(rec["player_id"])] = rec
    key = roster_key(rec.get("gender"), rec.get("team"), rec.get("athlete"))
    old_by_key[key] = rec

known_basketball_u18 = []
for rec in known_u18.get("records", []):
    if norm(rec.get("sport")) != "basketball":
        continue
    if str(rec.get("status") or "").upper() not in ("VERIFIED", "VERIFIED U18"):
        continue
    known_basketball_u18.append(rec)

def known_u18_match(team, athlete):
    nt, na = norm(team), norm(athlete)
    for rec in known_basketball_u18:
        if norm(rec.get("athlete")) != na:
            continue
        rt = norm(rec.get("team"))
        if not rt or not nt or rt == nt or rt in nt or nt in rt:
            return rec
    return None

matched_known_u18 = set()
records = []
for team_row in rosters.get("teams", []):
    gender = team_row.get("gender")
    team = team_row.get("team")
    conference = team_row.get("conference")
    roster_status = team_row.get("status")
    if gender not in ("Men", "Women"):
        continue

    for a in team_row.get("athletes") or []:
        athlete = a.get("name")
        if not athlete:
            continue

        pid = str(a.get("id") or "")
        key = roster_key(gender, team, athlete)
        old = old_by_id.get(pid) if pid else None
        old = old or old_by_key.get(key) or {}

        source_dob = a.get("date_of_birth")
        source_age = a.get("age")
        dob = old.get("dob") or source_dob
        dob_date = parse_dob(dob)

        # Preserve verified/manual statuses from older cache. Never downgrade them.
        old_status = str(old.get("status") or "").upper()
        if old_status in ("VERIFIED U18", "VERIFIED 18+"):
            status = old_status
            evidence_source = old.get("evidence_source")
            evidence_note = old.get("evidence_note")
            evidence_url = old.get("evidence_url")
            verified_at = old.get("verified_at")
        else:
            known = known_u18_match(team, athlete)
            if known:
                matched_known_u18.add((norm(known.get("team")), norm(known.get("athlete"))))
                status = "VERIFIED U18"
                evidence_source = known.get("source") or "Known U18 Registry"
                evidence_note = known.get("age_label") or known.get("age") or "Matched existing verified U18 registry"
                evidence_url = known.get("source_url")
                verified_at = old.get("verified_at") or NOW.isoformat()
            elif dob_date:
                age = calc_age(dob_date, TODAY)
                status = "VERIFIED U18" if age is not None and age < 18 else "VERIFIED 18+"
                evidence_source = "ESPN roster DOB"
                evidence_note = f"DOB supplied in roster feed: {dob_date.isoformat()}"
                evidence_url = team_row.get("roster_source_url")
                verified_at = old.get("verified_at") or NOW.isoformat()
            elif source_age not in (None, ""):
                try:
                    age_num = int(source_age)
                except Exception:
                    age_num = None
                if age_num is not None:
                    status = "VERIFIED U18" if age_num < 18 else "VERIFIED 18+"
                    evidence_source = "ESPN roster age"
                    evidence_note = f"Age supplied in roster feed: {age_num}"
                    evidence_url = team_row.get("roster_source_url")
                    verified_at = old.get("verified_at") or NOW.isoformat()
                else:
                    status = old_status or "UNRESOLVED"
                    evidence_source = old.get("evidence_source")
                    evidence_note = old.get("evidence_note")
                    evidence_url = old.get("evidence_url")
                    verified_at = old.get("verified_at")
            else:
                # Freshmen and priority schools are queued for review, but unknown age is not an alert.
                is_priority_school = norm(team) in {
                    "nebraska","nebraska cornhuskers",
                    "creighton","creighton bluejays",
                    "omaha","omaha mavericks","nebraska omaha","uno"
                }
                is_freshman = norm(a.get("class")) == "freshman"
                if old_status == "AGE REVIEW":
                    status = "AGE REVIEW"
                elif is_priority_school or is_freshman:
                    status = "AGE REVIEW"
                else:
                    status = "UNRESOLVED"
                evidence_source = old.get("evidence_source")
                evidence_note = old.get("evidence_note")
                evidence_url = old.get("evidence_url")
                verified_at = old.get("verified_at")

        calculated_age = calc_age(dob_date, TODAY) if dob_date else None

        priority_reasons = []
        known_for_priority = known_u18_match(team, athlete)
        if known_for_priority:
            matched_known_u18.add((norm(known_for_priority.get("team")), norm(known_for_priority.get("athlete"))))
            priority_reasons.append("KNOWN U18")
        if norm(team) in {
            "nebraska","nebraska cornhuskers",
            "creighton","creighton bluejays",
            "omaha","omaha mavericks","nebraska omaha","uno"
        }:
            priority_reasons.append("NEBRASKA PRIORITY")
        if norm(a.get("class")) == "freshman":
            priority_reasons.append("FRESHMAN")

        records.append({
            "player_id": pid or old.get("player_id"),
            "gender": gender,
            "division": "Division I",
            "conference": conference,
            "team": team,
            "athlete": athlete,
            "jersey": a.get("jersey"),
            "position": a.get("position"),
            "class": a.get("class"),
            "roster_status": roster_status,
            "status": status,
            "dob": dob,
            "calculated_age": calculated_age,
            "source_age": source_age,
            "source_dob": source_dob,
            "evidence_source": evidence_source,
            "evidence_note": evidence_note,
            "evidence_url": evidence_url,
            "verified_at": verified_at,
            "priority_reasons": priority_reasons,
            "first_seen": old.get("first_seen") or NOW.isoformat(),
            "last_seen": NOW.isoformat(),
            "last_researched": old.get("last_researched"),
        })

records.sort(key=lambda x:(x["gender"], x.get("conference") or "", x.get("team") or "", x.get("athlete") or ""))

unmatched_known_u18 = []
for rec in known_basketball_u18:
    key = (norm(rec.get("team")), norm(rec.get("athlete")))
    if key not in matched_known_u18:
        unmatched_known_u18.append({
            "team": rec.get("team"),
            "athlete": rec.get("athlete"),
            "age": rec.get("age"),
            "age_label": rec.get("age_label"),
            "league": rec.get("league"),
            "status": rec.get("status"),
            "lane": rec.get("lane"),
            "reason": "Verified U18 registry record is not currently matched to the active roster cache."
        })

summary = {
    "athletes_total": len(records),
    "verified_u18": sum(1 for x in records if x["status"] == "VERIFIED U18"),
    "verified_18_plus": sum(1 for x in records if x["status"] == "VERIFIED 18+"),
    "age_review": sum(1 for x in records if x["status"] == "AGE REVIEW"),
    "unresolved": sum(1 for x in records if x["status"] == "UNRESOLVED"),
    "source_dob": sum(1 for x in records if x.get("source_dob")),
    "source_age": sum(1 for x in records if x.get("source_age") not in (None, "")),
    "priority_known_u18": sum(1 for x in records if "KNOWN U18" in x.get("priority_reasons", [])),
    "priority_nebraska": sum(1 for x in records if "NEBRASKA PRIORITY" in x.get("priority_reasons", [])),
    "priority_freshmen": sum(1 for x in records if "FRESHMAN" in x.get("priority_reasons", [])),
    "known_u18_registry_total": len(known_basketball_u18),
    "known_u18_roster_matched": len(matched_known_u18),
    "known_u18_roster_unmatched": len(unmatched_known_u18),
}

out = {
    "schema_version": 1,
    "generated_at": NOW.isoformat(),
    "source": {
        "roster_cache": "data/ncaa-basketball-rosters.json",
        "known_u18": "data/known-u18.json",
        "note": "Persistent NCAA Division I basketball age intelligence cache."
    },
    "summary": summary,
    "known_u18_unmatched": unmatched_known_u18,
    "records": records
}

CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(summary))
