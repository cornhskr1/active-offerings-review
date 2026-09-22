#!/usr/bin/env python3
"""Apply fail-closed catalog and restriction guards to an existing schedule."""

from pathlib import Path
import datetime, json, re

from catalog_identity import exact_league_match, normalize_identity, restriction_scope

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

season_map=json.loads((DATA/"catalog-season-map.json").read_text(encoding="utf-8"))
schedule=json.loads((DATA/"global-schedule.json").read_text(encoding="utf-8"))
catalog=json.loads((DATA/"catalog-live.json").read_text(encoding="utf-8"))

approved_ids=set()
approved_labels=set()
source_labels={}
controlled_classifiers={
    "uci-calendar","pdc-calendar","cdc-calendar","riot-esports-calendar",
    "ubisoft-r6-calendar","pgl-cs2-calendar","esl-esports-calendar",
}

def esports_game_name(event):
    if event.get("sport")!="Esports":
        return None
    if event.get("game"):
        return event["game"]
    hay=f'{event.get("source_id") or ""} {event.get("league") or ""}'.lower()
    if "esports-lol-" in hay or "league of legends" in hay:return "League of Legends"
    if "esports-valorant-" in hay or "valorant" in hay:return "VALORANT"
    if "esports-r6-" in hay or "rainbow six" in hay:return "Rainbow Six Siege"
    if "esports-dota-" in hay or "dota 2" in hay or "dota2" in hay:return "Dota 2"
    if "esports-cs2-" in hay or "counter-strike" in hay or "cs2" in hay:return "Counter-Strike 2"
    return None

def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=="source_id" and item:
                approved_ids.add(str(item))
            elif key=="source_ids" and isinstance(item,list):
                approved_ids.update(str(x) for x in item if x)
            elif key in ("sport","governing_body","catalog_event") and item:
                approved_labels.add(normalize_identity(item))
            collect(item)
    elif isinstance(value,list):
        for item in value:
            collect(item)
collect(season_map)

def mapped_source_ids(entry):
    values=([entry["source_id"]] if entry.get("source_id") else [])+(entry.get("source_ids") or [])
    for child in entry.get("coverage_children") or []:
        values.extend(mapped_source_ids(child))
    return values

def source_is_approved(source):
    if str(source.get("id") or "") in approved_ids:
        return True
    children={str(x.get("source_id")) for x in source.get("official_events",[]) if x.get("source_id")}
    if children & approved_ids:
        return True
    if source.get("source_type") in controlled_classifiers:
        return True
    terms={normalize_identity(x) for x in source.get("catalog_terms",[]) if x}
    return bool(terms & approved_labels)

for mapping in season_map.get("source_mappings",[]):
    if mapping.get("source_id") and mapping.get("catalog_event"):
        source_labels.setdefault(str(mapping["source_id"]),set()).add(normalize_identity(mapping["catalog_event"]))
for sport in season_map.get("sports",[]):
    for group in sport.get("groups",[]):
        for entry in group.get("events",[]):
            label=normalize_identity(entry.get("catalog_event"))
            for source_id in mapped_source_ids(entry):
                if label:
                    source_labels.setdefault(str(source_id),set()).add(label)

def restriction_applies(event,restriction):
    text=str(restriction.get("text") or "").lower()
    sport=str(event.get("sport") or "").lower()
    league=str(event.get("league") or "").lower()
    name=str(event.get("name") or "").lower()
    stage=str(event.get("season_stage") or "").upper()
    if restriction.get("scope_type")=="GENERAL_U18_PRO":
        return False
    if league=="nfl":
        if "draft" in text:return "draft" in name
        if "preseason" in text or "pre-season" in text:return stage=="PRESEASON"
        if "postseason" in text or "playoff" in text:return stage=="POSTSEASON"
        if "regular season" in text:return stage=="REGULAR SEASON"
    if league=="mlb":
        if "draft" in text:return "draft" in name
        if "spring training" in text or "preseason" in text or "pre-season" in text:
            return stage=="PRESEASON" or any(x in name for x in ("spring training","preseason","pre-season"))
    special=("draft","all-star","home run derby","world baseball classic","preseason","pre-season","spring training")
    for term in special:
        if term in text:
            return term in f"{league} {name}"
    scope=restriction_scope(restriction.get("text"))
    scope_id=normalize_identity(scope)
    if exact_league_match(event.get("league"),scope):
        return True
    if scope_id in source_labels.get(str(event.get("source_id") or ""),set()):
        return True
    return (
        str(restriction.get("sport") or "").lower()==sport
        and scope_id in {"boxing restriction","combat sports restriction"}
    )

original_events=schedule.get("events",[])
discovered_count=max(int(schedule.get("discovered_event_count") or 0),len(original_events))
events=[]
for event in original_events:
    if str(event.get("source_id") or "") not in approved_ids:
        continue
    event["catalog_approval"]="EXPLICIT SOURCE MAPPING"
    game=esports_game_name(event)
    if game:
        event["game"]=game
    signals=[x.get("text") for x in catalog.get("restrictions",[]) if restriction_applies(event,x)]
    event["restriction_signals"]=signals[:5]
    event["restriction_risk"]=bool(signals)
    events.append(event)

schedule["generated_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
schedule["discovered_event_count"]=discovered_count
schedule["catalog_rejected_event_count"]=discovered_count-len(events)
schedule["event_count"]=len(events)
schedule["events"]=events
for state in schedule.get("sources",[]):
    source_id=str(state.get("id") or "")
    child_ids={str(x.get("source_id")) for x in state.get("official_events",[]) if x.get("source_id")}
    is_classifier=state.get("source_type") in controlled_classifiers
    if source_id not in approved_ids and not child_ids.intersection(approved_ids) and not is_classifier:
        discovered=int(state.get("events") or state.get("catalog_rejected_events") or 0)
        if discovered:
            state["catalog_rejected_events"]=discovered
            state["events"]=0
        state["approved_catalog"]=False
        state["note"]="Discovery-only adapter; emitted events require an explicit mapped source ID before publication."

sources=json.loads((DATA/"global-schedule-sources.json").read_text(encoding="utf-8")).get("sources",[])
for path in sorted(DATA.glob("soccer-*-sources.json")):
    sources.extend(json.loads(path.read_text(encoding="utf-8")).get("sources",[]))
gaps_by_area={}
for source in sources:
    if source_is_approved(source) and source.get("source_type")=="coverage-gap":
        gaps_by_area.setdefault(source.get("sport") or "Other",[]).append(source.get("league") or source.get("id"))
coverage_gaps=[]
for area,leagues in sorted(gaps_by_area.items()):
    coverage_gaps.append({
        "area":area,
        "state":"PARTIAL SCHEDULE COVERAGE",
        "note":f"{len(leagues)} approved competition{'s' if len(leagues)!=1 else ''} still lack a dependable automated adapter.",
        "competitions":sorted(leagues),
    })
configured_sports={str(source.get("sport")) for source in sources if source_is_approved(source)}
for area in ("Aussie Rules","Bowling","Boxing","Combat Sports","Cricket","Cycling","Darts","Esports","Golf","Lacrosse","Motorsports","Olympics","Rodeo","Rugby","Surfing","Table Tennis"):
    if area not in configured_sports and any(str(section.get("sport"))==area for section in catalog.get("sections",[])):
        coverage_gaps.append({
            "area":area,
            "state":"SCHEDULE ADAPTER PENDING",
            "note":"Approved catalog area is recognized but not yet included in the automated global schedule feed.",
        })
schedule["coverage_gaps"]=coverage_gaps
(DATA/"global-schedule.json").write_text(json.dumps(schedule,indent=2),encoding="utf-8")

print(json.dumps({
    "before":discovered_count,
    "published":len(events),
    "catalog_rejected":discovered_count-len(events),
    "approved_source_ids":len(approved_ids),
}))
