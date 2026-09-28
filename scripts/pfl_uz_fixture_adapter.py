"""Scoped PFL Uzbekistan senior Superleague fixtures from its official game API."""

import datetime
import re
from zoneinfo import ZoneInfo


SOURCE_ID = "soccer-afc-uzbekistan-uzbekistan-super-league-men"
TOURNAMENT_ID = 1
SEASON_ID = 11
TASHKENT = ZoneInfo("Asia/Tashkent")


def parse_superleague(payload, source, now):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("PFL catalog scope changed")
    data = payload.get("data") or {}
    tournament, season, rounds = data.get("tournament") or {}, data.get("season") or {}, data.get("table")
    if tournament.get("id") != TOURNAMENT_ID or tournament.get("title") != "Superliga":
        raise ValueError("PFL senior Superliga competition changed")
    if season.get("id") != SEASON_ID or season.get("year") != 2026:
        raise ValueError("PFL 2026 season changed")
    if not isinstance(rounds, list) or len(rounds) != 30:
        raise ValueError("PFL 30-round season changed")
    def round_number(round_):
        match = re.fullmatch(r"(\d+)-tur", str(round_.get("title")))
        if not match:
            raise ValueError("PFL senior round label changed")
        return int(match.group(1))
    ordered = sorted(rounds, key=round_number)
    if [round_number(r) for r in ordered] != list(range(1, 31)):
        raise ValueError("PFL round sequence changed")
    ids = set()
    for round_ in ordered:
        matches = round_.get("matches") or []
        if len(matches) != 8:
            raise ValueError("PFL eight-match round changed")
        for match in matches:
            mid = match.get("id")
            if not isinstance(mid, int) or mid in ids:
                raise ValueError("PFL match identity changed")
            ids.add(mid)
    if len(ids) != 240:
        raise ValueError("PFL full regular-season pairing count changed")

    upcoming_round = None
    for round_ in ordered:
        if any(_kickoff(m) > now for m in round_["matches"]):
            upcoming_round = round_
            break
    if upcoming_round is None:
        return [], 0, 240, None
    events, held, clubs = [], 0, set()
    next_start = min(_kickoff(m) for m in upcoming_round["matches"] if _kickoff(m) > now)
    for match in upcoming_round["matches"]:
        start = _kickoff(match)
        home, home_id = _club(match, "homeTeam")
        away, away_id = _club(match, "awayTeam")
        if home_id == away_id or home_id in clubs or away_id in clubs:
            raise ValueError("PFL senior round pairing changed")
        clubs.update((home_id, away_id))
        if start <= now:
            continue
        local = start.astimezone(TASHKENT)
        # Midnight and missing-venue rows are placeholders for later rounds.
        # Seconds in the API are noisy; the publisher displays minute precision.
        if (local.hour == 0 and local.minute == 0) or not match.get("stadium"):
            held += 1
            continue
        start = start.replace(second=0, microsecond=0)
        events.append({"id":f"pfl-uz-superleague-{match['id']}",
            "source_id":source["id"],"sport":source["sport"],
            "league":source["league"],"region":source["region"],
            "name":f"{away} at {home}",
            "start_time":start.isoformat().replace("+00:00","Z"),
            "status":"UPCOMING","status_detail":"Official 2026 Superliga next round",
            "season_stage":"REGULAR","location":match["stadium"].get("title"),
            "source_endpoint":f"https://pfl.uz/en/match/{match['id']}"})
    if len(clubs) != 16:
        raise ValueError("PFL senior round club count changed")
    return events, held, 240, next_start


def _kickoff(match):
    value = match.get("startDate")
    if not isinstance(value, str):
        raise ValueError("PFL kickoff missing")
    start = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if start.tzinfo is None or start.year != 2026:
        raise ValueError("PFL kickoff edition changed")
    return start.astimezone(datetime.timezone.utc)


def _club(match, side):
    team = match.get(side) or {}
    club = team.get("club") or {}
    name = club.get("title")
    if not isinstance(team.get("id"), int) or not isinstance(club.get("id"), int) or not isinstance(name, str) or not name.strip():
        raise ValueError("PFL senior club identity missing")
    if re.search(r"\b(?:U-?\d{2}|youth|academy|farm)\b", name, re.I):
        raise ValueError("PFL youth club in senior round")
    return name.strip(), club["id"]
