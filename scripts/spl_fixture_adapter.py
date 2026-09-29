"""Exact 2026–27 Singapore Premier League fixtures from the SPL publisher."""

import datetime
import re
from collections import Counter
from zoneinfo import ZoneInfo

from lxml import html


SOURCE_ID = "soccer-afc-singapore-singapore-premier-league-men"
SINGAPORE = ZoneInfo("Asia/Singapore")
CLUBS = {
    "Balestier Khalsa FC", "FC Jurong", "Geylang International FC",
    "Hougang United FC", "Lion City Sailors FC", "Tampines Rovers FC",
    "Tanjong Pagar United FC", "Young Lions",
}
FIRST = datetime.date(2026, 9, 11)
LAST = datetime.date(2027, 5, 16)


def _class(name):
    return f'contains(concat(" ",normalize-space(@class)," ")," {name} ")'


def _one_text(row, name):
    nodes = row.xpath(f'.//*[{_class(name)}]')
    if len(nodes) != 1:
        raise ValueError(f"SPL fixture {name} field changed")
    return " ".join(" ".join(nodes[0].xpath('.//text()')).split())


def parse_fixtures(page, source):
    if source.get("id") != SOURCE_ID or source.get("catalog_terms") != ["Singapore Premier League | Men"]:
        raise ValueError("SPL source scope changed")
    doc = html.fromstring(page)
    titles = doc.xpath('//title/text()')
    if len(titles) != 1 or "Fixtures – Singapore Premier League" != titles[0]:
        raise ValueError("SPL fixture page identity changed")
    roots = doc.xpath(f'//*[{_class("spl-gwnav")}]')
    if len(roots) != 1:
        raise ValueError("SPL fixture navigation changed")
    panels = roots[0].xpath(f'.//*[{_class("spl-gwnav-panel")}]')
    options = roots[0].xpath('.//select/option/text()')
    if len(panels) != 23 or options != [f"Matchweek {n}" for n in range(1, 24)]:
        raise ValueError("SPL 2026–27 matchweek structure changed")
    pairings = Counter()
    appearances = Counter()
    fixture_keys = set()
    events = []
    held_young_lions = 0
    held_starts = []
    for panel in panels:
        for row in panel.xpath(f'.//*[{_class("spl-gwrow")}]'):
            stamp = _one_text(row, "spl-gwrow-meta")
            match = re.fullmatch(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{1,2} [A-Z][a-z]{2} 20(?:26|27)) · (\d{1,2}:\d{2}[ap]m) · (.+)", stamp)
            if not match:
                raise ValueError("SPL fixture date, kickoff, or venue changed")
            day = datetime.datetime.strptime(match.group(2), "%d %b %Y").date()
            if not FIRST <= day <= LAST or day.strftime("%a") != match.group(1):
                raise ValueError("SPL fixture outside the 2026–27 season")
            local = datetime.datetime.strptime(match.group(3), "%I:%M%p").time()
            if not match.group(4).strip():
                raise ValueError("SPL fixture venue missing")
            home = _one_text(row, "home")
            away = _one_text(row, "away")
            if home not in CLUBS or away not in CLUBS or home == away or _one_text(row, "spl-gwrow-vs") != "vs":
                raise ValueError("SPL fixture club or pairing changed")
            key = (day, home, away)
            if key in fixture_keys:
                raise ValueError("SPL duplicate fixture")
            fixture_keys.add(key)
            pairings[tuple(sorted((home, away)))] += 1
            appearances.update((home, away))
            start = datetime.datetime.combine(day, local, SINGAPORE).astimezone(datetime.timezone.utc)
            if "Young Lions" in (home, away):
                held_young_lions += 1
                held_starts.append(start)
                continue
            events.append({
                "id": f"spl-2026-27-{day:%Y%m%d}-{re.sub('[^a-z0-9]+', '-', home.lower()).strip('-')}-{re.sub('[^a-z0-9]+', '-', away.lower()).strip('-')}",
                "source_id": SOURCE_ID, "sport": "Soccer", "league": source["league"],
                "region": "Singapore", "name": f"{away} at {home}",
                "start_time": start.isoformat(timespec="minutes").replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "SPL official fixture",
                "location": match.group(4).strip(), "source_endpoint": source["endpoint"],
            })
    if (len(fixture_keys) != 84 or len(pairings) != 28 or set(appearances) != CLUBS
            or any(count != 3 for count in pairings.values())
            or any(count != 21 for count in appearances.values())
            or held_young_lions != 21):
        raise ValueError("SPL full-season pairings or age-review hold changed")
    return events, held_young_lions, len(fixture_keys), held_starts
