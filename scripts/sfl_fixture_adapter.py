"""Exact 2026/27 Swiss Football League fixtures from the publisher's linked PDFs."""

import datetime
import io
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from lxml import html
from pypdf import PdfReader


ZURICH = ZoneInfo("Europe/Zurich")
SPECS = {
    "uefa-soccer-switzerland-swiss-super-league-men": (
        "Swiss Super League | Men", "Brack Super League", "21.09.2026", 22, 6,
        "Brack_Super_League_Spielplan-Calendrier_21-09-26_Season-2026-27"),
    "uefa-soccer-switzerland-swiss-challenge-league-men": (
        "Swiss Challenge League | Men", "dieci Challenge League", "07.09.2026", 17, 5,
        "dieci_Challenge_League_Spielplan-Calendrier_2026-27"),
}
ROW = re.compile(r"^\s*(\d{2}\.\d{2}\.(?:\d{2}|\d{4}))\s+"
                 r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{2}:\d{2})\s+"
                 r"(.+?)\s+[–-]\s+(.+?)(?:\s{3,}(?:SRG|blue))?\s*$")


def publisher_pdf_url(page, source):
    spec = SPECS[source["id"]]
    doc = html.fromstring(page)
    links = [urljoin(source["publisher_page"], href) for href in doc.xpath('//a/@href')
             if spec[5] in href]
    links = set(links)
    if len(links) != 1 or links.pop() != source["endpoint"]:
        raise ValueError("SFL publisher's current PDF link changed")
    return source["endpoint"]


def parse_pdf(content, source, today, window_end):
    spec = SPECS[source["id"]]
    if source.get("catalog_terms") != [spec[0]]:
        raise ValueError("SFL catalog scope changed")
    reader = PdfReader(io.BytesIO(content))
    raw = "\n".join(page.extract_text() for page in reader.pages)
    text = "\n".join(page.extract_text(extraction_mode="layout") for page in reader.pages)
    if (f"VERSION {spec[2]}" not in raw or not re.search(r"Spielplan\s*/\s*Calendrier, Saison 2026/27\s+" + re.escape(spec[1]), raw)):
        raise ValueError("SFL PDF edition or revision changed")
    rows = [match for line in text.splitlines() if (match := ROW.fullmatch(line))]
    if len(rows) != spec[3] * spec[4]:
        raise ValueError("SFL published fixture count changed")
    rounds = []
    for offset in range(0, len(rows), spec[4]):
        group = rows[offset:offset + spec[4]]
        teams = [team.strip() for row in group for team in row.groups()[3:5]]
        if len(set(teams)) != 2 * spec[4] or any(re.search(r"\b(?:U-?\d{2}|TBD|TBC)\b", team, re.I) for team in teams):
            raise ValueError("SFL round clubs or eligibility changed")
        rounds.append(group)
    events = []
    last_date = today
    for number, group in enumerate(rounds, 1):
      for row in group:
        date_string, weekday, clock, home, away = row.groups()
        day = datetime.datetime.strptime(date_string, "%d.%m.%Y" if len(date_string) == 10 else "%d.%m.%y").date()
        if day.strftime("%a") != weekday or day.year not in (2026, 2027):
            raise ValueError("SFL PDF weekday or season changed")
        last_date = max(last_date, day)
        if not today <= day <= window_end:
            continue
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), ZURICH)
        events.append({"id": f"sfl-{source['id']}-2026-27-r{number}-{re.sub('[^a-z0-9]+','-',home.lower()).strip('-')}",
                       "source_id": source["id"], "sport": source["sport"],
                       "league": source["league"], "region": source["region"],
                       "name": f"{away.strip()} at {home.strip()}",
                       "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                       "status": "UPCOMING", "status_detail": f"SFL published 2026/27 round {number}",
                       "season_stage": "REGULAR", "source_endpoint": source["publisher_page"]})
    if window_end > last_date:
        raise ValueError("SFL next-round PDF does not cover the full review window")
    return events, len(rounds), len(rows)
