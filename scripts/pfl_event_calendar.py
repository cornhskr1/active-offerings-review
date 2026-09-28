"""PFL publisher event dates, scoped to its separately approved regional series."""

import datetime
import json
import re
from urllib.parse import urlparse

from lxml import html


SERIES = {
    "combat-pfl-mena": re.compile(r"^PFL MENA\b", re.I),
    "combat-pfl-africa": re.compile(r"^PFL Africa\b", re.I),
    "combat-pfl-europe": re.compile(r"^PFL Europe\b", re.I),
    "combat-pfl-champions": re.compile(r"^PFL Champions Series\b", re.I),
}


def upcoming_event_links(page):
    document = html.fromstring(page)
    cards = document.xpath('//div[@id="nav-upcoming"]//div[contains(concat(" ",normalize-space(@class)," ")," event-hub ")]')
    if not cards:
        raise ValueError("PFL upcoming event cards missing")
    found = []
    for card in cards:
        title = " ".join(card.xpath('.//div[contains(@class,"event-card-info")]//h3/text()')).strip()
        links = [url for url in card.xpath('.//div[contains(@class,"event-card-info")]//a/@href')
                 if urlparse(url).hostname == "pflmma.com" and urlparse(url).path.startswith("/event/")]
        if not title or len(set(links)) != 1:
            raise ValueError("PFL event card changed")
        source_id = next((key for key, pattern in SERIES.items() if pattern.search(title)), None)
        if not source_id:
            continue
        url = links[0]
        parsed = urlparse(url)
        if parsed.hostname != "pflmma.com" or not parsed.path.startswith("/event/"):
            raise ValueError("PFL event link left the publisher")
        found.append({"source_id": source_id, "title": title, "url": url})
    return found


def verified_event(detail_page, card):
    document = html.fromstring(detail_page)
    for raw in document.xpath('//script[@type="application/ld+json"]/text()'):
        payload = json.loads(raw)
        graph = payload.get("@graph", []) if isinstance(payload, dict) else []
        for item in graph:
            if (item.get("@type") != "SportsEvent" or item.get("name") != card["title"]
                    or item.get("url") != card["url"]):
                continue
            start = datetime.datetime.fromisoformat(item["startDate"])
            end = datetime.datetime.fromisoformat(item["endDate"])
            if start.tzinfo is None or end.tzinfo is None or start.date() != end.date():
                raise ValueError("PFL event date changed")
            return {**card, "date": start.date(),
                    "location": (item.get("location") or {}).get("name") or ""}
    raise ValueError("PFL event detail did not verify the named series")
