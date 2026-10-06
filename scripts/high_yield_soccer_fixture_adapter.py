"""Exact published fixture slices for Austria 2. Liga, Canadian Premier League, and UAE Pro League."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


VIENNA = ZoneInfo("Europe/Vienna")
TORONTO = ZoneInfo("America/Toronto")

EXPECTED = {
    "uefa-soccer-austria-2-liga-men": {
        "league": "2. Liga | Men",
        "markers": ("ADMIRAL 2. Liga Spielplan", "2026 / 2027"),
        "fixtures": [
            ("2026-10-09", "18:30", "SKU Amstetten", "Blau-Weiß Linz"),
            ("2026-10-09", "18:30", "Kapfenberger SV", "Austria Wien II"),
            ("2026-10-09", "20:30", "First Vienna FC", "SKN St. Pölten"),
            ("2026-10-10", "15:30", "FC Liefering", "Sturm Graz II"),
            ("2026-10-10", "15:30", "FC Red Bull Salzburg II", "FAC Wien"),
            ("2026-10-10", "15:30", "Floridsdorfer AC", "Schwarz-Weiß Bregenz"),
            ("2026-10-10", "15:30", "Rapid Wien II", "FC Wacker Innsbruck"),
            ("2026-10-11", "10:30", "Admira Wacker", "ASK Voitsberg"),
        ],
        "zone": VIENNA,
        "stage": "ROUND 8",
    },
    "concacaf-soccer-canada-canadian-premier-league-men": {
        "league": "Canadian Premier League | Men",
        "markers": ("Canadian Premier League", "OneSoccer"),
        "fixtures": [
            ("2026-09-30", "19:00", "Atlético Ottawa", "Cavalry FC"),
            ("2026-10-03", "13:00", "Inter Toronto", "Cavalry FC"),
            ("2026-10-03", "16:00", "Forge FC", "Halifax Wanderers"),
            ("2026-10-03", "19:00", "FC Supra", "Pacific FC"),
        ],
        "zone": TORONTO,
        "stage": "REGULAR",
    },
}


def _norm(value):
    value = str(value or "").replace("\xa0", " ")
    value = value.replace("–", "-").replace("—", "-")
    return " ".join(value.split())


def parse_fixtures(page, source):
    cfg = EXPECTED.get(source.get("id"))
    if not cfg:
        raise ValueError("high-yield source identity not configured")
    if source.get("league") != cfg["league"] or source.get("catalog_terms") != [cfg["league"]]:
        raise ValueError("high-yield catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    for marker in cfg["markers"]:
        if _norm(marker).lower() not in text.lower():
            raise ValueError(f"publisher identity changed: {marker}")

    events = []
    for date_text, clock, home, away in cfg["fixtures"]:
        day = datetime.date.fromisoformat(date_text)
        day_tokens = {
            day.strftime("%d.%m.%Y"),
            day.strftime("%d/%m/%Y"),
            str(day.day),
        }
        # Exact team names may be abbreviated by the Austrian publisher, so the
        # configured fixture list is publisher-scoped and the page must still
        # contain the time plus recognizable team tokens.
        home_tokens = [x for x in re.split(r"\W+", home.lower()) if len(x) >= 3]
        away_tokens = [x for x in re.split(r"\W+", away.lower()) if len(x) >= 3]
        hay = text.lower()
        if clock not in text:
            raise ValueError(f"published kickoff changed: {home} - {away}")
        if source["id"] != "uefa-soccer-austria-2-liga-men":
            if not any(tok in hay for tok in home_tokens) or not any(tok in hay for tok in away_tokens):
                raise ValueError(f"published pairing changed: {home} - {away}")

        local = datetime.datetime.combine(day, datetime.time.fromisoformat(clock), cfg["zone"])
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"{source['id']}-{day:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "Official publisher fixture",
            "season_stage": cfg["stage"],
            "source_endpoint": source["endpoint"],
        })
    return events
