"""Exact 2026-27 Meridianbet 1. CFL round 10 fixtures from FSCG's official competition page."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


PODGORICA = ZoneInfo("Europe/Podgorica")
EXPECTED = [
    ("2026-10-10", "17:00", "Mornar", "Jezero", "SRC Topolica"),
    ("2026-10-10", "17:00", "Otrant-Olympic", "OFK Mladost Lob.bet", "Stadion Velika plaža"),
    ("2026-10-10", "17:00", "Bokelj sbbet", "Petrovac", "Stadion pod Vrmcem"),
    ("2026-10-10", "17:00", "Budućnost", "Sutjeska", "Gradski stadion"),
    ("2026-10-10", "17:00", "Arsenal", "Dečić", "Stadion FK Arsenal"),
]


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_round(page, source):
    if (source.get("id") != "uefa-soccer-montenegro-montenegrin-first-league-men"
            or source.get("league") != "Montenegrin First League | Men"
            or source.get("catalog_terms") != ["Montenegrin First League | Men"]):
        raise ValueError("Montenegro 1. CFL catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "Meridianbet 1. CFL" not in text or "2026/27" not in text or "10. kolo" not in text:
        raise ValueError("FSCG Meridianbet 1. CFL page identity changed")

    events = []
    for date_text, clock, home, away, venue in EXPECTED:
        marker = datetime.date.fromisoformat(date_text).strftime("%d.%m.%Y.") + clock
        pattern = re.compile(
            re.escape(marker) + r".{0,180}" + re.escape(home) + r".{0,90}" + re.escape(away),
            re.I,
        )
        if not pattern.search(text):
            raise ValueError(f"FSCG round 10 fixture changed: {home} - {away}")
        if venue not in text:
            raise ValueError(f"FSCG round 10 venue changed: {home} - {away}")

        date = datetime.date.fromisoformat(date_text)
        local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), PODGORICA)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"montenegro-cfl-r10-{date:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "FSCG published Meridianbet 1. CFL round 10",
            "season_stage": "ROUND 10",
            "location": venue,
            "source_endpoint": source["endpoint"],
        })
    if len(events) != 5:
        raise ValueError("FSCG round 10 publication incomplete")
    return events
