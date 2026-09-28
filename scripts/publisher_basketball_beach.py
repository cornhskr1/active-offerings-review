"""Exact NBB fixture and gender-specific Beach Pro Tour calendar parsing."""

import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from lxml import html


BRAZIL = ZoneInfo("America/Sao_Paulo")
BEACH_BASE = "https://en.volleyballworld.com"


def parse_nbb_fixtures(page, source):
    if source.get("catalog_terms") != ["Novo Basquete Brasil (NBB) | Men"]:
        raise ValueError("NBB catalog scope changed")
    document = html.fromstring(page)
    if "Tabela de Jogos" not in " ".join(document.xpath("//title/text()")):
        raise ValueError("NBB schedule page changed")
    rows = document.xpath('//tr[td[contains(concat(" ",normalize-space(@class)," ")," position_value ")]]')
    if not rows:
        raise ValueError("NBB schedule has no match rows")
    events = []
    seen_numbers, seen_ids = set(), set()
    for row in rows:
        def field(name):
            values = row.xpath(f'./td[@data-label="{name}"]')
            return values[0] if values else None

        edition = field("CAMPEONATO")
        if edition is None or " ".join(edition.itertext()).strip() != "2026/2027":
            continue
        number_cell = field("JOGO")
        date_cell = field("DATA")
        home_cell, away_cell = field("CASA"), field("VISITANTE")
        if any(cell is None for cell in (number_cell, date_cell, home_cell, away_cell)):
            raise ValueError("NBB fixture fields changed")
        number = "".join(number_cell.itertext()).strip()
        publisher_id = number_cell.get("data-real-id") or ""
        stamps = [" ".join(x.itertext()).strip() for x in date_cell.xpath("./span")]
        home, away = " ".join(home_cell.itertext()).strip(), " ".join(away_cell.itertext()).strip()
        links = row.xpath('.//a[contains(@href,"/partidas/nbb-2026-2027-")]/@href')
        if (not number.isdigit() or not publisher_id.isdigit() or len(stamps) < 2
                or not home or not away or home == away or len(set(links)) != 1):
            raise ValueError("NBB fixture identity or pairing changed")
        url = links[0]
        if urlparse(url).hostname != "lnb.com.br":
            raise ValueError("NBB fixture link left the publisher")
        try:
            local = datetime.datetime.strptime(" ".join(stamps[:2]), "%d/%m/%Y %H:%M").replace(tzinfo=BRAZIL)
        except ValueError as exc:
            raise ValueError("NBB kickoff changed") from exc
        if local.year not in (2026, 2027) or number in seen_numbers or publisher_id in seen_ids:
            raise ValueError("NBB fixture edition or ID changed")
        seen_numbers.add(number)
        seen_ids.add(publisher_id)
        events.append({
            "id": f"nbb-2026-27-{publisher_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "NBB official 2026/27 fixture",
            "season_stage": "REGULAR", "location": None, "source_endpoint": url,
        })
    if len(events) < 20 or len({event["name"] for event in events}) < 10:
        raise ValueError("NBB 2026/27 fixture list is incomplete")
    return events


def parse_beach_calendar(payload, source, year, month):
    gender = source.get("beach_gender")
    if gender not in ("men", "women") or source.get("catalog_terms") != [f"Beach Pro Tour | {gender.title()}"]:
        raise ValueError("Beach Pro Tour gender scope changed")
    if not isinstance(payload, dict) or not isinstance(payload.get("competitions"), list):
        raise ValueError("Beach Pro Tour calendar response changed")
    events = []
    for item in payload["competitions"]:
        if item.get("season") != str(year) or item.get("discipline") != "beach":
            raise ValueError("Beach Pro Tour calendar edition changed")
        tournament_id = item.get(f"{gender}Tournaments")
        if not tournament_id:
            continue
        if not str(tournament_id).isdigit():
            raise ValueError("Beach Pro Tour tournament ID changed")
        start = datetime.datetime.fromisoformat(item["startDate"].replace("Z", "+00:00")).date()
        end = datetime.datetime.fromisoformat(item["endDate"].replace("Z", "+00:00")).date()
        url = urljoin(BEACH_BASE, item["url"])
        if (start.year != year or start.month != month or end < start or (end-start).days > 14
                or urlparse(url).hostname != "en.volleyballworld.com"
                or f"/beach-pro-tour/{year}/" not in url):
            raise ValueError("Beach Pro Tour tournament window changed")
        events.append({"id": str(tournament_id), "name": item["competitionFullName"],
                       "start": start, "end": end, "url": url,
                       "location": item.get("destination") or ""})
    if len({event["id"] for event in events}) != len(events):
        raise ValueError("Duplicate Beach Pro Tour tournament ID")
    return events
