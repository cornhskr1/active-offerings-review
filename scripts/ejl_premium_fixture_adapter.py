"""EJL senior men's 2026 Premium liiga next round and linked match verification."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-estonia-meistriliiga-premium-liiga-men"
ROOT_PATH = "/voistlused/match_info/"
TALLINN = ZoneInfo("Europe/Tallinn")


def _text(node, query):
    return " ".join(" ".join(node.xpath(query)).split())


def next_round(page, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("EJL catalog scope changed")
    doc = html.fromstring(page.replace(b"\x00", b"") if isinstance(page, bytes) else page.replace("\x00", ""))
    if _text(doc, "//title/text()") != "A. Le Coq Premium liiga":
        raise ValueError("EJL senior competition changed")
    listings = doc.xpath('//div[contains(@class,"event-single-small")]')
    if len(listings) < 10:
        raise ValueError("EJL recent and upcoming match panel incomplete")
    rows = []
    for item in listings:
        time_text = _text(item, './/p[contains(@class,"time")]/text()')
        match = re.fullmatch(r"(\d{2})\.(\d{2})\.(2026) kell (\d{2}:\d{2})", time_text)
        if not match:
            raise ValueError("EJL match date or kickoff changed")
        day = datetime.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        if day < today:
            continue
        round_text = _text(item.getparent(), './div[contains(@class,"info")]/p/text()')
        round_match = re.fullmatch(r"(\d{1,2})\. Voor", round_text)
        names = [_text(item, f'.//div[contains(@class,"teams")]/p[contains(@class,"{side}")]/a/text()')
                 for side in ("left", "right")]
        clubs = item.xpath('.//div[contains(@class,"teams")]/p/a/@href')
        links = item.xpath(f'.//a[starts-with(@href,"{ROOT_PATH}")]/@href')
        if (not round_match or not 1 <= int(round_match.group(1)) <= 36 or not all(names)
                or len(clubs) != 2 or not all(link.startswith("/voistlused/52/team/") for link in clubs)
                or len(links) != 1 or not re.fullmatch(r"/voistlused/match_info/\d+", links[0])
                or _text(item, './/span[contains(@class,"result")]/text()') != "-"):
            raise ValueError("EJL senior upcoming match fields changed")
        rows.append((day, int(round_match.group(1)), match.group(4), names, links[0]))
    if not rows:
        return [],len(listings)
    first_round = min(row[1] for row in rows)
    selected = [row for row in rows if row[1] == first_round]
    if len(selected) != 5 or len({name for row in selected for name in row[3]}) != 10:
        raise ValueError("EJL five-match senior round changed")
    return selected,len(listings)


def verified_match(page, fixture, source):
    day, number, clock, names, path = fixture
    doc = html.fromstring(page.replace(b"\x00", b"") if isinstance(page, bytes) else page.replace("\x00", ""))
    head = doc.xpath('//*[@id="page" and contains(@class,"event-detail")]/div/div/div[contains(@class,"head")]')
    if len(head) != 1:
        raise ValueError("EJL match detail missing")
    node = head[0]
    page_names = [_text(team, './p/a/text()') for team in node.xpath('./div[contains(@class,"teams")]/div[contains(@class,"team")]')]
    league = _text(node, './/li[contains(@class,"type")]/a/text()')
    round_text = _text(node, './/div[contains(@class,"info")]/ul/li[not(@class)]/text()')
    kickoff = _text(node, './/li[contains(@class,"date")]/p//text()')
    venue = _text(node, './/li[contains(@class,"location")]/p/a/text()')
    if (page_names != names or league != "A. Le Coq Premium liiga"
            or round_text != f"{number}. voor" or kickoff != f"{day:%d.%m.%Y} kell {clock}"
            or not venue):
        raise ValueError("EJL match competition, pairing, kickoff or stadium changed")
    start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), TALLINN)
    return {"id": f"ejl-premium-{path.rsplit('/',1)[-1]}", "source_id": source["id"],
        "sport": source["sport"], "league": source["league"], "region": source["region"],
        "name": f"{names[1]} at {names[0]}",
        "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": f"Official 2026 Premium liiga round {number}",
        "season_stage": "REGULAR", "location": venue,
        "source_endpoint": "https://jalgpall.ee" + path}
