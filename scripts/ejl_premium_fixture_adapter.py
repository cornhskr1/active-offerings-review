"""EJL senior men's 2026 Premium liiga next round and linked match verification."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-estonia-meistriliiga-premium-liiga-men"
ROOT_PATH = "/voistlused/match_info/"
TALLINN = ZoneInfo("Europe/Tallinn")
# Exact senior round reviewed against the federation panel and all five details.
ROUND35 = {
    "186276": ("31.10.2026 kell 15:00", ("6314", "FC Nõmme United"), ("11", "Tallinna FCI Levadia"), "143981"),
    "186277": ("31.10.2026 kell 14:30", ("5387", "Pärnu JK Vaprus"), ("5", "Paide Linnameeskond"), "144002"),
    "186278": ("31.10.2026 kell 14:30", ("1382", "Tartu JK Tammeka"), ("3573", "Harju JK Laagri"), "143942"),
    "186279": ("01.11.2026 kell 12:30", ("3136", "Nõmme Kalju FC"), ("76", "FC Kuressaare"), None),
    "186280": ("01.11.2026 kell 14:30", ("4", "Tallinna FC Flora"), ("14", "JK Narva Trans"), None),
}
# Separately reviewed November 1 scored rows, bound to the two exact details.
# The October 31 observation and later rounds retain their existing boundaries.
NOV1_RESULTS = {"186279": ("143983", "1 - 0"), "186280": ("144017", "2 - 0")}


def _text(node, query):
    return " ".join(" ".join(node.xpath(query)).split())


def _reviewed_round35(listings, today, observed_at):
    if not datetime.date(2026, 10, 31) <= today <= datetime.date(2026, 11, 1):
        raise ValueError("EJL reviewed round-35 window expired")
    now = observed_at if observed_at is not None else datetime.datetime.now(datetime.timezone.utc)
    if not isinstance(now, datetime.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("EJL aware observation clock required")
    selected = [n for n in listings if _text(n.getparent(), './div[contains(@class,"info")]/p/text()') == "35. Voor"]
    if len(selected) != 5:
        raise ValueError("EJL reviewed five-match round incomplete")
    seen = set(); clubs = set(); rows = []
    for item in selected:
        links = item.xpath(f'.//a[starts-with(@href,"{ROOT_PATH}")]/@href')
        if len(links) != 1 or links[0] not in [ROOT_PATH + key for key in ROUND35]:
            raise ValueError("EJL reviewed match identity changed")
        key = links[0].rsplit('/', 1)[-1]
        if key in seen:
            raise ValueError("EJL duplicate reviewed match")
        seen.add(key)
        expected_time, home, away, protocol = ROUND35[key]
        names = [_text(item, f'.//div[contains(@class,"teams")]/p[contains(@class,"{side}")]/a/text()') for side in ("left", "right")]
        paths = item.xpath('.//div[contains(@class,"teams")]/p/a/@href')
        if (names != [home[1], away[1]] or paths != [f"/voistlused/52/team/{t[0]}?season=2026" for t in (home, away)]
                or _text(item, './/p[contains(@class,"time")]/text()') != expected_time):
            raise ValueError("EJL reviewed pairing or kickoff changed")
        clubs.update(paths)
        start = datetime.datetime.strptime(expected_time, "%d.%m.%Y kell %H:%M").replace(tzinfo=TALLINN)
        results = item.xpath('.//div[@class="results-container"]/*')
        if len(results) != 1:
            raise ValueError("EJL ambiguous result state")
        result = results[0]; score = " ".join(result.text_content().split())
        reviewed_result = NOV1_RESULTS.get(key) if today == datetime.date(2026, 11, 1) else None
        result_protocol = protocol or (reviewed_result[0] if reviewed_result else None)
        if result.tag == 'span' and result.get('class') == 'result' and score == '-' and not result.get('href'):
            rows.append((start.date(), 35, start.strftime('%H:%M'), names, links[0]))
        elif (result.tag == 'a' and result.get('class') == 'result' and result_protocol is not None
              and result.get('href') == '/voistlused/protocol/' + result_protocol
              and re.fullmatch(r'\d{1,2} - \d{1,2}', score) and start <= now
              and (protocol is not None or score == reviewed_result[1])):
            continue
        else:
            raise ValueError("EJL unknown or future scored result")
    if seen != set(ROUND35) or len(clubs) != 10:
        raise ValueError("EJL reviewed round identities changed")
    # Round 36 and qualification ties are not part of this bounded renewal.
    return rows, len(listings)


def next_round(page, source, today, observed_at=None):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("EJL catalog scope changed")
    doc = html.fromstring(page.replace(b"\x00", b"") if isinstance(page, bytes) else page.replace("\x00", ""))
    if _text(doc, "//title/text()") != "A. Le Coq Premium liiga":
        raise ValueError("EJL senior competition changed")
    listings = doc.xpath('//div[contains(@class,"event-single-small")]')
    if len(listings) < 10:
        raise ValueError("EJL recent and upcoming match panel incomplete")
    if today >= datetime.date(2026, 10, 31):
        return _reviewed_round35(listings, today, observed_at)
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
