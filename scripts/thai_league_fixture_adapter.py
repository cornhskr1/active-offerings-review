"""Scoped fixtures from the Thai League's public competition service."""

import datetime
from zoneinfo import ZoneInfo


BANGKOK = ZoneInfo("Asia/Bangkok")
CENTRAL = ZoneInfo("America/Chicago")


def parse_thai_league_matches(rows, source, today, end, now_utc):
    if not isinstance(rows, list):
        raise ValueError("Thai League match feed missing match list")
    if rows and not any(row.get("tournament_id") == source["tournament_id"] for row in rows):
        raise ValueError("Thai League feed returned the wrong tournament")
    events = []
    for row in rows:
        if row.get("tournament_id") != source["tournament_id"]:
            continue
        if row.get("tournament_name_en") != source["tournament_name"]:
            raise ValueError("Thai League tournament name or edition changed")
        if row.get("is_cancel") or row.get("match_status") not in (0, 1):
            continue
        live = row.get("match_status") == 1 and row.get("live") is True
        if row.get("match_status") == 1 and not live:
            continue
        home, away = row.get("home_team_name_en"), row.get("away_team_name_en")
        if not home or not away or any(name.strip().lower() in ("tbc", "tbd", "bye") for name in (home, away)):
            continue
        try:
            start = datetime.datetime.fromisoformat(f'{row["start_date"]}T{row["start_time"]}').replace(tzinfo=BANGKOK)
            utc = start.astimezone(datetime.timezone.utc)
            day = start.astimezone(CENTRAL).date()
        except (KeyError, TypeError, ValueError):
            continue
        if not row.get("id") or not today <= day <= end or (not live and utc < now_utc):
            continue
        events.append({
            "id": f'{source["id"]}-{row["id"]}',
            "source_id": source["id"], "sport": "Soccer", "league": source["league"],
            "region": "Thailand", "name": f"{away} at {home}",
            "start_time": utc.isoformat().replace("+00:00", "Z"),
            "status": "LIVE" if live else "UPCOMING",
            "season_stage": "REGULAR SEASON" if source["tournament_id"] == 224 else "CUP",
            "location": row.get("stadium_name_en"),
            "source_endpoint": source["official_schedule_url"],
        })
    return events
