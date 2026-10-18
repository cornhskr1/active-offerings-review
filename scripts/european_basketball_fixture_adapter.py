"""Exact men's EuroLeague/EuroCup fixtures from their public Media Game Center.

The publisher's page at https://mediagamecenter.euroleague.net/ embeds
getJSON('games', { seasonCode: SEASON }, true), where E/U identify the two
competitions. Its v2 schedule is explicitly the source of truth for utcDate.
Only the currently published 2026/27 regular seasons are supported here.
No XML fallback, inferred tipoffs, postseason placeholders, or age clearance.
"""

import datetime
import math
import re
from collections import Counter, defaultdict


BASE = "https://mediagamecenter.euroleague.net"
SPECS = {
    "basketball-euroleague": {
        "competition": "E", "season": "E2026", "name": "EuroLeague",
        "catalog": "EuroLeague | Men", "total": 380, "rounds": 38, "clubs": 20,
        "groups": {"Regular Season"}, "start": "2026-09-24", "end": "2027-04-16",
        "publisher_page": "https://mediacentre.euroleague.net/en/app/2/communication/communication/preview/24407",
    },
    "eurocup-basketball": {
        "competition": "U", "season": "U2026", "name": "EuroCup",
        "catalog": "EuroCup | Men", "total": 224, "rounds": 14, "clubs": 32,
        "groups": {"A", "B", "C", "D"}, "start": "2026-09-29", "end": "2027-01-13",
        "publisher_page": "https://mediacentre.euroleague.net/en/app/2/communication/communication/preview/24408",
    },
}
UTC_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
LOCAL_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?")
PLACEHOLDER = re.compile(r"\b(?:TBD|TBC|WINNER|LOSER|U-?\d{2})\b", re.I)


def source_config(source_id):
    """Integration helper: replace the existing source, do not append an alias."""
    spec = SPECS[source_id]
    return {
        "id": source_id, "source_type": "official-european-basketball-fixtures",
        "sport": "Basketball", "league": spec["catalog"], "region": "Europe",
        "endpoint": f"{BASE}/api/games?seasonCode={spec['season']}",
        "official_schedule_url": f"{BASE}/?c={spec['competition']}",
        "publisher_page": spec["publisher_page"],
        "endpoint_validation": "published-schedule",
        "coverage_status": "partial",
        "catalog_terms": [spec["catalog"]],
        "competition_code": spec["competition"], "season_code": spec["season"],
        "schedule_scope": "regular-season", "coverage_start": spec["start"],
        "coverage_end": spec["end"],
        "source_note": (
            f"The official Media Game Center publishes all {spec['total']} confirmed "
            f"{spec['name']} 2026/27 regular-season fixtures, with exact competition, "
            "season, round, club IDs and UTC/local tipoff evidence. The adapter "
            "fails closed on partial payloads, changed identities or ambiguous times. "
            f"Coverage ends {spec['end']}; postseason fixtures and participant ages "
            "are not established by this schedule."
        ),
    }


def _spec(source):
    source_id = source.get("id")
    if source_id not in SPECS:
        raise ValueError("European basketball source identity changed")
    expected = source_config(source_id)
    for key in ("source_type", "sport", "league", "region", "catalog_terms", "endpoint",
                "competition_code", "season_code", "schedule_scope",
                "coverage_start", "coverage_end"):
        if source.get(key) != expected[key]:
            raise ValueError(f"European basketball source {key} changed")
    return SPECS[source_id]


def validate_review_window(source, today, window_end):
    """Do not count an unpublished postseason or next season as an empty week."""
    spec = _spec(source)
    if today > window_end:
        raise ValueError("European basketball review window is reversed")
    if (today < datetime.date.fromisoformat(spec["start"])
            or window_end > datetime.date.fromisoformat(spec["end"])):
        raise ValueError("European basketball regular-season publication does not cover the review window")


def _club(game, side):
    participant = game.get(side)
    club = participant.get("club") if isinstance(participant, dict) else None
    if not isinstance(club, dict):
        raise ValueError("European basketball club payload changed")
    code, name = club.get("code"), club.get("name")
    if (not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9]+", code)
            or not isinstance(name, str) or not name.strip()
            or PLACEHOLDER.search(name) or club.get("isVirtual") is not False):
        raise ValueError("European basketball club identity is ambiguous")
    return code, " ".join(name.split())


def _game(game, spec):
    if not isinstance(game, dict):
        raise ValueError("European basketball game payload changed")
    season, phase = game.get("season"), game.get("phaseType")
    if (not isinstance(season, dict) or season.get("code") != spec["season"]
            or season.get("competitionCode") != spec["competition"]
            or season.get("year") != 2026 or season.get("alias") != "2026-27"
            or season.get("name") != f"{spec['name']} 2026-27"):
        raise ValueError("European basketball fixture competition or season changed")
    if (not isinstance(phase, dict) or phase.get("code") != "RS"
            or phase.get("name") != "Regular Season"
            or phase.get("isGroupPhase") is not True):
        raise ValueError("European basketball phase is outside published regular-season scope")
    group = game.get("group")
    if not isinstance(group, dict) or group.get("rawName") not in spec["groups"]:
        raise ValueError("European basketball competition group changed")
    number, round_number = game.get("gameCode"), game.get("round")
    if (type(number) is not int or not 1 <= number <= spec["total"]
            or game.get("identifier") != f"{spec['season']}_{number}"
            or type(round_number) is not int or not 1 <= round_number <= spec["rounds"]):
        raise ValueError("European basketball game or round identity changed")
    if (game.get("confirmedDate") is not True or game.get("confirmedHour") is not True
            or game.get("gameStatus") != "Confirmed"
            or type(game.get("played")) is not bool):
        raise ValueError("European basketball fixture date, hour or status is unconfirmed")
    home, away = _club(game, "local"), _club(game, "road")
    if home[0] == away[0] or home[1] == away[1]:
        raise ValueError("European basketball fixture has identical opponents")
    stamp, local_stamp, offset = game.get("utcDate"), game.get("localDate"), game.get("localTimeZone")
    if (not isinstance(stamp, str) or not UTC_STAMP.fullmatch(stamp)
            or not isinstance(local_stamp, str) or not LOCAL_STAMP.fullmatch(local_stamp)
            or type(offset) not in (int, float) or not math.isfinite(offset)
            or not -12 <= offset <= 14):
        raise ValueError("European basketball UTC/local tipoff evidence changed")
    try:
        kickoff = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        local = datetime.datetime.fromisoformat(local_stamp).replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=offset)))
    except ValueError as exc:
        raise ValueError("European basketball tipoff is invalid") from exc
    if kickoff != local:
        raise ValueError("European basketball UTC and arena-local tipoffs disagree")
    if not spec["start"] <= local.date().isoformat() <= spec["end"]:
        raise ValueError("European basketball fixture left the published season dates")
    return number, round_number, group["rawName"], home, away, kickoff


def parse_fixtures(payload, source):
    """Validate the complete publisher schedule, then emit confirmed unplayed games.

    The collector must call validate_review_window and filter past tipoffs and its
    America/Chicago date window. A completed game is never emitted as upcoming.
    """
    spec = _spec(source)
    if (not isinstance(payload, dict) or not isinstance(payload.get("data"), list)
            or type(payload.get("total")) is not int
            or payload["total"] != spec["total"] or len(payload["data"]) != spec["total"]):
        raise ValueError("European basketball schedule is incomplete or its published scope changed")
    seen, pairs, rounds, clubs, club_groups = set(), set(), defaultdict(list), {}, {}
    groups, events = Counter(), []
    for game in payload["data"]:
        number, round_number, group, home, away, kickoff = _game(game, spec)
        pair = (home[0], away[0])
        if number in seen or pair in pairs:
            raise ValueError("European basketball duplicate game identity or pairing")
        seen.add(number)
        pairs.add(pair)
        groups[group] += 1
        for code, name in (home, away):
            if code in clubs and clubs[code] != name:
                raise ValueError("European basketball club ID has conflicting names")
            if code in club_groups and club_groups[code] != group:
                raise ValueError("European basketball club crossed competition groups")
            clubs[code], club_groups[code] = name, group
            rounds[round_number].append(code)
        if game["played"]:
            continue
        url = f"{BASE}/{spec['season']}/{number}"
        venue = game.get("venue") or {}
        events.append({
            "id": f"euroleague-basketball-{spec['season']}-{number}",
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away[1]} at {home[1]}",
            "start_time": kickoff.isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": f"Official {spec['name']} 2026/27 regular season · Round {round_number}",
            "season_stage": "REGULAR", "season_code": spec["season"],
            "competition_code": spec["competition"], "phase": "RS",
            "location": venue.get("name") if isinstance(venue, dict) else None,
            "source_endpoint": url, "source_url": url,
            "coverage_status": "partial",
        })
    if (len(clubs) != spec["clubs"] or len(rounds) != spec["rounds"]
            or any(len(codes) != spec["clubs"] or len(set(codes)) != spec["clubs"]
                   for codes in rounds.values())
            or set(groups) != spec["groups"]
            or any(count != spec["total"] // len(spec["groups"]) for count in groups.values())):
        raise ValueError("European basketball complete regular-season structure changed")
    return sorted(events, key=lambda event: (event["start_time"], event["id"]))
