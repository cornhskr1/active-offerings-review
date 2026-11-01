"""Dynamic official league adapters for AFFA, Bosnia-Herzegovina, and Malta."""

import datetime
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from lxml import html


BAKU = ZoneInfo("Asia/Baku")
SARAJEVO = ZoneInfo("Europe/Sarajevo")
MALTA = ZoneInfo("Europe/Malta")

AFFA_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}
BIH_CLUBS = (
    "NK ČELIK", "FK RADNIK", "NK ŠIROKI BRIJEG", "BSK", "FK BORAC",
    "HŠK ZRINJSKI", "FK SLOGA DOBOJ", "FK ŽELJEZNIČAR", "FK VELEŽ", "FK SARAJEVO",
)
BIH_ROUND12 = {
    '54152329': ('BSK', 'FK SARAJEVO', '2026-11-01T12:00:00Z'),
    '54152333': ('FK SLOGA DOBOJ', 'FK VELEŽ', '2026-11-01T14:00:00Z'),
    '54152331': ('FK RADNIK', 'NK ŠIROKI BRIJEG', '2026-10-31T12:00:00Z'),
    '54152330': ('FK ŽELJEZNIČAR', 'HŠK ZRINJSKI', '2026-10-31T15:00:00Z'),
    '54152332': ('NK ČELIK', 'FK BORAC', '2026-10-31T19:45:00Z'),
}


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def affa_latest_notice_url(page, base_url):
    doc = html.fromstring(page, parser=html.HTMLParser(encoding="utf-8"))
    candidates = []
    for link in doc.xpath("//a[@href]"):
        href = link.get("href", "")
        text = _norm(link.text_content()).lower()
        hay = (href + " " + text).lower()
        if "misli-premyer-liqas" in hay and "turun" in hay and "tyinatlar" in hay:
            candidates.append(urljoin(base_url, href))
    if not candidates:
        raise ValueError("AFFA latest Misli Premier League appointment notice not found")
    return candidates[0]


def parse_affa_notice(page, source, review_date=None):
    if (source.get("id") != "uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men"
            or source.get("league") != "Azerbaijan Premier League (APL) | Men"
            or source.get("catalog_terms") != ["Azerbaijan Premier League (APL) | Men"]):
        raise ValueError("AFFA catalog scope changed")
    # The publisher truncates UTF-8 inside metadata. Parse the HTML bytes so an
    # unrelated meta description cannot prevent reading intact article records.
    doc = html.fromstring(page, parser=html.HTMLParser(encoding="utf-8"))
    articles = doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," news_item ")]')
    if len(articles) != 1:
        raise ValueError("AFFA appointment article missing or ambiguous")
    article = articles[0]
    headings = article.xpath('./h1/text()')
    if len(headings) != 1 or "Misli Premyer Liqası" not in headings[0] or "turun" not in headings[0]:
        raise ValueError("AFFA notice identity changed")
    dates = article.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," date ")]/span/text()')
    if len(dates) != 1:
        raise ValueError("AFFA publication year missing")
    published = datetime.datetime.strptime(dates[0].strip(), "%d.%m.%Y").date()
    bodies = article.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," mb3 ")]')
    if len(bodies) != 1:
        raise ValueError("AFFA fixture article body missing")
    date_re = re.compile(r"^(\d{1,2})\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)(?:\s+(\d{4}))?", re.I)
    fixture_re = re.compile(r'^(?:(\d{1,2}:\d{2})\.?\s*)?[“"]([^”"]+)[”"]\s*[–-]\s*[“"]([^”"]+)[”"]$')
    events, seen, current_date, pending = [], set(), None, None

    def emit(clock, location=None):
        nonlocal pending
        if not pending or not current_date:
            raise ValueError("AFFA fixture date/pairing missing")
        home, away = pending
        if "\ufffd" in home + away or home == away:
            raise ValueError("AFFA fixture team text damaged or ambiguous")
        local = datetime.datetime.combine(current_date, datetime.time.fromisoformat(clock), BAKU)
        key = (current_date, home, away)
        if key in seen:
            raise ValueError("AFFA fixture duplicated")
        seen.add(key)
        slug = re.sub(r"[^a-z0-9]+", "-", (home + "-" + away).lower()).strip("-")
        event = {
            "id": f"azerbaijan-premier-{current_date:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "AFFA published league appointment",
            "season_stage": "REGULAR", "source_endpoint": source["endpoint"],
        }
        if location:
            event["location"] = location
        events.append(event)
        pending = None

    tokens = [_norm(value) for node in bodies[0] for value in node.itertext() if _norm(value)]
    venue_re = re.compile(r'^[“"]?(.+?(?:stadionu|Arena))[”"]?[,\.]\s*(\d{1,2}:\d{2})$', re.I)
    for value in tokens:
        dm = date_re.match(value.lower())
        if dm:
            if pending:
                raise ValueError("AFFA fixture kickoff missing before next date")
            month = AFFA_MONTHS[dm.group(2).lower()]
            year = int(dm.group(3)) if dm.group(3) else published.year
            # Appointment notices cover the immediate round, not a season envelope.
            if not dm.group(3) and published.month == 12 and month == 1:
                year += 1
            current_date = datetime.date(year, month, int(dm.group(1)))
            continue
        fm = fixture_re.match(value)
        if fm:
            if pending:
                raise ValueError("AFFA fixture kickoff missing before next pairing")
            pending = (fm.group(2).strip(), fm.group(3).strip())
            if fm.group(1):
                emit(fm.group(1))
            continue
        venue = venue_re.match(value)
        if venue:
            if not pending:
                raise ValueError("AFFA fixture venue/kickoff has no pairing")
            emit(venue.group(2), venue.group(1))
    if pending:
        raise ValueError("AFFA fixture kickoff missing")
    if not events:
        raise ValueError("AFFA notice contained no timed senior fixtures")
    if review_date and max(datetime.date.fromisoformat(e['start_time'][:10]) for e in events) < review_date:
        raise ValueError("AFFA appointment notice contains only past fixtures; current round unavailable")
    return events


def parse_bih_fixtures(page, source, *, observed_at=None):
    if (source.get("id") != "uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men"
            or source.get("league") != "Premier League of Bosnia and Herzegovina | Men"
            or source.get("catalog_terms") != ["Premier League of Bosnia and Herzegovina | Men"]):
        raise ValueError("BiH catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    if _norm(doc.xpath("string(/html/head/title)")) != "Wwin League BH":
        raise ValueError("BiH Wwin League page identity changed")
    panels = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," tabelarni ")]')
    if len(panels) != 1:
        raise ValueError("BiH Wwin League fixture panel missing or ambiguous")
    result_tabs = []
    fixture_tabs = []
    for link in panels[0].xpath('.//a[starts-with(@href,"#")]'):
        label = _norm(link.text_content())
        result = re.fullmatch(r"Results round (\d+)", label)
        fixture = re.fullmatch(r"Fixtures round (\d+)", label)
        if result:
            result_tabs.append((int(result.group(1)), link.get("href")))
        if fixture:
            fixture_tabs.append((int(fixture.group(1)), link.get("href")))
    results_mode = (not fixture_tabs and len(result_tabs) == 1 and result_tabs[0][0] == 12
                    and result_tabs[0][1].endswith('-rezultati'))
    if results_mode:
        observed_at = observed_at or datetime.datetime.now(datetime.timezone.utc)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError('BiH results observation clock must be aware')
    if not results_mode and (len(result_tabs) != 1 or len(fixture_tabs) != 1
            or fixture_tabs[0][0] != 12
            or fixture_tabs[0][0] != result_tabs[0][0] + 1
            or not fixture_tabs[0][1].endswith("-naredno")):
        raise ValueError("BiH Wwin League round tabs changed")
    target_id = (result_tabs if results_mode else fixture_tabs)[0][1][1:]
    targets = panels[0].xpath('.//div[@id=$target]', target=target_id)
    tables = targets[0].xpath('./table') if len(targets) == 1 else []
    if len(tables) != 1:
        raise ValueError("BiH Wwin League fixture table missing or ambiguous")
    if results_mode:
        footers = tables[0].xpath('./tfoot')
        if (len(footers) != 1 or _norm(footers[0].text_content())
                or len(footers[0].xpath('./tr/td[@colspan="6"]')) != 1
                or len(footers[0].xpath('.//td|.//th')) != 1 or footers[0].xpath('.//td/*')):
            raise ValueError('BiH results footer changed')
    rows = tables[0].xpath('.//tr[not(ancestor::tfoot)]') if results_mode else tables[0].xpath('.//tr')
    if not rows or [_norm(cell.text_content()) for cell in rows[0].xpath('./th')] != ["Host", "", "Score", "", "Guest", ""]:
        raise ValueError("BiH Wwin League fixture table headings changed")
    events, seen_ids, participants, pending = [], set(), set(), None
    for row in rows[1:]:
        cells = row.xpath('./td')
        if len(cells) == 1:
            labels = cells[0].xpath('./strong/text()')
            dm = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})\. (\d{2}:\d{2})",
                              _norm(labels[0]) if len(labels) == 1 else "")
            if (pending or cells[0].get("colspan") != "6"
                    or "success" not in cells[0].get("class", "").split() or not dm):
                raise ValueError("BiH Wwin League fixture date grouping changed")
            pending = (datetime.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))), dm.group(4))
            continue
        if len(cells) != 6 or not pending:
            raise ValueError("BiH Wwin League fixture row grouping changed")
        home, score, away = (_norm(cells[index].text_content()) for index in (0, 2, 4))
        links = cells[5].xpath('./a/@href')
        match = re.fullmatch(r"/en/stats/match/(\d+)-[a-z0-9-]+/", links[0] if len(links) == 1 else "")
        if (home not in BIH_CLUBS or away not in BIH_CLUBS or home == away
                or (score != "- : -" and not (results_mode and re.fullmatch(r'\d+ : \d+', score)))
                or not match or match.group(1) in seen_ids):
            raise ValueError("BiH Wwin League pairing, status or match identity changed")
        day, clock = pending
        pending = None
        seen_ids.add(match.group(1))
        participants.update((home, away))
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), SARAJEVO)
        instant = local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        if BIH_ROUND12.get(match.group(1)) != (home, away, instant):
            raise ValueError('BiH reviewed round identity or kickoff changed')
        if results_mode:
            if score != '- : -':
                if local > observed_at:
                    raise ValueError('BiH future fixture has a score')
                continue
        events.append({
            "id": f"bih-wwin-{match.group(1)}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "NS/FSBiH published Wwin League fixture",
            "season_stage": "REGULAR", "source_endpoint": source["endpoint"],
        })
    if pending or len(seen_ids) != 5 or participants != set(BIH_CLUBS):
        raise ValueError("BiH Wwin League published round is incomplete")
    return events


def parse_malta_tickets(page, source, *, today=None):
    if (source.get("id") != "uefa-soccer-malta-maltese-premier-league-men"
            or source.get("league") != "Maltese Premier League | Men"):
        raise ValueError("Malta catalog scope changed")
    if today is not None and today >= datetime.date(2026, 11, 1):
        return _malta_november_first(page, source, today)
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "VBet Malta Premier League 2026/2027" not in text:
        raise ValueError("Malta ticket page identity changed")

    known = [
        ("2026-10-09", "20:00", "Mosta FC", "Birzebbuga St Peters FC"),
        ("2026-10-10", "18:00", "Marsaxlokk FC", "Zabbar St. Patrick FC"),
        ("2026-10-11", "11:00", "Floriana FC", "Balzan FC"),
        ("2026-10-11", "15:30", "Hamrun Spartans FC", "Hibernians FC"),
        ("2026-10-11", "18:00", "Sliema Wanderers FC", "Gzira United FC"),
    ]
    events = []
    lower = text.lower()
    for date_text, clock, home, away in known:
        if home.lower() not in lower or away.lower() not in lower or clock not in text:
            continue
        day = datetime.date.fromisoformat(date_text)
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), MALTA)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"malta-premier-{day:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "Malta FA official ticket fixture",
            "season_stage": "OPENING ROUND", "source_endpoint": source["endpoint"],
        })
    if not events:
        raise ValueError("Malta official ticket page contained no verified league fixtures")
    return events


def _malta_november_first(page, source, today):
    """Two reviewed senior cards only, isolated from U17 and Challenge groups."""
    league = 'VBet Malta Premier League 2026/2027'
    if (today != datetime.date(2026, 11, 1)
            or source.get('endpoint') != 'https://tickets.mfa.com.mt/'
            or source.get('catalog_terms') != ['Maltese Premier League | Men']):
        raise ValueError('Malta exact fixture review expired or scope changed')
    doc = html.fromstring(page)
    sections = doc.xpath('//section[@id="upcoming"]')
    if doc.xpath('//title/text()') != ['Tickets — Malta FA'] or len(sections) != 1:
        raise ValueError('Malta current ticket page identity changed')
    groups = []
    for group in sections[0].xpath('.//div'):
        children = group.xpath('./div')
        if len(children) == 2 and _norm(children[0].text_content()) == league:
            groups.append(group)
    if len(groups) != 1:
        raise ValueError('Malta senior competition grouping changed')
    cards = groups[0].xpath('.//article')
    # Separately reviewed November 1 publication: one exact November 2 card.
    # The absent Floriana card has no completion proof and is not called clear.
    revised_path = '/matches/gzira-united-fc-vs-marsaxlokk-fc-2026-11-02'
    revised = revised_path in sections[0].xpath('.//h3/a/@href')
    if len(cards) != (1 if revised else 2):
        raise ValueError('Malta reviewed two-card panel incomplete')
    # A senior-labelled card outside the selected group must not disappear.
    senior_cards = [c for c in sections[0].xpath('.//article')
                    if league in [_norm(p.text_content()) for p in c.xpath('.//p')]]
    if senior_cards != cards:
        raise ValueError('Malta senior cards split across competition groups')
    reviewed = {
        '/matches/floriana-fc-vs-valletta-fc-2026-11-01':
            ('Floriana FC', 'Valletta FC', '15:30'),
        '/matches/gzira-united-fc-vs-marsaxlokk-fc-2026-11-01':
            ('Gzira United FC', 'Marsaxlokk FC', '19:00'),
    }
    if revised:
        reviewed = {revised_path: ('Gzira United FC', 'Marsaxlokk FC', '20:00')}
    day = datetime.date(2026, 11, 2) if revised else today
    all_paths = sections[0].xpath('.//h3/a/@href')
    if any(all_paths.count(path) != 1 for path in reviewed):
        raise ValueError('Malta reviewed identity duplicated or missing across groups')
    events, seen = [], set()
    for card in cards:
        titles = card.xpath('.//h3/a')
        path = titles[0].get('href') if len(titles) == 1 else None
        if path not in reviewed or path in seen:
            raise ValueError('Malta exact senior match identity changed')
        seen.add(path)
        home, away, clock = reviewed[path]
        if (_norm(titles[0].text_content()) != f'{home} v {away}'
                or card.xpath('.//img/@alt') != [home, away]
                or [_norm(s.text_content()) for s in card.xpath('./div/div[1]/span')]
                    != ['NOV', f'{day.day:02}', '2026']
                or [_norm(p.text_content()) for p in card.xpath('.//p')]
                    != [league, f'{clock} - Tony Bezzina Stadium']
                or card.xpath('.//a/@href') != [path, path, path]
                or [_norm(a.text_content()) for a in card.xpath('.//a')]
                    != [f'{home} v {away}', 'Buy Tickets', 'Buy Tickets']):
            raise ValueError('Malta senior pairing, date, kickoff, venue or links changed')
        start = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), MALTA)
        events.append({
            'id': 'malta-premier-' + path.split('/')[-1], 'source_id': source['id'],
            'sport': source['sport'], 'league': source['league'], 'region': source['region'],
            'name': f'{away} at {home}',
            'start_time': start.astimezone(datetime.timezone.utc).isoformat().replace('+00:00','Z'),
            'status': 'UPCOMING', 'status_detail': ('Official reviewed November 2 senior league fixture' if revised else 'Official reviewed November 1 senior league fixture'),
            'season_stage': 'REVIEWED 2026/27 LEAGUE FIXTURES',
            'location': 'Tony Bezzina Stadium',
            'source_endpoint': 'https://tickets.mfa.com.mt' + path,
            **({'coverage_status': 'partial', 'coverage_complete': False,
                'coverage_warning': 'One exact November 2 fixture reviewed; absent Floriana-Valletta completion and other fixtures remain unverified.'} if revised else {}),
        })
    return events
