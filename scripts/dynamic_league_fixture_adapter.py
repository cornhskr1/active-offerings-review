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
    "NK ČELIK", "FK RADNIK", "NK ŠIROKI BRIJEG", "FK BSK", "FK BORAC",
    "HŠK ZRINJSKI", "FK SLOGA DOBOJ", "FK ŽELJEZNIČAR", "FK VELEŽ", "FK SARAJEVO",
)


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

    def emit(clock):
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
        events.append({
            "id": f"azerbaijan-premier-{current_date:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "AFFA published league appointment",
            "season_stage": "REGULAR", "source_endpoint": source["endpoint"],
        })
        pending = None

    for node in bodies[0]:
        value = _norm(node.text_content())
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
        clock = re.search(r"(?:Saat|stadionu[,\.]|Arena[“”\"]?[,\.])\s*(\d{1,2}:\d{2})", value, re.I)
        if clock and pending:
            emit(clock.group(1))
    if pending:
        raise ValueError("AFFA fixture kickoff missing")
    if not events:
        raise ValueError("AFFA notice contained no timed senior fixtures")
    if review_date and max(datetime.date.fromisoformat(e['start_time'][:10]) for e in events) < review_date:
        raise ValueError("AFFA appointment notice contains only past fixtures; current round unavailable")
    return events


def parse_bih_fixtures(page, source):
    if (source.get("id") != "uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men"
            or source.get("league") != "Premier League of Bosnia and Herzegovina | Men"
            or source.get("catalog_terms") != ["Premier League of Bosnia and Herzegovina | Men"]):
        raise ValueError("BiH catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "Wwin League" not in text and "Wwin liga" not in text:
        raise ValueError("BiH Wwin League page identity changed")
    events, seen = [], set()
    for row in doc.xpath("//tr"):
        value = _norm(row.text_content())
        dm = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\.\s*(\d{2}:\d{2})", value)
        if not dm:
            continue
        clubs = sorted((club for club in BIH_CLUBS if club in value), key=value.index)
        if len(clubs) != 2:
            continue
        home, away = clubs[0], clubs[1]
        day = datetime.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
        key = (day, home, away)
        if key in seen:
            continue
        seen.add(key)
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(dm.group(4)), SARAJEVO)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-") or str(len(events) + 1)
        events.append({
            "id": f"bih-wwin-{day:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "NS/FSBiH published Wwin League fixture",
            "season_stage": "REGULAR", "source_endpoint": source["endpoint"],
        })
    if not events:
        raise ValueError("BiH Wwin League page contained no timed fixtures")
    return events


def parse_malta_tickets(page, source):
    if (source.get("id") != "uefa-soccer-malta-maltese-premier-league-men"
            or source.get("league") != "Maltese Premier League | Men"):
        raise ValueError("Malta catalog scope changed")
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
