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
    if card.get("source_id") not in SERIES or not SERIES[card["source_id"]].search(card["title"]):
        raise ValueError("PFL event card has the wrong regional series")
    matches = []
    for raw in document.xpath('//script[@type="application/ld+json"]/text()'):
        payload = json.loads(raw)
        graph = payload.get("@graph", []) if isinstance(payload, dict) else []
        matches.extend(item for item in graph if item.get("@type") == "SportsEvent"
                       and item.get("name") == card["title"] and item.get("url") == card["url"])
    if len(matches) != 1:
        raise ValueError("PFL event detail did not uniquely verify the named series")
    item = matches[0]
    start = datetime.datetime.fromisoformat(item["startDate"])
    end = datetime.datetime.fromisoformat(item["endDate"])
    if (start.tzinfo is None or end.tzinfo is None or end < start
            or end-start > datetime.timedelta(days=1)):
        raise ValueError("PFL event date changed")
    if item.get("eventStatus", "https://schema.org/EventScheduled") != "https://schema.org/EventScheduled":
        raise ValueError("PFL event is not scheduled")
    displayed = [" ".join(n.text_content().split()).upper() for n in document.xpath(
        '//p[contains(concat(" ",normalize-space(@class)," ")," event-info-date-large ")]')]
    expected = f"{start.strftime('%a %b').upper()} {start.day}"
    if (displayed and displayed != [expected]) or (start.date() != end.date() and displayed != [expected]):
        raise ValueError("PFL displayed event date did not verify structured start date")
    # Date-only evidence: the end stamp is never turned into an extra event day or bout time.
    return {**card, "date": start.date(),
            "location": (item.get("location") or {}).get("name") or ""}
