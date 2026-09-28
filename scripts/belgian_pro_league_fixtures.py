"""Exact current Challenger Pro League round from the official Pro League page."""

import datetime
import json
import re


SOURCE_ID = "uefa-soccer-belgium-challenger-pro-league-men"
COMPETITION_ID = "6a1df724-3e95-4a0b-a8b6-c5ed108ed9b2"
EDITION_ID = "81ab09dd-e3f3-4227-aa29-a9b5478d9a93"
RESERVES = ("Club NXT", "RSCA Futures", "Jong Genk", "Jong KAA Gent")


def parse_challenger_round(page, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Challenger catalog scope changed")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Pro League published match data missing")
    data = json.loads(match.group(1))["props"]["pageProps"]["data"]["page"]
    modules = [module for grid in data["grids"] for area in grid["areas"]
               for module in area["modules"] if module.get("subtype") == "football_competition_match"]
    if len(modules) != 1:
        raise ValueError("Challenger fixture module changed")
    payload = modules[0]["data"]
    week = payload["gameweek"]["week"]
    rows = payload["matches"]
    if not isinstance(week, int) or not 1 <= week <= 30 or len(rows) != 7:
        raise ValueError("Challenger seven-match round changed")
    events, held, seen = [], 0, set()
    for row in rows:
        if (row["competition"]["id"] != COMPETITION_ID or row["edition"]["id"] != EDITION_ID
                or row["gameweek"]["week"] != week):
            raise ValueError("Challenger edition or round changed")
        identifier = row["id"]
        home, away = row["homeTeam"]["name"], row["awayTeam"]["name"]
        if not re.fullmatch(r"[0-9a-f-]{36}", identifier) or identifier in seen or not home or not away or home == away:
            raise ValueError("Challenger pairing changed")
        seen.add(identifier)
        if home in RESERVES or away in RESERVES:
            held += 1  # Reserve squads may field underage players.
            continue
        stamp = row.get("time")
        if not stamp or not re.fullmatch(r"2026-\d\d-\d\dT\d\d:\d\d:\d\dZ|2027-\d\d-\d\dT\d\d:\d\d:\d\dZ", stamp):
            held += 1
            continue
        start = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if row.get("date") != start.date().isoformat():
            raise ValueError("Challenger fixture date changed")
        events.append({"id": f"belgian-cpl-{identifier}", "source_id": source["id"],
                       "sport": source["sport"], "league": source["league"], "region": source["region"],
                       "name": f"{away} at {home}", "start_time": stamp, "status": "UPCOMING",
                       "status_detail": f"Official regular-season round {week}", "season_stage": "REGULAR",
                       "location": None, "source_endpoint": f"https://www.proleague.be/wedstrijden/{row['slug']}"})
    return events, held, len(rows)
