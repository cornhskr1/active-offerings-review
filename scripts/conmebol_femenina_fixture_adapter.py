"""Read the published 2026 CONMEBOL Libertadores Femenina group fixture list."""

import datetime
import html
import re
import unicodedata
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("America/Guayaquil")
MONTH_DAYS = {"jueves": {15, 22}, "viernes": {16}, "domingo": {18},
              "lunes": {19}, "miercoles": {21}}
VENUES = {"Banco Guayaquil", "Rodrigo Paz Delgado"}


def plain(markup):
    return html.unescape(re.sub(r"<[^>]+>", " ", markup)).replace("\xa0", " ").strip()


def fold(value):
    return "".join(char for char in unicodedata.normalize("NFD", value.lower())
                   if unicodedata.category(char) != "Mn")


def parse_group_fixtures(page, source):
    if "Copa Libertadores Femenina | Women" not in source.get("catalog_terms", []):
        raise ValueError("CONMEBOL source lacks the exact women's catalog identity")
    section = re.search(
        r"<h2\b[^>]*>[^<]*(?:<[^>]+>)*Calendario de la CONMEBOL Libertadores Femenina 2026"
        r".*?</h2>(.*?)(?=<h2\b|</article>)", page, re.I | re.S,
    )
    if not section:
        raise ValueError("CONMEBOL 2026 women's fixture section is missing")
    day = None
    days = set()
    fixtures = []
    held = []
    for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", section.group(1), re.I | re.S):
        line = re.sub(r"\s+", " ", plain(paragraph))
        heading = re.fullmatch(r"(\w+) (\d{1,2}) de octubre", fold(line))
        if heading:
            weekday, number = heading.group(1), int(heading.group(2))
            if number not in MONTH_DAYS.get(weekday, set()):
                raise ValueError("CONMEBOL fixture date or weekday changed")
            day = datetime.date(2026, 10, number)
            days.add(day)
            continue
        if not re.match(r"^\d{2}:\d{2}h\b", line):
            continue
        match = re.fullmatch(r"(\d{2}):(\d{2})h\s+(.+?)\s+vs\.?\s+(.+?)\s+\(([^()]+)\)", line, re.I)
        if not match or day is None:
            raise ValueError("CONMEBOL fixture has no exact date, teams, time, or venue")
        hour, minute = int(match.group(1)), int(match.group(2))
        home, away, venue = (value.strip() for value in match.group(3, 4, 5))
        if venue not in VENUES or hour not in (15, 19) or minute != 0:
            raise ValueError("CONMEBOL fixture time or venue changed")
        start = datetime.datetime.combine(day, datetime.time(hour, minute), LOCAL_TZ)
        item = {
            "id": f"conmebol-fem-2026-{day:%Y%m%d}-{hour:02d}{minute:02d}-{len(fixtures)+len(held)+1:02d}",
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "Published group fixture",
            "season_stage": "GROUP", "location": venue,
            "source_endpoint": source["endpoint"],
        }
        if re.search(r"\b(?:colombia [12]|representante|tbc|tbd)\b", f"{home} {away}", re.I):
            held.append(item)
        else:
            fixtures.append(item)
    if len(days) != 6 or len(fixtures) + len(held) != 24:
        raise ValueError("CONMEBOL group fixture list is incomplete or changed")
    return fixtures, held
