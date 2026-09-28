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


def _text(node, query):
    return " ".join(" ".join(node.xpath(query)).split())


def next_round(page, source, today):
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
