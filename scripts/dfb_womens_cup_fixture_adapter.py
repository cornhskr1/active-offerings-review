"""Exact 2026/27 DFB women's cup round-of-16 appointment notice.

The publisher's shared date and clock headings apply to every following pairing
until replaced. No timezone is stated: preserve calendar dates and printed clocks
without converting them to timestamps. A complete eight-match round is still only
partial season coverage and establishes no participant-age or eligibility status.
"""

import datetime as dt
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-germany-dfb-pokal-frauen-women"
SOURCE_TYPE = "official-dfb-womens-cup-fixtures"
ENDPOINT = "https://www.dfb.de/news/pokalachtelfinale-zeitgenau-angesetzt-topspiel-bayern-gegen-leverkusen-live-bei-sky-und-im-ard-livestream"
LEAGUE = "DFB-Pokal Frauen | Women"
SEASON = "2026/2027"
TITLE = "Pokalachtelfinale zeitgenau angesetzt: Topspiel Bayern gegen Leverkusen live bei Sky und im ARD-Livestream"
ROUND_HEADING = "Die Spiele im Achtelfinale"
PUBLICATION = dt.date(2026, 10, 5)
CHICAGO = ZoneInfo("America/Chicago")
MONTHS = dict(zip(("Januar", "Februar", "März", "April", "Mai", "Juni",
                   "Juli", "August", "September", "Oktober", "November", "Dezember"), range(1, 13)))
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
# Verified round cohort and actual home/away order, never fuzzy alias matching.
# Slots provide stable IDs even when this publication changes a date or clock.
PAIRINGS = (
    ("VfB Stuttgart", "SGS Essen"),
    ("1. FC Köln", "RB Leipzig"),
    ("Hamburger SV", "1. FC Union Berlin"),
    ("1. FC Nürnberg", "Eintracht Frankfurt"),
    ("SC Freiburg", "Carl Zeiss Jena"),
    ("1. FSV Mainz 05", "SV Werder Bremen"),
    ("FC Bayern München", "Bayer 04 Leverkusen"),
    ("VfL Wolfsburg", "TSG Hoffenheim"),
)


def source_config():
    return {
        "id": SOURCE_ID, "sport": "Soccer", "league": LEAGUE,
        "region": "Germany", "source_type": SOURCE_TYPE,
        "coverage_status": "partial", "coverage_complete": False,
        "endpoint": ENDPOINT, "official_schedule_url": ENDPOINT,
        "catalog_terms": [LEAGUE],
        "source_note": "Official DFB 2026/27 women's cup round-of-16 appointment notice, reconciled to eight pairings and 16 named clubs. Date-only because the printed clocks have no verified timezone. Partial published-round coverage, not a complete season; zero review-window fixtures is not offseason evidence. Participant ages, professional status and market eligibility require separate review.",
    }


def _scope(source):
    expected = source_config()
    for key in ("id", "sport", "league", "region", "source_type", "endpoint",
                "official_schedule_url", "catalog_terms", "coverage_status", "coverage_complete"):
        if source.get(key) != expected[key]:
            raise ValueError("DFB women's cup exact catalog scope or partial-coverage boundary changed")


def _class(name):
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def _text(node):
    return " ".join(node.text_content().split())


def _one(node, xpath, label):
    found = node.xpath(xpath)
    if len(found) != 1:
        raise ValueError(f"DFB women's cup {label} missing or duplicated")
    return found[0]


def _date(text):
    match = re.fullmatch(r"(\w+), (\d{1,2})\. (\w+)(?: (20\d{2}))?", text)
    if not match or match[3] not in MONTHS:
        raise ValueError("DFB women's cup date heading changed")
    month = MONTHS[match[3]]
    # The explicit 2026/2027 edition and October 2026 publication establish
    # the year for the publisher's yearless October/November headings.
    year = 2026 if month >= 7 else 2027
    if match[4] and int(match[4]) != year:
        raise ValueError("DFB women's cup fixture edition changed")
    day = dt.date(year, month, int(match[2]))
    if day < PUBLICATION or WEEKDAYS[day.weekday()] != match[1]:
        raise ValueError("DFB women's cup date weekday or publication horizon changed")
    return day


def parse_fixtures(page, source):
    """Validate the entire official round before returning any date-only cards."""
    _scope(source)
    doc = html.fromstring(page.decode("utf-8") if isinstance(page, bytes) else page)
    canonical = _one(doc, '//link[@rel="canonical"]', "canonical endpoint")
    if canonical.get("href") != ENDPOINT or _text(_one(doc, '//title', "page title")) != TITLE:
        raise ValueError("DFB women's cup official article identity changed")
    hero = _one(doc, f'//div[{_class("m-Hero-container")}]', "article header")
    if (_text(_one(hero, './h1', "competition heading")) != "DFB-Pokal der Frauen"
            or _text(_one(hero, './h2', "article heading")) != TITLE):
        raise ValueError("DFB women's cup competition or round identity changed")
    published = _text(_one(hero, f'./div[{_class("m-Hero-info")}]', "publication date"))
    if published != PUBLICATION.strftime("%d.%m.%Y"):
        raise ValueError("DFB women's cup publication date or edition changed")
    body = _one(doc, f'//div[{_class("dfb-Rte")}][h3="{ROUND_HEADING}"]', "round article")
    if re.findall(r"\bSaison (\d{4}/\d{4})\b", _text(body)) != [SEASON]:
        raise ValueError("DFB women's cup explicit season changed")
    heading = _one(body, f'./h3[text()="{ROUND_HEADING}"]', "round fixture heading")
    rows = list(heading.itersiblings())
    if not rows or any(row.tag != "p" for row in rows):
        raise ValueError("DFB women's cup fixture list layout changed")
    events, seen, clubs = [], set(), Counter()
    current_day, current_clock, clock_count = None, None, 0
    dates, clock_groups = set(), set()
    for row in rows:
        text = _text(row)
        if not text or row.attrib or row.xpath('.//script|.//style|.//*[@hidden]'):
            raise ValueError("DFB women's cup empty, flagged or hidden schedule row")
        if row.xpath('./strong'):
            if (len(row) != 1 or row[0].tag != "strong" or _text(row[0]) != text
                    or len(row[0]) or row[0].attrib):
                raise ValueError("DFB women's cup shared heading layout changed")
            if "Uhr" not in text:
                next_day = _date(text)
                if (current_day is not None and (not clock_count or next_day <= current_day)
                        or next_day in dates):
                    raise ValueError("DFB women's cup duplicate, unsorted or unused date heading")
                dates.add(next_day)
                current_day, current_clock, clock_count = next_day, None, 0
                continue
            clock = re.fullmatch(r"(\d{1,2}(?:[.:]\d{2})? Uhr) – live (?:auf|bei) (DFB\.TV|Sky(?: und im ARD-Livestream)?)", text)
            if not clock or current_day is None or (current_clock is not None and not clock_count):
                raise ValueError("DFB women's cup clock heading missing, malformed or unused")
            value = clock[1].removesuffix(" Uhr").replace(".", ":")
            hour, minute = (value.split(":") + ["00"])[:2]
            dt.time(int(hour), int(minute))
            if (current_day, clock[1]) in clock_groups:
                raise ValueError("DFB women's cup duplicate clock heading")
            clock_groups.add((current_day, clock[1]))
            current_clock, clock_count = clock[1], 0
            continue
        if len(row):
            raise ValueError("DFB women's cup pairing layout changed")
        pair = tuple(text.split(" vs. "))
        if len(pair) != 2 or pair not in PAIRINGS:
            raise ValueError("DFB women's cup exact women's round pairing or home/away identity changed")
        if current_day is None or current_clock is None:
            raise ValueError("DFB women's cup pairing missing shared date or clock heading")
        if pair in seen:
            raise ValueError("DFB women's cup duplicate pairing")
        seen.add(pair)
        clubs.update(pair)
        clock_count += 1
        home, away = pair
        events.append({
            "id": f"dfb-womens-cup-2026-27-r16-{PAIRINGS.index(pair) + 1}",
            "source_id": SOURCE_ID, "sport": "Soccer", "league": LEAGUE,
            "region": "Germany", "name": f"{away} at {home}",
            "start_time": current_day.isoformat(), "date_only": True,
            "status": "UPCOMING", "season_stage": "ROUND OF 16",
            "status_detail": "Official DFB women's cup fixture date only; publisher timezone unverified. Participant ages, professional status and market eligibility require separate review.",
            "published_kickoff_text": current_clock, "participant_review_required": True,
            "location": None, "source_endpoint": ENDPOINT,
        })
    if not clock_count or seen != set(PAIRINGS) or len(clubs) != 16 or set(clubs.values()) != {1}:
        raise ValueError("DFB women's cup missing pairings or 8-match/16-club round reconciliation failed")
    events.sort(key=lambda event: (event["start_time"], event["id"]))
    evidence = {
        "coverage_status": "partial", "coverage_complete": False,
        "published_edition": SEASON, "publication_date": PUBLICATION.isoformat(),
        "published_phase": "ROUND OF 16", "published_fixtures": len(events),
        "published_clubs": len(clubs), "published_date_headings": len(dates),
        "published_clock_headings": len(clock_groups),
        "published_first_fixture_date": events[0]["start_time"],
        "published_last_fixture_date": events[-1]["start_time"],
        "date_only_fixtures": len(events), "review_window_complete": False,
        "timezone_status": "unverified; literal publisher dates retained",
        "participant_age_coverage": "unverified",
        "professional_status_coverage": "not established by schedule",
        "coverage_note": "Partial published women's round-of-16 coverage only. Later undrawn rounds remain uncovered. No review-window fixtures does not imply offseason, participant-age verification or market eligibility clearance.",
    }
    return events, evidence


def fetch_fixtures(source, now, get=None):
    """Fetch once and return all current/future dates, not just the review week."""
    _scope(source)
    if not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("DFB women's cup requires an aware review timestamp")
    today = now.astimezone(CHICAGO).date()
    if not PUBLICATION <= today <= dt.date(2027, 6, 30):
        raise ValueError("DFB women's cup publication/edition review horizon expired or invalid")
    if get is None:
        import requests
        get = requests.get
    response = get(ENDPOINT, timeout=30, allow_redirects=False)
    if response.status_code in (401, 403, 429):
        raise ValueError(f"DFB women's cup publisher denied HTTP {response.status_code}; no retry or alternate route")
    if response.status_code != 200:
        raise ValueError(f"DFB women's cup expected HTTP 200, received {response.status_code}")
    if response.url != ENDPOINT:
        raise ValueError("DFB women's cup response moved away from the exact official endpoint")
    events, evidence = parse_fixtures(response.content, source)
    upcoming = [event for event in events if event["start_time"] >= today.isoformat()]
    if not upcoming:
        raise ValueError("DFB women's cup has no admissible current/future fixtures; stale publication is not offseason evidence")
    evidence.update({"past_unresolved_fixtures_held": len(events) - len(upcoming),
                     "future_confirmed_fixtures": len(upcoming),
                     "date_only_fixtures": len(upcoming), "requested_endpoints": [ENDPOINT]})
    return upcoming, evidence
