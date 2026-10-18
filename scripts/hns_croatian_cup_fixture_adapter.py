"""Exact senior 2026/27 Croatian Cup pairings from the HNS Semafor page.

Only the competition's current-results panel is read; player/scorer/profile
sections are deliberately ignored. Printed clocks do not establish a timezone,
so all emitted fixtures retain the literal publisher date. Preliminary rounds,
completed scores, and unresolved/non-senior opponents cannot become cards.
"""

import datetime
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-croatia-croatian-cup-men"
ENDPOINT = "https://semafor.hns.family/natjecanja/114492931/supersport-hnk/"
SOURCE_TYPE = "official-hns-croatian-cup-fixtures"
SEASON = "2026/2027"
CHICAGO = ZoneInfo("America/Chicago")
# Verified publisher phase IDs. New phases require review, not guessed IDs.
PHASES = {
    "10002": ("1/32 finala", "PRELIMINARY"),
    "10003": ("1/16 finala", "ROUND OF 32"),
    "10004": ("1/8 finala", "ROUND OF 16"),
}
PLACEHOLDER = re.compile(r"\b(?:tbc|tbd|unknown|winner|pobjednik|nepoznat\w*)\b|[/]", re.I)
NON_SENIOR = re.compile(
    r"\b(?:u\s*-?\s*\d{2}|under\s*\d{2}|junior\w*|kadet\w*|pionir\w*|"
    r"youth|reserve\w*|rezerv\w*)\b|(?:\s(?:B|II))$", re.I)
AMATEUR = re.compile(r"\b(?:amateur\w*|amater\w*)\b", re.I)


def source_config():
    return {
        "id": SOURCE_ID, "sport": "Soccer", "league": "Croatian Cup | Men",
        "region": "Croatia", "source_type": SOURCE_TYPE,
        "coverage_status": "partial", "endpoint": ENDPOINT,
        "official_schedule_url": ENDPOINT,
        "catalog_terms": ["Croatian Cup | Men"],
        "source_note": "Official HNS 2026/27 named unplayed senior cup pairings, excluding the preliminary round. Dates are date-only because publisher timezone is unverified. Partial published-phase coverage, not a complete season. Zero current-window fixtures is not offseason evidence; participant ages, professional status, and market eligibility require separate review.",
    }


def _class(name):
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def _text(node):
    return " ".join(node.text_content().split())


def _one(node, xpath, label):
    found = node.xpath(xpath)
    if len(found) != 1:
        raise ValueError(f"HNS Croatian Cup {label} missing or duplicated")
    return found[0]


def _scope(source):
    required = {
        "id": SOURCE_ID, "sport": "Soccer", "league": "Croatian Cup | Men",
        "region": "Croatia", "source_type": SOURCE_TYPE,
        "catalog_terms": ["Croatian Cup | Men"], "endpoint": ENDPOINT,
        "coverage_status": "partial",
    }
    if any(source.get(key) != value for key, value in required.items()):
        raise ValueError("HNS Croatian Cup catalog scope or official endpoint changed")


def _club(row, side):
    club = _one(row, f'./div/div[{_class(side)}]', "opponent")
    identifier = club.get("data-id", "")
    link = _one(club, './a', "opponent link")
    name = _text(link)
    if not re.fullmatch(r"[1-9]\d*", identifier) or not name:
        raise ValueError("HNS Croatian Cup named opponent evidence changed")
    if not re.fullmatch(rf"/klubovi/{identifier}/[a-z0-9-]+/", link.get("href", "")):
        raise ValueError("HNS Croatian Cup opponent identity mismatch")
    image = _one(link, f'./div[{_class("logo")}]/img', "opponent logo")
    if image.get("alt") != name:
        raise ValueError("HNS Croatian Cup opponent label mismatch")
    return name, identifier


def _date(row):
    printed = _text(_one(row, f'./div/div[{_class("date")}]', "fixture date"))
    match = re.fullmatch(r"(\d{2}\.\d{2}\.20\d{2}\.)(?: (\d{2}:\d{2}))?", printed)
    if not match:
        raise ValueError("HNS Croatian Cup date or printed clock changed")
    day = datetime.datetime.strptime(match.group(1), "%d.%m.%Y.").date()
    if not datetime.date(2026, 7, 1) <= day <= datetime.date(2027, 6, 30):
        raise ValueError("HNS Croatian Cup fixture edition changed")
    if match.group(2):
        datetime.time.fromisoformat(match.group(2))
    return day.isoformat(), match.group(2)


def parse_fixtures(page, source):
    """Parse unplayed main-draw pairings; the fetch wrapper holds stale dates."""
    _scope(source)
    doc = html.fromstring(page.decode("utf-8") if isinstance(page, bytes) else page)
    if doc.xpath('string(//title)') != "SuperSport HNK - Hrvatski nogometni savez":
        raise ValueError("HNS Croatian Cup page identity changed")
    title = _one(doc, f'//div[{_class("competition-title")}]', "competition title")
    if [_text(x) for x in title.xpath('./h1|./h2')] != ["SuperSport HNK", SEASON]:
        raise ValueError("HNS Croatian Cup competition or edition changed")
    season = _one(doc, '//select[@id="season"]/option[@selected]', "selected edition")
    if season.get("value") != SEASON or _text(season) != "2026/27":
        raise ValueError("HNS Croatian Cup selected edition changed")
    authority = _one(doc, '//select[@id="oid"]/option[@selected]', "national authority")
    if authority.get("value") != "1" or _text(authority) != "Hrvatski nogometni savez":
        raise ValueError("HNS Croatian Cup national authority changed")
    endpoint_option = _one(doc, f'//select[@id="cid"]/option[@value="{ENDPOINT}"]', "edition endpoint")
    if _text(endpoint_option) != "SuperSport HNK":
        raise ValueError("HNS Croatian Cup edition endpoint identity changed")
    section = _one(doc, f'//div[{_class("competition_results_scorers_cards")}]', "competition fixture section")
    panel = _one(section, f'./div[{_class("grid")}]/div[{_class("colMiddle")}]/div[{_class("current_results")}]', "fixture panel")
    listing = _one(panel, f'./div[{_class("matchlist")}]/ul', "fixture list")
    rows = listing.xpath('./li[@data-match]')
    if (not rows or len(rows) != len(panel.xpath('.//*[@data-match]'))
            or len(listing.xpath('./li')) != len(listing)):
        raise ValueError("HNS Croatian Cup fixture layout changed")

    events, seen_ids, seen_pairings = [], set(), set()
    holds, phases = Counter(), Counter()
    seen_phases, current_phase = set(), None
    for row in listing:
        classes = set((row.get("class") or "").split())
        phase = row.get("data-round")
        if phase not in PHASES:
            raise ValueError("HNS Croatian Cup unknown phase")
        if "header" in classes:
            if (classes - {"header", "visible", "hidden"} or phase in seen_phases
                    or row.get("data-match") or _text(row) != PHASES[phase][0]):
                raise ValueError("HNS Croatian Cup phase identity changed")
            seen_phases.add(phase)
            current_phase = phase
            continue
        if ("row" not in classes or classes - {"row", "visible", "hidden"}
                or phase != current_phase
                or set(row.attrib) - {"class", "data-round", "data-match"}):
            raise ValueError("HNS Croatian Cup fixture layout or phase changed")
        row_body = _one(row, './div', "fixture body")
        if ([node.get("class") for node in row_body] != [
                "expand", "date", "club1", "result", "club2", "facility", "link nolink"]
                and not row_body.xpath(f'./div[{_class("result")}]/a')):
            raise ValueError("HNS Croatian Cup unplayed fixture layout or status changed")
        identifier = row.get("data-match", "")
        if not re.fullmatch(r"[1-9]\d*", identifier) or identifier in seen_ids:
            raise ValueError("HNS Croatian Cup duplicate or invalid match identity")
        seen_ids.add(identifier)
        result = _one(row, f'./div/div[{_class("result")}]', "result")
        score = [_text(_one(result, f'.//div[{_class(name)}]', "score"))
                 for name in ("res1", "res2")]
        if _text(_one(result, f'.//div[{_class("sep")}]', "score separator")) != ":":
            raise ValueError("HNS Croatian Cup score separator changed")
        completed = all(re.fullmatch(r"\d+", value) for value in score)
        if not completed and score != ["-", "-"]:
            raise ValueError("HNS Croatian Cup ambiguous result status")
        if phase == "10002":
            holds["preliminary_fixtures_excluded"] += 1
        if completed:
            holds["completed_fixtures_excluded"] += 1
            continue
        holds["published_unplayed_fixtures"] += 1
        # A bare '-:-' is the observed unplayed representation. A result link,
        # penalty text, postponement/cancellation flag, or extra status is not.
        if (set(result.get("class", "").split()) != {"result"}
                or result.xpath('.//a') or _text(result) != "-:-"
                or len(result.xpath('./div')) != 1
                or not result.xpath(f'./div[{_class("resRegular")}]')
                or len(result.xpath('./div/*')) != 3):
            raise ValueError("HNS Croatian Cup unplayed status changed")
        if phase == "10002":
            continue
        home, home_id = _club(row, "club1")
        away, away_id = _club(row, "club2")
        if home == away or home_id == away_id:
            raise ValueError("HNS Croatian Cup identical opponents")
        pairing = (phase, *sorted((home_id, away_id)))
        if pairing in seen_pairings:
            raise ValueError("HNS Croatian Cup duplicate phase pairing")
        seen_pairings.add(pairing)
        date, clock = _date(row)
        phases[PHASES[phase][0]] += 1
        holds["published_clocks_without_verified_timezone"] += bool(clock)
        if any(PLACEHOLDER.search(name) for name in (home, away)):
            holds["unresolved_pairings_held"] += 1
            continue
        if any(NON_SENIOR.search(name) for name in (home, away)):
            holds["age_or_reserve_fixtures_held"] += 1
            continue
        if any(AMATEUR.search(name) for name in (home, away)):
            holds["amateur_scope_held"] += 1
            continue
        facility = _one(row, f'./div/div[{_class("facility")}]', "facility")
        events.append({
            "id": f"hns-croatian-cup-2026-27-{identifier}", "source_id": SOURCE_ID,
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}", "start_time": date, "date_only": True,
            "status": "UPCOMING", "season_stage": PHASES[phase][1],
            "status_detail": "Official HNS Croatian Cup fixture date only; publisher timezone unverified. Participant ages, professional status, and market eligibility require separate review.",
            "published_kickoff_text": clock, "participant_review_required": True,
            "location": _text(facility) or None, "source_endpoint": ENDPOINT,
        })
    if not holds["published_unplayed_fixtures"]:
        raise ValueError("HNS Croatian Cup has no published unplayed fixtures; absence is not offseason evidence")
    events.sort(key=lambda event: (event["start_time"], event["id"]))
    evidence = {
        "coverage_status": "partial", "published_edition": SEASON,
        "published_fixtures": len(rows), "published_phase_pairings": dict(phases),
        "date_only_fixtures": len(events), "review_window_complete": False,
        "timezone_status": "unverified; literal publisher dates retained",
        "participant_age_coverage": "unverified",
        "professional_status_coverage": "not established by schedule",
        "coverage_note": "Partial published senior main-draw pairings only. Preliminary fixtures and completed results are excluded. Undrawn later rounds remain uncovered; zero review-window fixtures does not imply offseason or eligibility clearance.",
        **{key: holds[key] for key in (
            "published_unplayed_fixtures", "completed_fixtures_excluded",
            "preliminary_fixtures_excluded", "published_clocks_without_verified_timezone",
            "unresolved_pairings_held", "age_or_reserve_fixtures_held", "amateur_scope_held")},
    }
    return events, evidence


def fetch_fixtures(source, now, get=None):
    """Read the exact official endpoint, returning all current/future dates.

    America/Chicago is the application's review-day boundary, not an assertion
    about the publisher's clock. The collector applies its own seven-day window.
    """
    _scope(source)
    if not isinstance(now, datetime.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("HNS Croatian Cup requires an aware review timestamp")
    if get is None:
        import requests
        get = requests.get
    response = get(ENDPOINT, timeout=30)
    response.raise_for_status()
    if getattr(response, "url", ENDPOINT) != ENDPOINT:
        raise ValueError("HNS Croatian Cup official response URL changed")
    events, evidence = parse_fixtures(response.content, source)
    day = now.astimezone(CHICAGO).date().isoformat()
    upcoming = [event for event in events if event["start_time"] >= day]
    if not upcoming:
        raise ValueError("HNS Croatian Cup has no admissible current/future fixtures; stale publication is not offseason evidence")
    evidence["past_unresolved_fixtures_held"] = len(events) - len(upcoming)
    evidence["future_confirmed_fixtures"] = len(upcoming)
    evidence["date_only_fixtures"] = len(upcoming)
    return upcoming, evidence
