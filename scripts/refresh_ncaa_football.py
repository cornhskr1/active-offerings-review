#!/usr/bin/env python3
from pathlib import Path
import json, datetime, urllib.request, re, html
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG_PATH = DATA / "ncaa-football-sources.json"
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))
REVIEW_PATH = DATA / "review-data.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"}
TZ = ZoneInfo("America/Chicago")
NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()

FRESHMAN_RE = re.compile(r"\b(true\s+freshman|freshman|first[- ]year|fr\.)\b", re.I)
RECLASS_RE = re.compile(
    r"\b(reclassif(?:ied|ication)|early enrollee|"
    r"forgo(?:es|ne)? (?:his|her) senior year|"
    r"skipp?ed (?:his|her) senior year)\b", re.I
)

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12
}

def fetch(url, timeout=16, max_bytes=950000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        return {
            "ok": 200 <= getattr(resp, "status", 200) < 400,
            "status": getattr(resp, "status", 200),
            "final_url": resp.geturl(),
            "html": raw.decode("utf-8", errors="ignore")
        }

def strip_tags(src):
    if not src:
        return ""
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", src)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def validate_football_page(result, kind):
    if not result or not result.get("ok"):
        return False
    txt = strip_tags(result.get("html","")).lower()
    url = result.get("final_url","").lower()
    if "football" not in txt and "footbl" not in url and "football" not in url:
        return False
    if kind == "schedule":
        return "schedule" in txt or "schedule" in url
    return "roster" in txt or "roster" in url

def discover(team, kind):
    roots = team.get("candidate_roots", [])
    defaults = CFG["path_candidates"][kind]
    overrides = (team.get("path_overrides") or {}).get(kind, [])
    candidates = overrides + [p for p in defaults if p not in overrides]
    for root in roots:
        for path in candidates:
            url = root.rstrip("/") + path
            try:
                r = fetch(url)
                if validate_football_page(r, kind):
                    return {"ok":True, "url":r["final_url"], "html":r["html"], "root":root}
            except Exception:
                pass
    return {"ok":False, "url":None, "html":""}

def slug_to_name(href):
    path = urlparse(href).path.rstrip("/")
    parts = path.split("/")
    last = parts[-1]
    if last.isdigit() and len(parts) >= 2:
        last = parts[-2]
    last = re.sub(r"[-_]+", " ", last)
    last = re.sub(r"\b\d+\b", "", last)
    return " ".join(w.capitalize() for w in last.split()).strip()

def looks_like_player_name(text):
    text = (text or "").strip()
    if not text or len(text) < 3 or len(text) > 70:
        return False
    low = text.lower()
    reject = [
        "jersey number", "roster", "bio", "profile", "football",
        "opens in a new window", "instagram", "twitter", "x.com",
        "facebook", "linkedin", "previous", "next"
    ]
    if any(x in low for x in reject):
        return False
    if re.fullmatch(r"[\d#\s\-–—]+", text):
        return False
    # Require at least two alphabetic name tokens for automated player identity.
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’.-]+", text)
    return len(tokens) >= 2

def profile_links_from_roster(roster_url, roster_html):
    links = []
    seen = set()
    pattern = re.compile(r"(?is)<a\b[^>]*href=[\"']([^\"']*roster[^\"']*)[\"'][^>]*>(.*?)</a>")
    for m in pattern.finditer(roster_html):
        href = html.unescape(m.group(1))
        if href.startswith("#") or "season/" in href.lower():
            continue
        full = urljoin(roster_url, href)
        path = urlparse(full).path.lower().rstrip("/")
        if path.endswith("/roster"):
            continue
        if full in seen:
            continue

        anchor_text = strip_tags(m.group(2)).strip()
        slug_name = slug_to_name(full)

        # Roster sites often wrap jersey number and player name in separate links
        # pointing to the same bio. Never treat "Jersey Number 0" as a player.
        if looks_like_player_name(anchor_text):
            name = anchor_text
        elif looks_like_player_name(slug_name):
            name = slug_name
        else:
            continue

        start = max(0, m.start()-1200)
        end = min(len(roster_html), m.end()+1600)
        nearby = strip_tags(roster_html[start:end])

        freshman = bool(FRESHMAN_RE.search(nearby))
        reclass = bool(RECLASS_RE.search(nearby))
        if freshman or reclass:
            links.append({
                "name": name,
                "profile_url": full,
                "freshman_signal": freshman,
                "reclassification_signal": reclass
            })
            seen.add(full)
    return links

def parse_explicit_dob(text):
    """
    Conservative DOB parser.

    IMPORTANT:
    A bare date anywhere on a player page is NOT birth evidence. Athletics bios
    contain game dates, award dates, class years, article dates, and metadata.
    Automated verification only accepts a date immediately associated with
    explicit birth language: Born, Date of Birth, DOB, or Birthday.
    """
    label = r"(?:date\s+of\s+birth|dob|birthday|born)"
    month = (
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|"
        r"Sep|Sept|Oct|Nov|Dec)"
    )

    # Born: September 16, 2008
    m = re.search(
        rf"\b{label}\b\s*(?:is|on)?\s*[:\-]?\s*"
        rf"{month}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+((?:19|20)\d{{2}})\b",
        text, re.I
    )
    if m:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
        except ValueError:
            pass

    # DOB: 09/16/2008
    m = re.search(
        rf"\b{label}\b\s*(?:is|on)?\s*[:\-]?\s*"
        r"(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})\b",
        text, re.I
    )
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    # Born 16 September 2008
    m = re.search(
        rf"\b{label}\b\s*(?:is|on)?\s*[:\-]?\s*"
        rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+{month}\.?\s+((?:19|20)\d{{2}})\b",
        text, re.I
    )
    if m:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            pass

    return None

def age_on(dob, on_date):
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))

def class_conflict(text, age):
    """
    A claimed U18 age conflicts with class/status language that normally
    represents multiple prior collegiate seasons. This is not proof of age;
    it is a safeguard that prevents automated VERIFIED U18 classification.
    """
    if age >= 18:
        return None
    conflict_patterns = [
        (r"\bfifth[- ]year\b", "Fifth Year"),
        (r"\bgraduate\b", "Graduate"),
        (r"\bpost[- ]?baccalaureate\b", "Post-Baccalaureate"),
        (r"\bsenior\b", "Senior"),
        (r"\bredshirt senior\b", "Redshirt Senior"),
    ]
    for pattern, label in conflict_patterns:
        if re.search(pattern, text, re.I):
            return label
    return None

def explicit_age_statement(text):
    """
    Narrative ages are useful review evidence, but are not strong enough for
    automated VERIFIED status because a bio can mention siblings, recruits,
    historical ages, etc. Return the age only as a review signal.
    """
    patterns = [
        r"\bage\s*[:\-]\s*(1[5-9]|2[0-9])\b",
        r"\b(1[5-9]|2[0-9])[- ]year[- ]old\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return int(m.group(1))
    return None

def classify_bio(candidate):
    result = dict(candidate)
    result.update({
        "bio_checked_at": NOW.isoformat(),
        "bio_ok": False,
        "dob": None,
        "calculated_age": None,
        "age_status": "AGE REVIEW NEEDED",
        "age_evidence": None,
        "evidence_type": None
    })
    try:
        r = fetch(candidate["profile_url"], timeout=14, max_bytes=700000)
        if not r["ok"]:
            result["age_status"] = "UNRESOLVED"
            result["age_evidence"] = "Official bio could not be retrieved."
            return result

        result["bio_ok"] = True
        result["profile_url"] = r["final_url"]
        text = strip_tags(r["html"])

        dob = parse_explicit_dob(text)
        if dob:
            age = age_on(dob, TODAY)

            # Hard plausibility gate for NCAA football.
            if dob > TODAY:
                result["age_status"] = "AGE REVIEW NEEDED"
                result["age_evidence"] = f"Rejected birth date {dob.isoformat()}: date is in the future."
                result["evidence_type"] = "PARSER CONFLICT"
                return result

            if age < 15 or age > 40:
                result["age_status"] = "AGE REVIEW NEEDED"
                result["age_evidence"] = (
                    f"Rejected birth date {dob.isoformat()}: calculated age {age} is outside "
                    "the plausible NCAA football review range (15–40)."
                )
                result["evidence_type"] = "PARSER CONFLICT"
                return result

            conflict = class_conflict(text, age)
            if conflict:
                result["age_status"] = "AGE REVIEW NEEDED"
                result["dob"] = dob.isoformat()
                result["calculated_age"] = age
                result["age_evidence"] = (
                    f"Official page contains explicit birth date {dob.isoformat()}, but calculated "
                    f"age {age} conflicts with class/status language ({conflict}). Manual review required."
                )
                result["evidence_type"] = "CLASS CONFLICT"
                return result

            result["dob"] = dob.isoformat()
            result["calculated_age"] = age
            result["age_status"] = "VERIFIED U18" if age < 18 else "VERIFIED 18+"
            result["age_evidence"] = (
                f"Official player bio explicitly labels birth date {dob.isoformat()}; "
                f"age {age} on {TODAY.isoformat()}."
            )
            result["evidence_type"] = "EXPLICIT DOB"
            return result

        narrative_age = explicit_age_statement(text)
        if narrative_age is not None:
            result["calculated_age"] = narrative_age
            result["age_status"] = "AGE REVIEW NEEDED"
            result["age_evidence"] = (
                f"Official bio contains an age-{narrative_age} statement, but no explicit labeled DOB "
                "was found. Treat as review evidence, not automated verification."
            )
            result["evidence_type"] = "NARRATIVE AGE"
            return result

        if RECLASS_RE.search(text):
            result["age_status"] = "AGE REVIEW NEEDED"
            result["age_evidence"] = (
                "Official bio contains reclassification/early-enrollee language but no explicit labeled DOB."
            )
            result["evidence_type"] = "RECLASS SIGNAL"
        else:
            result["age_status"] = "UNRESOLVED"
            result["age_evidence"] = (
                "Official bio checked; no explicit labeled DOB was found. Bare dates elsewhere on the page are ignored."
            )
            result["evidence_type"] = "NO DOB"
        return result

    except Exception as e:
        result["error"] = str(e)[:180]
        result["age_status"] = "UNRESOLVED"
        result["age_evidence"] = "Official bio check failed."
        return result

def load_review():
    if REVIEW_PATH.exists():
        try:
            return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema_version":1,"review_window_days":7,"events":[],"u18_matches":[],"restriction_triggers":[],"coverage_alerts":[]}

team_results = []
coverage_alerts = []
all_candidates = []
known_seed = []

for team in CFG["teams"]:
    schedule = discover(team, "schedule")
    roster = discover(team, "roster")

    if schedule["ok"] and roster["ok"]:
        mapping_status = "AUTO-MAPPED"
    elif schedule["ok"] or roster["ok"]:
        mapping_status = "PARTIAL"
    else:
        mapping_status = "UNRESOLVED"

    team["mapped"] = mapping_status in ("AUTO-MAPPED","PARTIAL")
    team["mapping_status"] = mapping_status
    team["last_mapping_check"] = NOW.isoformat()
    if schedule["ok"]:
        team["schedule_url"] = schedule["url"]
    if roster["ok"]:
        team["roster_url"] = roster["url"]
    if schedule.get("root") or roster.get("root"):
        team["official_root"] = schedule.get("root") or roster.get("root")

    candidates = profile_links_from_roster(roster.get("url") or "", roster.get("html","")) if roster["ok"] else []
    for c in candidates:
        c["team"] = team["team"]
        c["conference"] = team.get("conference")
        c["sport"] = "NCAA Football"
    all_candidates.extend(candidates)

    for a in team.get("known_u18", []):
        known_seed.append({
            "team":team["team"], "conference":team.get("conference"),
            "athlete":a["name"], "age":a["age"], "position":a.get("position"),
            "evidence_url":a.get("evidence_url"), "age_evidence":a.get("evidence_note")
        })

    team_results.append({
        "team":team["team"],
        "conference":team.get("conference"),
        "mapping_status":mapping_status,
        "schedule_ok":schedule["ok"],
        "roster_ok":roster["ok"],
        "schedule_url":team.get("schedule_url"),
        "roster_url":team.get("roster_url"),
        "candidate_count":len(candidates)
    })

dedup = {}
for c in all_candidates:
    dedup[(c["team"], c["profile_url"])] = c
all_candidates = list(dedup.values())

screened = []
with ThreadPoolExecutor(max_workers=18) as ex:
    futures = {ex.submit(classify_bio, c): c for c in all_candidates}
    for fut in as_completed(futures):
        try:
            screened.append(fut.result())
        except Exception as e:
            c = futures[fut]
            x = dict(c)
            x.update({"bio_ok":False,"age_status":"UNRESOLVED","error":str(e)[:180]})
            screened.append(x)

verified_keys = {(x.get("team"), (x.get("name") or "").lower()) for x in screened if x.get("age_status")=="VERIFIED U18"}
for seed in known_seed:
    key = (seed["team"], seed["athlete"].lower())
    if key not in verified_keys:
        screened.append({
            "sport":"NCAA Football",
            "team":seed["team"],
            "conference":seed.get("conference"),
            "name":seed["athlete"],
            "profile_url":seed.get("evidence_url"),
            "bio_ok":True,
            "calculated_age":seed.get("age"),
            "age_status":"VERIFIED U18",
            "age_evidence":seed.get("age_evidence"),
            "seeded_verified":True
        })

by_team = {t["team"]: {"candidates":0,"verified_u18":0,"verified_18plus":0,"review_needed":0,"unresolved":0} for t in team_results}
for p in screened:
    m = by_team.setdefault(p["team"], {"candidates":0,"verified_u18":0,"verified_18plus":0,"review_needed":0,"unresolved":0})
    if not p.get("seeded_verified"):
        m["candidates"] += 1
    st = p.get("age_status")
    if st == "VERIFIED U18": m["verified_u18"] += 1
    elif st == "VERIFIED 18+": m["verified_18plus"] += 1
    elif st == "AGE REVIEW NEEDED": m["review_needed"] += 1
    else: m["unresolved"] += 1

for tr in team_results:
    m = by_team[tr["team"]]
    tr.update(m)
    if tr["mapping_status"] == "UNRESOLVED" or not tr["roster_ok"]:
        age_state = "UNMAPPED"
    elif m["review_needed"] or m["unresolved"] or m["candidates"] == 0:
        age_state = "PARTIAL"
    else:
        age_state = "SCREENED HIGH-RISK COHORT"
    tr["age_coverage"] = age_state
    coverage_alerts.append({
        "sport":"NCAA Football","league":"NCAA FBS",
        "team":tr["team"],"conference":tr.get("conference"),
        "mapped":tr["mapping_status"] != "UNRESOLVED",
        "mapping_status":tr["mapping_status"],
        "schedule_ok":tr["schedule_ok"],"participants_ok":tr["roster_ok"],
        "age_coverage":age_state,
        "known_u18_count":m["verified_u18"],
        "review_needed_count":m["review_needed"],
        "unresolved_count":m["unresolved"],
        "coverage_state":"PARTIAL" if age_state != "UNMAPPED" else "UNMAPPED",
        "checked_at":NOW.isoformat()
    })

verified_u18 = [p for p in screened if p.get("age_status") == "VERIFIED U18"]
verified_18 = [p for p in screened if p.get("age_status") == "VERIFIED 18+"]
review_needed = [p for p in screened if p.get("age_status") == "AGE REVIEW NEEDED"]
unresolved = [p for p in screened if p.get("age_status") == "UNRESOLVED"]

age_out = {
    "schema_version":4,
    "generated_at":NOW.isoformat(),
    "screening_date":TODAY.isoformat(),
    "sport":"NCAA Football",
    "scope":"FBS high-risk age discovery",
    "method":"Roster-first screening of freshman/reclassification candidates followed by official bio review.",
    "candidates_extracted":len(all_candidates),
    "bios_screened":len(screened),
    "verified_u18_count":len(verified_u18),
    "verified_18plus_count":len(verified_18),
    "age_review_needed_count":len(review_needed),
    "unresolved_count":len(unresolved),
    "verified_u18":verified_u18,
    "verified_18plus":verified_18,
    "age_review_needed":review_needed,
    "unresolved":unresolved,
    "team_metrics":team_results
}
(DATA/"ncaa-football-age-review.json").write_text(json.dumps(age_out, indent=2), encoding="utf-8")

football_out = {
    "schema_version":4,
    "generated_at":NOW.isoformat(),
    "sport":"NCAA Football",
    "scope":"FBS auto-mapping + age discovery",
    "teams_total":len(team_results),
    "teams_mapped":sum(1 for t in team_results if t["mapping_status"]=="AUTO-MAPPED"),
    "teams_partial":sum(1 for t in team_results if t["mapping_status"]=="PARTIAL"),
    "teams_unmapped":sum(1 for t in team_results if t["mapping_status"]=="UNRESOLVED"),
    "known_u18":[
        {
            "sport":"NCAA Football","league":"NCAA FBS","team":p["team"],
            "athlete":p.get("name"),"age":p.get("calculated_age"),
            "status":"VERIFIED U18","evidence_url":p.get("profile_url"),
            "evidence_note":p.get("age_evidence"),"checked_at":NOW.isoformat()
        } for p in verified_u18
    ],
    "coverage_alerts":coverage_alerts,
    "teams":team_results,
    "conference_counts":{}
}
for t in CFG["teams"]:
    c=t.get("conference","Unknown")
    football_out["conference_counts"][c]=football_out["conference_counts"].get(c,0)+1

(DATA/"ncaa-football-data.json").write_text(json.dumps(football_out, indent=2), encoding="utf-8")

CFG["last_auto_map_run"] = NOW.isoformat()
CFG["last_age_discovery_run"] = NOW.isoformat()
CFG_PATH.write_text(json.dumps(CFG, indent=2), encoding="utf-8")

review = load_review()
review["background_checked_at"] = NOW.isoformat()
review["generated_at"] = NOW.isoformat()
review["u18_matches"] = [x for x in review.get("u18_matches",[]) if x.get("sport")!="NCAA Football"] + football_out["known_u18"]
review["coverage_alerts"] = [x for x in review.get("coverage_alerts",[]) if x.get("sport")!="NCAA Football"] + coverage_alerts
review["age_review_needed"] = [x for x in review.get("age_review_needed",[]) if x.get("sport")!="NCAA Football"] + [
    {
        "sport":"NCAA Football","team":p["team"],"athlete":p.get("name"),
        "profile_url":p.get("profile_url"),"status":p.get("age_status"),
        "reason":p.get("age_evidence"),"checked_at":NOW.isoformat()
    } for p in review_needed + unresolved
]
REVIEW_PATH.write_text(json.dumps(review, indent=2), encoding="utf-8")

print(json.dumps({
    "generated_at":NOW.isoformat(),
    "teams_total":len(team_results),
    "auto_mapped":football_out["teams_mapped"],
    "partial_mapping":football_out["teams_partial"],
    "unresolved_mapping":football_out["teams_unmapped"],
    "candidates_extracted":len(all_candidates),
    "bios_screened":len(screened),
    "verified_u18":len(verified_u18),
    "verified_18plus":len(verified_18),
    "age_review_needed":len(review_needed),
    "unresolved_age":len(unresolved)
}))
