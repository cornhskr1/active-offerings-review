"""MOL Cup's named 2026/27 fixtures, without an inferred publisher timezone.

Use response.content: the page declares UTF-8 but HTTP has no charset, so
requests.text can incorrectly decode Czech names as ISO-8859-1. The caller must
filter date_only cards by the literal published date, not a midnight conversion.
This is a partial, published-pairing feed, never full-season or age clearance.
"""

import datetime
import re
from collections import Counter

from lxml import html


SOURCE_ID = "uefa-soccer-czech-republic-czech-cup-men"
ENDPOINT = "https://www.molcup.cz/vysledky"
SEASON = "2026/2027"
STAGES = {
    "1. předkolo": "PRELIMINARY 1", "Předkolo": "PRELIMINARY",
    "1.kolo": "ROUND 1", "2.kolo": "ROUND 2", "3.kolo": "ROUND 3",
    "Osmifinále": "ROUND OF 16", "Čtvrtfinále": "QUARTERFINALS",
    "Semifinále": "SEMIFINALS", "Finále": "FINAL",
}
WEEKDAYS = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")
PLACEHOLDER = re.compile(r"\b(?:tbc|tbd|unknown|neznámý|vítěz|los|winner)\b|[/]", re.I)
AGE_OR_RESERVE = re.compile(r"\b(?:u\s*-?\s*\d{2}|under\s*\d{2}|junioři|dorost|mládež|youth|reserves?)\b|(?:\s(?:B|II))$", re.I)
AMATEUR = re.compile(r"\b(?:amatér\w*|amateur\w*)\b", re.I)


def source_config():
    """Exact replacement for the existing approved Czech Cup source row."""
    return {
        "id": SOURCE_ID, "sport": "Soccer", "league": "Czech Cup | Men",
        "region": "Czech Republic", "source_type": "official-czech-cup-fixtures",
        "coverage_status": "partial", "endpoint": ENDPOINT,
        "official_schedule_url": ENDPOINT,
        "season_calendar_url": "https://www.molcup.cz/clanek/714-terminy-mol-cupu-2026-2027",
        "catalog_terms": ["Czech Cup | Men"],
        "source_note": "Official 2026/27 named unplayed pairings, retained as date-only because the publisher timezone is unverified. Partial published-phase coverage only; later or undrawn pairings remain uncovered. No fixtures in the review window is not offseason evidence, and schedule coverage does not clear participant ages or market eligibility.",
    }


def _class(name):
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def _text(node):
    return " ".join(node.text_content().split())


def _one(node, xpath, label):
    found = node.xpath(xpath)
    if len(found) != 1:
        raise ValueError(f"MOL Cup {label} missing or duplicated")
    return found[0]


def _club(row, right):
    side = _class("right") if right else f'not({_class("right")})'
    link = _one(row, f'./div[{_class("name")} and {side}]/div[{_class("shortcut")}]/a', "opponent")
    logo = _one(row, f'./div[{_class("logo")} and {side}]/a', "opponent logo")
    name = _text(link)
    identifier = re.fullmatch(r"/klub/([1-9]\d*)-[a-z0-9-]+", link.get("href", ""))
    image = _one(logo, './img', "opponent image")
    if (not name or not identifier or logo.get("href") != link.get("href")
            or image.get("alt") != name):
        raise ValueError("MOL Cup named opponent evidence changed")
    return name, identifier.group(1)


def _date(row):
    box = _one(row, f'.//div[{_class("info")}]/div[{_class("date")}]', "fixture date")
    long = _text(_one(box, f'./div[{_class("long")}]', "full-year date"))
    short = _text(_one(box, f'./div[{_class("short")}]', "short date"))
    if not re.fullmatch(r"\d{2}/\d{2}/20\d{2}", long):
        raise ValueError("MOL Cup fixture date has no explicit four-digit year")
    date = datetime.datetime.strptime(long, "%d/%m/%Y").date()
    if short != date.strftime("%d.%m.%y"):
        raise ValueError("MOL Cup published dates disagree")
    if not datetime.date(2026, 7, 1) <= date <= datetime.date(2027, 6, 30):
        raise ValueError("MOL Cup fixture edition changed")
    return date


def _printed_clock(row, date):
    box = row.xpath(f'.//div[{_class("info")}]/div[{_class("time")}]')
    if not box:
        return None
    if len(box) != 1:
        raise ValueError("MOL Cup kickoff field duplicated")
    long = _text(_one(box[0], f'./div[{_class("long")}]', "printed kickoff"))
    short = _text(_one(box[0], f'./div[{_class("short")}]', "short kickoff"))
    if not long and not short:
        return None
    match = re.fullmatch(r"([\wěščřžýáíéůúťďň]+) (\d{2}:\d{2}) hod\.", long)
    if not match or match.group(1) != WEEKDAYS[date.weekday()] or short != match.group(2):
        raise ValueError("MOL Cup published kickoff or weekday changed")
    datetime.time.fromisoformat(short)  # Validate the clock, but do not infer its zone.
    return long


def parse_fixtures(page, source):
    """Return every admissible unplayed card and honest coverage/hold evidence.

    Missing/malformed identity, phase, year, date, or contradictory representations
    fail closed. Explicit placeholder, youth/reserve, and amateur rows are counted
    as holds. Normal senior club names do not establish individual player ages or
    professional status: those reviews remain separate and explicitly incomplete.
    """
    if (source.get("id") != SOURCE_ID or source.get("sport") != "Soccer"
            or source.get("league") != "Czech Cup | Men"
            or source.get("region") != "Czech Republic"
            or source.get("catalog_terms") != ["Czech Cup | Men"]
            or source.get("endpoint") != ENDPOINT):
        raise ValueError("MOL Cup catalog scope or official endpoint changed")
    doc = html.fromstring(page.decode("utf-8") if isinstance(page, bytes) else page)
    if doc.xpath('string(//title)') != "Zápasy & výsledky | MOL Cup":
        raise ValueError("MOL Cup page identity changed")
    panel = _one(doc, f'//div[{_class("content")} and {_class("schedule")}]', "schedule panel")
    form = _one(panel, './form[@method="get" and @action="/vysledky"]', "filter form")
    season = _one(form, './/select[@id="id_season"]/option[@selected]', "selected season")
    if _text(season) != SEASON or season.get("value") != "34":
        raise ValueError("MOL Cup selected edition changed")
    stage = _one(form, './/select[@id="id_stage"]/option[@selected]', "stage filter")
    if stage.get("value") != "999" or _text(stage) != "--všechna kola--":
        raise ValueError("MOL Cup page is filtered to a phase")
    team = _one(form, './/select[@id="id_team"]', "team filter")
    selected_teams = team.xpath('./option[@selected]') or team.xpath('./option[1]')
    if len(selected_teams) != 1 or selected_teams[0].get("value") != "0":
        raise ValueError("MOL Cup page is filtered to a team")
    if [_text(x) for x in panel.xpath('./h2')] != ["Výsledky", "Rozpis zápasů"]:
        raise ValueError("MOL Cup completed/upcoming section identity changed")

    if len(panel.xpath(f'.//div[{_class("item")}]')) != len(panel.xpath(f'./div[{_class("item")}]')):
        raise ValueError("MOL Cup fixture row layout changed")

    events, seen, stages = [], set(), Counter()
    holds = Counter()
    completed, published, printed_clocks = 0, 0, 0
    section = None
    for row in panel:
        if row.tag == "h2":
            section = _text(row)
            continue
        if not (row.tag == "div" and "item" in (row.get("class") or "").split()):
            continue
        if section not in ("Výsledky", "Rozpis zápasů"):
            raise ValueError("MOL Cup fixture appears outside an identified section")
        phase = _text(_one(row, f'.//div[{_class("info")}]/div[{_class("stage")}]', "fixture phase"))
        if phase not in STAGES:
            raise ValueError("MOL Cup unrecognized fixture phase")
        if section == "Výsledky":
            score = _text(_one(row, f'.//div[{_class("info")}]/div[{_class("score")}]', "completed result"))
            if not re.fullmatch(r"\d+:\d+(?: \((?:\d+:\d+ PEN|prodloužení)\))?", score):
                raise ValueError("MOL Cup completed result changed")
            completed += 1
            continue
        published += 1
        if row.xpath(f'.//div[{_class("score")}]'):
            raise ValueError("MOL Cup upcoming fixture contains a completed result")
        home, home_id = _club(row, True)
        away, away_id = _club(row, False)
        if home == away or home_id == away_id:
            raise ValueError("MOL Cup identical opponents")
        identifier = f"mol-cup-2026-27-{STAGES[phase].lower().replace(' ', '-')}-{home_id}-{away_id}"
        # The pairing and phase, rather than mutable date or kickoff, identify it.
        duplicate_key = (phase, *sorted((home_id, away_id)))
        if duplicate_key in seen:
            raise ValueError("MOL Cup duplicate phase pairing")
        seen.add(duplicate_key)
        date = _date(row)
        clock = _printed_clock(row, date)
        printed_clocks += bool(clock)
        stages[phase] += 1
        if any(PLACEHOLDER.search(name) for name in (home, away)):
            holds["unresolved_pairings_held"] += 1
            continue
        if any(AGE_OR_RESERVE.search(name) for name in (home, away)):
            holds["age_or_reserve_fixtures_held"] += 1
            continue
        if any(AMATEUR.search(name) for name in (home, away)):
            holds["amateur_scope_held"] += 1
            continue
        events.append({
            "id": identifier, "source_id": SOURCE_ID, "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}", "start_time": date.isoformat(),
            "date_only": True, "status": "UPCOMING", "season_stage": STAGES[phase],
            "status_detail": "Official MOL Cup fixture date only; publisher timezone unverified. Participant ages and market eligibility require separate review.",
            "published_kickoff_text": clock,
            "participant_review_required": True,
            "location": None, "source_endpoint": ENDPOINT,
        })
    if not published:
        raise ValueError("MOL Cup has no published unplayed fixtures; absence is not offseason evidence")
    events.sort(key=lambda event: (event["start_time"], event["id"]))
    evidence = {
        "coverage_status": "partial", "published_edition": SEASON,
        "published_unplayed_fixtures": published,
        "completed_fixtures_excluded": completed,
        "published_phase_pairings": dict(stages),
        "date_only_fixtures": len(events),
        "published_clocks_without_verified_timezone": printed_clocks,
        "timezone_status": "unverified; literal publisher dates retained",
        "review_window_complete": False,
        "participant_age_coverage": "unverified",
        "professional_status_coverage": "not established by schedule",
        "coverage_note": "Partial published pairings only, not a full-season or complete-phase guarantee. Unpublished later pairings remain uncovered; zero cards in the review window does not imply offseason or eligibility clearance.",
        **{key: holds[key] for key in ("unresolved_pairings_held", "age_or_reserve_fixtures_held", "amateur_scope_held")},
    }
    return events, evidence
