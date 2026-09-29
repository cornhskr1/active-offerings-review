"""Exact 2027 men's Supercopa semifinal fixtures from RFEF's official Istanbul schedule."""

import datetime
import re
from zoneinfo import ZoneInfo

from lxml import html


MADRID = ZoneInfo("Europe/Madrid")
EXPECTED = [
    ("2027-02-02", "20:00", "FC Barcelona", "Club Atlético de Madrid",
     "Chobani Stadium Fenerbahçe Şükrü Saracoğlu Sports Complex"),
    ("2027-02-03", "20:00", "Real Sociedad de Fútbol", "Real Madrid CF",
     "Tüpraş Stadium"),
]


def _norm(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_semifinals(page, source):
    if (source.get("id") != "uefa-soccer-spain-supercopa-de-espa-a-men"
            or source.get("league") != "Supercopa de España | Men"
            or source.get("catalog_terms") != ["Supercopa de España | Men"]):
        raise ValueError("Spain men's Supercopa catalog scope changed")
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    doc = html.fromstring(page)
    text = _norm(doc.text_content())
    if ("Supercopa de España 2027" not in text
            or "Estambul" not in text
            or "6 de febrero de 2027" not in text):
        raise ValueError("RFEF Supercopa 2027 page identity changed")

    events = []
    for date_text, clock, home, away, venue in EXPECTED:
        if home not in text or away not in text or venue not in text or clock not in text:
            raise ValueError(f"RFEF Supercopa semifinal changed: {home} - {away}")
        date = datetime.date.fromisoformat(date_text)
        local = datetime.datetime.combine(date, datetime.time.fromisoformat(clock), MADRID)
        slug = re.sub(r"[^a-z0-9]+", "-", home.lower()).strip("-")
        events.append({
            "id": f"spain-supercopa-2027-semi-{date:%Y%m%d}-{slug}",
            "source_id": source["id"],
            "sport": source["sport"],
            "league": source["league"],
            "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING",
            "status_detail": "RFEF published Supercopa de España 2027 semifinal",
            "season_stage": "SEMIFINAL",
            "location": venue,
            "source_endpoint": source["endpoint"],
        })
    if len(events) != 2:
        raise ValueError("RFEF Supercopa semifinal publication incomplete")
    return events
