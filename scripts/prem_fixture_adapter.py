"""Exact Gallagher PREM and PREM Rugby Cup fixtures from PREM's public match feed."""

import datetime
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")


def parse_prem_matches(payload, source, today, end):
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("PREM match feed missing data array")
    if rows and not any(row.get("compId") == source["competition_id"] for row in rows):
        raise ValueError("PREM match feed returned the wrong competition")
    events = []
    for row in rows:
        if row.get("compId") != source["competition_id"]:
            continue
        if str(row.get("season")) != str(source["season_id"]):
            raise ValueError("PREM match feed returned the wrong season")
        if row.get("status") not in ("fixture", "live") or row.get("tbc"):
            continue
        home = (row.get("homeTeam") or {}).get("name")
        away = (row.get("awayTeam") or {}).get("name")
        if not home or not away or any(x.strip().lower() in ("tbc", "tbd") for x in (home, away)):
            continue
        try:
            start = datetime.datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
            if start.tzinfo is None or not row.get("id"):
                continue
            date = start.astimezone(CENTRAL).date()
        except (KeyError, TypeError, ValueError):
            continue
        if not today <= date <= end:
            continue
        events.append({
            "id": f'{source["id"]}-{row["id"]}',
            "source_id": source["id"], "sport": "Rugby",
            "league": source["league"], "region": "England",
            "name": f"{away} at {home}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "LIVE" if row["status"] == "live" else "UPCOMING",
            "season_stage": "CUP" if source["competition_id"] == 1297 else "REGULAR SEASON",
            "location": (row.get("venue") or {}).get("name"),
            "source_endpoint": source["official_schedule_url"],
        })
    return events
