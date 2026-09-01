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
# EVENT-FIRST PRIORITY QUEUE
# --------------------------------------------------
# Priority Queue answers one question:
# "Which CURRENT / UPCOMING Today + 7 events need a sportsbook check?"
#
# Research inventories (age vetting, source coverage, generic watch lists)
# live in their dedicated site sections and do not create Priority Queue cards.

event_cards = {}
def event_key(ev):
    return str(ev.get("id") or f"{ev.get('league')}|{ev.get('name')}|{ev.get('start_time')}")

def ensure_event(ev, severity="AMBER", reason_type="REVIEW"):
    key=event_key(ev)
    if key not in event_cards:
        event_cards[key]={
            "key":f"event|{key}",
            "severity":severity,
            "type":reason_type,
            "sport":ev.get("sport"),
            "league":ev.get("league"),
            "event":ev.get("name"),
            "start_time":ev.get("start_time"),
            "status":ev.get("status"),
            "title":ev.get("name"),
            "athletes":[],
            "triggers":[],
            "staff_actions":[]
        }
    card=event_cards[key]
    if severity=="RED":
        card["severity"]="RED"
    return card

def push_unique(arr, value):
    if value and value not in arr:
        arr.append(value)

# A) Known U18 international soccer athlete + upcoming club match.
soccer_records=[x for x in known.get("records",[]) if x.get("sport")=="Soccer"]
soccer_events=[e for e in schedule.get("events",[]) if e.get("sport")=="Soccer" and e.get("status") in ("UPCOMING","LIVE")]

for player in soccer_records:
    for ev in soccer_events:
        if team_in_event(player.get("team"), ev.get("name")):
            c=ensure_event(ev,"RED","U18 EXPOSURE")
            push_unique(c["athletes"], player.get("athlete"))
            push_unique(c["triggers"], f"Known U18 — {player.get('athlete')} ({player.get('team')})")
            push_unique(c["staff_actions"], "Search known U18 athlete names in active SWSP markets and review athlete-specific performance/nonperformance offerings.")

# B) Verified NCAA Football U18 + upcoming team game.
football_events=[e for e in schedule.get("events",[]) if e.get("league")=="NCAA Football" and e.get("status") in ("UPCOMING","LIVE")]

for player in football.get("known_u18",[]):
    team=player.get("team")
    for ev in football_events:
        if team_in_event(team, ev.get("name")):
            c=ensure_event(ev,"RED","U18 EXPOSURE")
            push_unique(c["athletes"], player.get("athlete"))
            push_unique(c["triggers"], f"Verified U18 — {player.get('athlete')} ({team})")
            push_unique(c["staff_actions"], "Review athlete-specific NCAA markets involving the verified U18 participant.")

# C) HIGH-risk unresolved NCAA athletes only, aggregated by current game.
# MEDIUM / LOW / UNKNOWN remain in NCAA Football Age Vetting.
age_records = age_review.get("age_review_needed",[]) + age_review.get("unresolved",[])
for player in age_records:
    tier=(player.get("u18_risk_tier") or "UNKNOWN").upper()
    if tier != "HIGH":
        continue
    team=player.get("team")
    for ev in football_events:
        if team_in_event(team, ev.get("name")):
            c=ensure_event(ev,"AMBER","NCAA AGE REVIEW")
            push_unique(c["athletes"], player.get("name"))
            push_unique(c["triggers"], f"High-risk unresolved age — {player.get('name')} ({team})")
            push_unique(c["staff_actions"], "Prioritize age verification for high-risk roster candidates tied to this upcoming game.")

# D) Nebraska collegiate home/site restrictions.
for ev in college.get("events",[]):
    if ev.get("status")=="FINAL" or ev.get("site")!="HOME":
        continue
    # Match or synthesize an event-shaped object for the operational queue.
    ev_obj={
        "id":f"ne|{ev.get('school')}|{ev.get('sport')}|{ev.get('date')}|{ev.get('opponent')}",
        "sport":ev.get("sport"),
        "league":f"{ev.get('school')} Collegiate",
        "name":f"{ev.get('school')} vs {ev.get('opponent')}",
        "start_time":f"{ev.get('date')}T{ev.get('time')}" if ev.get("time") and ev.get("time")!="TBA" else ev.get("date"),
        "status":ev.get("status") or "UPCOMING"
    }
    c=ensure_event(ev_obj,"RED","NOT PERMISSIBLE")
    push_unique(c["triggers"], "Nebraska collegiate home-event/site restriction")
    push_unique(c["staff_actions"], "Confirm the event is not offered where the Nebraska collegiate site restriction applies.")

# E) Event-specific catalog restrictions only.
for ev in schedule.get("events",[]):
    if ev.get("status") not in ("UPCOMING","LIVE") or not ev.get("restriction_risk"):
        continue

    league=(ev.get("league") or "").strip().upper()
    name=(ev.get("name") or "").strip().lower()

    # Ordinary MLB games do not inherit Draft / Spring Training restrictions.
    if league=="MLB":
        special=any(term in name for term in ("draft","spring training","preseason","pre-season"))
        if not special:
            continue

    # Ordinary NCAA Football games do not inherit generic NCAA restrictions.
    if league=="NCAA FOOTBALL":
        continue

    c=ensure_event(ev,"AMBER","CATALOG RESTRICTION")
    signals=ev.get("restriction_signals") or []
    for sig in signals[:4]:
        push_unique(c["triggers"], str(sig))
    push_unique(c["staff_actions"], "Review the applicable catalog restriction and confirm active SWSP markets comply.")

# Finalize event cards.
cards=[]
for c in event_cards.values():
    athlete_count=len(c.get("athletes") or [])
    if athlete_count:
        c["title"]=f"{c.get('event')} · {athlete_count} athlete{'s' if athlete_count!=1 else ''}"
    c["reason"]=" | ".join(c.get("triggers") or [])
    c["staff_action"]=" ".join(c.get("staff_actions") or [])
    cards.append(c)

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
