"""Exact 2027 men's Supercopa semifinal fixtures from RFEF's official Istanbul schedule."""

import datetime
import re
import unicodedata
from zoneinfo import ZoneInfo

from lxml import html


MADRID = ZoneInfo("Europe/Madrid")
EXPECTED = [
    ("2027-02-02", "20:00", "FC Barcelona", "Club Atlético de Madrid",
     "Chobani Stadyumu Fenerbahçe Şükrü Saracoğlu Sports Complex"),
    ("2027-02-03", "20:00", "Real Sociedad de Fútbol", "Real Madrid CF",
     "Tüpraş Stadium"),
]


def _norm(value):
    return " ".join(unicodedata.normalize('NFC', str(value or "")).replace("\xa0", " ").split())


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
            ):
        raise ValueError("RFEF Supercopa 2027 page identity changed")

    tables = doc.xpath('//table[.//th[contains(.,"RONDA")]]')
    if len(tables) != 1:
        raise ValueError('RFEF exact schedule table missing or ambiguous')
    headers = [_norm(' '.join(c.itertext())) for c in tables[0].xpath('./thead/tr/th')]
    if headers != ['RONDA','PARTIDO','FECHA','HORARIO (peninsular español)','ESTADIO']:
        raise ValueError('RFEF schedule fields or time zone changed')
    rows = [[_norm(c.text_content()) for c in row.xpath('./th|./td')]
            for row in tables[0].xpath('./tbody/tr')]
    if len(rows) != 3 or any(len(row) != 5 for row in rows):
        raise ValueError('RFEF schedule row count changed')
    if rows[2] != ['FINAL','Por determinar','06/02/2027','20:00','Ali Sami Yen Sports Complex - RAMS Park']:
        raise ValueError('RFEF unconfirmed final evidence changed')

    events = []
    for number, (date_text, clock, home, away, venue) in enumerate(EXPECTED,1):
        date = datetime.date.fromisoformat(date_text)
        if rows[number-1] != [f'SEMIFINAL {number}',f'{home} - {away}',date.strftime('%d/%m/%Y'),clock,venue]:
            raise ValueError(f"RFEF Supercopa semifinal changed: {home} - {away}")
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
