"""Exact EPCR competition fixtures from each official Nuxt match page."""

import datetime
import html
import json
import re
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")


def parse_epcr_matches(page, source, today, end):
    script = re.search(r'<script[^>]+id="__NUXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not script:
        raise ValueError("EPCR fixture payload missing")
    payload = json.loads(html.unescape(script.group(1)))
    key = "fixtures-and-results-" + source["competition_slug"]
    if not isinstance(payload, list) or len(payload) < 6 or not isinstance(payload[3], dict) or key not in payload[3]:
        raise ValueError("EPCR competition fixture list missing")
    fixture_refs = payload[payload[3][key]]
    if not isinstance(fixture_refs, list):
        raise ValueError("EPCR fixture list invalid")

    def field(record, name):
        ref = record[name]
        return payload[ref] if isinstance(ref, int) and 0 <= ref < len(payload) else None

    results = []
    for ref in fixture_refs:
        if not isinstance(ref, int) or not isinstance(payload[ref], dict):
            continue
        fixture = payload[ref]
        if field(fixture, "compId") != source["competition_id"] or field(fixture, "compName") != source["competition_name"]:
            continue
        if field(fixture, "status") != "fixture" or field(fixture, "tbc"):
            continue
        try:
            match_id = field(fixture, "id")
            start = datetime.datetime.fromisoformat(field(fixture, "date").replace("Z", "+00:00"))
            home = field(field(fixture, "homeTeam"), "name")
            away = field(field(fixture, "awayTeam"), "name")
        except (KeyError, TypeError, ValueError):
            continue
        if not isinstance(match_id, int) or start.tzinfo is None or not all(isinstance(n, str) and n.strip() for n in (home, away)):
            continue
        if any(re.search(r'\b(?:tbc|tbd|under[ -]?\d{1,2}s?|u[ -]?\d{1,2}s?)\b', n, re.I) for n in (home, away)):
            continue
        if not today <= start.astimezone(CENTRAL).date() <= end:
            continue
        results.append({
            "id": f'{source["id"]}-{match_id}', "source_id": source["id"],
            "sport": "Rugby", "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "Official EPCR fixture",
            "season_stage": "REGULAR SEASON" if field(fixture, "roundTypeId") == 1 else "PLAYOFFS",
            "location": None, "source_endpoint": source["official_schedule_url"],
        })
    return results
