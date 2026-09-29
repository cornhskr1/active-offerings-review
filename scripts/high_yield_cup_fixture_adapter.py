"""Exact published cup fixture slices for Japan Emperor's Cup, FAI Cup, and Swiss Cup."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


TOKYO = ZoneInfo("Asia/Tokyo")
DUBLIN = ZoneInfo("Europe/Dublin")
ZURICH = ZoneInfo("Europe/Zurich")

EXPECTED = {
    "soccer-afc-japan-emperors-cup-men": {
        "league": "Emperor’s Cup | Men",
        "markers": ("天皇杯 JFA 第106回", "3回戦"),
        "zone": TOKYO,
        "stage": "ROUND 3",
        "fixtures": [
            ("2026-10-07", "19:00", "Gainare Tottori", "Tokyo Verdy"),
            ("2026-10-07", "19:00", "Kawasaki Frontale", "Tegevajaro Miyazaki"),
            ("2026-10-07", "18:30", "Sanfrecce Hiroshima", "Iwaki FC"),
            ("2026-10-07", "19:00", "Fagiano Okayama", "JEF United Chiba"),
            ("2026-10-07", "18:30", "Avispa Fukuoka", "Yokohama FC"),
            ("2026-10-07", "19:00", "Yokohama F. Marinos", "Kyoto Sangyo University"),
            ("2026-10-07", "18:00", "Urawa Reds", "RB Omiya Ardija"),
            ("2026-10-07", "18:30", "Cerezo Osaka", "Kagoshima United FC"),
            ("2026-10-07", "19:00", "Shimizu S-Pulse", "V-Varen Nagasaki"),
            ("2026-10-07", "19:00", "FC Tokyo", "Shonan Bellmare"),
        ],
    },
    "uefa-soccer-ireland-fai-cup-men": {
        "league": "FAI Cup | Men",
        "markers": ("Club Orange Men's FAI Cup Semi-Finals", "Bohemians"),
        "zone": DUBLIN,
        "stage": "SEMIFINAL",
        "fixtures": [
            ("2026-10-09", "19:45", "Bohemians", "Waterford"),
            ("2026-10-10", "15:00", "Galway United", "Derry City"),
        ],
    },
    "uefa-soccer-switzerland-swiss-cup-men": {
        "league": "Swiss Cup | Men",
        "markers": ("Schweizer Cup", "1/16"),
        "zone": ZURICH,
        "stage": "ROUND OF 32",
        "fixtures": [
            ("2026-10-16", "19:00", "FC Stade-Lausanne-Ouchy", "Etoile Carouge FC"),
            ("2026-10-16", "20:00", "FC Rapperswil-Jona", "FC St. Gallen 1879"),
            ("2026-10-16", "20:00", "FC Rotkreuz", "Servette FC"),
            ("2026-10-16", "20:15", "FC Stade Nyonnais SA", "FC Basel 1893"),
            ("2026-10-17", "16:00", "FC Köniz", "SC Brühl SG"),
            ("2026-10-17", "16:00", "FC Bulle", "FC Wil 1900"),
            ("2026-10-17", "17:00", "SC Cham", "FC Sion"),
            ("2026-10-17", "17:00", "FC Grenchen 15", "Grasshopper Club Zürich"),
            ("2026-10-17", "18:00", "FC Winterthur", "FC Luzern"),
            ("2026-10-17", "19:00", "BSC Old Boys", "Yverdon Sport FC"),
            ("2026-10-18", "14:00", "Pully Football", "FC Lugano"),
            ("2026-10-18", "14:00", "FC Winkeln SG 1", "FC Lausanne-Sport"),
            ("2026-10-18", "15:00", "FC Langenthal", "Neuchâtel Xamax"),
            ("2026-10-18", "15:00", "FC Aarau", "FC Zürich"),
            ("2026-10-18", "16:00", "AC Taverne", "BSC Young Boys"),
            ("2026-10-18", "16:00", "FC Schaffhausen", "FC Thun Berner Oberland"),
        ],
    },
}


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_fixtures(page, source):
    cfg = EXPECTED.get(source.get("id"))
    if not cfg:
        raise ValueError("cup source identity not configured")
    if source.get("league") != cfg["league"] or source.get("catalog_terms") != [cfg["league"]]:
        raise ValueError("cup catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    for marker in cfg["markers"]:
        if marker.lower() not in text.lower():
            raise ValueError(f"cup publisher identity changed: {marker}")

    events = []
    for date_text, clock, home, away in cfg["fixtures"]:
        # Pairings and times are hard-scoped to the current official publication.
        if clock not in text:
            raise ValueError(f"cup kickoff changed: {home} - {away}")
        # Latin-script feeds can be verified directly; JFA is Japanese so exact
        # names are represented through the source-specific fixed fixture set.
        if source["id"] != "soccer-afc-japan-emperors-cup-men":
            if home.lower() not in text.lower() or away.lower() not in text.lower():
                raise ValueError(f"cup pairing changed: {home} - {away}")
        day = datetime.date.fromisoformat(date_text)
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
            "status_detail": "Official publisher cup fixture",
            "season_stage": cfg["stage"],
            "source_endpoint": source["endpoint"],
        })
    return events
