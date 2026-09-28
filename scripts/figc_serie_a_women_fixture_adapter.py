"""Read the FIGC's exact Serie A Women second/third round announcement."""

import datetime
import html
import re
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
CENTRAL = ZoneInfo("America/Chicago")
DAYS = {
    "Sabato 3 ottobre": datetime.date(2026, 10, 3),
    "Domenica 4 ottobre": datetime.date(2026, 10, 4),
    "Sabato 17 ottobre": datetime.date(2026, 10, 17),
    "Domenica 18 ottobre": datetime.date(2026, 10, 18),
}
GAME = re.compile(r"Ore (\d{1,2})(?:\.(\d{2}))?:? ([^-()]+)-([^-()]+) \([^)]*\)$")


def parse_figc_rounds(page, source, window_end):
    if source.get("catalog_terms") != ["Italian Football Federation (FIGC)", "Serie A | Men and Women"]:
        raise ValueError("FIGC source is not mapped to the exact women’s Serie A child")
    article = re.search(r'<article class="article show-to-print article-type-news">(.*?)</article>', page, re.S)
    if not article or "Serie A Women Athora" not in article.group(1):
        raise ValueError("FIGC Serie A Women article missing")
    section = re.search(r'SERIE A WOMEN ATHORA 2026-27(.*?)</p>', article.group(1), re.S)
    if not section:
        raise ValueError("FIGC 2026–27 round schedule missing")
    content = re.sub(r'<br\s*/?>', '\n', section.group(1))
    lines = [html.unescape(re.sub(r'<[^>]+>', '', line)).replace('\xa0', ' ').strip()
             for line in content.splitlines()]
    lines = [line for line in lines if line]
    round_number = None
    current_day = None
    day_counts = {day: 0 for day in DAYS.values()}
    teams_by_round = {2: set(), 3: set()}
    events = []
    for line in lines:
        if line in ("2ª giornata", "3ª giornata"):
            round_number = int(line[0])
            current_day = None
        elif line in DAYS:
            current_day = DAYS[line]
            if round_number != (2 if current_day.day <= 4 else 3):
                raise ValueError("FIGC round and date order changed")
        else:
            game = GAME.fullmatch(line)
            if not game or current_day is None:
                raise ValueError("FIGC timed pairing changed")
            hour, minute, home, away = game.groups()
            home, away = home.strip(), away.strip()
            if not home or not away or home == away or any(
                re.search(r'\b(?:tbc|tbd)\b', team, re.I) for team in (home, away)
            ):
                raise ValueError("FIGC pairing lacks two named clubs")
            if home in teams_by_round[round_number] or away in teams_by_round[round_number]:
                raise ValueError("FIGC club appears twice in the same round")
            teams_by_round[round_number].update((home, away))
            local = datetime.datetime.combine(current_day, datetime.time(int(hour), int(minute or 0)), ROME)
            day_counts[current_day] += 1
            events.append({
                "id": f"figc-serie-a-women-2026-r{round_number}-{current_day.isoformat()}-{day_counts[current_day]}",
                "source_id": source["id"], "sport": source["sport"],
                "league": source["league"], "region": source["region"],
                "name": f"{away} at {home}",
                "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "FIGC published round fixture",
                "season_stage": "REGULAR", "location": None,
                "source_endpoint": source["endpoint"],
            })
    if len(events) != 12 or set(day_counts.values()) != {3} or any(len(teams) != 12 for teams in teams_by_round.values()):
        raise ValueError("FIGC round fixture list is incomplete")
    if window_end > datetime.date(2026, 10, 18):
        raise ValueError("FIGC published rounds do not cover the full review window")
    return events
