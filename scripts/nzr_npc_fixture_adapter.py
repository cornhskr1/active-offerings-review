"""Scoped 2026 NPC regular-season fixtures from NZ Rugby's linked schedule PDF."""

import datetime
import io
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pdfplumber
from lxml import html


AUCKLAND = ZoneInfo("Pacific/Auckland")
MONTHS = {"JUL": 7, "AUG": 8, "SEPT": 9, "OCT": 10}
CLUBS = {
    "AUCKLAND", "BAY OF PLENTY", "CANTERBURY", "COUNTIES MANUKAU",
    "HAWKE’S BAY", "MANAWATŪ", "NORTH HARBOUR", "NORTHLAND",
    "OTAGO", "SOUTHLAND", "TARANAKI", "TASMAN", "WAIKATO", "WELLINGTON",
}
DISPLAY = {"HAWKE’S BAY": "Hawke’s Bay", "MANAWATŪ": "Manawatū",
           "BAY OF PLENTY": "Bay of Plenty", "NORTH HARBOUR": "North Harbour",
           "COUNTIES MANUKAU": "Counties Manukau"}


def club_name(club):
    return DISPLAY.get(club, club.title())


def publisher_pdf_url(page, source):
    if source.get("catalog_terms") != ["National Provincial Championship (NPC) | Men"]:
        raise ValueError("NPC catalog scope changed")
    doc = html.fromstring(page)
    urls = {urljoin(source["publisher_page"], href) for href in doc.xpath("//a/@href")
            if "NPC-SCHEDULE_Package-2026.pdf" in href}
    if urls != {source["endpoint"]}:
        raise ValueError("NZ Rugby's 2026 NPC schedule link changed")
    return source["endpoint"]


def _row(words, marker):
    y = marker["top"]
    home = " ".join(w["text"] for w in words if 290 < w["x0"] < 530
                    and abs(w["top"] - y) < 19)
    away = " ".join(w["text"] for w in words if 590 < w["x0"] < 780
                    and abs(w["top"] - y) < 19)
    # The PDF abbreviates Counties Manukau to Counties in two rounds.
    home = "COUNTIES MANUKAU" if home == "COUNTIES" else home
    away = "COUNTIES MANUKAU" if away == "COUNTIES" else away
    if home not in CLUBS or away not in CLUBS or home == away:
        raise ValueError("NPC PDF has an unknown or repeated club")
    return home, away


def parse_pdf(content, source, today, window_end):
    if source.get("catalog_terms") != ["National Provincial Championship (NPC) | Men"]:
        raise ValueError("NPC catalog scope changed")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if len(pdf.pages) != 12:
            raise ValueError("NPC PDF edition or page count changed")
        rounds = []
        for number, page in enumerate(pdf.pages[1:11], 1):
            words = page.extract_words()
            heading = " ".join(w["text"] for w in words if 390 < w["top"] < 425)
            if "ROUND" not in heading or "2026" not in heading:
                raise ValueError("NPC PDF round or edition changed")
            markers = [w for w in words if w["text"] == "V" and 500 < w["x0"] < 570]
            if len(markers) != 7:
                raise ValueError("NPC PDF round is incomplete")
            matches = [(_row(words, marker), words, marker) for marker in markers]
            if {club for (home, away), _, _ in matches for club in (home, away)} != CLUBS:
                raise ValueError("NPC PDF round clubs are incomplete or duplicated")
            rounds.append(matches)
        finals = pdf.pages[11].extract_text()
        if "QUARTER FINAL" not in finals or "KICK OFF TBC" not in finals:
            raise ValueError("NPC finals boundary changed")
        events = []
        for (home, away), words, marker in rounds[9]:
            date_text = " ".join(w["text"] for w in words if 180 < w["x0"] < 290
                                 and abs(w["top"] - marker["top"]) < 23)
            match = re.fullmatch(r"(THURSDAY|FRIDAY|SATURDAY|SUNDAY) (\d{1,2}) (OCT) (\d{2}:\d{2})", date_text)
            if not match:
                raise ValueError("NPC round ten lacks an exact date or kickoff")
            weekday, day, month, clock = match.groups()
            date = datetime.date(2026, MONTHS[month], int(day))
            if date.strftime("%A").upper() != weekday:
                raise ValueError("NPC PDF weekday and date disagree")
            if not today <= date <= window_end:
                continue
            local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), AUCKLAND)
            events.append({
                "id": f"nzr-npc-2026-r10-{date:%Y%m%d}-{re.sub('[^a-z0-9]+', '-', home.lower()).strip('-')}",
                "source_id": source["id"], "sport": source["sport"],
                "league": source["league"], "region": source["region"],
                "name": f"{club_name(away)} at {club_name(home)}",
                "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "NZ Rugby published NPC 2026 round 10",
                "season_stage": "REGULAR", "source_endpoint": source["publisher_page"],
            })
        return events, len(rounds), sum(len(group) for group in rounds)
