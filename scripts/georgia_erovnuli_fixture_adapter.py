"""Georgian senior Erovnuli Liga calendar with linked UTC match verification."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-georgia-erovnuli-liga-men"
TBILISI = ZoneInfo("Asia/Tbilisi")


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def candidates(page, source, today, end):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Georgian catalog scope changed")
    doc = html.fromstring(page)
    if (_text(doc, '//title/text()') != "Fixtures - Erovnuli Liga"
            or _text(doc, '//h1/text()') != "Fixtures"):
        raise ValueError("Georgian league calendar changed")
    active = doc.xpath('//a[contains(@class,"bef-link") and contains(@class,"active")]/text()')
    if [" ".join(value.split()) for value in active] != ["CRYSTALBET Erovnuli Liga"]:
        raise ValueError("Georgian top division filter changed")
    groups = doc.xpath('//section[contains(@class,"games-list-group")]')
    if not groups:
        raise ValueError("Georgian fixture rounds missing")
    rows = []
    ids = set()
    for group in groups:
        match = re.fullmatch(r"ტური (\d{1,2})", _text(group, './h2//text()'))
        if not match or not 1 <= int(match.group(1)) <= 36:
            raise ValueError("Georgian league round changed")
        round_number = int(match.group(1))
        for teaser in group.xpath('.//div[contains(@class,"e-game-teaser")]'):
            link = teaser.xpath('./a[contains(@class,"gt-main")]/@href')
            names = [_text(teaser, f'.//span[contains(@class,"grs-{side}")]//span[contains(@class,"normal")]/text()')
                     for side in (1, 2)]
            local = _text(teaser, './/span[contains(@class,"grs-time")]//time/text()')
            venue = _text(teaser, './/span[contains(@class,"f-game-stadium")]//text()')
            match_id = teaser.get("data-id")
            if (teaser.get("data-status") != "upcoming" or not match_id or not match_id.isdigit()
                    or match_id in ids or len(link) != 1
                    or not re.fullmatch(r"/en/game/" + match_id + r"-[a-z0-9-]+", link[0])
                    or not all(names) or names[0] == names[1] or not venue
                    or not re.fullmatch(r"\d{2}:\d{2}", local)):
                raise ValueError("Georgian senior upcoming match fields changed")
            ids.add(match_id)
            # Day headings belong to the enclosing round section, before each subgroup.
            subgroup = teaser.getparent()
            preceding = subgroup.xpath('preceding-sibling::div[contains(@class,"row")][1]/div/h3/text()')
            if not preceding:
                raise ValueError("Georgian fixture date heading missing")
            try:
                day = datetime.datetime.strptime(" ".join(preceding[0].split()), "%A, %d %B, %Y").date()
            except ValueError as exc:
                raise ValueError("Georgian fixture date changed") from exc
            if day.year != 2026:
                raise ValueError("Georgian edition changed")
            if today - datetime.timedelta(days=1) <= day <= end + datetime.timedelta(days=1):
                rows.append((day, round_number, local, venue, names, link[0], match_id))
    return rows, len(ids)


def verified_match(page, fixture, source):
    day, number, local, venue, names, path, match_id = fixture
    doc = html.fromstring(page)
    clubs = doc.xpath('//h1[contains(@class,"gfh-clubs-inner")]/a[contains(@class,"gfh-club")]')
    actual_names = [_text(club, './/span[contains(@class,"d-md-inline")]/text()') for club in clubs]
    round_label = _text(doc, '//h1[contains(@class,"gfh-clubs-inner")]//span[contains(@class,"gfh-tour")]/text()')
    match_time = doc.xpath('//div[contains(@class,"gfh-status-bar")]//time/@datetime')
    actual_venue = _text(doc, '//span[contains(@class,"f-game-stadium")]//text()')
    if len(match_time) != 1:
        raise ValueError("Georgian linked match UTC kickoff missing")
    try:
        start = datetime.datetime.fromisoformat(match_time[0].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Georgian linked match UTC kickoff changed") from exc
    local_start = start.astimezone(TBILISI)
    if (len(clubs) != 2 or actual_names != names or round_label != f"ტური {number}"
            or actual_venue != venue or (local_start.date(), local_start.strftime("%H:%M")) != (day, local)
            or not _text(doc, '/html/head/title/text()').endswith(" - Erovnuli Liga")):
        raise ValueError("Georgian match pairing, round, local kickoff or stadium changed")
    return {"id": f"erovnuli-{match_id}", "source_id": source["id"],
        "sport": source["sport"], "league": source["league"], "region": source["region"],
        "name": f"{names[1]} at {names[0]}",
        "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": f"Official 2026 Erovnuli Liga round {number}",
        "season_stage": "REGULAR", "location": venue,
        "source_endpoint": "https://erovnuliliga.ge" + path}
