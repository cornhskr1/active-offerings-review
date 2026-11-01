"""LFF's 2026 senior men's Virslīga, limited to its next complete round."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-latvia-latvian-higher-league-virsl-ga-men"
COMPETITION_ID = "23300000"
RIGA = ZoneInfo("Europe/Riga")
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "jūn": 6,
          "jūl": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}

# Separately reviewed November 1 result/next-round transition; no later review renewal.
NOVEMBER_ROUNDS = {
    "23300239": {
        "round": 35,
        "day": 1,
        "names": [
            "Ogre United",
            "Riga FC"
        ],
        "links": [
            "/klubi/ogre-united-37095/?cid=23300000",
            "/klubi/riga-fc-38388/?cid=23300000"
        ],
        "venue": "Ogres stadions",
        "scores": [
            "0",
            "0"
        ],
        "details": [
            "/speles/ogre-united-riga-fc-23300239/"
        ]
    },
    "23300240": {
        "round": 35,
        "day": 1,
        "names": [
            "FC RFS",
            "FK Grobiņa"
        ],
        "links": [
            "/klubi/fc-rfs-36395/?cid=23300000",
            "/klubi/fk-grobina-38391/?cid=23300000"
        ],
        "venue": "LNK Sporta Parks (dabīgais)",
        "scores": [
            "3",
            "0"
        ],
        "details": [
            "/speles/fc-rfs-fk-grobina-23300240/"
        ]
    },
    "23300241": {
        "round": 35,
        "day": 1,
        "names": [
            "FK Liepāja",
            "SK Super Nova"
        ],
        "links": [
            "/klubi/fk-liepaja-38387/?cid=23300000",
            "/klubi/sk-super-nova-13440/?cid=23300000"
        ],
        "venue": "Stadions \"Daugava\", rezerves laukums",
        "scores": [
            "3",
            "3"
        ],
        "details": [
            "/speles/fk-liepaja-sk-super-nova-23300241/"
        ]
    },
    "23300242": {
        "round": 35,
        "day": 1,
        "names": [
            "BFC Daugavpils",
            "FK Tukums 2000"
        ],
        "links": [
            "/klubi/bfc-daugavpils-38389/?cid=23300000",
            "/klubi/fk-tukums-2000-11786/?cid=23300000"
        ],
        "venue": "Stadions \"Esplanāde\", mākslīgais laukums",
        "scores": [
            "2",
            "0"
        ],
        "details": [
            "/speles/bfc-daugavpils-fk-tukums-2000-23300242/"
        ]
    },
    "23300243": {
        "round": 35,
        "day": 1,
        "names": [
            "FK Auda",
            "FS Jelgava"
        ],
        "links": [
            "/klubi/fk-auda-36363/?cid=23300000",
            "/klubi/fs-jelgava-36466/?cid=23300000"
        ],
        "venue": "Jāņa Skredeļa stadions",
        "scores": [
            "4",
            "3"
        ],
        "details": [
            "/speles/fk-auda-fs-jelgava-23300243/"
        ]
    },
    "23300244": {
        "round": 36,
        "day": 8,
        "names": [
            "FS Jelgava",
            "Ogre United"
        ],
        "links": [
            "/klubi/fs-jelgava-36466/?cid=23300000",
            "/klubi/ogre-united-37095/?cid=23300000"
        ],
        "venue": "FK Jelgava Sporta bāzes mākslīgais laukums",
        "scores": [
            "-",
            "-"
        ],
        "details": []
    },
    "23300245": {
        "round": 36,
        "day": 8,
        "names": [
            "FK Tukums 2000",
            "FK Auda"
        ],
        "links": [
            "/klubi/fk-tukums-2000-11786/?cid=23300000",
            "/klubi/fk-auda-36363/?cid=23300000"
        ],
        "venue": "Tukuma pils. stad. māksl. lauk.",
        "scores": [
            "-",
            "-"
        ],
        "details": []
    },
    "23300246": {
        "round": 36,
        "day": 8,
        "names": [
            "SK Super Nova",
            "BFC Daugavpils"
        ],
        "links": [
            "/klubi/sk-super-nova-13440/?cid=23300000",
            "/klubi/bfc-daugavpils-38389/?cid=23300000"
        ],
        "venue": "Jāņa Skredeļa stadions",
        "scores": [
            "-",
            "-"
        ],
        "details": []
    },
    "23300247": {
        "round": 36,
        "day": 8,
        "names": [
            "FK Grobiņa",
            "FK Liepāja"
        ],
        "links": [
            "/klubi/fk-grobina-38391/?cid=23300000",
            "/klubi/fk-liepaja-38387/?cid=23300000"
        ],
        "venue": "Stadions \"Daugava\", rezerves laukums",
        "scores": [
            "-",
            "-"
        ],
        "details": []
    },
    "23300248": {
        "round": 36,
        "day": 8,
        "names": [
            "Riga FC",
            "FC RFS"
        ],
        "links": [
            "/klubi/riga-fc-38388/?cid=23300000",
            "/klubi/fc-rfs-36395/?cid=23300000"
        ],
        "venue": "Skonto stadions",
        "scores": [
            "-",
            "-"
        ],
        "details": []
    }
}


def _text(node, query):
    return " ".join(" ".join(node.xpath(query)).split())


def _reviewed_transition(upcoming, by_id, source, today, observed_at):
    if (source.get('sport') != 'Soccer' or source.get('region') != 'Latvia'
            or source.get('league') != 'Latvian Higher League / Virslīga | Men'
            or source.get('official_schedule_url') != 'https://lff.lv/sacensibas/viriesi/virsliga/?p=2026'):
        raise ValueError("LFF reviewed senior source changed")
    if (today != datetime.date(2026, 11, 1) or observed_at is None
            or observed_at.tzinfo is None or observed_at.utcoffset() is None
            or observed_at.astimezone(ZoneInfo("America/Chicago")).date() != today):
        raise ValueError("LFF November transition requires current reviewed date and aware clock")
    current_day = None
    headings = []
    seen = set()
    events = []
    for row in upcoming.xpath('./div'):
        classes = row.get("class", "").split()
        if "th1" in classes:
            heading = _text(row, './/span[contains(@class,"h3")]/text()')
            match = re.fullmatch(r"Svētdiena, (01|08)\.11\.2026\.", heading)
            if not match:
                raise ValueError("LFF reviewed date heading changed")
            current_day = int(match.group(1))
            headings.append(current_day)
            continue
        if "match" not in classes:
            if row.xpath('.//*[@data-id]') or _text(row, './/text()'):
                raise ValueError("LFF unexpected reviewed row")
            continue
        key = row.get("data-id")
        if key not in NOVEMBER_ROUNDS or key in seen:
            raise ValueError("LFF reviewed round identities changed")
        seen.add(key)
        spec = NOVEMBER_ROUNDS[key]
        if current_day != spec['day'] or row.xpath('.//div[contains(@class,"matchday")]/h5/text()') != [str(spec['round'])]:
            raise ValueError("LFF reviewed date or round changed")
        start = datetime.datetime(2026, 11, spec['day'], 13, tzinfo=RIGA)
        for view, full in ((row, False), (by_id[key], True)):
            clubs = view.xpath('.//div[contains(@class,"clubs")]/div[contains(@class,"club")]')
            names = [_text(c, './/div[contains(@class,"title")]//a/text()') for c in clubs]
            links = view.xpath('.//div[contains(@class,"clubs")]//a/@href')
            details = view.xpath('.//a[not(ancestor::div[contains(@class,"clubs")])]/@href')
            scores = [view.xpath('.//span[@class="res1"]/text()'), view.xpath('.//span[@class="res2"]/text()')]
            clock_query = './/div[contains(@class,"date")]/div[@class="h7"]/text()' if full else './/div[contains(@class,"matchday")]/h4/text()'
            if (names != spec['names'] or links != spec['links'] or details != spec['details']
                    or scores != [[s] for s in spec['scores']]
                    or _text(view, clock_query) != '13:00'
                    or _text(view, './/div[contains(@class,"stadium")]/text()') != spec['venue']):
                raise ValueError("LFF reviewed clubs, links, state, clock or stadium changed")
            if full and (view.xpath('.//div[@class="date"]/h5/text()') != [str(spec['day'])]
                         or view.xpath('.//div[@class="date"]/h6/text()') != ['nov']
                         or view.xpath('.//div[@class="date"]/div[@class="h8"]/text()') != ['2026']):
                raise ValueError("LFF reviewed full-view date changed")
        if spec['round'] == 35:
            if start >= observed_at:
                raise ValueError("LFF future scored result")
            continue
        if start <= observed_at:
            raise ValueError("LFF reviewed upcoming fixture already started")
        events.append({"id": f"lff-virsliga-{key}", "source_id": source['id'],
            "sport": source['sport'], "league": source['league'], "region": source['region'],
            "name": f"{spec['names'][1]} at {spec['names'][0]}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            "status": "UPCOMING", "status_detail": "Official 2026 Tonybet Virslīga round 36",
            "season_stage": "REGULAR", "location": spec['venue'],
            "source_endpoint": source['official_schedule_url']})
    if headings != [1, 8] or seen != NOVEMBER_ROUNDS.keys() or len(events) != 5:
        raise ValueError("LFF reviewed complete rounds changed")
    return events, len(by_id), 0


def next_round(page, source, today, observed_at=None):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("LFF catalog scope changed")
    doc = html.fromstring(page)
    selected = doc.xpath('//select[contains(@class,"pageParams")]/option[@selected="selected"]/text()')
    if selected != ["2026"] or "Tonybet Virslīga" not in " ".join(" ".join(doc.xpath("//h1//text()")).split()):
        raise ValueError("LFF senior 2026 edition changed")
    upcoming = doc.xpath('//*[@id="tabContent_1_1"]//div[contains(@class,"fixtures")][@data-genid]')
    all_games = doc.xpath('//*[@id="tabContent_1_2"]//div[contains(@class,"fixtures")][@data-genid]')
    if len(upcoming) != 1 or len(all_games) != 1 or not all(
        f"stats_competition_{COMPETITION_ID}_" in x.get("data-genid", "") for x in upcoming + all_games
    ):
        raise ValueError("LFF competition feed changed")
    all_rows = all_games[0].xpath('./div[contains(@class,"tr match")]')
    ids = [row.get("data-id") for row in all_rows]
    if len(ids) != 180 or len(set(ids)) != 180 or not all(i and i.isdecimal() for i in ids):
        raise ValueError("LFF 180-match league schedule incomplete")
    by_id = {row.get("data-id"): row for row in all_rows}
    reviewed_ids = [r.get("data-id") for r in upcoming[0].xpath('./div[contains(@class,"tr match")]')]
    scored_reviewed = any(r.get("data-id") in NOVEMBER_ROUNDS and
                          r.xpath('.//span[contains(@class,"res1")]/text()') != ["-"]
                          for r in upcoming[0].xpath('./div[contains(@class,"tr match")]'))
    if scored_reviewed or (today >= datetime.date(2026, 11, 1) and set(reviewed_ids) & NOVEMBER_ROUNDS.keys()):
        if [_text(n, './/text()') for n in doc.xpath('//h1[@class="sizeMedium"]')] != ['Tonybet Virslīga']:
            raise ValueError("LFF reviewed senior title changed")
        return _reviewed_transition(upcoming[0], by_id, source, today, observed_at)
    current_day = None
    rows = []
    for row in upcoming[0].xpath('./div'):
        if "th1" in row.get("class", "").split():
            heading = _text(row, './/span[contains(@class,"h3")]/text()')
            match = re.search(r"(\d{1,2})\.(\d{2})\.(2026)\.", heading)
            if not match:
                raise ValueError("LFF upcoming date heading changed")
            current_day = datetime.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            continue
        if "match" not in row.get("class", "").split():
            continue
        match_id = row.get("data-id")
        names = [_text(club, './/div[contains(@class,"title")]//a/text()')
                 for club in row.xpath('.//div[contains(@class,"clubs")]/div[contains(@class,"club")]')]
        club_links = row.xpath('.//div[contains(@class,"clubs")]//a/@href')
        round_text = _text(row, './/div[contains(@class,"matchday")]/h5/text()')
        clock = _text(row, './/div[contains(@class,"matchday")]/h4/text()')
        venue = _text(row, './/div[contains(@class,"stadium")]/text()')
        if (not current_day or not match_id or match_id not in by_id or len(names) != 2
                or not all(names) or len(club_links) != 2
                or not all(f"cid={COMPETITION_ID}" in link for link in club_links)
                or not round_text.isdecimal() or not re.fullmatch(r"\d{2}:\d{2}", clock)
                or not venue or row.xpath('.//span[contains(@class,"res1")]/text()') != ["-"]
                or row.xpath('.//span[contains(@class,"res2")]/text()') != ["-"]):
            raise ValueError("LFF senior upcoming fixture fields changed")
        past = by_id[match_id]
        full_names = [_text(club, './/div[contains(@class,"title")]//a/text()')
                      for club in past.xpath('.//div[contains(@class,"clubs")]/div[contains(@class,"club")]')]
        day_text = _text(past, './/div[contains(@class,"date")]/h5/text()')
        month_text = _text(past, './/div[contains(@class,"date")]/h6/text()')
        year_text = _text(past, './/div[contains(@class,"date")]/div[contains(@class,"h8")]/text()')
        full_clock = _text(past, './/div[contains(@class,"date")]/div[contains(@class,"h7")]/text()')
        if (full_names != names or day_text != str(current_day.day)
                or MONTHS.get(month_text.lower()) != current_day.month or year_text != "2026"
                or full_clock != clock or _text(past, './/div[contains(@class,"stadium")]/text()') != venue):
            raise ValueError("LFF current and full fixture views disagree")
        rows.append((current_day, int(round_text), match_id, names, venue, clock))
    future = [row for row in rows if row[0] >= today]
    if not future:
        return [], len(ids), 0
    first_day = min(row[0] for row in future)
    first_round = next(row[1] for row in future if row[0] == first_day)
    selected_rows = [row for row in future if row[1] == first_round]
    if len(selected_rows) != 5 or len({name for row in selected_rows for name in row[3]}) != 10:
        raise ValueError("LFF next complete five-match round changed")
    events = []
    for day, number, match_id, names, venue, clock in selected_rows:
        start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), RIGA)
        events.append({"id": f"lff-virsliga-{match_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026 Tonybet Virslīga round {number}",
            "season_stage": "REGULAR", "location": venue,
            "source_endpoint": source["official_schedule_url"]})
    return events, len(ids), len(future) - len(selected_rows)
