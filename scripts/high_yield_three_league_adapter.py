"""Partial team schedules from the Egyptian Pro League and SAFF publishers."""

import datetime
import json
import re
from zoneinfo import ZoneInfo

from lxml import html


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _scope(source, source_id, league):
    if source.get("id") != source_id or source.get("league") != league or source.get("catalog_terms") != [league]:
        raise ValueError("Publisher catalog scope changed")


def _event(source, fixture_id, start, home, away, detail, stage, venue=None):
    if not home or not away or home == away:
        raise ValueError("Publisher pairing is missing or ambiguous")
    return {
        "id": fixture_id, "source_id": source["id"], "sport": source["sport"],
        "league": source["league"], "region": source["region"],
        "name": f"{away} at {home}",
        "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": detail, "season_stage": stage,
        "location": venue, "source_endpoint": source["endpoint"],
    }


def parse_egypt_fixture(page, source):
    _scope(source, "caf-soccer-egypt-egyptian-premier-league-men", "Egyptian Premier League | Men")
    doc = html.fromstring(page)
    states = doc.xpath('//script[@id="ng-state" and @type="application/json"]/text()')
    if len(states) != 1:
        raise ValueError("Egypt publisher structured fixture data missing")
    state = json.loads(states[0])
    bodies = [v["body"] for v in state.values() if isinstance(v, dict) and isinstance(v.get("body"), list)]
    if len(bodies) != 1:
        raise ValueError("Egypt publisher fixture list is ambiguous")
    events, seen = [], set()
    for row in bodies[0]:
        if row.get("championshipId") != 1667 or row.get("championshipName") != "الدوري المصري":
            continue
        if row.get("homeScore") is not None or row.get("awayScore") is not None or row.get("isDelayed"):
            continue
        status = row.get("currentMatchStatus") or {}
        if status.get("matchStatusName") == "انتهت":
            continue
        stamp = row.get("date", "")
        start = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("Egypt publisher kickoff lacks explicit timezone")
        fixture_id = row.get("id")
        if not isinstance(fixture_id, int) or fixture_id in seen:
            raise ValueError("Egypt publisher fixture identifier missing or duplicated")
        seen.add(fixture_id)
        events.append(_event(source, f"egypt-premier-{fixture_id}", start,
            _norm(row.get("homeTeamName")), _norm(row.get("awayTeamName")),
            "Egyptian Pro League structured team fixture (partial coverage)",
            f"ROUND {row.get('week')}", row.get("stadiumName")))
    if not events:
        raise ValueError("Egypt publisher contained no upcoming league fixtures")
    return events


def parse_saudi_fixture(page, source):
    _scope(source, "soccer-afc-saudi-arabia-first-division-league-men", "First Division League | Men")
    doc = html.fromstring(page)
    events, seen = [], set()
    for clock_cell in doc.xpath('//td[starts-with(@id,"fixture_td_1_")]'):
        row = clock_cell.getparent()
        table = row.getparent()
        while table is not None and table.tag != "table":
            table = table.getparent()
        if table is None:
            raise ValueError("SAFF fixture table missing")
        previous = list(table.itersiblings(preceding=True))
        if len(previous) < 2:
            raise ValueError("SAFF fixture date or competition missing")
        competition, date_table = previous[:2]
        links = competition.xpath('.//a[@href="championship.php?id=416"]')
        if len(links) != 1 or _norm(links[0].text_content()) != "First Division League":
            continue
        dates = date_table.xpath('.//a[contains(@href,"calendar_date=")]/@href')
        if len(dates) != 1:
            raise ValueError("SAFF fixture date is ambiguous")
        day = datetime.date.fromisoformat(dates[0].split("calendar_date=")[-1])
        clock = _norm(clock_cell.text_content())
        if not re.fullmatch(r"\d{2}:\d{2}", clock):
            raise ValueError("SAFF fixture kickoff missing")
        cells = row.xpath('./td')
        if len(cells) != 5:
            raise ValueError("SAFF fixture pairing layout changed")
        home, away = (_norm(cells[i].text_content()) for i in (1, 3))
        fixture_id = clock_cell.get("id").removeprefix("fixture_td_1_")
        if fixture_id in seen:
            raise ValueError("SAFF fixture identifier duplicated")
        seen.add(fixture_id)
        start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), ZoneInfo("Asia/Riyadh"))
        events.append(_event(source, f"saudi-first-division-{fixture_id}", start, home, away,
            "SAFF published team fixture (partial coverage)", "REGULAR", _norm(cells[4].text_content())))
    if not events:
        raise ValueError("SAFF page contained no timed First Division fixtures")
    return events
