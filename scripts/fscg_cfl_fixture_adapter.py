"""Current named, timed 2026–27 Meridianbet 1. CFL fixtures from FSCG."""

import datetime
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from lxml import html

PODGORICA = ZoneInfo("Europe/Podgorica")


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_round(page, source):
    if (source.get("id") != "uefa-soccer-montenegro-montenegrin-first-league-men"
            or source.get("league") != "Montenegrin First League | Men"
            or source.get("catalog_terms") != ["Montenegrin First League | Men"]):
        raise ValueError("Montenegro 1. CFL catalog scope changed")
    doc = html.fromstring(page, parser=html.HTMLParser(encoding="utf-8"))
    headers = doc.xpath('//div[@class="text"][h1]')
    if len(headers) != 1 or _norm(headers[0].xpath('string(./h1)')) != "Meridianbet 1. CFL" or _norm(headers[0].xpath('string(./h2)')) != "2026/27":
        raise ValueError("FSCG Meridianbet 1. CFL edition changed")
    # Read only the current-fixtures panel, never the archive or a neighbouring league.
    tables = doc.xpath('//div[@id="tabContent_1_1"]//table[contains(concat(" ",normalize-space(@class)," ")," fixtures ")]')
    if len(tables) != 1:
        raise ValueError("FSCG current fixture table missing or ambiguous")
    day, events, seen = None, [], set()
    for row in tables[0].xpath('./tr|./tbody/tr'):
        if row.xpath('./th'):
            marker = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\.", _norm(row.text_content()))
            if not marker:
                raise ValueError("FSCG current fixture date missing")
            day = datetime.datetime.strptime(marker.group(1), "%d.%m.%Y").date()
            if not datetime.date(2026,7,1) <= day <= datetime.date(2027,6,30):
                raise ValueError("FSCG fixture date outside edition")
            continue
        cells = row.xpath('./td')
        if not cells:
            continue
        match_id = row.get('data-id', '')
        if len(cells) != 6 or day is None or not match_id.isdigit() or match_id in seen:
            raise ValueError("FSCG fixture structure or identifier changed")
        seen.add(match_id)
        round_marker = re.fullmatch(r"(\d+)\. kolo", _norm(cells[1].text_content()))
        if not round_marker:
            raise ValueError("FSCG fixture round missing")
        home_links, away_links = (cells[i].xpath('.//a[starts-with(@href,"/klubovi/")]') for i in (3,4))
        if len(home_links) != 1 or len(away_links) != 1:
            raise ValueError("FSCG fixture clubs missing")
        home, away = (_norm(links[0].text_content()) for links in (home_links, away_links))
        if not home or not away or home == away or any(re.search(r"\b(?:TBC|TBD|U\d{2})\b", team, re.I) for team in (home,away)):
            raise ValueError("FSCG fixture pairing unidentified")
        scores = [_norm(cells[i].xpath(f'string(.//span[@class="res{j}"])')) for i,j in ((3,1),(4,2))]
        if all(score.isdigit() for score in scores):
            continue
        if scores != ['-','-']:
            raise ValueError("FSCG fixture score/status ambiguous")
        clock, venue = _norm(cells[0].text_content()), _norm(cells[2].text_content())
        if not re.fullmatch(r"\d{2}:\d{2}",clock) or not venue:
            raise ValueError("FSCG fixture kickoff or venue missing")
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), PODGORICA)
        detail = row.xpath('.//a[starts-with(@href,"/utakmice/")]/@href')
        events.append({
            "id": f"montenegro-cfl-{match_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "FSCG published current Meridianbet 1. CFL fixture",
            "season_stage": f"ROUND {round_marker.group(1)}", "location": venue,
            "source_endpoint": urljoin(source["endpoint"],detail[0]) if len(detail)==1 else source["endpoint"],
        })
    if not events:
        raise ValueError("FSCG current panel contained no timed upcoming fixtures")
    return events
