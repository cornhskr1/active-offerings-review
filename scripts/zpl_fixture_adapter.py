"""Official ZPL Transitional 2026 senior men's stream calendars, fail closed.

Both ten-club streams map to the one approved Zambia Super League identity.
The official directory controls membership; all twenty unauthenticated team
calendars are required. A fixture must agree in both clubs' calendars. No cup,
women's, reserve, historic unsplit league, or National League event is mapped.
"""

import datetime
import json
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html

SOURCE_ID = "caf-soccer-zambia-zambia-super-league-men"
LEAGUE = "Zambia Super League | Men"
SEASON = "Transitional 2026"
STREAMS = ("Men - Stream A - MTN Super League", "Men - Stream B - MTN Super League")
HOME = "https://zpl.co.zm/"
CALENDAR_BASE = "https://zpl.co.zm/api/v1/calendar/team.php?id="
LUSAKA = ZoneInfo("Africa/Lusaka")


def source_config():
    return {"id": SOURCE_ID, "sport": "Soccer", "league": LEAGUE, "region": "Zambia",
            "source_type": "official-zpl-transitional-calendars", "coverage_status": "partial",
            "endpoint": HOME, "official_schedule_url": HOME,
            "catalog_terms": [LEAGUE],
            "source_note": "Official Transitional 2026 men's MTN Super League Streams A and B. All twenty club calendars are inventoried, competition-scoped and reconciled by official fixture ID. UTC kickoff timestamps are publisher supplied; no cup, women, reserve or National League fixtures. Partial current published calendar coverage, not proof of later fixtures or offseason."}


def _text(node):
    return " ".join(node.text_content().split())


def _source(source):
    if any(source.get(k) != v for k, v in {"id": SOURCE_ID, "sport": "Soccer", "league": LEAGUE,
                                           "region": "Zambia", "catalog_terms": [LEAGUE],
                                           "coverage_status": "partial"}.items()):
        raise ValueError("ZPL catalog identity changed")
    if source.get("endpoint") != HOME:
        raise ValueError("ZPL official directory endpoint changed")


def team_calendar_requests(page, source):
    """Return the complete, exact senior team inventory and public feed URLs."""
    _source(source)
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    if doc.xpath('//title/text()') != ["Zambian Premier League | Official Website"]:
        raise ValueError("ZPL official publisher changed")
    for stream in STREAMS:
        nodes = [n for n in doc.xpath('//h3') if _text(n) == stream]
        if len(nodes) != 1 or [_text(n) for n in nodes[0].getparent().xpath('./small')] != [SEASON]:
            raise ValueError("ZPL senior stream or Transitional 2026 edition changed")
    matches = re.findall(r'const teams=(\[.*?\]),search=', page, re.S)
    if len(matches) != 1 or f'base="{CALENDAR_BASE}"' not in page:
        raise ValueError("ZPL public calendar directory missing")
    teams = json.loads(matches[0])
    if not isinstance(teams, list):
        raise ValueError("ZPL team inventory malformed")
    result = []
    for team in teams:
        if not isinstance(team, dict) or not isinstance(team.get("competition"), str):
            raise ValueError("ZPL team competition missing")
        memberships = set(team["competition"].split(", ")).intersection(STREAMS)
        if not memberships:
            continue
        ident, name = team.get("id"), team.get("name")
        if (len(memberships) != 1 or type(ident) is not int or ident <= 0
                or not isinstance(name, str) or not name.strip()
                or re.search(r'\b(?:TBD|TBC|winner|reserve|women|queens|ladies|U\d{2})\b', name, re.I)):
            raise ValueError("ZPL senior team identity malformed")
        result.append({"id": ident, "name": name, "competition": next(iter(memberships)),
                       "endpoint": CALENDAR_BASE + str(ident)})
    if (len(result) != 20 or len({r["id"] for r in result}) != 20
            or len({r["name"] for r in result}) != 20
            or Counter(r["competition"] for r in result) != Counter({s: 10 for s in STREAMS})):
        raise ValueError("ZPL complete two-stream twenty-team inventory changed")
    return sorted(result, key=lambda x: x["id"])


def _ics_text(value):
    return re.sub(r'\\([nN,;\\])', lambda m: "\n" if m[1].lower() == "n" else m[1], value)


def _calendar_fields(body):
    if isinstance(body, bytes):
        body = body.decode("utf-8-sig")
    lines = re.sub(r'\r?\n[ \t]', '', body).splitlines()
    stack, header, records, record = [], {}, [], None
    for line in lines:
        if not line:
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError("ZPL malformed iCalendar line")
        if key == "BEGIN":
            if (not stack and value != "VCALENDAR") or (stack and value not in ("VEVENT", "VALARM")):
                raise ValueError("ZPL invalid calendar component")
            if value == "VEVENT":
                if stack != ["VCALENDAR"]:
                    raise ValueError("ZPL nested fixture")
                record = {}
            if value == "VALARM" and stack != ["VCALENDAR", "VEVENT"]:
                raise ValueError("ZPL invalid alarm nesting")
            stack.append(value)
        elif key == "END":
            if not stack or stack.pop() != value:
                raise ValueError("ZPL truncated calendar component")
            if value == "VEVENT":
                records.append(record)
                record = None
        elif stack in (["VCALENDAR"], ["VCALENDAR", "VEVENT"]):
            target = header if len(stack) == 1 else record
            if key in target:
                raise ValueError("ZPL duplicate calendar field")
            target[key] = _ics_text(value)
        elif stack != ["VCALENDAR", "VEVENT", "VALARM"]:
            raise ValueError("ZPL calendar content outside component")
    if stack or not records or header.get("VERSION") != "2.0":
        raise ValueError("ZPL empty or incomplete calendar")
    return header, records


def parse_zpl_calendars(page, calendars, source, now, *, include_evidence=False):
    """Return future confirmed timed events, requiring both teams' copies.

    Do not filter to the dashboard window here: a healthy empty review window
    differs from an empty future publication. The latter raises explicitly.
    """
    teams = team_calendar_requests(page, source)
    if now.tzinfo is None:
        raise ValueError("ZPL now must be timezone-aware")
    by_name = {t["name"]: t for t in teams}
    if not isinstance(calendars, dict) or set(calendars) != {t["id"] for t in teams}:
        raise ValueError("ZPL all twenty team calendars are required")
    fixtures, copies = {}, Counter()
    excluded_records = 0
    for team in teams:
        header, records = _calendar_fields(calendars[team["id"]])
        if (header.get("PRODID") != "-//ZPL//Smart Football Calendar//EN"
                or header.get("X-WR-CALNAME") != team["name"] + " - ZPL Fixtures"
                or header.get("X-WR-TIMEZONE") != "Africa/Lusaka"):
            raise ValueError("ZPL team calendar or explicit timezone changed")
        seen = set()
        scoped = 0
        for record in records:
            desc = record.get("DESCRIPTION", "")
            competition = desc.split(" | ")[0]
            if competition not in STREAMS:
                excluded_records += 1
                continue
            scoped += 1
            if competition != team["competition"]:
                raise ValueError("ZPL calendar mixed senior streams")
            matchweek = re.fullmatch(re.escape(competition) + r' \| Matchweek ([1-9]|1[0-8])(?: \| Result: \d+-\d+(?: \| https://zpl\.co\.zm/fixture/\d+)?)?', desc)
            uid = re.fullmatch(r'fixture-(\d+)@zpl\.co\.zm', record.get("UID", ""))
            names = record.get("SUMMARY", "").split(" vs ")
            clock = record.get("DTSTART", "")
            if (not matchweek or not uid or len(names) != 2 or names[0] == names[1]
                    or team["name"] not in names or any(n not in by_name for n in names)
                    or any(by_name[n]["competition"] != competition for n in names)
                    or not re.fullmatch(r'\d{8}T\d{6}Z', clock)):
                raise ValueError("ZPL competition, pairing, year or UTC kickoff malformed")
            match_id = uid[1]
            if match_id in seen or record.get("URL") != f"https://zpl.co.zm/fixture/{match_id}":
                raise ValueError("ZPL duplicate fixture or fixture link changed")
            seen.add(match_id)
            start = datetime.datetime.strptime(clock, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
            if start.astimezone(LUSAKA).year not in (2026, 2027):
                raise ValueError("ZPL fixture outside Transitional 2026 calendar years")
            status = record.get("STATUS")
            if status not in ("CONFIRMED", "CANCELLED", "TENTATIVE"):
                raise ValueError("ZPL fixture status unknown")
            venue = record.get("LOCATION", "").strip()
            if not venue:
                raise ValueError("ZPL fixture venue missing")
            signature = (competition, matchweek[1], tuple(names), clock, status, venue, " | Result: " in desc)
            if match_id in fixtures and fixtures[match_id] != signature:
                raise ValueError("ZPL team calendars disagree on fixture")
            fixtures[match_id] = signature
            copies[match_id] += 1
        if not scoped:
            raise ValueError("ZPL calendar has no exact senior stream fixtures")
    if any(n != 2 for n in copies.values()):
        raise ValueError("ZPL fixture missing the other team's calendar copy")
    result = []
    counts = Counter()
    for match_id, (competition, week, names, clock, status, venue, completed) in fixtures.items():
        start = datetime.datetime.strptime(clock, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
        if completed:
            counts["completed_results"] += 1
            continue
        if status != "CONFIRMED":
            counts["cancelled_fixtures" if status == "CANCELLED" else "tentative_fixtures_held"] += 1
            continue
        if start <= now:
            counts["past_unresolved_fixtures_held"] += 1
            continue
        result.append({"id": f"zpl-{match_id}", "source_id": SOURCE_ID, "sport": source["sport"],
                       "league": LEAGUE, "region": "Zambia", "name": f"{names[1]} at {names[0]}",
                       "start_time": start.isoformat().replace("+00:00", "Z"), "status": "UPCOMING",
                       "status_detail": f"Official {SEASON}, {competition}, matchweek {week}",
                       "season_stage": "REGULAR", "location": venue,
                       "source_endpoint": f"https://zpl.co.zm/fixture/{match_id}"})
    if not result:
        raise ValueError("ZPL no future confirmed timed fixtures published; not evidence of offseason")
    result.sort(key=lambda e: (e["start_time"], e["id"]))
    evidence = {"season": SEASON, "competitions": list(STREAMS),
                "team_calendars_checked": len(teams), "published_fixtures": len(fixtures),
                "reconciled_calendar_copies": sum(copies.values()),
                "excluded_other_competition_copies": excluded_records,
                "future_confirmed_fixtures": len(result),
                "completed_results": counts["completed_results"],
                "past_unresolved_fixtures_held": counts["past_unresolved_fixtures_held"],
                "cancelled_fixtures": counts["cancelled_fixtures"],
                "tentative_fixtures_held": counts["tentative_fixtures_held"],
                "published_future_start": result[0]["start_time"],
                "published_future_end": result[-1]["start_time"],
                "coverage_status": "partial"}
    return (result, evidence) if include_evidence else result


def fetch_zambia_fixtures(source, now, get=None):
    """Fetch official public HTML + every inventoried team ICS, once each.

    Returns all future events and evidence; caller applies its review timezone
    and window. HTTP errors propagate immediately, without alternate routes.
    """
    _source(source)
    if get is None:
        import requests
        get = requests.get
    response = get(source["endpoint"], timeout=30)
    response.raise_for_status()
    page = response.content
    teams = team_calendar_requests(page, source)
    calendars = {}
    for team in teams:
        response = get(team["endpoint"], timeout=30)
        response.raise_for_status()
        calendars[team["id"]] = response.content
    return parse_zpl_calendars(page, calendars, source, now, include_evidence=True)
