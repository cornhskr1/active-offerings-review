"""Exact top-division Liga Nacional basketball fixtures from its public date endpoint."""

import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from lxml import html


ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
BASE = "https://www.laliganacional.com.ar"


def parse_arg_lnb_fixtures(page, source, start_date, end_date):
    if source.get("catalog_terms") != ["Liga Nacional de Básquet (LNB) | Men"]:
        raise ValueError("Argentina LNB catalog scope changed")
    document = html.fromstring(page)
    rows = document.xpath('//tr[contains(concat(" ",normalize-space(@class)," ")," fila-tabla-calendarios ")]')
    if not rows:
        if "No se encontraron partidos" in document.text_content():
            return []
        raise ValueError("Argentina LNB fixture response changed")
    events, seen = [], set()
    for row in rows:
        names = [" ".join(name.itertext()).strip() for name in row.xpath('.//strong[contains(@class,"nombre-equipo")]')]
        dates = [" ".join(date.itertext()).strip() for date in row.xpath('.//td[contains(@class,"fecha-campo")]/strong')]
        links = row.xpath('.//a[contains(@class,"btn-estadisticas")]/@href')
        if len(names) != 2 or not all(names) or names[0] == names[1] or len(dates) != 1 or len(links) != 1:
            raise ValueError("Argentina LNB pairing or kickoff changed")
        try:
            local = datetime.datetime.strptime(dates[0], "%d/%m/%Y %H:%M").replace(tzinfo=ARGENTINA)
        except ValueError as exc:
            raise ValueError("Argentina LNB kickoff format changed") from exc
        if not start_date <= local.date() <= end_date:
            raise ValueError("Argentina LNB response crossed the requested date window")
        url = urljoin(BASE, links[0])
        parsed = urlparse(url)
        if parsed.hostname != "www.laliganacional.com.ar" or not parsed.path.startswith("/laliga/partido/"):
            raise ValueError("Argentina LNB detail link left the top division")
        publisher_id = parsed.path.split("/")[3]
        if not publisher_id or publisher_id in seen:
            raise ValueError("Argentina LNB match identity changed")
        seen.add(publisher_id)
        events.append({
            "id": f"arg-lnb-{publisher_id}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "Argentina LNB official fixture",
            "season_stage": "REGULAR", "location": None, "source_endpoint": url,
        })
    return events
