"""Exact Premier Division fixtures from SA Rugby's public match-centre feed."""

import datetime
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")


def parse_saru_matches(payload, source, today, end):
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not isinstance(payload.get("totalDataCount"), int):
        raise ValueError("SA Rugby match feed missing paginated items")
    if payload["totalDataCount"] > len(rows):
        raise ValueError("SA Rugby match feed has uncollected pages")
    if rows and not any(row.get("competitionId") == source["competition_id"] for row in rows):
        raise ValueError("SA Rugby match feed returned the wrong competition")
    events = []
    for row in rows:
        if row.get("competitionId") != source["competition_id"]:
            continue
        if row.get("competitionName") != "Carling Currie Cup Premier Division":
            raise ValueError("SA Rugby competition name changed")
        if row.get("isCancelled") or row.get("isPostponed") or row.get("statsStatus") in ("Complete", "Result"):
            continue
        teams = row.get("teams") or []
        home = next((team.get("name") for team in teams if team.get("isHomeTeam") is True), None)
        away = next((team.get("name") for team in teams if team.get("isHomeTeam") is False), None)
        if not home or not away or any(name.strip().lower() in ("tbc", "tbd") for name in (home, away)):
            continue
        try:
            # SA Rugby's utcDate is UTC even though the API omits a timezone suffix.
            start = datetime.datetime.fromisoformat(row["utcDate"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=datetime.timezone.utc)
            date = start.astimezone(CENTRAL).date()
        except (KeyError, TypeError, ValueError):
            continue
        if row.get("seasonName") != str(date.year):
            raise ValueError("SA Rugby match feed returned the wrong season")
        if not row.get("matchId") or not today <= date <= end:
            continue
        events.append({
            "id": f'{source["id"]}-{row["matchId"]}',
            "source_id": source["id"], "sport": "Rugby", "league": source["league"],
            "region": "South Africa", "name": f"{away} at {home}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "LIVE" if row.get("isLive") else "UPCOMING",
            "season_stage": "CUP",
            "location": row.get("venueName"),
            "source_endpoint": source["official_schedule_url"],
        })
    return events
