#!/usr/bin/env python3
from pathlib import Path
import datetime
import json
import requests
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((DATA / "ncaa-basketball-sources.json").read_text(encoding="utf-8"))

TZ = ZoneInfo(CFG.get("timezone", "America/Chicago"))
ET = ZoneInfo("America/New_York")
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
TODAY = datetime.datetime.now(TZ).date()
WINDOW_DAYS = int(CFG.get("window_days", 7))
END = TODAY + datetime.timedelta(days=WINDOW_DAYS)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)",
    "Accept": "application/json,text/plain,*/*",
}

ENDPOINT = CFG["source_endpoint"]
QUERY_HASH = CFG["persisted_query_hash"]


def ncaa_season_year(day: datetime.date) -> int:
    # NCAA winter-sport season is keyed to the academic year start.
    # Aug-Dec 2026 => 2026 season; Jan-Jul 2027 => 2026 season.
    return day.year if day.month >= 8 else day.year - 1


def status_from_state(state):
    state = str(state or "").upper().strip()
    if state == "F":
        return "COMPLETED"
    if state == "I":
        return "LIVE"
    return "UPCOMING"


def team_name(team):
    return (
        team.get("nameShort")
        or team.get("name6Char")
        or team.get("seoname")
        or "Unknown team"
    )


def parse_start_time(contest):
    epoch = contest.get("startTimeEpoch")
    if epoch not in (None, ""):
        try:
            value = float(epoch)
            if value > 10_000_000_000:  # milliseconds
                value /= 1000.0
            return datetime.datetime.fromtimestamp(
                value, tz=datetime.timezone.utc
            ).isoformat()
        except Exception:
            pass

    start_date = str(contest.get("startDate") or "").strip()
    start_time = str(contest.get("startTime") or "").strip()
    if not start_date:
        return None

    # NCAA data can expose several date/time shapes.
    candidates = []
    if start_time:
        candidates.extend([
            f"{start_date} {start_time}",
            f"{start_date}T{start_time}",
        ])
    candidates.append(start_date)

    formats = [
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %I:%M%p",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for value in candidates:
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(value, fmt)
                dt = dt.replace(tzinfo=ET)
                return dt.astimezone(datetime.timezone.utc).isoformat()
            except ValueError:
                continue
    return None


def fetch_lane_day(lane, day):
    variables = {
        "sportCode": lane["sport_code"],
        "division": lane["division_code"],
        "seasonYear": ncaa_season_year(day),
        "contestDate": day.strftime("%Y/%m/%d"),
    }
    params = {
        "extensions": json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": QUERY_HASH,
            }
        }, separators=(",", ":")),
        "variables": json.dumps(variables, separators=(",", ":")),
    }
    r = requests.get(ENDPOINT, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    payload = r.json()
    return ((payload.get("data") or {}).get("contests") or [])


def parse_contest(lane, contest, requested_day):
    teams = contest.get("teams") or []
    home = next((t for t in teams if t.get("isHome") is True), None)
    away = next((t for t in teams if t.get("isHome") is False), None)

    # Ignore malformed rows rather than inventing participants.
    if not home or not away:
        return None

    home_name = team_name(home)
    away_name = team_name(away)
    contest_id = str(contest.get("contestId") or "").strip()
    start_time = parse_start_time(contest)

    return {
        "id": f'{lane["id"]}-{contest_id or requested_day.isoformat()}-{away_name}-{home_name}',
        "contest_id": contest_id or None,
        "sport": "Basketball",
        "league": lane["league"],
        "region": "United States",
        "gender": lane["gender"],
        "division": lane["division"],
        "division_code": lane["division_code"],
        "lane_id": lane["id"],
        "name": f"{away_name} at {home_name}",
        "away": away_name,
        "home": home_name,
        "away_seo": away.get("seoname"),
        "home_seo": home.get("seoname"),
        "away_conference": away.get("conferenceSeo"),
        "home_conference": home.get("conferenceSeo"),
        "start_time": start_time,
        "source_date": requested_day.isoformat(),
        "status": status_from_state(contest.get("gameState")),
        "status_detail": contest.get("finalMessage") or "",
        "network": contest.get("broadcasterName") or None,
        "source_url": contest.get("url") or None,
        "source_endpoint": ENDPOINT,
        "championship_id": contest.get("championshipId"),
        "bracket_id": contest.get("bracketId"),
        "round_number": contest.get("roundNumber"),
        "round_description": contest.get("roundDescription"),
    }


events = []
lane_status = []

for lane in CFG.get("lanes", []):
    lane_events = 0
    errors = []
    seen = set()

    for offset in range(WINDOW_DAYS + 1):
        day = TODAY + datetime.timedelta(days=offset)
        try:
            contests = fetch_lane_day(lane, day)
            for contest in contests:
                parsed = parse_contest(lane, contest, day)
                if not parsed:
                    continue
                key = (
                    parsed.get("contest_id"),
                    parsed.get("lane_id"),
                    parsed.get("start_time"),
                    parsed.get("name"),
                )
                if key in seen:
                    continue
                seen.add(key)
                events.append(parsed)
                lane_events += 1
        except Exception as exc:
            errors.append(f"{day.isoformat()}: {str(exc)[:160]}")

    lane_status.append({
        "id": lane["id"],
        "league": lane["league"],
        "gender": lane["gender"],
        "division": lane["division"],
        "ok": len(errors) == 0,
        "events": lane_events,
        "errors": errors[:4],
        "checked_at": NOW_UTC.isoformat(),
    })

events.sort(key=lambda x: (
    x.get("start_time") or "9999",
    x.get("league") or "",
    x.get("division") or "",
    x.get("name") or "",
))

out = {
    "schema_version": 1,
    "generated_at": NOW_UTC.isoformat(),
    "timezone": CFG.get("timezone", "America/Chicago"),
    "window_start": TODAY.isoformat(),
    "window_end": END.isoformat(),
    "event_count": len(events),
    "lane_count": len(lane_status),
    "events": events,
    "lanes": lane_status,
    "source": {
        "name": CFG.get("source_name"),
        "endpoint": ENDPOINT,
    },
}

(DATA / "ncaa-basketball.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)

print(json.dumps({
    "window": f"{TODAY} through {END}",
    "events": len(events),
    "lanes_ok": sum(1 for x in lane_status if x.get("ok")),
    "lanes_total": len(lane_status),
    "lane_counts": {
        x["id"]: x["events"] for x in lane_status
    },
}))
