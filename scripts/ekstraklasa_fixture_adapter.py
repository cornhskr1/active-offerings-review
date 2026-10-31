"""Publisher next-round fixtures for Poland's senior Ekstraklasa."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "uefa-soccer-poland-ekstraklasa-men"
WARSAW = ZoneInfo("Europe/Warsaw")
ROUND_URL = re.compile(r"https://ekstraklasa\.org/terminarz/2026-2027/kolejka-(\d{1,2})/")
MATCH_PATH = re.compile(r"/mecz/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})/[a-z0-9-]+/(?:statystyki|przeglad|relacja)/")


def next_round(page, final_url, source):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("Polish senior league catalog scope changed")
    # The publisher's season URL redirects to its selected current round.
    match = ROUND_URL.fullmatch(final_url)
    if not match or not 1 <= int(match.group(1)) <= 34:
        raise ValueError("Ekstraklasa selected season round changed")
    number = int(match.group(1))
    doc = html.fromstring(page)
    title = " ".join(doc.xpath('//title/text()')).strip()
    round_labels = [" ".join(x.split()) for x in doc.xpath('//span[contains(text(),"Kolejka")]/text()')]
    if (title != f"Terminarz — sezon 2026-2027, kolejka {number}"
            or " ".join(doc.xpath('//h1/text()')).strip() != "Terminarz"
            or f"{number}. Kolejka" not in round_labels):
        raise ValueError("Ekstraklasa edition or selected round changed")
    links = doc.xpath('//a[starts-with(@href,"/mecz/")]')
    if len(links) != 9:
        raise ValueError("Ekstraklasa nine-match round changed")
    events = []
    teams = set()
    ids = set()
    held_untimed = 0
    for link in links:
        path = link.get("href")
        match_link = MATCH_PATH.fullmatch(path or "")
        card = link.getparent().getparent().getparent()
        names = [" ".join(x.split()) for x in card.xpath('.//p[contains(@class,"w-[120px]")]/text()')]
        label = card.xpath('./button/@aria-label')
        stamps = [" ".join(x.split()) for x in card.xpath('.//div[contains(@class,"md:flex")]/div/span/text()')]
        venue = [" ".join(x.split()) for x in card.xpath('.//p[contains(@class,"text-xsmall")]/text()')]
        mobile = [" ".join(x.split()) for x in card.xpath('.//p[contains(@class,"label-xsmall-bold")]/text()')]
        finished = "Zakończony" in card.text_content()
        live_labels = card.xpath('.//span[normalize-space(.)="na żywo"]')
        live = path.endswith('/relacja/')
        if (not match_link or match_link.group(1) in ids or len(names) != 2
                or not all(names) or names[0] == names[1]
                or label != [f"Otwórz szczegóły meczu {names[0]} kontra {names[1]}"]):
            raise ValueError("Ekstraklasa match pairing, date or venue changed")
        if finished != path.endswith("/przeglad/") or bool(live_labels) != live or (live and finished):
            raise ValueError("Ekstraklasa match state and detail route disagree")
        ids.add(match_link.group(1))
        teams.update(names)
        if live:
            # Live cards omit kickoff/date fields. Validate their explicit state,
            # score and senior club links, then exclude them from upcoming output.
            scores = [x.strip() for x in card.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," heading-medium ")]/text()')]
            clubs = card.xpath('.//a[starts-with(@href,"/kluby/")]/@href')
            if (len(live_labels)!=1 or len(scores)!=3 or scores[1]!=':'
                    or not re.fullmatch(r'\d+',scores[0]) or not re.fullmatch(r'\d+',scores[2])
                    or len(clubs)!=2 or len(set(clubs))!=2
                    or any(not re.fullmatch(r'/kluby/[a-z0-9-]+/',c) for c in clubs)):
                raise ValueError('Ekstraklasa live match evidence changed')
            continue
        if len(stamps) < 2 or not re.fullmatch(r"\d{2}\.\d{2}", stamps[1]):
            raise ValueError("Ekstraklasa match pairing, date or venue changed")
        month = int(stamps[1][3:])
        year = 2026 if month >= 7 else 2027
        try:
            day = datetime.datetime.strptime(f"{stamps[1]}.{year}", "%d.%m.%Y").date()
        except ValueError as exc:
            raise ValueError("Ekstraklasa match date changed") from exc
        if not datetime.date(2026, 7, 24) <= day <= datetime.date(2027, 5, 22):
            raise ValueError("Ekstraklasa fixture outside edition")
        if finished:
            continue
        if len(venue) != 1 or not venue[0] or len(mobile) != 1 or mobile[0] != f"{stamps[1]}, {stamps[0]}":
            raise ValueError("Ekstraklasa upcoming match venue or kickoff changed")
        if not re.fullmatch(r"\d{2}:\d{2}", stamps[0]):
            held_untimed += 1
            continue
        try:
            local = datetime.datetime.combine(day, datetime.time.fromisoformat(stamps[0]), WARSAW)
        except ValueError as exc:
            raise ValueError("Ekstraklasa kickoff changed") from exc
        events.append({"id": f"ekstraklasa-{match_link.group(1)}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": f"Official 2026–27 Ekstraklasa round {number}",
            "season_stage": "REGULAR", "location": venue[0],
            "source_endpoint": "https://ekstraklasa.org" + path})
    if len(ids) != 9 or len(teams) != 18:
        raise ValueError("Ekstraklasa duplicate or incomplete round clubs")
    return events, number, held_untimed
