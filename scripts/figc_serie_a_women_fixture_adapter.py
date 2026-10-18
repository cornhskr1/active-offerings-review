"""Read the FIGC's explicitly reviewed 2026–27 Serie A Women announcements.

Each announcement is a bounded source, not a full-season calendar. Its endpoint,
rounds and published date distribution must agree before any fixtures are returned.
"""

import datetime
import html
import re
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
ROUNDS_2_3_URL = (
    "https://www.figc.it/it/serie-a-women/news/"
    "date-e-orari-della-seconda-e-della-terza-giornata-il-derby-di-roma-si-gioca-"
    "sabato-3-ottobre-alle-18-milan-juventus-domenica-4-alle-15-x3ew23ox"
)
ROUNDS_4_6_URL = (
    "https://www.figc.it/it/serie-a-women/news/"
    "date-e-orari-dalla-4-alla-6-giornata-juventus-roma-sabato-24-ottobre-alle-1830-"
    "il-derby-di-milano-sabato-7-novembre-alle-15-iefuxgby"
)
# Dates and counts are the reviewed official announcements, never inferred from
# a weekday or round number. In particular, round 5 finishes on Monday November 2.
ANNOUNCEMENTS = {
    ROUNDS_2_3_URL: {
        2: {
            "Sabato 3 ottobre": (datetime.date(2026, 10, 3), 3),
            "Domenica 4 ottobre": (datetime.date(2026, 10, 4), 3),
        },
        3: {
            "Sabato 17 ottobre": (datetime.date(2026, 10, 17), 3),
            "Domenica 18 ottobre": (datetime.date(2026, 10, 18), 3),
        },
    },
    ROUNDS_4_6_URL: {
        4: {
            "Sabato 24 ottobre": (datetime.date(2026, 10, 24), 3),
            "Domenica 25 ottobre": (datetime.date(2026, 10, 25), 3),
        },
        5: {
            "Sabato 31 ottobre": (datetime.date(2026, 10, 31), 2),
            "Domenica 1° novembre": (datetime.date(2026, 11, 1), 3),
            "Lunedì 2 novembre": (datetime.date(2026, 11, 2), 1),
        },
        6: {
            "Sabato 7 novembre": (datetime.date(2026, 11, 7), 3),
            "Domenica 8 novembre": (datetime.date(2026, 11, 8), 3),
        },
    },
}
CLUBS = {
    "Como 1907", "Como Women", "Fiorentina", "Inter", "Juventus", "Lazio",
    "Milan", "Napoli Women", "Parma", "Roma", "Sassuolo", "Ternana Women",
}
GAME = re.compile(r"Ore (\d{1,2})(?:\.(\d{2}))?:? ([^-()]+)-([^-()]+) \([^)]*\)$")
ROUND = re.compile(r"(\d+)ª giornata")


def parse_figc_rounds(page, source, window_end):
    if (source.get("id") != "soccer-italy-serie-a-women"
            or source.get("source_type") != "official-figc-serie-a-women-fixtures"
            or source.get("sport") != "Soccer"
            or source.get("league") != "Serie A | Women"
            or source.get("region") != "Italy"
            or source.get("catalog_terms") != ["Italian Football Federation (FIGC)", "Serie A | Men and Women"]):
        raise ValueError("FIGC source is not mapped to the exact women’s Serie A child")
    schedule = ANNOUNCEMENTS.get(source.get("endpoint"))
    if schedule is None:
        raise ValueError("FIGC announcement endpoint has not been reviewed")
    article = re.search(r'<article class="article show-to-print article-type-news">(.*?)</article>', page, re.S)
    if not article or "Serie A Women Athora" not in article.group(1):
        raise ValueError("FIGC Serie A Women article missing")
    sections = re.findall(r'SERIE A WOMEN ATHORA 2026-27(.*?)</p>', article.group(1), re.S)
    if len(sections) != 1:
        raise ValueError("FIGC 2026–27 round schedule missing or repeated")
    content = re.sub(r'<br\s*/?>', '\n', sections[0])
    lines = [html.unescape(re.sub(r'<[^>]+>', '', line)).replace('\xa0', ' ').strip()
             for line in content.splitlines()]
    lines = [line for line in lines if line]
    days = {label: (number, day, count)
            for number, round_days in schedule.items()
            for label, (day, count) in round_days.items()}
    round_number = None
    current_day = None
    seen_rounds = []
    seen_days = []
    day_counts = {day: 0 for _, day, _ in days.values()}
    teams_by_round = {number: set() for number in schedule}
    round_counts = {number: 0 for number in schedule}
    events = []
    for line in lines:
        round_heading = ROUND.fullmatch(line)
        if round_heading:
            round_number = int(round_heading.group(1))
            if round_number not in schedule or round_number in seen_rounds:
                raise ValueError("FIGC round is unexpected or repeated for this announcement")
            seen_rounds.append(round_number)
            current_day = None
        elif line in days:
            expected_round, current_day, _ = days[line]
            if round_number != expected_round or current_day in seen_days:
                raise ValueError("FIGC round and date order changed")
            seen_days.append(current_day)
        else:
            game = GAME.fullmatch(line)
            if not game or current_day is None:
                raise ValueError("FIGC timed pairing changed")
            hour, minute, home, away = game.groups()
            home, away = home.strip(), away.strip()
            if home not in CLUBS or away not in CLUBS or home == away:
                raise ValueError("FIGC pairing lacks two reviewed Serie A Women clubs")
            if home in teams_by_round[round_number] or away in teams_by_round[round_number]:
                raise ValueError("FIGC club appears twice in the same round")
            teams_by_round[round_number].update((home, away))
            # ZoneInfo applies CEST (UTC+2) on October 24 and CET (UTC+1)
            # from October 25. A fixed offset would shift every later kickoff.
            local = datetime.datetime.combine(current_day, datetime.time(int(hour), int(minute or 0)), ROME)
            day_counts[current_day] += 1
            round_counts[round_number] += 1
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
    if (seen_rounds != list(schedule) or seen_days != sorted(day_counts)
            or any(day_counts[day] != count for _, day, count in days.values())
            or any(count != 6 for count in round_counts.values())
            or any(teams != CLUBS for teams in teams_by_round.values())):
        raise ValueError("FIGC round fixture list is incomplete or out of order")
    if window_end > max(day_counts):
        raise ValueError("FIGC published rounds do not cover the full review window")
    return events
