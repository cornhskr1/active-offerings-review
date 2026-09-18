#!/usr/bin/env python3
"""Regression checks for exact team, league, restriction, and approval identity."""

from pathlib import Path
import json

from catalog_identity import exact_league_match, exact_team_in_event, team_event_match

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"


def require(condition,message):
    if not condition:
        raise AssertionError(message)


# Known false positives must remain impossible.
require(not team_event_match("D.C. United","MLS","Manchester United at Arsenal","Premier League")[0],"D.C. United leaked into Manchester United")
require(not team_event_match("D.C. United","MLS","JEF United at Mito HollyHock","J2 League")[0],"D.C. United leaked into JEF United")
require(not team_event_match("New York City FC","MLS","York City at Rochdale","National League")[0],"New York City leaked into York City")
require(not team_event_match("Arsenal","Premier League","Chelsea at Arsenal","Women's Super League")[0],"Arsenal men leaked into WSL")
require(not team_event_match("Ajax","Eredivisie","Jong Ajax at FC Eindhoven","Eerste Divisie")[0],"Ajax leaked into Jong Ajax")
require(not exact_league_match("Super League | Women","USL Super League | Women"),"USL restriction leaked into England Super League")
require(not exact_team_in_event("Miami","Miami (OH) RedHawks at Cincinnati Bearcats")[0],"Miami leaked into Miami (OH)")

# Reviewed exact identities and aliases must continue to match.
require(team_event_match("D.C. United","MLS","Charlotte FC at D.C. United","MLS")[0],"D.C. United exact match failed")
require(team_event_match("Ajax","Eredivisie","Ajax Amsterdam at PSV","Eredivisie")[0],"Ajax reviewed alias failed")
require(exact_league_match("USL Super League | Women","USL Super League | Women"),"USL exact league match failed")
require(exact_team_in_event("Miami","Florida State Seminoles at Miami Hurricanes")[0],"Miami Hurricanes reviewed alias failed")

# Every published schedule event must trace to an explicitly approved source ID.
season_map=json.loads((DATA/"catalog-season-map.json").read_text(encoding="utf-8"))
approved_ids=set()
def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=="source_id" and item:
                approved_ids.add(str(item))
            elif key=="source_ids" and isinstance(item,list):
                approved_ids.update(str(x) for x in item if x)
            collect(item)
    elif isinstance(value,list):
        for item in value:
            collect(item)
collect(season_map)

schedule=json.loads((DATA/"global-schedule.json").read_text(encoding="utf-8"))
ghosts=[(x.get("source_id"),x.get("league"),x.get("name")) for x in schedule.get("events",[]) if str(x.get("source_id") or "") not in approved_ids]
require(not ghosts,f"ghost approvals in global schedule: {ghosts[:5]}")
esports_without_game=[(x.get("source_id"),x.get("league"),x.get("name")) for x in schedule.get("events",[]) if x.get("sport")=="Esports" and not x.get("game")]
require(not esports_without_game,f"Esports events missing game identity: {esports_without_game[:5]}")

print(json.dumps({
    "identity_regressions":"passed",
    "published_events":len(schedule.get("events",[])),
    "approved_source_ids":len(approved_ids),
    "ghost_approvals":len(ghosts),
    "esports_events_with_game":sum(1 for x in schedule.get("events",[]) if x.get("sport")=="Esports" and x.get("game")),
}))
