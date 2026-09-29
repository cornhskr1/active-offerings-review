"""Scoped 2026-27 Allianz Cup quarterfinals from Liga Portugal's official competition page."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


LISBON = ZoneInfo("Europe/Lisbon")
EXPECTED = [
    ("2026-10-27", "20:15", "Sporting CP", "Marítimo M.", "SCP", "CSM"),
    ("2026-10-28", "20:30", "FC Porto", "Académico", "FCP", "AVFC"),
    ("2026-10-29", "18:45", "SC Braga", "FC Famalicão", "SCB", "FCF"),
    ("2026-10-29", "20:45", "SL Benfica", "Gil Vicente FC", "SLB", "GVFC"),
]


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_quarterfinals(page, source):
    if (source.get("id") != "uefa-soccer-portugal-ta-a-da-liga-men"
            or source.get("league") != "Taça da Liga | Men"
            or source.get("catalog_terms") != ["Taça da Liga | Men"]):
        raise ValueError("Allianz Cup catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if "Allianz Cup" not in text or "2026-2027" not in text or "Quartos-de-Final" not in text:
        raise ValueError("Allianz Cup competition page identity changed")

    events = []
    for date_text, clock, home, away, home_code, away_code in EXPECTED:
        if home_code not in text or away_code not in text or clock.replace(":", "h") not in text and clock not in text:
            raise ValueError(f"Allianz Cup quarterfinal changed: {home} - {away}")
        date = datetime.date.fromisoformat(date_text)
        local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), LISBON)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"portugal-allianz-cup-qf-{date:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "Liga Portugal published Allianz Cup quarterfinal",
            "season_stage": "QUARTERFINAL",
            "source_endpoint": source["endpoint"],
        })
    if len(events) != 4:
        raise ValueError("Allianz Cup quarterfinal publication incomplete")
    return events
