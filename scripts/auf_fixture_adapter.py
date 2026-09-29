"""AUF's separate 2026 women's A league and men's cup fixture pages."""

import datetime
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html


URUGUAY = ZoneInfo("America/Montevideo")
SOURCES = {
    "conmebol-soccer-uruguay-campeonato-femenino-women": {
        "title": "Campeonato Femenino A - AUF",
        "league": "Campeonato Femenino | Women",
        "headings": [
            "FIXTURE Primera Fase - CAMPEONATO APERTURA LPD 2026",
            "FIXTURE Primera Fase - CAMPEONATO CLAUSURA LPD 2026",
        ],
        "rows": [45, 45],
    },
    "conmebol-soccer-uruguay-copa-uruguay-men": {
        "title": "Copa AUF Uruguay - AUF",
        "league": "Copa Uruguay | Men",
        "headings": [*(f"FIXTURE Primera Fase - GRUPO {n}" for n in range(1, 7)),
                     "Primera Fase - AMATEUR AUF"],
        "rows": [6] * 6 + [4],
    },
}


def _class(name):
    return f'contains(concat(" ",normalize-space(@class)," ")," {name} ")'


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def parse_fixtures(page, source):
    scope = SOURCES.get(source.get("id"))
    if not scope or source.get("league") != scope["league"] or source.get("catalog_terms") != [scope["league"]]:
        raise ValueError("AUF competition approval scope changed")
    # AUF declares Windows-1252 in its page; the HTTP charset says ISO-8859-1.
    doc = html.fromstring(page.decode("windows-1252") if isinstance(page, bytes) else page)
    if doc.xpath('//title/text()') != [scope["title"]]:
        raise ValueError("AUF competition page identity changed")
    blocks = doc.xpath(f'//*[{_class("cont-fixture_campeonato")}]')
    if [_text(block, './h3/text()') for block in blocks] != scope["headings"]:
        raise ValueError("AUF competition phases changed")
    fixture_keys = set()
    appearances = Counter()
    pairings = Counter()
    events = []
    amateur_held = 0
    for index, block in enumerate(blocks):
        rows = block.xpath(f'.//*[{_class("item-fixture")}]')
        if len(rows) != scope["rows"][index]:
            raise ValueError("AUF phase fixture count changed")
        group_clubs = set()
        for row in rows:
            home_nodes = row.xpath(f'./div[{_class("col")} and not({_class("club2")})][1]/a')
            away_nodes = row.xpath(f'./div[{_class("club2")}]/a')
            if len(home_nodes) != 1 or len(away_nodes) != 1:
                raise ValueError("AUF fixture pairing fields changed")
            home = _text(home_nodes[0], f'.//span[{_class("hidden-xs")}]/text()')
            away = _text(away_nodes[0], f'.//span[{_class("hidden-xs")}]/text()')
            if (not home or not away or home == away
                    or not home_nodes[0].get("href", "").startswith("/")
                    or not away_nodes[0].get("href", "").startswith("/")):
                raise ValueError("AUF fixture clubs changed")
            stamps = row.xpath(f'.//div[{_class("fecha_estadio")}]/strong/text()')
            if len(stamps) != 1:
                raise ValueError("AUF fixture kickoff missing")
            stamp = " ".join(stamps[0].split())
            if not re.fullmatch(r"\d{2}/\d{2}/2026 - \d{2}:\d{2} h", stamp):
                raise ValueError("AUF fixture kickoff format changed")
            local = datetime.datetime.strptime(stamp, "%d/%m/%Y - %H:%M h").replace(tzinfo=URUGUAY)
            venue = _text(row, f'.//div[{_class("fecha_estadio")}]/text()')
            if not venue:
                raise ValueError("AUF fixture venue missing")
            score = _text(row, f'./div[{_class("resultado")}]/text()')
            if score and not re.fullmatch(r"(?:\(\d+\) )?\d+ - \d+(?: \(\d+\))?", score):
                raise ValueError("AUF fixture result changed")
            key = (index, local.date(), home, away)
            if key in fixture_keys:
                raise ValueError("AUF duplicate fixture")
            fixture_keys.add(key)
            group_clubs.update((home, away))
            if index == 6 and source["id"].endswith("copa-uruguay-men"):
                amateur_held += 1
                continue
            appearances.update((home, away))
            pairings[tuple(sorted((home, away)))] += 1
            if score:
                continue
            start = local.astimezone(datetime.timezone.utc)
            slug = lambda value: re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
            events.append({
                "id": f"auf-{slug(source['id'])}-{index}-{local:%Y%m%d}-{slug(home)}-{slug(away)}",
                "source_id": source["id"], "sport": "Soccer", "league": source["league"],
                "region": "Uruguay", "name": f"{away} at {home}",
                "start_time": start.isoformat(timespec="minutes").replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "AUF official fixture",
                "location": venue, "source_endpoint": source["endpoint"],
            })
        if source["id"].endswith("copa-uruguay-men") and index < 6 and len(group_clubs) != 4:
            raise ValueError("AUF cup group scope changed")
        if source["id"].endswith("campeonato-femenino-women") and len(group_clubs) != 10:
            raise ValueError("AUF women's A division scope changed")
    if source["id"].endswith("campeonato-femenino-women"):
        if (len(fixture_keys) != 90 or len(appearances) != 10 or len(pairings) != 45
                or any(n != 18 for n in appearances.values())
                or any(n != 2 for n in pairings.values())):
            raise ValueError("AUF women's A season pairings changed")
    elif (len(fixture_keys) != 40 or len(appearances) != 24 or amateur_held != 4
          or any(n != 3 for n in appearances.values())):
        raise ValueError("AUF cup first phase pairings changed")
    return events, len(fixture_keys), amateur_held
