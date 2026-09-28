"""Scoped senior league fixtures from Czech LFA and Croatian HNL pages."""

import datetime
import re
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from lxml import html


PRAGUE = ZoneInfo("Europe/Prague")
ZAGREB = ZoneInfo("Europe/Zagreb")
SOURCES = {
    "uefa-soccer-czech-republic-czech-first-league-men": "chance",
    "uefa-soccer-czech-republic-czech-national-football-league-men": "national",
    "uefa-soccer-croatia-croatian-football-league-supersport-hnl-men": "hnl",
}


def _event(source, identifier, home, away, date, clock, zone, link, round_number):
    if not home or not away or home == away or not re.fullmatch(r"\d{1,2}:\d{2}", clock):
        raise ValueError("League pairing or kickoff changed")
    local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), zone)
    return {
        "id": f"central-europe-{identifier}", "source_id": source["id"],
        "sport": source["sport"], "league": source["league"], "region": source["region"],
        "name": f"{away} at {home}",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": f"Official senior league round {round_number}",
        "season_stage": "REGULAR", "location": None, "source_endpoint": link,
    }


def parse_fixtures(page, source):
    """Return timed candidates, untimed/reserve holds, and verified page row count."""
    kind = SOURCES[source["id"]]
    if source.get("catalog_terms") != [source["league"]]:
        raise ValueError("League catalog scope changed")
    doc = html.fromstring(page)
    if kind == "chance":
        if "Chance Liga" not in doc.xpath("string(//title)"):
            raise ValueError("Chance Liga page identity changed")
        rows = doc.xpath('//ul[contains(@class,"scoreboard-horizontal")]/li')
        if len(rows) != 16:
            raise ValueError("Chance Liga scoreboard round size changed")
        events, held, seen = [], 0, set()
        for row in rows:
            links = row.xpath('.//span[contains(@class,"score-container")]//span[contains(@class,"score")]/b/a[contains(@href,"/zapas/")]')
            if len(links) != 1:
                raise ValueError("Chance Liga match link changed")
            match = re.fullmatch(r"/zapas/(\d+)-[a-z0-9-]+", links[0].get("href", ""))
            if not match or match.group(1) in seen:
                raise ValueError("Chance Liga match identity changed")
            seen.add(match.group(1))
            if not row.xpath('.//b[contains(@class,"time")]'):
                continue
            date_text = row.xpath('string(.//span[contains(@class,"info-container")]/span[contains(@class,"date")])')
            round_match = re.search(r"#(\d+)", date_text)
            date_match = re.search(r"\b(\d{2}/\d{2}/\d{2})\b", date_text)
            teams = row.xpath('.//span[contains(@class,"game-container")]/span[contains(@class,"team")]//img/@alt')
            kickoff = re.search(r"\b(\d{1,2}:\d{2})\b", " ".join(links[0].itertext()))
            if not round_match or not date_match or len(teams) != 2 or not kickoff:
                raise ValueError("Chance Liga published fixture changed")
            date = datetime.datetime.strptime(date_match.group(1), "%d/%m/%y").date()
            if not datetime.date(2026, 7, 1) <= date <= datetime.date(2027, 6, 30):
                raise ValueError("Chance Liga edition changed")
            events.append(_event(source, f"chance-{match.group(1)}", *teams, date,
                kickoff.group(1), PRAGUE, urljoin(source["endpoint"], links[0].get("href")), round_match.group(1)))
        if len(events) != 8:
            raise ValueError("Chance Liga next round is incomplete")
        return events, held, len(rows)
    if kind == "national":
        if "Chance Národní Liga" not in doc.xpath("string(//title)"):
            raise ValueError("National league page identity changed")
        rows = doc.xpath('//tr[td[contains(@class,"schedule_table__date")]]')
        if len(rows) != 8:
            raise ValueError("National league round size changed")
        events, held, seen = [], 0, set()
        for row in rows:
            date_text = row.xpath('string(./td[contains(@class,"schedule_table__date")]/span[contains(@class,"--full")])')
            date_match = re.search(r"(\d{2}\.\d{2}\.20\d{2})", date_text)
            clock = re.search(r"\b(\d{1,2}:\d{2})\b", date_text)
            teams = [" ".join(row.xpath(f'./td[contains(@class,"schedule_table__team--{side}")]//span[contains(@class,"__name")]//text()')).strip()
                     for side in ("home", "away")]
            links = row.xpath('./td[contains(@class,"schedule_table__score")]//a[contains(@href,"/zapas/")]/@href')
            match = re.fullmatch(r"/zapas/(\d+)-[a-z0-9-]+", links[0]) if len(links) == 1 else None
            if not date_match or not match or match.group(1) in seen or not all(teams):
                raise ValueError("National league fixture identity changed")
            seen.add(match.group(1))
            date = datetime.datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
            if not datetime.date(2026, 7, 1) <= date <= datetime.date(2027, 6, 30):
                raise ValueError("National league edition changed")
            # B teams may have underage participants; keep their match cards out of automated review.
            if any(re.search(r"(?:\sB|\sII)$", team) for team in teams):
                held += 1
                continue
            if not clock:
                held += 1
                continue
            events.append(_event(source, f"national-{match.group(1)}", *teams, date,
                clock.group(1), PRAGUE, urljoin(source["endpoint"], links[0]), "current"))
        return events, held, len(rows)
    if "SuperSport HNL" not in doc.xpath("string(//title)"):
        raise ValueError("HNL page identity changed")
    rows = doc.xpath('//table[contains(@class,"raspored")]/tr[td]')
    if len(rows) != 180:
        raise ValueError("HNL 36-round fixture count changed")
    events, held, seen, round_number = [], 0, set(), 0
    for row in doc.xpath('//table[contains(@class,"raspored")]/tr'):
        if row.xpath("./th"):
            marker = re.search(r"\b(\d+)\. kolo", " ".join(row.itertext()))
            if not marker or int(marker.group(1)) != round_number + 1:
                raise ValueError("HNL round sequence changed")
            round_number += 1
            continue
        if not row.xpath("./td"):
            continue
        cells = row.xpath("./td")
        stamp = cells[0].text or ""
        match = re.fullmatch(r"(\d{2}\.\d{2}\.20\d{2})\.(?: (\d{2}:\d{2}))?", stamp.strip())
        home, away = (" ".join(cells[i].itertext()).strip() for i in (1, 5))
        league = row.xpath('string(./td[1]/div[contains(@class,"natjecanje")])').strip()
        if not match or league != "SuperSport HNL" or not home or not away or home == away:
            raise ValueError("HNL senior fixture structure changed")
        date = datetime.datetime.strptime(match.group(1), "%d.%m.%Y").date()
        if not datetime.date(2026, 7, 1) <= date <= datetime.date(2027, 6, 30):
            raise ValueError("HNL edition changed")
        key = (round_number, date, home, away)
        if key in seen:
            raise ValueError("HNL duplicate fixture")
        seen.add(key)
        if len(cells) > 6 and cells[6].xpath('.//a[contains(@href,"/matches/")]'):
            continue
        if not match.group(2):
            held += 1
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", f"{home}-{away}".lower()).strip("-")
        events.append(_event(source, f"hnl-{round_number}-{slug}", home, away, date,
            match.group(2), ZAGREB, source["endpoint"], round_number))
    if round_number != 36 or len(seen) != 180:
        raise ValueError("HNL round publication changed")
    return events, held, len(rows)
