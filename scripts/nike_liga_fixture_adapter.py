"""Official Niké liga senior regular-season fixture listing."""

import datetime
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-slovakia-slovak-first-football-league-slovak-1-liga-men"
BRATISLAVA = ZoneInfo("Europe/Bratislava")


def _text(node, path):
    return " ".join(" ".join(node.xpath(path)).split())


def parse_fixtures(page, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Slovak senior league scope changed")
    doc = html.fromstring(page)
    if (_text(doc, '//title/text()') != "Rozpis zápasov | Niké liga"
            or _text(doc, '//h1/text()') != "Zápasy"):
        raise ValueError("Niké liga schedule page changed")
    selections = [(_text(option, './text()'), option.get("value"))
                  for option in doc.xpath('//header//select/option[@selected]')]
    if (("2026/2027", "/zapasy/2026") not in selections
            or ("Základná časť", "/zapasy/2026?id_stage=1") not in selections
            or ("Všetky tímy", "/zapasy/2026") not in selections):
        raise ValueError("Niké liga edition or regular-season selection changed")
    rows = doc.xpath('//table[contains(concat(" ",normalize-space(@class)," ")," schedule_table ")]/tbody/tr')
    if len(rows) != 132:
        raise ValueError("Niké liga 22-round schedule changed")
    events = []
    ids = set()
    rounds = Counter()
    held_untimed = 0
    for row in rows:
        cells = row.xpath('./td')
        if len(cells) != 9:
            raise ValueError("Niké liga fixture columns changed")
        number = _text(cells[0], './/text()').rstrip('.')
        home = _text(cells[1], './/span[contains(@class,"schedule_table__team__name")]/a/text()')
        away = _text(cells[3], './/span[contains(@class,"schedule_table__team__name")]/a/text()')
        score = _text(cells[2], './a/text()')
        links = cells[2].xpath('./a/@href')
        date_label = _text(cells[4], './/span[contains(@class,"schedule_table__date--full")]/text()')
        clock = _text(cells[5], './text()')
        if (not number.isdigit() or not 1 <= int(number) <= 22
                or not home or not away or home == away or len(links) != 1
                or not re.fullmatch(r"/zapas/(\d+)-[a-z0-9-]+", links[0])
                or not re.fullmatch(r"(?:po|ut|st|št|pi|so|ne) \d{2}\.\d{2}\.20(?:26|27)", date_label)
                or not re.fullmatch(r"\d{2}:\d{2}|--:--", clock)):
            raise ValueError("Niké liga fixture fields changed")
        match_id = links[0].split('/')[2].split('-')[0]
        if match_id in ids:
            raise ValueError("Niké liga duplicate match ID")
        ids.add(match_id)
        rounds[int(number)] += 1
        day = datetime.datetime.strptime(date_label.split()[1], "%d.%m.%Y").date()
        if not datetime.date(2026, 7, 25) <= day <= datetime.date(2027, 2, 28):
            raise ValueError("Niké liga regular-season date outside edition")
        if date_label.split()[0] != ("po", "ut", "st", "št", "pi", "so", "ne")[day.weekday()]:
            raise ValueError("Niké liga fixture weekday changed")
        if score != "-:-":
            if not re.fullmatch(r"\d+:\d+", score):
                raise ValueError("Niké liga fixture result changed")
            continue
        if clock == "--:--":
            held_untimed += 1
            continue
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), BRATISLAVA)
        start = local.astimezone(datetime.timezone.utc)
        events.append({"id": f"nike-liga-{match_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026–27 Niké liga regular-season round {number}",
            "season_stage": "REGULAR", "source_endpoint": "https://www.nikeliga.sk" + links[0]})
    if rounds != Counter({number: 6 for number in range(1, 23)}) or len(ids) != 132:
        raise ValueError("Niké liga regular-season rounds changed")
    return events, held_untimed, len(ids)
