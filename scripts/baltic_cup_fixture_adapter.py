"""Exact LFF men's 2026 cup fixtures, cross-checked against both publisher views.

Estonia is intentionally not promoted: its 2026/27 calendar has only month-level
future dates, and linked stage feeds currently contain no future named fixtures.
Neither an empty window nor a successfully downloaded page establishes offseason,
participant-age coverage, professional status, or market eligibility.
"""

import datetime as dt
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-latvia-latvian-cup-latvijas-kauss-men"
SOURCE_TYPE = "official-lff-cup-fixtures"
ENDPOINT = "https://lff.lv/sacensibas/viriesi/latvijas-kauss/"
COMPETITION_ID = "23910990"
REVIEW_ZONE = ZoneInfo("America/Chicago")
LEAGUE = "Latvian Cup / Latvijas Kauss | Men"
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "jūn": 6,
          "jūl": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}
STAGES = {"1/64 fināls": "ROUND OF 128", "1/32 fināls": "ROUND OF 64",
          "1/16 fināls": "ROUND OF 32", "1/8 fināls": "ROUND OF 16",
          "1/4 fināls": "QUARTERFINALS", "Pusfināli": "SEMIFINALS", "Fināls": "FINAL"}
PLACEHOLDER = re.compile(r"\b(?:tbc|tbd|tba|unknown|winner|loser|uzvarētājs)\b|[/]", re.I)
YOUTH_RESERVE = re.compile(r"\b(?:u[ -]?\d{1,2}|under[ -]?\d{1,2}|youth|junior\w*|reserves?)\b|\b(?:II|III|IV)\b|(?:\sB)$", re.I)
AMATEUR = re.compile(r"\b(?:amateur\w*|amatier\w*)\b", re.I)


def source_configs():
    return [{"id": SOURCE_ID, "sport": "Soccer", "league": LEAGUE,
             "region": "Latvia", "source_type": SOURCE_TYPE,
             "coverage_status": "partial", "coverage_complete": False,
             "endpoint": ENDPOINT, "official_schedule_url": ENDPOINT,
             "catalog_terms": [LEAGUE],
             "source_note": "Official 2026 men's Latvijas kauss named future pairings, cross-checked against full and upcoming LFF views. Date-only because publisher timezone is unverified. Partial published-pairing coverage; zero review-window fixtures is not offseason. Participant ages, professional status and market eligibility remain separate review requirements."}]


def _scope(source):
    expected = source_configs()[0]
    for key in ("id", "sport", "league", "region", "source_type", "endpoint",
                "official_schedule_url", "catalog_terms", "coverage_status", "coverage_complete"):
        if source.get(key) != expected[key]:
            raise ValueError("LFF cup exact approved scope or partial-coverage boundary changed")


def _class(name):
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def _text(node, xpath=".//text()"):
    return " ".join(" ".join(node.xpath(xpath)).split())


def _one(node, xpath, label):
    found = node.xpath(xpath)
    if len(found) != 1:
        raise ValueError(f"LFF cup {label} missing or duplicated")
    return found[0]


def _clubs(row):
    clubs = row.xpath(f'.//div[{_class("clubs")}]/div[{_class("club")}]')
    if len(clubs) != 2:
        raise ValueError("LFF cup two named opponents required")
    names, links, scores = [], [], []
    for index, club in enumerate(clubs, 1):
        link = _one(club, f'.//div[{_class("title")}]//a', "opponent link")
        name, href = _text(link), link.get("href", "")
        if not name or not re.fullmatch(r"/klubi/[\w-]+/\?cid=" + COMPETITION_ID, href):
            raise ValueError("LFF cup named opponent or competition ID changed")
        names.append(name)
        links.append(href)
        scores.append(_text(_one(club, f'.//span[{_class("res" + str(index))}]', "score")))
    if names[0] == names[1] or links[0] == links[1]:
        raise ValueError("LFF cup opponents are identical")
    return names, links, scores


def _clock(value):
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("LFF cup printed kickoff changed")
    dt.time.fromisoformat(value)  # Preserve text; do not manufacture a timezone.
    return value


def parse_fixtures(page, source, today):
    """Return only future named pairings corroborated in both official views."""
    _scope(source)
    if type(today) is not dt.date or today.year != 2026:
        raise ValueError("LFF cup 2026 edition expired or review date invalid")
    text = page.decode("utf-8") if isinstance(page, bytes) else page
    doc = html.fromstring(text)
    if _text(doc, "//title/text()") != "LVBET Latvijas kauss - Latvijas Futbola federācija":
        raise ValueError("LFF cup competition identity changed")
    if "LVBET Latvijas kauss" not in [_text(x) for x in doc.xpath('//h1')]:
        raise ValueError("LFF cup senior competition heading changed")
    select = _one(doc, f'//select[{_class("pageParams")}]', "edition selector")
    selected = select.xpath('./option[@selected]') or select.xpath('./option[1]')
    if (len(selected) != 1 or _text(selected[0]) != "2026"
            or selected[0].get("value") != "/sacensibas/viriesi/latvijas-kauss/"):
        raise ValueError("LFF cup explicit 2026 edition changed")
    upcoming = _one(doc, '//*[@id="tabContent_1_1"]//div[@data-genid]', "upcoming feed")
    complete = _one(doc, '//*[@id="tabContent_1_2"]//div[@data-genid]', "full feed")
    for feed in (upcoming, complete):
        if not feed.get("data-genid", "").startswith(f"stats_competition_{COMPETITION_ID}_"):
            raise ValueError("LFF cup competition feed ID changed")

    all_rows, phase, completed = {}, None, 0
    for row in complete:
        classes = row.get("class", "").split()
        if "th1" in classes:
            phase = _text(row, f'.//span[{_class("h3")}]//text()')
            if phase not in STAGES:
                raise ValueError("LFF cup phase changed")
            continue
        if "match" not in classes:
            continue
        mid = row.get("data-id", "")
        if not phase or not mid.isdecimal() or mid in all_rows:
            raise ValueError("LFF cup missing or duplicate fixture identity")
        names, links, scores = _clubs(row)
        date = _one(row, f'.//div[{_class("date")}]', "full date")
        day, month, year = _text(date, './h5/text()'), _text(date, './h6/text()'), _text(date, f'./div[{_class("h8")}]/text()')
        if not day.isdecimal() or month.lower() not in MONTHS or year != "2026":
            raise ValueError("LFF cup explicit full-year date changed")
        full_day = dt.date(int(year), MONTHS[month.lower()], int(day))
        clock = _clock(_text(date, f'./div[{_class("h7")}]/text()'))
        venue = _text(row, f'.//div[{_class("stadium")}]//text()')
        if not venue:
            raise ValueError("LFF cup venue missing")
        if scores != ["-", "-"]:
            if not all(re.fullmatch(r"\d+", value) for value in scores):
                raise ValueError("LFF cup unknown result or status")
            completed += 1
        all_rows[mid] = (full_day, phase, names, links, scores, clock, venue)
    if not all_rows:
        raise ValueError("LFF cup full fixture view empty; absence is not offseason evidence")

    events, seen, published, past = [], set(), 0, 0
    holds = {"unresolved_pairings_held": 0, "age_or_reserve_fixtures_held": 0, "amateur_scope_held": 0}
    current_day = None
    for row in upcoming:
        classes = row.get("class", "").split()
        if "th1" in classes:
            heading = _text(row, f'.//span[{_class("h3")}]//text()')
            match = re.fullmatch(r"\w+, (\d{2})\.(\d{2})\.(2026)\.", heading)
            if not match:
                raise ValueError("LFF cup upcoming explicit date changed")
            current_day = dt.date(int(match[3]), int(match[2]), int(match[1]))
            continue
        if "match" not in classes:
            continue
        published += 1
        mid = row.get("data-id", "")
        if not current_day or mid not in all_rows or mid in seen:
            raise ValueError("LFF cup upcoming fixture missing or duplicated in full view")
        seen.add(mid)
        names, links, scores = _clubs(row)
        phase = _text(row, f'.//div[{_class("matchday")}]/h6/text()')
        clock = _clock(_text(row, f'.//div[{_class("matchday")}]/h4/text()'))
        venue = _text(row, f'.//div[{_class("stadium")}]//text()')
        if scores != ["-", "-"] or phase not in STAGES:
            raise ValueError("LFF cup upcoming fixture is not an unplayed cup pairing")
        if all_rows[mid] != (current_day, phase, names, links, scores, clock, venue):
            raise ValueError("LFF cup full and upcoming fixture views disagree")
        if current_day < today:
            past += 1
            continue
        held = next((key for key, regex in (("unresolved_pairings_held", PLACEHOLDER),
                    ("age_or_reserve_fixtures_held", YOUTH_RESERVE),
                    ("amateur_scope_held", AMATEUR)) if any(regex.search(name) for name in names)), None)
        if held:
            holds[held] += 1
            continue
        events.append({"id": f"lff-cup-{mid}", "source_id": SOURCE_ID,
            "sport": "Soccer", "league": LEAGUE, "region": "Latvia",
            "name": f"{names[1]} at {names[0]}", "start_time": current_day.isoformat(),
            "date_only": True, "status": "UPCOMING", "season_stage": STAGES[phase],
            "status_detail": "Official 2026 LFF cup fixture date only; publisher timezone unverified. Participant ages and market eligibility require separate review.",
            "published_kickoff_text": clock, "participant_review_required": True,
            "location": venue, "source_endpoint": ENDPOINT})
    if not published:
        raise ValueError("LFF cup has no published upcoming fixtures; absence is not offseason evidence")
    events.sort(key=lambda event: (event["start_time"], event["id"]))
    evidence = {"coverage_status": "partial", "coverage_complete": False,
        "published_edition": "2026", "publisher_competition_id": COMPETITION_ID,
        "published_full_view_rows": len(all_rows), "published_upcoming_fixtures": published,
        "completed_fixtures_excluded": completed, "past_unplayed_fixtures_held": past,
        "verified_future_fixtures": len(events), "date_only_fixtures": len(events),
        "timezone_status": "unverified; literal publisher dates retained",
        "review_window_complete": False, "participant_age_coverage": "unverified",
        "professional_status_coverage": "not established by schedule",
        "coverage_note": "Partial published pairings cross-checked against both LFF views. Unpublished or unverified future pairings remain uncovered. No review-window cards does not imply offseason or eligibility clearance.",
        **holds}
    return events, evidence


def fetch_fixtures(source, now, get=None):
    """Read one exact official page once, with no fallback after denial."""
    _scope(source)
    if isinstance(now, dt.datetime):
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("LFF cup refresh timestamp must be timezone-aware")
        today = now.astimezone(REVIEW_ZONE).date()
    else:
        today = now
    if type(today) is not dt.date or today.year != 2026:
        raise ValueError("LFF cup 2026 edition expired or review date invalid")
    if get is None:
        import requests
        get = requests.get
    response = get(ENDPOINT, timeout=30, allow_redirects=False)
    if response.status_code in (401, 403, 429):
        raise ValueError(f"LFF cup publisher denied HTTP {response.status_code}; no retry or alternate route")
    if response.status_code != 200:
        raise ValueError(f"LFF cup expected HTTP 200, received {response.status_code}")
    if response.url != ENDPOINT:
        raise ValueError("LFF cup response moved away from the exact approved endpoint")
    events, evidence = parse_fixtures(response.content, source, today)
    if not events:
        raise ValueError(
            "LFF cup has no admissible future fixture: published cards are past or held; "
            "source coverage remains unresolved, not offseason or eligibility clearance "
            f"(past={evidence['past_unplayed_fixtures_held']}, "
            f"unresolved={evidence['unresolved_pairings_held']}, "
            f"age/reserve={evidence['age_or_reserve_fixtures_held']}, "
            f"amateur={evidence['amateur_scope_held']})")
    evidence["requested_endpoints"] = [ENDPOINT]
    return events, evidence
