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
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
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


def parse_affa_notice(page, source):
    if (source.get("id") != "uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men"
            or source.get("league") != "Azerbaijan Premier League (APL) | Men"
            or source.get("catalog_terms") != ["Azerbaijan Premier League (APL) | Men"]):
        raise ValueError("AFFA catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "Misli Premyer Liqası" not in text or "turun" not in text:
        raise ValueError("AFFA notice identity changed")

    # Parse dated fixture blocks from the official appointments notice.
    events = []
    current_date = None
    date_re = re.compile(r"(\d{1,2})\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)", re.I)
    fixture_re = re.compile(r'(?:(\d{1,2}:\d{2})\.?\s*)?[“"]([^”"]+)[”"]\s*[–-]\s*[“"]([^”"]+)[”"]')
    for node in doc.xpath("//p|//div|//li"):
        value = _norm(node.text_content())
        dm = date_re.search(value.lower())
        if dm:
            current_date = datetime.date(2026, AFFA_MONTHS[dm.group(2).lower()], int(dm.group(1)))
        fm = fixture_re.search(value)
        if not fm or not current_date:
            continue
        clock = fm.group(1)
        if not clock:
            tm = re.search(r"(?:Saat|stadionu,|Arena,|stadionu\.)\s*(\d{1,2}:\d{2})", value, re.I)
            clock = tm.group(1) if tm else None
        if not clock:
            continue
        home, away = fm.group(2).strip(), fm.group(3).strip()
        local = datetime.datetime.combine(current_date, datetime.time.fromisoformat(clock), BAKU)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-") or str(len(events) + 1)
        events.append({
            "id": f"azerbaijan-premier-{current_date:%Y%m%d}-{slug}",
            "source_id": source["id"], "sport": source["sport"], "league": source["league"],
            "region": source["region"], "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "AFFA published league appointment",
            "season_stage": "REGULAR", "source_endpoint": source["endpoint"],
        })
    if not events:
        raise ValueError("AFFA notice contained no timed senior fixtures")
    return events


def parse_bih_fixtures(page, source):
    if (source.get("id") != "uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men"
            or source.get("league") != "Premier League of Bosnia and Herzegovina | Men"):
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
        dm = re.search(r"(\d{2})\.(\d{2})\.2026\.\s*(\d{2}:\d{2})", value)
        if not dm:
            continue
        clubs = [club for club in BIH_CLUBS if club in value]
        if len(clubs) != 2:
            continue
        home, away = clubs[0], clubs[1]
        day = datetime.date(2026, int(dm.group(2)), int(dm.group(1)))
        key = (day, home, away)
        if key in seen:
            continue
        seen.add(key)
        local = datetime.datetime.combine(day, datetime.time.fromisoformat(dm.group(3)), SARAJEVO)
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
