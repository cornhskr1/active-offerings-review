import json, hashlib, datetime, re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TZ=ZoneInfo("America/Chicago")
NOW=datetime.datetime.now(datetime.timezone.utc)
TODAY=datetime.datetime.now(TZ).date()
END=TODAY+datetime.timedelta(days=7)

def load(path,default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",str(s or "").lower()).strip()

known=load(DATA/"tennis-known-u18.json",{}).get("records",[])
schedule=load(DATA/"global-schedule.json",{})
previous=load(DATA/"tennis-intelligence.json",{})

lanes=[
    {"id":"itf-men","label":"ITF Men","coverage":"SOURCE ADAPTER PENDING","source":"ITF official calendar/draw/player profile","primary_age_source":"ITF official player profile"},
    {"id":"itf-women","label":"ITF Women","coverage":"SOURCE ADAPTER PENDING","source":"ITF official calendar/draw/player profile","primary_age_source":"ITF official player profile"},
    {"id":"atp","label":"ATP","coverage":"MAPPED PUBLIC SCHEDULE","source":"Mapped public ATP scoreboard schedule","primary_age_source":"ATP / ITF official profile"},
    {"id":"wta","label":"WTA","coverage":"MAPPED PUBLIC SCHEDULE","source":"Mapped public WTA scoreboard schedule","primary_age_source":"WTA / ITF official profile"},
    {"id":"utr-men","label":"UTR Men","coverage":"SOURCE ADAPTER PENDING","source":"UTR Pro Tennis Tour field/schedule","primary_age_source":"Official profile where available"},
    {"id":"utr-women","label":"UTR Women","coverage":"SOURCE ADAPTER PENDING","source":"UTR Pro Tennis Tour field/schedule","primary_age_source":"Official profile where available"},
    {"id":"grand-slams","label":"Grand Slams","coverage":"DERIVED FROM ATP/WTA WHEN PRESENT","source":"Official event draw/order of play preferred","primary_age_source":"ATP / WTA / ITF / official event profile"},
]

def lane_for(e):
    league=str(e.get("league") or "").upper()
    comp=str(e.get("competition") or e.get("tournament") or e.get("name") or "").upper()
    if any(x in comp for x in ("AUSTRALIAN OPEN","ROLAND GARROS","FRENCH OPEN","WIMBLEDON","US OPEN")):
        return "grand-slams"
    if league=="ATP": return "atp"
    if league=="WTA": return "wta"
    return None

events=[]
for e in schedule.get("events",[]):
    if e.get("sport")!="Tennis":
        continue
    lane=lane_for(e)
    if not lane:
        continue
    start=e.get("start_time")
    events.append({**e,"lane":lane})

known_by_name={norm(x["name"]):x for x in known}
for e in events:
    hay=norm(e.get("name"))
    matches=[]
    for k,v in known_by_name.items():
        if k and k in hay:
            matches.append(v)
    e["known_u18"]=matches
    e["verified_u18_risk"]=bool(matches)

groups={}
for e in events:
    tournament=e.get("tournament") or e.get("competition") or e.get("league") or "Tennis"
    key=f'{e["lane"]}|{tournament}'
    g=groups.setdefault(key,{
        "id":hashlib.sha1(key.encode()).hexdigest()[:12],
        "lane":e["lane"],
        "tournament":tournament,
        "region":e.get("region"),
        "location":e.get("location"),
        "events":[],
        "participants":set(),
        "known_u18":{},
    })
    g["events"].append(e)
    # derive participant names from "A vs B"
    parts=re.split(r"\s+(?:vs\.?|at)\s+",str(e.get("name") or ""),maxsplit=1,flags=re.I)
    for p in parts:
        if p.strip():
            g["participants"].add(p.strip())
    for k in e.get("known_u18",[]):
        g["known_u18"][k["name"]]=k

prev_sig={x.get("id"):x.get("draw_signature") for x in previous.get("tournaments",[])}

tournaments=[]
risk_queue=[]
for g in groups.values():
    evs=sorted(g["events"],key=lambda x:x.get("start_time") or "")
    participant_names=sorted(g["participants"])
    sig=hashlib.sha256(("|".join(participant_names)+"|"+"|".join(str(x.get("id")) for x in evs)).encode()).hexdigest()[:16]
    draw_changed=bool(prev_sig.get(g["id"]) and prev_sig.get(g["id"])!=sig)

    today_count=0
    live_count=0
    for e in evs:
        try:
            local=datetime.datetime.fromisoformat(e["start_time"].replace("Z","+00:00")).astimezone(TZ).date()
            if local==TODAY: today_count+=1
        except Exception: pass
        if e.get("status")=="LIVE": live_count+=1

    t={
        "id":g["id"],
        "lane":g["lane"],
        "tournament":g["tournament"],
        "region":g["region"],
        "location":g["location"],
        "event_count":len(evs),
        "today_count":today_count,
        "live_count":live_count,
        "participant_count":len(participant_names),
        "participants":participant_names,
        "known_u18":list(g["known_u18"].values()),
        "known_u18_count":len(g["known_u18"]),
        "age_review_count":0,
        "draw_signature":sig,
        "draw_changed":draw_changed,
        "events":evs,
    }
    tournaments.append(t)

    for e in evs:
        for player in e.get("known_u18",[]):
            risk_queue.append({
                "severity":"RED",
                "type":"VERIFIED U18",
                "lane":g["lane"],
                "tournament":g["tournament"],
                "event":e.get("name"),
                "start_time":e.get("start_time"),
                "player":player["name"],
                "age":player.get("age"),
                "reason":"Known U18 participant is tied to a mapped current/upcoming tennis match.",
                "staff_action":"Search the athlete by name in active SWSP player-specific markets."
            })
    if draw_changed:
        risk_queue.append({
            "severity":"AMBER",
            "type":"DRAW CHANGE",
            "lane":g["lane"],
            "tournament":g["tournament"],
            "event":None,
            "start_time":evs[0].get("start_time") if evs else None,
            "player":None,
            "reason":"Mapped tournament participant/match signature changed since the previous tennis refresh.",
            "staff_action":"Re-screen the current draw/field for U18 exposure."
        })

# Explicit source issues for lanes not yet automated.
for lane in lanes:
    if "PENDING" in lane["coverage"]:
        risk_queue.append({
            "severity":"AMBER",
            "type":"SOURCE ISSUE",
            "lane":lane["id"],
            "tournament":lane["label"],
            "event":None,
            "start_time":None,
            "player":None,
            "reason":"Automated draw/participant adapter is not yet mapped for this lane.",
            "staff_action":"Use the official lane source for manual current draw/participant screening."
        })

lane_counts={x["id"]:0 for x in lanes}
for t in tournaments: lane_counts[t["lane"]]=lane_counts.get(t["lane"],0)+1
for lane in lanes: lane["active_tournaments"]=lane_counts.get(lane["id"],0)

out={
    "schema_version":1,
    "generated_at":NOW.isoformat(),
    "timezone":"America/Chicago",
    "window_start":TODAY.isoformat(),
    "window_end":END.isoformat(),
    "lanes":lanes,
    "tournaments":sorted(tournaments,key=lambda x:(x["lane"],x["tournament"])),
    "risk_queue":risk_queue,
    "known_u18_registry":known,
    "summary":{
        "lanes":len(lanes),
        "mapped_tournaments":len(tournaments),
        "mapped_matches":len(events),
        "known_u18_registry":len(known),
        "active_u18_matches":sum(1 for x in risk_queue if x["type"]=="VERIFIED U18"),
        "draw_changes":sum(1 for x in risk_queue if x["type"]=="DRAW CHANGE"),
        "source_issues":sum(1 for x in risk_queue if x["type"]=="SOURCE ISSUE")
    },
    "methodology":{
        "primary_age_source":"Official ITF player profile where available.",
        "review_today_rule":"Only match/tournament-linked U18 or draw-change risks are promoted into the operational Today + 7 view.",
        "unknown_rule":"Unknown/unmapped participant ages remain in Tennis Watch and do not flood Review Today without current event linkage."
    }
}
(DATA/"tennis-intelligence.json").write_text(json.dumps(out,indent=2,default=list),encoding="utf-8")
print(json.dumps(out["summary"]))
