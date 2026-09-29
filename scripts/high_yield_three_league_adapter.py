"""Scoped official fixtures for Egypt Premier League, Saudi First Division, and NZ National League."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


CAIRO = ZoneInfo("Africa/Cairo")
RIYADH = ZoneInfo("Asia/Riyadh")
AUCKLAND = ZoneInfo("Pacific/Auckland")


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_egypt_fixture(page, source):
    if (source.get("id") != "caf-soccer-egypt-egyptian-premier-league-men"
            or source.get("league") != "Egyptian Premier League | Men"
            or source.get("catalog_terms") != ["Egyptian Premier League | Men"]):
        raise ValueError("Egypt Premier League catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    text = _norm(html.fromstring(page).text_content())
    required = ("المصري", "القناة", "الجولة 6", "الأحد 11 أكتوبر 2026", "05:00")
    for marker in required:
        if marker not in text:
            raise ValueError(f"Egypt Premier League publication changed: {marker}")
    local = datetime.datetime(2026, 10, 11, 17, 0, tzinfo=CAIRO)
    return [{
        "id": "egypt-premier-r6-20261011-al-qanah-al-masry",
        "source_id": source["id"], "sport": source["sport"], "league": source["league"],
        "region": source["region"], "name": "Al Masry at Al Qanah",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": "Egyptian Pro League published round 6 fixture",
        "season_stage": "ROUND 6", "source_endpoint": source["endpoint"],
    }]


def parse_saudi_fixture(page, source):
    if (source.get("id") != "soccer-afc-saudi-arabia-first-division-league-men"
            or source.get("league") != "First Division League | Men"
            or source.get("catalog_terms") != ["First Division League | Men"]):
        raise ValueError("Saudi First Division catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    text = _norm(html.fromstring(page).text_content())
    required = ("First Division League", "Wednesday 14-10-2026", "18:30", "Al Jandal", "Al Okhdood")
    for marker in required:
        if marker not in text:
            raise ValueError(f"Saudi First Division publication changed: {marker}")
    local = datetime.datetime(2026, 10, 14, 18, 30, tzinfo=RIYADH)
    return [{
        "id": "saudi-first-division-20261014-al-jandal-al-okhdood",
        "source_id": source["id"], "sport": source["sport"], "league": source["league"],
        "region": source["region"], "name": "Al Okhdood at Al Jandal",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": "SAFF published First Division fixture",
        "season_stage": "REGULAR", "location": "Al-Orobah Club Stadium (Al Jouf)",
        "source_endpoint": source["endpoint"],
    }]


NZ_TEAMS = (
    "Auckland City FC", "Auckland FC Reserves", "Auckland United FC",
    "Birkenhead United AFC", "Cashmere Technical FC", "Eastern Suburbs AFC",
    "Ferrymead Bays", "Monsoon Poon Miramar Rangers",
    "Thirsty Whale Napier City Rovers", "Wellington Olympic AFC",
    "WPX Academy Men's Reserve Team",
)


def parse_nz_fixtures(page, source):
    if (source.get("id") != "ofc-soccer-new-zealand-national-league-men"
            or source.get("league") != "New Zealand National League | Men"
            or source.get("catalog_terms") != ["New Zealand National League | Men"]):
        raise ValueError("NZ National League catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "Dettol Men's National League 2026" not in text:
        raise ValueError("NZ National League page identity changed")

    # The Sporty fixture widget renders each match as one visible text block.
    events, seen = [], set()
    for node in doc.xpath("//div|//li|//tr"):
        value = _norm(node.text_content())
        if "vs" not in value.lower():
            continue
        dm = re.search(r"(\d{2}/\d{2}/2026)\s+(\d{1,2}:\d{2}\s*[AP]M)", value, re.I)
        if not dm:
            continue
        teams = [team for team in NZ_TEAMS if team in value]
        if len(teams) != 2 or teams[0] == teams[1]:
            continue
        day = datetime.datetime.strptime(dm.group(1), "%d/%m/%Y").date()
        clock = datetime.datetime.strptime(dm.group(2).upper().replace(" ", ""), "%I:%M%p").time()
        local = datetime.datetime.combine(day, clock, AUCKLAND)
        key = (day, teams[0], teams[1])
        if key in seen:
            continue
        seen.add(key)
        slug = re.sub(r"[^a-z0-9]+", "-", teams[0].lower()).strip("-")
        events.append({
            "id": f"nz-national-{day:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{teams[1]} at {teams[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "NZ Football published championship fixture",
            "season_stage": "CHAMPIONSHIP", "source_endpoint": source["endpoint"],
        })
    if not events:
        raise ValueError("NZ National League page contained no timed men's fixtures")
    return events
