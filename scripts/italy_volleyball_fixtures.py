"""Timed first-leg Italian top-flight volleyball fixtures from each league publisher."""

import datetime
import re
from html import unescape
from zoneinfo import ZoneInfo

from lxml import html


ROME = ZoneInfo("Europe/Rome")
MONTH = {"ottobre": 10, "novembre": 11, "dicembre": 12}


def event(source, round_number, home, away, local):
    if not home or not away or home == away:
        raise ValueError("Italian volleyball pairing changed")
    slug = re.sub(r"[^a-z0-9]+", "-", f"{home}-{away}".lower()).strip("-")
    return {
        "id": f"{source['id']}-2026-r{round_number}-{slug}",
        "source_id": source["id"], "sport": source["sport"],
        "league": source["league"], "region": source["region"],
        "name": f"{away} at {home}",
        "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "UPCOMING", "status_detail": "Official 2026–27 first-leg fixture",
        "season_stage": f"REGULAR SEASON ROUND {round_number}",
        "location": None, "source_endpoint": source["official_schedule_url"],
    }


def parse_superlega(page, source, today, end):
    if source.get("catalog_terms") != ["Italian Volleyball Federation (FIPAV)", "SuperLega | Men"]:
        raise ValueError("SuperLega catalog scope changed")
    document = html.fromstring(page)
    seasons = document.xpath('//select[.//option[@selected and @value="2026"]]')
    divisions = document.xpath('//select[.//option[@selected and @value="999"]]')
    if "Calendario 2026/2027" not in " ".join(document.xpath("//title/text()")) or not seasons or not divisions:
        raise ValueError("SuperLega season or competition changed")
    tables = document.xpath('//table[@id="GareGiornata"][.//span[contains(text(),"Giornata Andata")]]')
    if len(tables) != 11:
        raise ValueError("SuperLega first-leg rounds changed")
    result = []
    for number, table in enumerate(tables, 1):
        heading = " ".join(table.xpath('./tr[@id="HeadCol"]//span/text()'))
        if not re.search(rf"\b{number}ª Giornata Andata\b", heading):
            raise ValueError("SuperLega round identity changed")
        header_date = re.search(r"\b(\d{1,2})\s+(Ottobre|Novembre|Dicembre)\s+2026\b", heading, re.I)
        if not header_date:
            raise ValueError("SuperLega round date changed")
        default_day = int(header_date.group(1))
        default_month = MONTH[header_date.group(2).lower()]
        default_time = re.search(r"Ore\s+(\d{1,2}):(\d{2})", heading)
        if not default_time:
            raise ValueError("SuperLega default kickoff changed")
        rows = table.xpath('./tr[@id="EvenRow" or @id="OddRow"]')
        if len(rows) != 6:
            raise ValueError("SuperLega round fixture count changed")
        clubs = set()
        for row_number, row in enumerate(rows, 1):
            cells = [" ".join(" ".join(c.itertext()).split()) for c in row.xpath("./td")]
            if len(cells) != 7 or cells[0] != str(6 * (number - 1) + row_number):
                raise ValueError("SuperLega row identity changed")
            home, away, note = cells[1], cells[3], cells[6]
            if home in clubs or away in clubs:
                raise ValueError("SuperLega club appears twice in a round")
            clubs.update((home, away))
            date = re.search(r"(\d{1,2})/(\d{1,2})/2026\s+Ore\s+(\d{1,2}):(\d{2})", note)
            time_only = re.search(r"^Ore\s+(\d{1,2}):(\d{2})$", note)
            if date:
                day, month, hour, minute = map(int, date.groups())
            elif time_only:
                day, month = default_day, default_month
                hour, minute = map(int, time_only.groups())
            elif not note:
                day, month = default_day, default_month
                hour, minute = map(int, default_time.groups())
            else:
                raise ValueError("SuperLega fixture kickoff changed")
            local = datetime.datetime(2026, month, day, hour, minute, tzinfo=ROME)
            result.append(event(source, number, home, away, local))
    if today <= end and end > max(datetime.date.fromisoformat(x["start_time"][:10]) for x in result):
        # The return leg and playoffs are not present in the published page.
        raise ValueError("SuperLega published first-leg horizon ended")
    return result


def parse_serie_a1(page, source, today, end):
    if source.get("catalog_terms") != ["Italian Volleyball Federation (FIPAV)", "Serie A1 | Women"]:
        raise ValueError("Serie A1 catalog scope changed")
    document = html.fromstring(page)
    content = document.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," single-news__content ")]')
    if len(content) != 1 or "LVF A1 Fineco" not in content[0].text_content() or "16 Settembre 2026" not in document.text_content():
        raise ValueError("Serie A1 publication or edition changed")
    paragraphs = [p for p in content[0].xpath('./p') if re.search(r"\b\d\^ Giornata\b", p.text_content())]
    if len(paragraphs) != 5:
        raise ValueError("Serie A1 published rounds changed")
    result = []
    for number, paragraph in enumerate(paragraphs, 1):
        parts = re.split(r"<br\s*/?>", html.tostring(paragraph, encoding="unicode"), flags=re.I)
        lines = [" ".join(html.fromstring(f"<div>{part}</div>").itertext()).strip() for part in parts]
        lines = [unescape(" ".join(line.split())) for line in lines if line.strip()]
        if not re.search(rf"\b{number}\^ Giornata\b", lines[0]):
            raise ValueError("Serie A1 round identity changed")
        fixtures = []
        clubs = set()
        kickoff = None
        for line in lines[1:]:
            date = re.search(r"\b(\d{1,2})\s+(ottobre)\s+ore\s+(\d{1,2})[.:](\d{2})\b", line, re.I)
            if date:
                day, month, hour, minute = date.groups()
                kickoff = datetime.datetime(2026, MONTH[month.lower()], int(day), int(hour), int(minute), tzinfo=ROME)
                continue
            if " – " in line and kickoff:
                home, away = line.split(" – ", 1)
                if home in clubs or away in clubs:
                    raise ValueError("Serie A1 club appears twice in a round")
                clubs.update((home, away))
                fixtures.append(event(source, number, home, away, kickoff))
                kickoff = None
        if len(fixtures) != 7 or len(clubs) != 14:
            raise ValueError("Serie A1 timed round incomplete")
        result.extend(fixtures)
    if today <= end and end > max(datetime.datetime.fromisoformat(x["start_time"].replace("Z", "+00:00")).astimezone(ROME).date() for x in result):
        raise ValueError("Serie A1 five-round publication horizon ended")
    return result
