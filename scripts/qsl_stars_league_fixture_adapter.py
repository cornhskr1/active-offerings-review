"""Read exact Doha Bank Stars League upcoming weeks from QSL."""

import datetime
import html
import re
from zoneinfo import ZoneInfo

from qsl_cup_fixture_adapter import TEAM

QATAR = ZoneInfo("Asia/Qatar")
CLUBS = {
    "Al Ahli", "Al Arabi", "Al Duhail", "Al Gharafa", "Al Rayyan", "Al Sadd",
    "Al Sailiya", "Al Shahania", "Al Shamal", "Al Wakrah", "Lusail", "Qatar SC",
}


def _row(row, *, result=False):
    match_number = re.search(r'<div class="table__date__round">\s*<span>(\d+)</span>', row)
    date_block = re.search(r'<div class="table__date__round">(.*?)</div>', row, re.S)
    date_text = html.unescape(re.sub(r'<[^>]+>', ' ', date_block.group(1))) if date_block else ''
    kickoff_match = re.search(r'(\d{2}/\d{2}/26)\s+(\d{2}:\d{2})', date_text)
    names = [
        html.unescape(name.group(1)).strip()
        for anchor in TEAM.finditer(row)
        if (name := re.search(r'<span>\s*([^<]+)</span>', anchor.group(1), re.S))
    ]
    score = re.search(r'<div class="table__result__points">\s*\d+\s*-\s*\d+\s*</div>', row)
    if (not match_number or not kickoff_match or len(names) != 2
            or any(name not in CLUBS for name in names)
            or (result and not score) or (not result and score)):
        raise ValueError("QSL league match number, kickoff, clubs, or result changed")
    local = datetime.datetime.strptime(
        ' '.join(kickoff_match.groups()), '%d/%m/%y %H:%M'
    ).replace(tzinfo=QATAR)
    return int(match_number.group(1)), local, names


def parse_qsl_stars_fixtures(page, source, now, window_end):
    if (source.get("id") != "soccer-afc-qatar-qatar-stars-league-men"
            or source.get("league") != "Qatar Stars League | Men"
            or source.get("catalog_terms") != ["Qatar Stars League | Men"]):
        raise ValueError("QSL league source has the wrong catalog identity")
    if "Doha Bank Stars League" not in page or "2026-2027" not in page:
        raise ValueError("QSL league season identity changed")
    pane = re.search(
        r'<div class="tab-pane fade show active" id="nav-fixtures"(.*?)'
        r'<div class="tab-pane fade" id="nav-result"', page, re.S
    )
    if not pane:
        raise ValueError("QSL league upcoming fixture pane missing")
    rows = re.findall(r'<tr class="fixture-result">(.*?)</tr>', pane.group(1), re.S)
    if not 6 <= len(rows) <= 12:
        raise ValueError("QSL league upcoming weeks have an unexpected match count")
    result_pane = re.search(
        r'<div class="tab-pane fade" id="nav-result"(.*?)(?:<div class="tab-pane|\Z)',
        page, re.S,
    )
    if not result_pane:
        raise ValueError("QSL league result pane missing")

    fixtures = [_row(row) for row in rows]
    results = [
        _row(row, result=True)
        for row in re.findall(r'<tr class="result-row">(.*?)</tr>', result_pane.group(1), re.S)
    ]
    fixture_ids = [number for number, _local, _names in fixtures]
    result_ids = [number for number, _local, _names in results]
    if (not results or fixture_ids != sorted(fixture_ids)
            or len(set(fixture_ids)) != len(fixture_ids)
            or len(set(result_ids)) != len(result_ids)
            or set(fixture_ids) & set(result_ids)):
        raise ValueError("QSL league published match identity is missing or duplicated")

    round_numbers = sorted({(number - 1) // 6 + 1 for number in fixture_ids})
    if len(round_numbers) > 2 or round_numbers != list(range(round_numbers[0], round_numbers[-1] + 1)):
        raise ValueError("QSL league upcoming rows span unexpected weeks")
    combined = {number: (local, names) for number, local, names in results + fixtures}
    for week in round_numbers:
        expected = set(range((week - 1) * 6 + 1, week * 6 + 1))
        if not expected <= combined.keys():
            raise ValueError("QSL league published week is incomplete")
        clubs = [name for number in expected for name in combined[number][1]]
        if len(clubs) != 12 or set(clubs) != CLUBS:
            raise ValueError("QSL league week does not include each senior club exactly once")

    if any(local.astimezone(datetime.timezone.utc) > now for _number, local, _names in results):
        raise ValueError("QSL league result pane contains a future result")

    events = []
    dates = []
    for match_number, local, names in fixtures:
        week = (match_number - 1) // 6 + 1
        dates.append(local.date())
        events.append({
            "id": f"qsl-stars-2026-27-{match_number}",
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"QSL published league fixture, week {week}",
            "season_stage": "REGULAR", "location": None,
            "source_endpoint": source["endpoint"],
        })
    if dates != sorted(dates) or not any(
        datetime.datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")) > now
        for event in events
    ):
        raise ValueError("QSL league upcoming weeks are stale or out of order")
    if window_end > dates[-1]:
        raise ValueError("QSL league published weeks do not cover the full review window")
    return events
