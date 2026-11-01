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


def parse_serie_a1(page, source, today, end, *, completed_pages=None, observed_at=None):
    if source.get("catalog_terms") != ["Italian Volleyball Federation (FIPAV)", "Serie A1 | Women"]:
        raise ValueError("Serie A1 catalog scope changed")
    if source.get('endpoint') == 'https://www.legavolleyfemminile.it/calendario/':
        return parse_serie_a1_calendar(page, source, today, end,
                                       completed_pages=completed_pages, observed_at=observed_at)
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


# October 31's two completed games disappear from the current calendar. Only
# this reviewed round can combine its five remaining rows with exact results.
_A1_BASE = 'https://www.legavolleyfemminile.it'
_A1_ROUND_SIX = {
    '3040': ('748021', '31/10/2026', '18:00', 'Fontescodella - Macerata',
             '710945', 'Cbf Balducci Hr Macerata', '710947', 'Granda Volley Cuneo'),
    '3036': ('748017', '31/10/2026', '20:30', 'Palafenera - Chieri',
             '710954', 'Reale Mutua Fenera Chieri', '710946', 'Laica Cioccolato Uyba'),
    '3042': ('748023', '01/11/2026', '16:00', 'Pala BigMat - Firenze',
             '710949', 'Il Bisonte Firenze', '710953', 'Prosecco Doc A.Carraro Imoco Conegliano'),
    '3037': ('748018', '01/11/2026', '17:00', 'Opiquad Arena - Monza',
             '710951', 'Numia Vero Volley Milano', '710952', 'Omag Consolini Volley 1907'),
    '3038': ('748019', '01/11/2026', '17:00', 'Pala Megabox - Pesaro',
             '710950', 'Megabox Ond. Savio Vallefoglia', '710971', 'Cda Volley Talmassons Fvg'),
    '3039': ('748020', '01/11/2026', '18:00', 'Choruslife Arena - Bergamo',
             '710944', 'ChorusLife Volley Bergamo', '710955', 'Savino Del Bene Scandicci'),
    '3041': ('748022', '02/11/2026', '20:40', 'Pala Igor - Novara',
             '710948', 'Igor Gorgonzola Novara', '710972', 'Banca Valsabbina Millenium Brescia'),
}
_A1_COMPLETED = {
    '3040': ('Fontescodella', ['3', '1'], '3 1 25-17, 19-25, 25-23, 25-15'),
    '3036': ('Palafenera', ['3', '0'], '3 0 25-20, 25-22, 25-22'),
}


def _a1_text(node):
    return ' '.join(node.text_content().split())


def serie_a1_completed_round_urls(page, source, today):
    """Only request the two pinned results after proving the remaining panel."""
    if (source.get('endpoint') != _A1_BASE + '/calendario/'
            or source.get('season_code') != '2026-2027'
            or source.get('catalog_terms') != ['Italian Volleyball Federation (FIPAV)', 'Serie A1 | Women']
            or not datetime.date(2026, 10, 31) <= today <= datetime.date(2026, 11, 2)):
        return []
    document = html.fromstring(page)
    if document.xpath('//title/text()') != ['Calendario – Lega Pallavolo Serie A Femminile']:
        return []
    selected = []
    for table in document.xpath('//table[contains(concat(" ",normalize-space(@class)," ")," risultati ")]'):
        cells = table.xpath('./thead/tr/th')
        if len(cells) != 7 or _a1_text(cells[3]) != 'LVF A1 Fineco 6a Giornata - Andata':
            continue
        values = [_a1_text(c) for c in cells]
        game = values[0].removeprefix('#')
        if game not in _A1_ROUND_SIX or game in _A1_COMPLETED or game in selected:
            return []
        mid, day, clock, venue, home_id, home, away_id, away = _A1_ROUND_SIX[game]
        clubs = table.xpath('./tbody/tr/td/a')
        if (values[0] != '#' + game or values[1:3] != [day, clock] or values[4] != venue
                or [(c.get('href'), _a1_text(c)) for c in clubs] != [
                    (f'/club/club/{home_id}/', home), (f'/club/club/{away_id}/', away)]
                or cells[6].xpath('./a/@href') != [f'{_A1_BASE}/match-center/{mid}/']):
            return []
        selected.append(game)
    if set(selected) != set(_A1_ROUND_SIX) - set(_A1_COMPLETED):
        return []
    return [f'{_A1_BASE}/match-center/{_A1_ROUND_SIX[g][0]}/' for g in _A1_COMPLETED]


def _validate_a1_completed(pages, observed_at):
    if observed_at is None or observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError('Serie A1 completed results require an aware observation clock')
    expected_urls = {f'{_A1_BASE}/match-center/{_A1_ROUND_SIX[g][0]}/' for g in _A1_COMPLETED}
    if set(pages) != expected_urls:
        raise ValueError('Serie A1 complete exact result evidence missing')
    for game, (venue, score, score_text) in _A1_COMPLETED.items():
        mid, day, clock, _, home_id, home, away_id, away = _A1_ROUND_SIX[game]
        local = datetime.datetime.strptime(day + ' ' + clock, '%d/%m/%Y %H:%M').replace(tzinfo=ROME)
        if local >= observed_at:
            raise ValueError('Serie A1 completed result has a future kickoff')
        url = f'{_A1_BASE}/match-center/{mid}/'
        document = html.fromstring(pages[url])
        if (document.xpath('//title/text()') != ['Play by Play - Lega Pallavolo Serie A Femminile']
                or [(a.get('href'), _a1_text(a)) for a in document.xpath('//a[contains(concat(" ",normalize-space(@class)," ")," selez ")]')] != [(url, 'Match')]):
            raise ValueError('Serie A1 completed result identity changed')
        panels = document.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," tabellone-alto-match-center ")]')
        if len(panels) != 1:
            raise ValueError('Serie A1 completed result panel changed')
        panel = panels[0]
        live = panel.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," live ")]/div')
        teams = panel.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," pre-roster ")]')
        if len(live) != 3 or [_a1_text(c) for c in live[:2]] != [day + ' ' + clock, venue] or len(teams) != 1:
            raise ValueError('Serie A1 completed result kickoff or venue changed')
        home_links = teams[0].xpath('./div[contains(concat(" ",normalize-space(@class)," ")," casa ")]/a')
        away_links = teams[0].xpath('./div[contains(concat(" ",normalize-space(@class)," ")," fuori ")]/a')
        if ([(a.get('href'), _a1_text(a)) for a in home_links + away_links] != [
                (f'/club/club/{home_id}/', home), (f'/club/club/{away_id}/', away)]
                or len(teams[0].xpath('./div')) != 3):
            raise ValueError('Serie A1 completed result pairing changed')
        scores = teams[0].xpath('./div[contains(concat(" ",normalize-space(@class)," ")," count ")]')
        if (len(scores) != 1 or scores[0].xpath('./span/text()') != score
                or ' '.join(' '.join(scores[0].itertext()).split()) != score_text):
            raise ValueError('Serie A1 completed result score changed')


def parse_serie_a1_calendar(page, source, today, end, *, completed_pages=None, observed_at=None):
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
    if completed_pages:
        urls = serie_a1_completed_round_urls(page, source, today)
        if not urls or set(completed_pages) != set(urls):
            raise ValueError('Serie A1 completed evidence outside reviewed round')
        _validate_a1_completed(completed_pages, observed_at)
        key = ('Andata', 6)
        if rounds.get(key) != 5 or len(teams[key]) != 10:
            raise ValueError('Serie A1 reviewed remaining round incomplete')
        for game in _A1_COMPLETED:
            mid, _, _, _, _, home, _, away = _A1_ROUND_SIX[game]
            if any(name in teams[key] for name in (home, away)) or any(
                    ident[0] == '#' + game or ident[1] == f'/match-center/{mid}/' for ident in ids):
                raise ValueError('Serie A1 completed result duplicates calendar identity')
            teams[key].update((home, away))
            rounds[key] += 1
    if not result or any(count != 7 or len(teams[key]) != 14 for key, count in rounds.items()):
        raise ValueError('Serie A1 calendar round incomplete')
    sequence = sorted(number + (13 if leg == 'Ritorno' else 0) for leg, number in rounds)
    if sequence != list(range(sequence[0], sequence[-1] + 1)):
        raise ValueError('Serie A1 calendar has a missing round')
    if end > max(datetime.datetime.fromisoformat(e['start_time'].replace('Z','+00:00')).astimezone(ROME).date() for e in result):
        raise ValueError('Serie A1 calendar publication horizon ended')
    return result
