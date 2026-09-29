"""VPF's exact 2026–27 top-flight calendar; month-only dates remain held."""

import datetime
import re
from collections import Counter
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "soccer-afc-vietnam-vleague-1-men"
EDITION_ID = "154439"
HANOI = ZoneInfo("Asia/Ho_Chi_Minh")
SEASON_URL = "https://vpf.vn/season/v-league-2027/?action=calendar&pagejs=1"
MOBILE_URL = "https://vpf.vn/mobile/"


def _team(row, side):
    links = row.xpath(f'./div[contains(@class,"jsMatchDiv{side}")]//div[contains(@class,"js_div_particName")]/a')
    if len(links) != 1:
        raise ValueError("VPF club pairing changed")
    link = links[0]
    url = urlparse(link.get("href", ""))
    if url.netloc != "vpf.vn" or not re.fullmatch(r"/team/[a-z0-9-]+/", url.path):
        raise ValueError("VPF club link changed")
    if parse_qs(url.query).get("sid") != [EDITION_ID]:
        raise ValueError("VPF club edition changed")
    name = " ".join(link.itertext()).strip()
    if not name:
        raise ValueError("VPF club name missing")
    return name, url.path


def parse_vleague(page, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("VPF catalog scope changed")
    doc = html.fromstring(page)
    if "2026/27" not in doc.xpath("string(//h1)") or "LPBank" not in doc.xpath("string(//h1)"):
        raise ValueError("VPF league edition changed")
    articles = doc.xpath("//article")
    if len(articles) != 1:
        raise ValueError("VPF season page structure changed")
    article = articles[0]
    rounds = [" ".join(x.itertext()).strip() for x in article.xpath(
        './/div[contains(@class,"jsrow-matchday-name")][starts-with(@id,"round_")]')]
    numbered = [int(m.group(1)) for title in rounds
                if (m := re.fullmatch(r"Vòng (\d+) LPBank V\.League 1-2026/27", title))]
    if sorted(numbered) != list(range(1, 27)) or len(rounds) < 26:
        raise ValueError("VPF 26-round season structure changed")
    rows = article.xpath('.//div[contains(@class,"js-matchday-wrapper")]//div[contains(@class,"jstable-row")][.//div[contains(@class,"jsMatchDivHome")]]')
    if len(rows) != 182:
        raise ValueError("VPF 182-match regular season changed")
    events, held, seen, clubs, pair_counts = [], 0, set(), Counter(), Counter()
    candidates = []
    for row in rows:
        home, home_id = _team(row, "Home")
        away, away_id = _team(row, "Away")
        if home_id == away_id:
            raise ValueError("VPF self-pairing")
        clubs[home_id] += 1
        clubs[away_id] += 1
        pair = tuple(sorted((home_id, away_id)))
        pair_counts[pair] += 1
        links = row.xpath('./div[contains(@class,"jsMatchDivScore")]//a[contains(@href,"/match/")]/@href')
        if len(links) != 1:
            raise ValueError("VPF match link changed")
        link = urlparse(links[0])
        if link.netloc != "vpf.vn" or not re.fullmatch(r"/match/[a-z0-9-]+/", link.path) or link.path in seen:
            raise ValueError("VPF match identity changed")
        seen.add(link.path)
        score = " ".join(row.xpath('./div[contains(@class,"jsMatchDivScore")]')[0].itertext()).strip()
        if score != "v":
            if not re.fullmatch(r"\d+\s*-\s*\d+", score):
                raise ValueError("VPF result status changed")
            continue
        wrapper = row.getparent().getparent()
        date_label = wrapper.xpath('string(./div[contains(@class,"js-matchday-title")]/p[contains(@class,"js-matchday-date")])').strip()
        exact = re.fullmatch(r"(\d{1,2}) Tháng (\d{2}), (2026|2027)", date_label)
        if not exact:
            if not re.fullmatch(r"Tháng \d{2}, 2027", date_label):
                raise ValueError("VPF fixture date changed")
            held += 1
            continue
        date = datetime.date(int(exact.group(3)), int(exact.group(2)), int(exact.group(1)))
        if not datetime.date(2026, 9, 4) <= date <= datetime.date(2027, 5, 22):
            raise ValueError("VPF fixture outside edition")
        clock = row.xpath('string(./div[contains(@class,"jsMatchDivTime")])').strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", clock):
            held += 1
            continue
        start = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), HANOI)
        candidates.append((pair, {"id": f"vpf-vleague1-{link.path.strip('/').split('/')[-1]}",
                       "source_id": source["id"], "sport": source["sport"],
                       "league": source["league"], "region": source["region"],
                       "name": f"{away} at {home}",
                       "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                       "status": "UPCOMING", "status_detail": "Official 2026–27 V.League 1 regular season",
                       "season_stage": "REGULAR", "location": None, "source_endpoint": links[0]}))
    if len(clubs) != 14 or len(seen) != 182:
        raise ValueError("VPF club or match completeness changed")
    # The publisher currently repeats one future pair three times and omits its
    # expected counterpart. Hold affected cards until its schedule is corrected.
    for pair, event in candidates:
        if pair_counts[pair] != 2:
            held += 1
        else:
            events.append(event)
    return events, held, len(rows)


def parse_vleague_mobile_round(page, source, now):
    """Use only the complete, exact current round when the season page is blocked."""
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("VPF catalog scope changed")
    doc = html.fromstring(page)
    widgets = doc.xpath('//*[@id="jsScrollMatches1668"]')
    if len(widgets) != 1:
        raise ValueError("VPF mobile league widget changed")
    widget = widgets[0]
    title = widget.xpath('string(.//h3[contains(@class,"jsmatchseason")])').strip()
    if not re.fullmatch(r"Vòng \d+ LPBank V\.League 1-2026/27", title):
        raise ValueError("VPF mobile league edition changed")
    container = widget.xpath('./div[contains(@class,"jsmatchcont")]')
    if len(container) != 1:
        raise ValueError("VPF mobile round structure changed")
    cards = container[0].xpath('./div[contains(@class,"jo-match-in-week")]')
    if len(cards) != 7:
        raise ValueError("VPF mobile round is incomplete")
    events, seen, clubs = [], set(), set()
    for card in cards:
        dates = card.xpath('preceding-sibling::p[contains(@class,"jo-date")][1]')
        label = dates[0].text_content().strip() if dates else ""
        match = re.fullmatch(r"[^,]+, (\d{1,2}) Tháng (\d{2}), (2026|2027)", label)
        if not match:
            raise ValueError("VPF mobile fixture date changed")
        date = datetime.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        if not datetime.date(2026, 9, 4) <= date <= datetime.date(2027, 5, 22):
            raise ValueError("VPF mobile date outside edition")
        teams = []
        for side in ("left", "right"):
            links = card.xpath(f'.//div[contains(@class,"jo-name-team-{side}")]//div[contains(@class,"js_div_particName")]/a')
            if len(links) != 1:
                raise ValueError("VPF mobile clubs changed")
            link = urlparse(links[0].get("href", ""))
            if (link.netloc != "vpf.vn" or not re.fullmatch(r"/team/[a-z0-9-]+/", link.path)
                    or parse_qs(link.query).get("sid") != [EDITION_ID]):
                raise ValueError("VPF mobile club edition changed")
            teams.append((links[0].text_content().strip(), link.path))
        if not all(name for name, _ in teams) or teams[0][1] == teams[1][1]:
            raise ValueError("VPF mobile club pairing changed")
        clubs.update(team_id for _, team_id in teams)
        fixture = card.xpath('.//div[contains(@class,"jo-fixture")]')
        links = fixture[0].xpath('.//a') if len(fixture) == 1 else []
        if len(links) != 1:
            raise ValueError("VPF mobile match link changed")
        link = urlparse(links[0].get("href", ""))
        if (link.netloc != "vpf.vn" or not re.fullmatch(r"/match/[a-z0-9-]+/", link.path)
                or link.path in seen):
            raise ValueError("VPF mobile match identity changed")
        seen.add(link.path)
        clock = links[0].text_content().strip()
        if re.fullmatch(r"\d+\s*-\s*\d+", clock):
            continue
        if not re.fullmatch(r"\d{1,2}:\d{2}", clock):
            raise ValueError("VPF mobile kickoff changed")
        start = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), HANOI)
        if start.astimezone(datetime.timezone.utc) <= now:
            raise ValueError("VPF mobile round has stale fixture")
        events.append({"id": f"vpf-vleague1-{link.path.strip('/').split('/')[-1]}",
                       "source_id": source["id"], "sport": source["sport"],
                       "league": source["league"], "region": source["region"],
                       "name": f"{teams[1][0]} at {teams[0][0]}",
                       "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                       "status": "UPCOMING", "status_detail": "Official 2026–27 V.League 1 mobile round",
                       "season_stage": "REGULAR", "location": None, "source_endpoint": links[0].get("href")})
    if len(clubs) != 14 or not events:
        raise ValueError("VPF mobile round clubs or future fixtures changed")
    return events, len(cards)
