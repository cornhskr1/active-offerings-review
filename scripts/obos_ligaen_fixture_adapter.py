"""Official OBOS-ligaen 2026 senior men's next upcoming round."""

import datetime
import hashlib
import re
from collections import defaultdict
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-norway-obos-ligaen-men"
OSLO = ZoneInfo("Europe/Oslo")


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def next_round(page, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("OBOS catalog scope changed")
    doc = html.fromstring(page)
    if _text(doc, '//title/text()') != "Terminliste / OBOS-ligaen":
        raise ValueError("OBOS senior competition changed")
    nodes = doc.xpath('//tr[contains(concat(" ",normalize-space(@class)," ")," schedule__match ")]')
    if not nodes:
        raise ValueError("OBOS fixture table missing")
    by_pair = {}
    for node in nodes:
        classes = node.get("class", "").split()
        featured = "schedule__match--upcoming" in classes
        if not featured and "future__match__terminlist" not in classes:
            continue
        team_cell = node.xpath('./td[contains(@class,"schedule__match__item--teams")]')
        date_cell = node.xpath('./td[contains(@class,"schedule__match__item--date")]')
        league_alt = node.xpath('./td[contains(@class,"schedule__match__item--league")]//img/@alt')
        if len(team_cell) != 1 or len(date_cell) != 1 or league_alt != ["OBOS-ligaen"]:
            raise ValueError("OBOS senior fixture columns changed")
        away = _text(team_cell[0], './span[contains(@class,"schedule__team--opponent")]/text()')
        home_text = _text(team_cell[0], './text()')
        home_match = re.fullmatch(r"(.+?) -", home_text)
        names = [home_match.group(1), away] if home_match else []
        date_node = date_cell[0].xpath('./span[1]')
        date_text = "".join(date_node[0].itertext()).strip() if date_node else ""
        m = re.fullmatch(r"(\d{2})\.(\d{2})\.(2026)", date_text)
        clock = _text(date_cell[0], './span[contains(@class,"schedule__time")]/text()')
        rounds = [_text(date_cell[0], './span[contains(@class,"schedule__match__item--match-round-number")]/text()')]
        if featured:
            rounds = [_text(date_cell[0], './span[not(@class)][last()]/text()')]
            venue = _text(node, './td[contains(@class,"schedule__match__item--venue")]/text()')
        else:
            rounds.append(_text(node, './td[contains(@class,"schedule__match__item--round")]/span/text()'))
            venue = " ".join(" ".join(date_cell[0].xpath('./text()')).split())
        rounds = [value for value in rounds if value]
        if (len(names) != 2 or not all(names) or names[0] == names[1] or not m
                or not re.fullmatch(r"\d{2}:\d{2}", clock) or not venue
                or not rounds or len(set(rounds)) != 1
                or not re.fullmatch(r"#(?:[1-9]|[12]\d|30)", rounds[0])):
            raise ValueError("OBOS date, round, pairing or venue changed")
        day = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        number = int(rounds[0][1:])
        pair = (number, names[0], names[1])
        row = (day, number, clock, venue, names)
        if pair in by_pair and by_pair[pair] != row:
            raise ValueError("OBOS duplicate pairing conflicts")
        by_pair[pair] = row
    future = [row for row in by_pair.values() if row[0] >= today]
    if not future:
        return [], len(by_pair), 0
    number = min(row[1] for row in future)
    chosen = [row for row in future if row[1] == number]
    if not 1 <= len(chosen) <= 8 or len({name for row in chosen for name in row[4]}) != 2 * len(chosen):
        raise ValueError("OBOS next senior round pairing structure changed")
    events = []
    for day, number, clock, venue, names in chosen:
        start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), OSLO)
        match_key = f"{number}:{names[0]}:{names[1]}".encode("utf-8")
        match_id = hashlib.sha256(match_key).hexdigest()[:16]
        events.append({"id": f"obos-{match_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026 OBOS-ligaen round {number}",
            "season_stage": "REGULAR", "location": venue,
            "source_endpoint": source["official_schedule_url"]})
    return events, len(by_pair), len(future) - len(chosen)
