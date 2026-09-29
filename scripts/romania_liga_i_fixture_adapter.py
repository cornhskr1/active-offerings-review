"""Exact 2026-27 SuperLiga round 11 fixtures from LPF's official notice."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


BUCHAREST = ZoneInfo("Europe/Bucharest")
TITLE = "SUPERLIGA – Programul etapei a 11-a"
PUBLISHED = "Comunicat de presă | 17.09.2026"
EXPECTED = [
    ("2026-10-09", "18:00", "Corvinul Hunedoara", "FC Voluntari"),
    ("2026-10-09", "21:00", "Sepsi OSK Sf. Gheorghe", "Dinamo"),
    ("2026-10-10", "17:15", "FC Botoșani", "UTA Arad"),
    ("2026-10-10", "21:30", "FCSB", "Oțelul Galați"),
    ("2026-10-11", "18:00", "FK Csikszereda Miercurea Ciuc", "Universitatea Craiova"),
    ("2026-10-11", "21:00", "Farul Constanța", "Petrolul Ploiești"),
    ("2026-10-12", "18:00", "FC Argeș", "CFR 1907 Cluj"),
    ("2026-10-12", "21:00", "Universitatea Cluj", "FC Rapid"),
]


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_round(page, source):
    if (source.get("id") != "uefa-soccer-romania-liga-i-men"
            or source.get("catalog_terms") != ["Liga I | Men"]
            or source.get("league") != "Liga I | Men"):
        raise ValueError("Romania Liga I catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if TITLE not in text or PUBLISHED not in text:
        raise ValueError("LPF round 11 notice identity changed")
    if "PRIMA Sport" not in text or "DIGI Sport" not in text:
        raise ValueError("LPF round 11 notice body changed")

    events = []
    for date_text, clock, home, away in EXPECTED:
        romanian_clock = clock.replace(":", ".")
        phrase = _norm(f"Ora {romanian_clock} {home} - {away}")
        if phrase not in text:
            raise ValueError(f"LPF round 11 fixture changed: {home} - {away}")
        date = datetime.date.fromisoformat(date_text)
        local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), BUCHAREST)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"romania-liga-i-r11-{date:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "LPF published SuperLiga round 11",
            "season_stage": "REGULAR",
            "source_endpoint": source["endpoint"],
        })
    if len(events) != 8:
        raise ValueError("LPF round 11 is incomplete")
    return events
