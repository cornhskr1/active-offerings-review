"""Parse the MFL's separately published 2026–27 league and FA Cup schedules."""

import datetime
import io
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pypdf import PdfReader

MALAYSIA = ZoneInfo("Asia/Kuala_Lumpur")
MONTHS = {"OGOS": 8, "SEPTEMBER": 9, "OKTOBER": 10, "NOVEMBER": 11,
          "DISEMBER": 12, "JANUARI": 1, "FEBRUARI": 2, "MAC": 3,
          "APRIL": 4, "MEI": 5}
SENIOR_CLUBS = {
    "JOHOR DARUL TA'ZIM", "KUCHING CITY FC", "SELANGOR FC", "KUALA LUMPUR CITY FC",
    "TERENGGANU FC", "STAR CITY FC", "NEGERI SEMBILAN FC", "PENANG FC",
    "SABAH FC", "DPMM FC", "MELAKA FC", "KELANTAN RED WARRIOR FC",
}
PDF_PATTERN = re.compile(r'https://files\.malaysianfootballleague\.com/[^"<>\s]+\.pdf')
ROW = re.compile(r"^\s*(\d{1,2}) (OGOS|SEPTEMBER|OKTOBER|NOVEMBER|DISEMBER|JANUARI|FEBRUARI|MAC|APRIL|MEI) (2026|2027), [A-Z]+\s+(\d+)\s+(.+?)\s+v\s+(.+?)\s+STADIUM\s+.+?\s+(\d{1,2})\.(\d{2}) (AM|PM)\s*$")
FA_ROW = re.compile(r"^\s*(\d{1,2}) (September|Oktober) (2026), [A-Za-z]+\s+(\d+)\s+(.+?)\s+v\s+(.+?)\s+STADIUM\s+.+?\s+(\d{1,2})\.(\d{2}) (AM|PM)\s*$")


def pdf_url(article, kind):
    matches = PDF_PATTERN.findall(article)
    token = "LIGA-SUPER-2026-2027" if kind == "league" else "PIALA-FA-2026-2027-PUSINGAN-SUKU-AKHIR"
    matches = [url for url in matches if token in url and urlparse(url).hostname == "files.malaysianfootballleague.com"]
    if len(set(matches)) != 1:
        raise ValueError("MFL exact competition schedule link changed")
    return matches[0]


def pdf_text(content):
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


def _event(row, source, kind):
    day, month, year, number, home, away, hour, minute, meridiem = row.groups()
    home, away = home.strip().replace("’", "'"), away.strip().replace("’", "'")
    if home == away or any(not club or re.search(r"\b(?:TBC|TBD|U-?\d{2})\b", club) for club in (home, away)):
        raise ValueError("MFL club pairing changed")
    month_number = MONTHS[month.upper()]
    hour = int(hour) % 12 + (12 if meridiem == "PM" else 0)
    local = datetime.datetime(int(year), month_number, int(day), hour, int(minute), tzinfo=MALAYSIA)
    return {
        "id": f"mfl-{kind}-2026-27-{number}", "source_id": source["id"],
        "sport": source["sport"], "league": source["league"], "region": source["region"],
        "name": f"{away} at {home}",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": "MFL published fixture",
        "season_stage": "REGULAR" if kind == "league" else "QUARTERFINAL",
        "location": None, "source_endpoint": source["endpoint"],
    }, (home, away)


def parse_mfl_schedule(text, source, kind, window_end):
    expected = {"league": "Malaysia Super League | Men", "fa-cup": "Malaysia FA Cup | Men"}
    if kind not in expected or source.get("catalog_terms") != [expected[kind]]:
        raise ValueError("MFL schedule is mapped to a different catalog competition")
    marker = r"KEMASKINI\s*:\s*2 SEPTEMBER 2026" if kind == "league" else r"KEMASKINI\s*:\s*17 SEPTEMBER 2026"
    if not re.search(marker, text) or ("LIGA PUSINGAN PERTAMA" if kind == "league" else "PERLAWANAN (PUSINGAN SUKU AKHIR)") not in text:
        raise ValueError("MFL schedule edition or revision changed")
    if kind == "league":
        section = re.search(r"\bLS5\s*\n(.*?)\bLS6\s*\n", text, re.S)
        if not section:
            raise ValueError("MFL league round five missing")
        rows = [ROW.match(line) for line in section.group(1).splitlines()]
        rows = [row for row in rows if row]
        expected_numbers = set(range(25, 31))
    else:
        section = re.search(r"FA QF \(2\)\s*\n(.*?)(?:\f|KEMASKINI)", text, re.S)
        if not section:
            raise ValueError("MFL FA Cup second quarterfinal legs missing")
        rows = [FA_ROW.match(line) for line in section.group(1).splitlines()]
        rows = [row for row in rows if row]
        expected_numbers = set(range(21, 25))
    if {int(row.group(4)) for row in rows} != expected_numbers or len(rows) != len(expected_numbers):
        raise ValueError("MFL published round is incomplete")
    events, clubs, held = [], [], 0
    for row in rows:
        event, pair = _event(row, source, kind)
        if kind == "fa-cup" and not set(pair) <= SENIOR_CLUBS:
            held += 1
            continue
        if kind == "league" and not set(pair) <= SENIOR_CLUBS:
            raise ValueError("MFL league club inventory changed")
        clubs.extend(pair)
        events.append(event)
    if kind == "league" and len(set(clubs)) != 12:
        raise ValueError("MFL league week has duplicate or missing clubs")
    if kind == "fa-cup" and held != 1:
        raise ValueError("MFL FA Cup lower-tier hold changed")
    horizon = datetime.date(2026, 10, 18) if kind == "league" else datetime.date(2026, 10, 11)
    if window_end > horizon:
        raise ValueError("MFL published round does not cover the full review window")
    return events, held
