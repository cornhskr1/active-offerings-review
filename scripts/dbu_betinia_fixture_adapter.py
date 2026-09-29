"""DBU's verified 2026/27 Betinia Liga first-division round 10."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


POOL = "507530"
ROUND_IDS = {173959, 173963, 173961, 173960, 173952, 173962}
COPENHAGEN = ZoneInfo("Europe/Copenhagen")
BASE = "https://www.dbu.dk"


def _scope(source):
    if (source.get("id") != "uefa-soccer-denmark-danish-1st-division-men"
            or source.get("catalog_terms") != ["Danish 1st Division | Men"]):
        raise ValueError("DBU first-division catalog identity changed")


def round_fixtures(page, source):
    _scope(source)
    doc = html.fromstring(page)
    if doc.xpath('string(//h2)').strip() != "Betinia LIGA - Grundspil 2026/27":
        raise ValueError("DBU Betinia season or phase changed")
    rows = doc.xpath('//table[contains(@class,"match-program--table")]//tr[@onclick]')
    if len(rows) != 132:
        raise ValueError("DBU Betinia first phase fixture count changed")
    seen, selected, clubs = set(), [], set()
    for index, row in enumerate(rows):
        link = re.fullmatch(r"MatchProgramMatchClick\('(/resultater/kamp/(\d+)_507530/kampinfo)'\)", row.get("onclick", ""))
        if not link or int(link.group(2)) in seen:
            raise ValueError("DBU Betinia match identity changed")
        match_id = int(link.group(2))
        seen.add(match_id)
        if (match_id in ROUND_IDS) != (54 <= index < 60):
            raise ValueError("DBU Betinia round-10 position changed")
        cells = row.xpath('./td[contains(@class,"hide-on-mobile")]')
        if len(cells) < 8 or cells[1].text_content().strip() != str(match_id):
            raise ValueError("DBU Betinia match row changed")
        if match_id not in ROUND_IDS:
            continue
        date_text = " ".join(cells[2].text_content().split())
        match = re.fullmatch(r"(fre|lør|søn)\.(\d{2})-(10) (2026)", date_text)
        clock = cells[3].text_content().strip()
        teams = [" ".join(cells[i].xpath('string(.//a[contains(@href,"/resultater/hold/")])').split()) for i in (4, 5)]
        team_links = [cells[i].xpath('.//a[contains(@href,"/resultater/hold/")]/@href') for i in (4, 5)]
        if (not match or not re.fullmatch(r"\d{2}:\d{2}", clock)
                or any(len(links) != 1 or not re.fullmatch(r"/resultater/hold/\d+_507530", links[0])
                       for links in team_links) or any(not name for name in teams)):
            raise ValueError("DBU Betinia named or timed pairing changed")
        date = datetime.date(2026, 10, int(match.group(2)))
        if date.weekday() != {"fre": 4, "lør": 5, "søn": 6}[match.group(1)] or not 9 <= date.day <= 11:
            raise ValueError("DBU Betinia round date changed")
        clubs.update(links[0] for links in team_links)
        selected.append((match_id, date, clock, teams[0], teams[1], BASE + link.group(1)))
    if {item[0] for item in selected} != ROUND_IDS or len(clubs) != 12:
        raise ValueError("DBU Betinia round completeness changed")
    return selected, len(rows)


def verified_fixture(page, fixture, source):
    _scope(source)
    match_id, date, clock, home, away, url = fixture
    doc = html.fromstring(page)
    if doc.xpath('string(//meta[@name="description"]/@content)') != "Betinia LIGA - Grundspil 2026/27 - 1. Division":
        raise ValueError("DBU Betinia detail competition changed")
    if " ".join(doc.xpath('string(//h2)').split()) != f"{home} - {away}":
        raise ValueError("DBU Betinia detail pairing changed")
    fields = {}
    for col in doc.xpath('//div[contains(@class,"sr-info-col-wrap")]/div[contains(@class,"col-pad")]'):
        key = col.xpath('string(./label)').strip()
        if key:
            fields[key] = " ".join(col.xpath('string(./span)').split())
    detail_time = fields.get("Tidspunkt", "")
    if (fields.get("Kampnummer") != str(match_id)
            or fields.get("Række") != "Betinia LIGA - Grundspil 2026/27"
            or fields.get("Pulje") != "1. Division"
            or not re.fullmatch(rf"(?:fre|lør|søn)\. {date:%d-%m-%Y} Kl\. {clock}", detail_time)):
        raise ValueError("DBU Betinia detail match, division, or kickoff changed")
    start = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), COPENHAGEN)
    return {"id": f"dbu-betinia-2026-27-{match_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "DBU verified first-division round 10 fixture",
            "season_stage": "REGULAR", "location": None, "source_endpoint": url}
