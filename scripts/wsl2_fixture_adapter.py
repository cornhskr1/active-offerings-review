"""Extract exact Barclays WSL2 fixtures from WSL Football's rolling schedule."""

import datetime
import html
import re
from zoneinfo import ZoneInfo


LONDON = ZoneInfo("Europe/London")
CENTRAL = ZoneInfo("America/Chicago")
MATCH = re.compile(
    r'<a\b[^>]*href="https://www\.wslfootball\.com/match/barclays-wsl2/'
    r'([a-f0-9]{32})/[^\"]+"[^>]*aria-label="([^\"]+)"[^>]*>', re.I,
)


def parse_wsl2_fixtures(page, source, window_end):
    if source.get("catalog_terms") != ["Super League 2 | Women"]:
        raise ValueError("WSL2 source does not target its exact current catalog identity")
    if not re.search(r"Fixtures 2026-27", page, re.I):
        raise ValueError("WSL2 season heading changed")
    matches = list(MATCH.finditer(page))
    if not matches or len(matches) > 10:
        raise ValueError("WSL2 rolling fixture list is missing or changed")
    events = []
    previous = None
    seen = set()
    for index, match in enumerate(matches):
        match_id = match.group(1).lower()
        if match_id in seen:
            raise ValueError("WSL2 match ID repeated")
        seen.add(match_id)
        scope = page[match.end():matches[index + 1].start() if index + 1 < len(matches) else match.end() + 1200]
        time_match = re.search(r'<time dateTime="(202[67]-\d\d-\d\dT\d\d:\d\d:\d\d)"', scope)
        if not time_match or not re.search(r'alt="Barclays WSL2"', scope[:time_match.end() + 400]):
            raise ValueError("WSL2 competition badge or kickoff is missing")
        teams = html.unescape(match.group(2)).split(" - ")
        if len(teams) != 2 or any(not team.strip() or re.search(r"\b(?:tbc|tbd)\b", team, re.I)
                                       for team in teams):
            raise ValueError("WSL2 fixture has no exact named teams")
        local = datetime.datetime.fromisoformat(time_match.group(1)).replace(tzinfo=LONDON)
        if previous and local < previous:
            raise ValueError("WSL2 rolling list is not date ordered")
        previous = local
        if any(re.search(r"\b" + word + r"\b", scope[:500], re.I)
               for word in ("postponed", "cancelled", "abandoned")):
            continue
        events.append({
            "id": match_id, "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{teams[1].strip()} at {teams[0].strip()}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "WSL Football fixture",
            "season_stage": "REGULAR", "location": None,
            "source_endpoint": source["endpoint"],
        })
    if len(matches) == 10 and previous.astimezone(CENTRAL).date() <= window_end:
        raise ValueError("WSL2 rolling page may omit fixtures inside review window")
    return events
