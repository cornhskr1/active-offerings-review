"""Dated championship event cards from publisher-owned public calendars."""

import datetime
import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin


def _date(value):
    return datetime.date.fromisoformat(str(value)[:10])


class MotoGPEvents(HTMLParser):
    def __init__(self):
        super().__init__()
        self.events = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag != "div" or data.get("data-widget") != "structured-data-event/structured-data-event":
            return
        if data.get("data-structured-kind") != "GP" or data.get("data-structured-year") != "2026":
            return
        title = str(data.get("data-structured-title") or "").strip()
        start, end = data.get("data-structured-start-date"), data.get("data-structured-end-date")
        if title and start and end:
            self.events.append({"id": f"motogp-{_date(start)}", "name": title,
                "start": _date(start), "end": _date(end),
                "location": " · ".join(x for x in (data.get("data-structured-location"),
                    data.get("data-structured-country")) if x)})


def motogp_events(page, url):
    parser = MotoGPEvents()
    parser.feed(page)
    if len(parser.events) < 15:
        raise ValueError("MotoGP calendar has fewer than 15 identified grands prix")
    return [{**event, "url": url} for event in parser.events]


def nhra_events(page, url):
    events = []
    for block in re.split(r'<div[^>]*class="views-row"[^>]*typeof="ListItem Event"[^>]*>', page)[1:]:
        start = re.search(r'property="startDate"\s+content="([^"]+)"', block)
        end = re.search(r'property="endDate"\s+content="([^"]+)"', block)
        title = re.search(r'<h3[^>]*property="name"[^>]*>(.*?)</h3>', block, re.S)
        link = re.search(r'href="([^"]*nhra-mission-foods-drag-racing-series/[^"]+)"', block)
        if not (start and title and link):
            continue
        name = html.unescape(re.sub(r'<[^>]+>', '', title.group(1))).strip()
        if not name:
            continue
        events.append({"id": link.group(1).rstrip('/').split('/')[-1],
            "name": name, "start": _date(start.group(1)),
            "end": _date(end.group(1)) if end else None,
            "location": None, "url": urljoin(url, html.unescape(link.group(1)))})
    if len(events) < 15:
        raise ValueError("NHRA calendar has fewer than 15 identified Mission Foods events")
    return events


def supercars_events(page, url):
    events = {}
    for match in re.finditer(r'<script>self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)</script>', page):
        flight = json.loads(match.group(1))
        for key in ("featuredEvents", "events"):
            marker = f'"{key}":'
            offset = flight.find(marker)
            if offset < 0:
                continue
            rows, _ = json.JSONDecoder().raw_decode(flight[offset + len(marker):])
            for row in rows:
                slug, name = row.get("slug"), row.get("title")
                start, end = row.get("startDate"), row.get("endDate")
                if (not all((slug, name, start, end)) or not slug.startswith("2026-")
                        or not name.startswith("2026 ")):
                    continue
                events[slug] = {"id": slug, "name": name, "start": _date(start),
                    "end": _date(end), "location": row.get("location"),
                    "url": urljoin(url, "/events/" + slug)}
    if len(events) < 12:
        raise ValueError("Supercars calendar has fewer than 12 identified 2026 events")
    return list(events.values())


def formula_e_events(page, url):
    match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*id="calendar-schema"[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Formula E calendar schema missing")
    schema = json.loads(match.group(1))
    if schema.get("@type") != "ItemList" or schema.get("numberOfItems", 0) < 20:
        raise ValueError("Formula E published round list is incomplete")
    events = []
    for row in schema.get("itemListElement") or []:
        item = row.get("item") or {}
        position, start = row.get("position"), item.get("startDate")
        place = (item.get("location") or {}).get("name")
        # The publisher still labels these race names TBC. Round/date and a
        # specific venue or city identify an event; "Americas" does not.
        if (not isinstance(position, int) or not start or not place
                or place.strip().lower() in ("tbc", "americas")):
            continue
        events.append({"id": f"formula-e-2026-27-r{position:02d}",
            "name": f"Formula E Round {position} · {place}", "start": _date(start),
            "end": _date(item.get("endDate") or start), "location": place, "url": url})
    if len(events) < 19:
        raise ValueError("Formula E calendar has fewer than 19 identified rounds")
    return events


PARSERS = {"motogp": motogp_events, "nhra": nhra_events,
           "supercars": supercars_events, "formula-e": formula_e_events}
