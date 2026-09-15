#!/usr/bin/env python3
from pathlib import Path
import datetime, json, os, re, time
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MAP_PATH = DATA / "ncaa-basketball-di-map.json"
CACHE_PATH = DATA / "ncaa-basketball-rosters.json"

NOW = datetime.datetime.now(datetime.timezone.utc)
NOW_ISO = NOW.isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)",
    "Accept": "application/json,text/plain,*/*",
}

LEAGUES = {
    "Men": "mens-college-basketball",
    "Women": "womens-college-basketball",
}

TEAM_DIRECTORY = "https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/teams?limit=500"
ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/teams/{team_id}/roster"

FULL_REFRESH = os.getenv("FULL_REFRESH", "false").lower() in ("1","true","yes","on")
MAX_TEAMS = int(os.getenv("MAX_TEAMS", "160"))
STALE_DAYS = int(os.getenv("STALE_DAYS", "4"))

if not MAP_PATH.exists():
    raise SystemExit("Missing data/ncaa-basketball-di-map.json")

team_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
if team_map.get("quality",{}).get("passed") is not True:
    raise SystemExit("D-I team map quality gate has not passed; refusing roster refresh.")

if CACHE_PATH.exists():
    try:
        old_cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        old_cache = {"teams":[]}
else:
    old_cache = {"teams":[]}

def norm(v):
    s = str(v or "").lower()
    s = s.replace("&", " and ")
    # Keep meaningful institution words such as "college" and "university".
    # Removing them can turn Boston College / Boston University into the same key.
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# NCAA standings commonly abbreviate school names. Expand only known institutional
# forms rather than applying unsafe global "St." -> State/Saint assumptions.
NCAA_NAME_ALIASES = {
    "Central Ark.": ["Central Arkansas"],
    "Eastern Ky.": ["Eastern Kentucky"],
    "North Ala.": ["North Alabama"],
    "Queens (NC)": ["Queens", "Queens University"],
    "West Ga.": ["West Georgia"],
    "South Fla.": ["South Florida"],
    "Iowa St.": ["Iowa State"],
    "Eastern Wash.": ["Eastern Washington"],
    "Northern Ariz.": ["Northern Arizona"],
    "Northern Colo.": ["Northern Colorado"],
    "Ohio St.": ["Ohio State"],
    "Penn St.": ["Penn State"],
    "CSU Bakersfield": ["Cal State Bakersfield", "California State Bakersfield"],
    "Cal St. Fullerton": ["Cal State Fullerton", "California State Fullerton"],
    "Col. of Charleston": ["Charleston", "College of Charleston"],
    "Jacksonville St.": ["Jacksonville State"],
    "Middle Tenn.": ["Middle Tennessee"],
    "Northern Ky.": ["Northern Kentucky"],
    "Central Mich.": ["Central Michigan"],
    "Eastern Mich.": ["Eastern Michigan"],
    "Western Mich.": ["Western Michigan"],
    "N.C. Central": ["NC Central", "North Carolina Central"],
    "South Carolina St.": ["South Carolina State"],
    "Southern Ill.": ["Southern Illinois"],
    "Utah St.": ["Utah State"],
    "Eastern Ill.": ["Eastern Illinois"],
    "Southeast Mo. St.": ["Southeast Missouri State", "SE Missouri State"],
    "Southern Ind.": ["Southern Indiana"],
    "Western Ill.": ["Western Illinois"],
    "Alcorn": ["Alcorn State"],
    "Ark.-Pine Bluff": ["Arkansas-Pine Bluff", "Arkansas Pine Bluff", "UAPB"],
    "Mississippi Val.": ["Mississippi Valley State"],
    "Southern U.": ["Southern", "Southern University"],
    "A&M-Corpus Christi": ["Texas A&M-Corpus Christi", "Texas A&M Corpus Christi"],
    "Northwestern St.": ["Northwestern State"],
    "Southeastern La.": ["Southeastern Louisiana"],
    "North Dakota St.": ["North Dakota State"],
    "South Dakota St.": ["South Dakota State"],
    "St. Thomas (MN)": ["St. Thomas-Minnesota", "St Thomas Minnesota", "St. Thomas"],
    "Boston College": ["Boston College"],
    "USC Upstate": ["USC Upstate", "South Carolina Upstate"],
    "Saint Francis": ["Saint Francis", "Saint Francis (PA)", "St. Francis (PA)"],
    "Mercyhurst": ["Mercyhurst"],
    "Lindenwood": ["Lindenwood"],
}

COMMON_ALIASES = {
    "Miami (FL)": ["Miami", "Miami FL"],
    "Miami (OH)": ["Miami Ohio", "Miami OH"],
    "NC State": ["North Carolina State"],
    "Ole Miss": ["Mississippi"],
    "USC": ["Southern California"],
    "UConn": ["Connecticut"],
    "UNC": ["North Carolina"],
    "LSU": ["Louisiana State"],
    "SMU": ["Southern Methodist"],
    "TCU": ["Texas Christian"],
    "UCF": ["Central Florida"],
    "BYU": ["Brigham Young"],
}

def canonical_set(v):
    raw = str(v or "").strip()
    values = {raw}
    values.update(NCAA_NAME_ALIASES.get(raw, []))
    values.update(COMMON_ALIASES.get(raw, []))
    return {norm(x) for x in values if x}

def flatten_directory(payload):
    found = []
    sports = payload.get("sports") or []
    for sport in sports:
        for league in sport.get("leagues") or []:
            for entry in league.get("teams") or []:
                team = entry.get("team") or entry
                if team:
                    found.append(team)
    if not found:
        for entry in payload.get("teams") or []:
            team = entry.get("team") or entry
            if team:
                found.append(team)
    return found

def team_names(team):
    vals = [
        team.get("location"),
        team.get("shortDisplayName"),
        team.get("displayName"),
        team.get("name"),
        team.get("abbreviation"),
        team.get("slug"),
    ]
    return {norm(v) for v in vals if v}

def candidate_score(wanted, team):
    names = team_names(team)
    best = 0
    for a in wanted:
        if not a:
            continue
        for b in names:
            if not b:
                continue
            if a == b:
                best = max(best, 100)
                continue
            if b.startswith(a + " ") or a.startswith(b + " "):
                best = max(best, 88)
            aw = set(a.split())
            bw = set(b.split())
            if aw and bw:
                overlap = len(aw & bw) / max(len(aw), len(bw))
                if overlap == 1 and min(len(aw),len(bw)) >= 2:
                    best = max(best, 82)
                elif overlap >= 0.75 and min(len(aw),len(bw)) >= 2:
                    best = max(best, 72)
    return best

def match_team(ncaa_name, directory):
    wanted = canonical_set(ncaa_name)
    scored = []
    for team in directory:
        score = candidate_score(wanted, team)
        if score:
            scored.append((score, str(team.get("id")), team))

    if not scored:
        return None

    scored.sort(key=lambda x:(-x[0], x[1]))
    best_score = scored[0][0]
    best = [x for x in scored if x[0] == best_score]

    # Require a strong, unique result. Never guess across tied candidates.
    if best_score < 82 or len(best) != 1:
        return None
    return best[0][2]

def directory_for(gender):
    league = LEAGUES[gender]
    url = TEAM_DIRECTORY.format(league=league)
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    teams = flatten_directory(r.json())
    return teams, url

def match_team(ncaa_name, directory):
    wanted = canonical_set(ncaa_name)

    exact = []
    fuzzy = []
    for team in directory:
        names = team_names(team)
        if wanted & names:
            exact.append(team)
            continue
        for a in wanted:
            for b in names:
                if a and b and (a == b or a in b or b in a):
                    fuzzy.append(team)
                    break
            else:
                continue
            break

    candidates = exact or fuzzy
    unique = {}
    for t in candidates:
        unique[str(t.get("id"))] = t
    candidates = list(unique.values())

    return candidates[0] if len(candidates) == 1 else None

def athlete_from_obj(a):
    pos = a.get("position") or {}
    exp = a.get("experience") or {}
    return {
        "id": str(a.get("id") or ""),
        "name": a.get("fullName") or a.get("displayName") or a.get("shortName"),
        "first_name": a.get("firstName"),
        "last_name": a.get("lastName"),
        "jersey": a.get("jersey"),
        "position": pos.get("abbreviation") or pos.get("displayName") if isinstance(pos, dict) else pos,
        "class": (
            exp.get("displayValue") or exp.get("abbreviation") or exp.get("years")
            if isinstance(exp, dict) else exp
        ),
        "age": a.get("age"),
        "date_of_birth": a.get("dateOfBirth"),
        "height": a.get("displayHeight"),
        "weight": a.get("displayWeight"),
        "headshot": (a.get("headshot") or {}).get("href") if isinstance(a.get("headshot"), dict) else None,
    }

def parse_roster(payload):
    athletes = []
    raw = payload.get("athletes") or []

    for item in raw:
        # College roster responses commonly group athletes by position.
        if isinstance(item, dict) and isinstance(item.get("items"), list):
            for a in item["items"]:
                athletes.append(athlete_from_obj(a))
        elif isinstance(item, dict):
            athletes.append(athlete_from_obj(item))

    # Defensive alternate shapes.
    if not athletes:
        for a in payload.get("items") or []:
            if isinstance(a, dict):
                athletes.append(athlete_from_obj(a))

    dedup = {}
    for a in athletes:
        key = a.get("id") or norm(a.get("name"))
        if key and a.get("name"):
            dedup[key] = a

    return sorted(dedup.values(), key=lambda x:(x.get("last_name") or "", x.get("first_name") or "", x.get("name") or ""))

def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except Exception:
        return None

old_index = {
    (x.get("gender"), x.get("team")): x
    for x in old_cache.get("teams", [])
    if x.get("gender") and x.get("team")
}

directories = {}
directory_urls = {}
for gender in ("Men","Women"):
    directory, directory_url = directory_for(gender)
    directories[gender] = directory
    directory_urls[gender] = directory_url

mapped = []
for t in team_map.get("teams", []):
    if t.get("division") != "Division I" or t.get("gender") not in ("Men","Women"):
        continue
    key = (t["gender"], t["team"])
    old = old_index.get(key, {})
    matched = match_team(t["team"], directories[t["gender"]])

    row = {
        "gender": t["gender"],
        "division": "Division I",
        "conference": t.get("conference"),
        "team": t.get("team"),
        "ncaa_team_url": t.get("team_url"),
        "espn_team_id": str(matched.get("id")) if matched and matched.get("id") is not None else old.get("espn_team_id"),
        "espn_team_name": matched.get("displayName") if matched else old.get("espn_team_name"),
        "roster_source_url": old.get("roster_source_url"),
        "last_checked": old.get("last_checked"),
        "status": old.get("status") or "SOURCE GAP",
        "athletes": old.get("athletes") or [],
        "error": old.get("error"),
    }
    mapped.append(row)

loaded_existing = sum(1 for x in mapped if x.get("status") in ("LOADED","PARTIAL"))
force_initial = loaded_existing < max(25, int(len(mapped) * 0.50))
refresh_all = FULL_REFRESH or force_initial

cutoff = NOW - datetime.timedelta(days=STALE_DAYS)
candidates = []
for row in mapped:
    checked = parse_dt(row.get("last_checked"))
    stale = checked is None or checked < cutoff
    if refresh_all or stale or row.get("status") == "SOURCE GAP":
        candidates.append(row)

# On controlled scheduled runs, prioritize source gaps, then oldest checks.
def priority(row):
    gap = 0 if row.get("status") == "SOURCE GAP" else 1
    dt = parse_dt(row.get("last_checked"))
    stamp = dt.timestamp() if dt else 0
    return (gap, stamp, row.get("gender"), row.get("conference") or "", row.get("team") or "")

candidates.sort(key=priority)
if not refresh_all:
    candidates = candidates[:MAX_TEAMS]

attempted = 0
success = 0
for row in candidates:
    attempted += 1
    gender = row["gender"]
    league = LEAGUES[gender]

    if not row.get("espn_team_id"):
        matched = match_team(row["team"], directories[gender])
        if matched:
            row["espn_team_id"] = str(matched.get("id"))
            row["espn_team_name"] = matched.get("displayName")

    if not row.get("espn_team_id"):
        row["status"] = "SOURCE GAP"
        row["error"] = "No unique ESPN team match."
        row["last_checked"] = NOW_ISO
        continue

    url = ROSTER_URL.format(league=league, team_id=row["espn_team_id"])
    row["roster_source_url"] = url
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        athletes = parse_roster(r.json())
        row["athletes"] = athletes
        row["last_checked"] = NOW_ISO
        row["error"] = None
        if len(athletes) >= 8:
            row["status"] = "LOADED"
            success += 1
        elif athletes:
            row["status"] = "PARTIAL"
            success += 1
        else:
            row["status"] = "SOURCE GAP"
            row["error"] = "Roster response contained no athletes."
    except Exception as exc:
        # Preserve an older good roster if we have one; mark partial rather than erase it.
        row["last_checked"] = NOW_ISO
        row["error"] = str(exc)[:180]
        if row.get("athletes"):
            row["status"] = "PARTIAL"
        else:
            row["status"] = "SOURCE GAP"

    time.sleep(0.08)

mapped.sort(key=lambda x:(x["gender"], x.get("conference") or "", x["team"]))

athletes_cached = sum(len(x.get("athletes") or []) for x in mapped)
athletes_with_age = sum(
    1 for x in mapped for a in (x.get("athletes") or [])
    if a.get("age") not in (None,"")
)
athletes_with_dob = sum(
    1 for x in mapped for a in (x.get("athletes") or [])
    if a.get("date_of_birth")
)

summary = {
    "teams_total": len(mapped),
    "teams_loaded": sum(1 for x in mapped if x.get("status") == "LOADED"),
    "teams_partial": sum(1 for x in mapped if x.get("status") == "PARTIAL"),
    "teams_source_gap": sum(1 for x in mapped if x.get("status") == "SOURCE GAP"),
    "athletes_cached": athletes_cached,
    "athletes_with_age": athletes_with_age,
    "athletes_with_dob": athletes_with_dob,
    "teams_attempted_this_run": attempted,
    "teams_succeeded_this_run": success,
}

out = {
    "schema_version": 1,
    "generated_at": NOW_ISO,
    "source": {
        "team_universe": "NCAA.com Division I basketball map",
        "rosters": "ESPN public college basketball roster feed",
        "directory_urls": directory_urls,
    },
    "refresh": {
        "full_refresh": refresh_all,
        "requested_full_refresh": FULL_REFRESH,
        "stale_days": STALE_DAYS,
        "max_teams": MAX_TEAMS,
    },
    "summary": summary,
    "teams": mapped,
}

CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

print(json.dumps({
    "mode": "FULL" if refresh_all else "BATCH",
    **summary
}))
