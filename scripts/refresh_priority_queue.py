#!/usr/bin/env python3
from pathlib import Path
import json, datetime, re, unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOW = datetime.datetime.now(datetime.timezone.utc)

def load(name, default):
    p = DATA/name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(fc|cf|afc|sc|sv|if|fk|ac|as|ogc|rc|estac)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def team_in_event(team, event_name):
    t = norm(team)
    e = norm(event_name)
    if not t or not e:
        return False
    if t in e:
        return True
    # Token overlap fallback for names such as "Bayern Munich" / "FC Bayern München".
    toks = [x for x in t.split() if len(x) >= 4]
    return len(toks) >= 1 and sum(1 for x in toks if x in e.split()) >= min(2, len(toks))

def add_card(cards, seen, **card):
    key = card.get("key") or (
        card.get("type"), card.get("athlete"), card.get("event"),
        card.get("team"), card.get("title")
    )
    key = str(key)
    if key in seen:
        return
    seen.add(key)
    cards.append(card)

schedule = load("global-schedule.json", {"events":[],"coverage_gaps":[]})
known = load("known-u18.json", {"records":[]})
football = load("ncaa-football-data.json", {"known_u18":[],"coverage_alerts":[]})
age_review = load("ncaa-football-age-review.json", {"age_review_needed":[],"unresolved":[]})
college = load("nebraska-collegiate-live.json", {"events":[],"sources":[]})
catalog = load("catalog-live.json", {"restrictions":[]})

cards=[]
seen=set()

# --------------------------------------------------
# A) International soccer Known U18 ↔ scheduled match
# --------------------------------------------------
soccer_records=[x for x in known.get("records",[]) if x.get("sport")=="Soccer"]
soccer_events=[e for e in schedule.get("events",[]) if e.get("sport")=="Soccer" and e.get("status") in ("UPCOMING","LIVE")]

for player in soccer_records:
    for ev in soccer_events:
        if team_in_event(player.get("team"), ev.get("name")):
            add_card(cards, seen,
                key=f'soccer|{player.get("athlete")}|{ev.get("id")}',
                severity="RED",
                type="U18 ATHLETE",
                sport="Soccer",
                league=ev.get("league") or player.get("league"),
                team=player.get("team"),
                athlete=player.get("athlete"),
                age=player.get("age"),
                event=ev.get("name"),
                start_time=ev.get("start_time"),
                status=ev.get("status"),
                title=f'{player.get("athlete")} · {player.get("team")}',
                reason="Known U18 athlete's club has an approved-catalog match in the current Today + 7 schedule.",
                staff_action="Search this athlete by name in active SWSP markets and review any athlete-specific performance/nonperformance offering.",
                source="Known U18 registry + Approved Sports Schedule"
            )

# --------------------------------------------------
# B) Known/verified NCAA football U18 ↔ scheduled game
# --------------------------------------------------
football_events=[e for e in schedule.get("events",[]) if e.get("league")=="NCAA Football" and e.get("status") in ("UPCOMING","LIVE")]
for player in football.get("known_u18",[]):
    team=player.get("team")
    matches=[e for e in football_events if team_in_event(team,e.get("name"))]
    if matches:
        for ev in matches:
            add_card(cards, seen,
                key=f'ncaa-u18|{player.get("athlete")}|{ev.get("id")}',
                severity="RED",
                type="U18 ATHLETE",
                sport="NCAA Football",
                league="NCAA Football",
                team=team,
                athlete=player.get("athlete"),
                age=player.get("age"),
                event=ev.get("name"),
                start_time=ev.get("start_time"),
                status=ev.get("status"),
                title=f'{player.get("athlete")} · {team}',
                reason="Verified U18 NCAA football athlete is tied to a game in the current Today + 7 schedule.",
                staff_action="Search athlete-specific markets and review any individual performance/nonperformance offering.",
                source="NCAA Football age discovery + Approved Sports Schedule"
            )
    else:
        add_card(cards, seen,
            key=f'ncaa-watch|{player.get("athlete")}|{team}',
            severity="AMBER",
            type="NCAA U18 WATCH",
            sport="NCAA Football",
            league="NCAA Football",
            team=team,
            athlete=player.get("athlete"),
            age=player.get("age"),
            event=None,
            start_time=None,
            status="WATCH",
            title=f'{player.get("athlete")} · {team}',
            reason="Verified U18 NCAA football athlete remains on the watch list; no matching Today + 7 game was resolved in the mapped schedule feed.",
            staff_action="Keep athlete-specific markets on the watch list and confirm upcoming team schedule/source coverage.",
            source="NCAA Football age discovery"
        )

# --------------------------------------------------
# C) NCAA age review / unresolved candidates
# --------------------------------------------------
# Age Vetting is now the primary home for unresolved NCAA athletes.
# Only athletes with current Today + 7 schedule relevance may bubble into
# operational Priority Queue.
age_records = age_review.get("age_review_needed",[]) + age_review.get("unresolved",[])
football_events=[e for e in schedule.get("events",[]) if e.get("league")=="NCAA Football" and e.get("status") in ("UPCOMING","LIVE")]

for player in age_records:
    tier=(player.get("u18_risk_tier") or "UNKNOWN").upper()

    if tier in ("LOW","VERIFIED_18_PLUS"):
        continue

    team=player.get("team")
    matches=[e for e in football_events if team_in_event(team,e.get("name"))]

    if not matches:
        continue

    if tier == "HIGH":
        type_label="AGE REVIEW — HIGH RISK"
    elif tier == "MEDIUM":
        type_label="AGE REVIEW — MEDIUM RISK"
    else:
        type_label="AGE REVIEW NEEDED"

    for ev in matches:
        add_card(cards, seen,
            key=f'age-review|{team}|{player.get("name")}|{ev.get("id")}',
            severity="AMBER",
            type=type_label,
            sport="NCAA Football",
            league="NCAA Football",
            team=team,
            athlete=player.get("name"),
            age=player.get("calculated_age"),
            event=ev.get("name"),
            start_time=ev.get("start_time"),
            status=ev.get("status"),
            title=f'{player.get("name") or "Roster candidate"} · {team}',
            reason=(player.get("u18_risk_reason") or player.get("age_evidence") or
                    "Official age evidence remains unresolved.") +
                   " Team has a game in the current Today + 7 window.",
            staff_action="Prioritize age verification because this athlete's team has a current upcoming game. Class/history is a screening tool only.",
            source="NCAA Football age discovery + Approved Sports Schedule"
        )

# --------------------------------------------------
# D) Nebraska collegiate home-event/site rule
# --------------------------------------------------
for ev in college.get("events",[]):
    if ev.get("status")=="FINAL":
        continue
    if ev.get("site")=="HOME":
        add_card(cards, seen,
            key=f'ne-home|{ev.get("school")}|{ev.get("sport")}|{ev.get("date")}|{ev.get("opponent")}',
            severity="RED",
            type="NOT PERMISSIBLE",
            sport=ev.get("sport"),
            league=f'{ev.get("school")} Collegiate',
            team=ev.get("school"),
            athlete=None,
            age=None,
            event=f'{ev.get("school")} vs {ev.get("opponent")}',
            start_time=f'{ev.get("date")}T{ev.get("time")}' if ev.get("time") and ev.get("time")!="TBA" else ev.get("date"),
            status=ev.get("status"),
            title=f'{ev.get("school")} {ev.get("sport")} home event',
            reason="Nebraska collegiate home event appears in the current Today + 7 schedule.",
            staff_action="Confirm the event is not offered where the Nebraska collegiate site restriction applies.",
            source="Official Nebraska/Creighton schedule feed"
        )

# --------------------------------------------------
# E) Approved scheduled events with restriction signals
# --------------------------------------------------
for ev in schedule.get("events",[]):
    if ev.get("status") not in ("UPCOMING","LIVE"):
        continue
    if not ev.get("restriction_risk"):
        continue

    league=(ev.get("league") or "").strip().upper()
    sport=(ev.get("sport") or "").strip().lower()
    name=(ev.get("name") or "").strip().lower()

    # HARD MLB EXCLUSION:
    # Normal MLB games never become catalog-restriction Priority Queue cards.
    # Only explicitly named special events may pass.
    if league == "MLB":
        allowed_special = any(
            term in name
            for term in ("draft", "spring training", "preseason", "pre-season")
        )
        if not allowed_special:
            continue

    # HARD NCAA FOOTBALL SCOPE:
    # Generic catalog restrictions must never turn the entire NCAA Football
    # schedule into Priority Queue cards. NCAA Football risks are generated by
    # dedicated logic elsewhere in this script:
    #   - verified U18 athlete + scheduled game
    #   - Nebraska collegiate home/site restriction
    #   - NCAA age-review / unresolved player watch
    # Therefore generic CATALOG RESTRICTION cards are suppressed here.
    if league == "NCAA FOOTBALL":
        continue

    add_card(cards, seen,
        key=f'restriction|{ev.get("id")}',
        severity="AMBER",
        type="CATALOG RESTRICTION",
        sport=ev.get("sport"),
        league=ev.get("league"),
        team=None,
        athlete=None,
        age=None,
        event=ev.get("name"),
        start_time=ev.get("start_time"),
        status=ev.get("status"),
        title=f'{ev.get("league")} · {ev.get("name")}',
        reason="Current approved-catalog schedule event intersects with one or more restriction signals.",
        staff_action="Review the applicable catalog restriction and confirm the active SWSP markets comply.",
        source="Current NRGC catalog + Approved Sports Schedule"
    )

# --------------------------------------------------
# F) Tennis U18 watch: keep visible until automated draw adapter exists
# --------------------------------------------------
tennis_records=[x for x in known.get("records",[]) if x.get("sport")=="Tennis"]
if tennis_records:
    # One compact lane card rather than dozens of permanent static cards.
    names=[x.get("athlete") for x in tennis_records if x.get("athlete")]
    add_card(cards, seen,
        key="tennis-u18-watch-lane",
        severity="AMBER",
        type="TENNIS U18 WATCH",
        sport="Tennis",
        league="ATP / WTA / ITF / UTR / Grand Slams",
        team=None,
        athlete=None,
        age=None,
        event=None,
        start_time=None,
        status="WATCH",
        title=f'{len(tennis_records)} known U18 tennis athletes',
        reason="Known U18 tennis registry is active, but automated draw/match-to-player matching is not yet complete.",
        staff_action="Prioritize current draws/entry lists and search known U18 names before clearing player-specific markets.",
        source="Known U18 registry",
        names=names
    )

# --------------------------------------------------
# G) Coverage/source issues
# --------------------------------------------------
for gap in schedule.get("coverage_gaps",[]):
    if gap.get("area") in ("Tennis","Soccer"):
        add_card(cards, seen,
            key=f'coverage-gap|{gap.get("area")}',
            severity="AMBER",
            type="SOURCE COVERAGE",
            sport=gap.get("area"),
            league=gap.get("area"),
            team=None,
            athlete=None,
            age=None,
            event=None,
            start_time=None,
            status="COVERAGE GAP",
            title=f'{gap.get("area")} schedule coverage incomplete',
            reason=gap.get("note"),
            staff_action="Do not interpret a lack of matched events as no risk. Continue manual/secondary source review until the adapter is complete.",
            source="Approved Sports Schedule coverage control"
        )

# Priority order: RED first; timed upcoming next; then amber watches.
sev_rank={"RED":0,"AMBER":1}
def sort_key(c):
    return (
        sev_rank.get(c.get("severity"),9),
        c.get("start_time") is None,
        c.get("start_time") or "9999",
        c.get("sport") or "",
        c.get("title") or ""
    )
# Final defensive purge: never publish ordinary MLB restriction cards.
cards = [
    c for c in cards
    if not (
        c.get("type") == "CATALOG RESTRICTION"
        and str(c.get("league") or "").strip().upper() == "MLB"
        and not any(
            term in str(c.get("event") or "").lower()
            for term in ("draft","spring training","preseason","pre-season")
        )
    )
]

# Final defensive purge:
# ordinary NCAA Football games cannot be generic CATALOG RESTRICTION cards.
cards = [
    c for c in cards
    if not (
        c.get("type") == "CATALOG RESTRICTION"
        and str(c.get("league") or "").strip().upper() == "NCAA FOOTBALL"
    )
]

cards.sort(key=sort_key)

out={
    "schema_version":1,
    "generated_at":NOW.isoformat(),
    "card_count":len(cards),
    "red_count":sum(1 for x in cards if x.get("severity")=="RED"),
    "amber_count":sum(1 for x in cards if x.get("severity")=="AMBER"),
    "cards":cards
}
(DATA/"priority-queue.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({
    "cards":len(cards),
    "red":out["red_count"],
    "amber":out["amber_count"],
    "soccer_u18_matches":sum(1 for x in cards if x.get("type")=="U18 ATHLETE" and x.get("sport")=="Soccer"),
    "ncaa_u18":sum(1 for x in cards if x.get("type") in ("U18 ATHLETE","NCAA U18 WATCH") and x.get("sport")=="NCAA Football")
}))
