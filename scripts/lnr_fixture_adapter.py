"""Exact Top 14 and Pro D2 match records from LNR's competition pages."""

import datetime
import html
import json
import re
from zoneinfo import ZoneInfo


PARIS = ZoneInfo("Europe/Paris")
CENTRAL = ZoneInfo("America/Chicago")
MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12,
}


def current_round(page):
    match = re.search(r'<score-slider\b[^>]*:weeks=\'([^\']+)\'', page, re.S)
    if not match:
        raise ValueError("LNR current round missing")
    weeks = json.loads(html.unescape(match.group(1)))
    if len(weeks) != 1 or not isinstance(weeks[0].get("number"), int):
        raise ValueError("LNR current round ambiguous")
    return weeks[0]["number"]


def parse_lnr_round(page, source, season_start_year, today, end):
    """Only date-and-time match cards from the configured competition page."""
    if "calendar-results__fixture-date" not in page or "match-calendar-line" not in page:
        raise ValueError("LNR fixture markup missing")
    parsed = []
    date_sections = re.split(r'(?=<div class="calendar-results__fixture-date\b)', page)[1:]
    for section in date_sections:
        heading = re.search(r'class="calendar-results__fixture-date[^>]*>\s*([^<]+)', section)
        date_match = re.search(r'(\d{1,2})\s+([a-zéûôîàè]+)',
                               html.unescape(heading.group(1)).casefold()) if heading else None
        if not date_match:
            continue
        month = MONTHS.get(date_match.group(2))
        if not month:
            continue
        year = season_start_year if month >= 7 else season_start_year + 1
        try:
            match_date = datetime.date(year, month, int(date_match.group(1)))
        except ValueError:
            continue
        if match_date < today - datetime.timedelta(days=1) or match_date > end + datetime.timedelta(days=1):
            continue
        for card in re.split(r'(?=<div class="match-calendar-line\b)', section)[1:]:
            teams = [html.unescape(re.sub(r'<[^>]+>', '', name)).strip() for name in
                     re.findall(r'class="club-line__name[^\"]*"\s*>\s*(.*?)\s*</a>', card, re.S)]
            clock = re.search(r'class="match-line__time"\s*>\s*(\d{1,2})h(\d{2})', card)
            match_id = re.search(r'/feuille-de-match/\d{4}-\d{4}/[^/]+/(\d+)-', card)
            if len(teams) != 2 or not clock or not match_id or any(
                not name or name.casefold() in {"tbc", "tbd"} or
                re.search(r'\b(?:under|u)[ -]?\d{1,2}s?\b', name, re.I) for name in teams
            ):
                continue
            start = datetime.datetime.combine(match_date,
                datetime.time(int(clock.group(1)), int(clock.group(2))), tzinfo=PARIS)
            if not today <= start.astimezone(CENTRAL).date() <= end:
                continue
            parsed.append({
                "id": f'{source["id"]}-{match_id.group(1)}',
                "source_id": source["id"], "sport": "Rugby",
                "league": source["league"], "region": "France",
                "name": f"{teams[1]} at {teams[0]}",
                "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "Official LNR fixture",
                "season_stage": "REGULAR SEASON", "location": None,
                "source_endpoint": source["official_schedule_url"],
            })
    return parsed
