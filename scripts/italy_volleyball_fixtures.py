"""Timed first-leg Italian top-flight volleyball fixtures from each league publisher."""

import datetime
import re
from html import unescape
from urllib.parse import urlparse
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
        headings = table.xpath('./tr/td/span[contains(text(),"Giornata Andata")]/text()')
        if len(headings) != 1:
            raise ValueError("SuperLega round heading changed")
        heading = headings[0]
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
    if source.get('endpoint') == 'https://www.legavolleyfemminile.it/calendario/':
        return parse_serie_a1_calendar(page, source, today, end)
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


def parse_serie_a1_calendar(page, source, today, end):
    """Published current A1 rows only; the same page also contains A2 fixtures."""
    if source.get('season_code') != '2026-2027':
        raise ValueError('Serie A1 configured edition changed')
    document = html.fromstring(page)
    if document.xpath('//title/text()') != ['Calendario – Lega Pallavolo Serie A Femminile']:
        raise ValueError('Serie A1 calendar identity changed')
    tables = document.xpath('//table[contains(concat(" ",normalize-space(@class)," ")," risultati ")]')
    result, ids, rounds, teams = [], set(), {}, {}
    for table in tables:
        cells = table.xpath('./thead/tr/th')
        if len(cells) != 7:
            raise ValueError('Serie A1 calendar header changed')
        values = [' '.join(c.text_content().split()) for c in cells]
        if values[3].startswith('LVF A2 Fineco '):
            continue
        match = re.fullmatch(r'LVF A1 Fineco (\d{1,2})a Giornata - (Andata|Ritorno)', values[3])
        if not match:
            raise ValueError('Serie A1 competition or phase changed')
        number, leg = int(match[1]), match[2]
        if not 1 <= number <= 13 or not re.fullmatch(r'#\d+', values[0]):
            raise ValueError('Serie A1 round or game identity changed')
        try:
            local = datetime.datetime.strptime(values[1]+' '+values[2], '%d/%m/%Y %H:%M').replace(tzinfo=ROME)
        except ValueError as exc:
            raise ValueError('Serie A1 calendar kickoff missing or invalid') from exc
        if not datetime.date(2026, 7, 1) <= local.date() <= datetime.date(2027, 6, 30):
            raise ValueError('Serie A1 calendar edition changed')
        clubs = table.xpath('./tbody/tr/td/a')
        names = [' '.join(c.text_content().split()) for c in clubs]
        if len(clubs) != 2 or any(not re.fullmatch(r'/club/club/\d+/', c.get('href','')) for c in clubs):
            raise ValueError('Serie A1 club identities changed')
        links = cells[6].xpath('./a/@href')
        if len(links) != 1:
            raise ValueError('Serie A1 match link missing')
        parsed = urlparse(links[0])
        if parsed.scheme != 'https' or parsed.netloc != 'www.legavolleyfemminile.it' or not re.fullmatch(r'/match-center/\d+/', parsed.path):
            raise ValueError('Serie A1 match link identity changed')
        identity = (values[0], parsed.path)
        if any(ident[0] == identity[0] or ident[1] == identity[1] for ident in ids):
            raise ValueError('Serie A1 duplicate game identity')
        ids.add(identity)
        key = (leg, number)
        if any(name in teams.setdefault(key, set()) for name in names):
            raise ValueError('Serie A1 club appears twice in a round')
        teams[key].update(names)
        rounds[key] = rounds.get(key, 0) + 1
        row = event(source, number, names[0], names[1], local)
        row.update(id=f"{source['id']}-2026-27-{values[0][1:]}",
                   status_detail='Official 2026–27 published Serie A1 calendar fixture',
                   season_stage=f'REGULAR SEASON {leg.upper()} ROUND {number}',
                   source_endpoint=links[0], location=values[4] or None)
        result.append(row)
    if not result or any(count != 7 or len(teams[key]) != 14 for key, count in rounds.items()):
        raise ValueError('Serie A1 calendar round incomplete')
    sequence = sorted(number + (13 if leg == 'Ritorno' else 0) for leg, number in rounds)
    if sequence != list(range(sequence[0], sequence[-1] + 1)):
        raise ValueError('Serie A1 calendar has a missing round')
    if end > max(datetime.datetime.fromisoformat(e['start_time'].replace('Z','+00:00')).astimezone(ROME).date() for e in result):
        raise ValueError('Serie A1 calendar publication horizon ended')
    return result
