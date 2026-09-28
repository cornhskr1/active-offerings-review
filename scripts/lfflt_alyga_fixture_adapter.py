"""Lithuanian LFF senior A Lyga, limited to the next complete 2026 round."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-lithuania-a-lyga-men"
COMPETITION_ID = "23198513"
VILNIUS = ZoneInfo("Europe/Vilnius")


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def next_round(page, source, today):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Lithuanian LFF catalog scope changed")
    doc = html.fromstring(page)
    if (_text(doc, '//div[@class="mlh-league-name"]/text()') != "A lyga, kurią remia TOPsport 2026"
            or _text(doc, '//div[@class="mlh-season"]/text()') != "Sezonas 2026"):
        raise ValueError("Lithuanian LFF senior 2026 competition changed")
    panels = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," matches-tour-table ")]')
    if len(panels) != 36:
        raise ValueError("Lithuanian LFF 36-round schedule incomplete")
    rounds = {}
    ids = set()
    for panel in panels:
        heading = _text(panel, './h1/text()')
        m = re.fullmatch(r"(\d{1,2})\. TURAS", heading)
        if not m or int(m.group(1)) in rounds:
            raise ValueError("Lithuanian LFF round labels changed")
        number = int(m.group(1))
        entries = panel.xpath('.//table[contains(@class,"matches-table")]//tr[@data-matchdate]')
        if len(entries) != 4:
            raise ValueError("Lithuanian LFF four-match round incomplete")
        rows = []
        for entry in entries:
            cells = entry.xpath('./td')
            names = [entry.get("data-hometeam"), entry.get("data-awayteam")]
            paths = entry.xpath('./td[4]/a/@href') + entry.xpath('./td[6]/a/@href')
            link = entry.xpath('./td[7]/a/@href')
            if (len(cells) != 7 or len(paths) != 2 or len(link) != 1
                    or not all(names) or len(set(names)) != 2
                    or not all(re.fullmatch(r"/komanda/[^/]+-\d+-" + COMPETITION_ID, path) for path in paths)
                    or not re.fullmatch(r"/(?:artimiausios|ivykusios)-varzybos/[^/]+-(\d+)", link[0])):
                raise ValueError("Lithuanian LFF senior fixture scope changed")
            if entry.get("data-status") not in ("1", "2"):
                raise ValueError("Lithuanian LFF match status changed")
            if entry.get("data-status") == "2" and not link[0].startswith("/artimiausios-varzybos/"):
                raise ValueError("Lithuanian LFF upcoming match detail changed")
            match_id = link[0].rsplit("-", 1)[-1]
            if match_id in ids:
                raise ValueError("Lithuanian LFF duplicate match ID")
            ids.add(match_id)
            date_text, clock, venue = (_text(entry, f'./td[{n}]/text()') for n in (1, 2, 3))
            if (date_text != entry.get("data-matchdate") or not re.fullmatch(r"\d{2}:\d{2}", clock)
                    or not venue or _text(entry, './td[4]/a/text()') != names[0]
                    or _text(entry, './td[6]/a/text()') != names[1]):
                raise ValueError("Lithuanian LFF fixture fields changed")
            day = datetime.datetime.strptime(date_text, "%Y %m %d").date()
            if day.year != 2026:
                raise ValueError("Lithuanian LFF edition date changed")
            if entry.get("data-status") == "2":
                if (_text(entry, './td[5]//div[@class="result-home"]/text()') != "-"
                        or _text(entry, './td[5]//div[@class="result-away"]/text()') != "-"):
                    raise ValueError("Lithuanian LFF played match marked upcoming")
                rows.append((day, number, clock, venue, names, link[0], match_id))
        rounds[number] = rows
    if set(rounds) != set(range(1, 37)) or len(ids) != 144:
        raise ValueError("Lithuanian LFF full league schedule incomplete")
    future = [(number, rows) for number, rows in rounds.items() if rows and any(r[0] >= today for r in rows)]
    complete = [(number, rows) for number, rows in future if len(rows) == 4 and all(r[0] >= today for r in rows)]
    if not complete:
        return [], 144, sum(len(rows) for _, rows in future)
    number, selected = min(complete, key=lambda item: min(row[0] for row in item[1]))
    if len({name for row in selected for name in row[4]}) != 8:
        raise ValueError("Lithuanian LFF next round repeats a club")
    held = sum(len(rows) for _, rows in future) - 4
    return selected, 144, held


def verified_match(page, fixture, source):
    day, number, clock, venue, names, path, match_id = fixture
    doc = html.fromstring(page)
    main = doc.xpath('//div[contains(@class,"main_info_desktop")]')
    if len(main) != 1:
        raise ValueError("Lithuanian LFF match detail missing")
    node = main[0]
    page_names = [_text(node, f'./div[contains(@class,"{side}")]/div[@class="team_name"]/text()')
                  for side in ("home_team", "away_team")]
    time_text = _text(node, './/span[@class="top_info_right_time"]//text()')
    date_match = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\s+(\d{2}:\d{2})$", time_text)
    detail_id = node.xpath('.//div[@class="cm-btn add-calendar"]/@data-match-id')
    if (page_names != names or detail_id != [match_id]
            or _text(doc, '//span[@class="top_info_league"]/text()') != "TOPLYGA 2026"
            or _text(doc, '//span[@class="top_info_league_extrainfo"]/text()') != f"{number} turas"
            or not date_match or (int(date_match.group(1)), int(date_match.group(2)), date_match.group(3))
            != (day.month, day.day, clock)
            or _text(node, './/div[@class="top_info_right_facility"]/text()') != venue):
        raise ValueError("Lithuanian LFF match competition, pairing, kickoff or venue changed")
    start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), VILNIUS)
    return {"id": f"lfflt-alyga-{match_id}", "source_id": source["id"],
        "sport": source["sport"], "league": source["league"], "region": source["region"],
        "name": f"{names[1]} at {names[0]}",
        "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": f"Official 2026 TOPLYGA round {number}",
        "season_stage": "REGULAR", "location": venue,
        "source_endpoint": "https://www.lff.lt" + path}
