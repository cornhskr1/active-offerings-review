"""Competition-scoped J.League match cards from the official schedule search page."""

import datetime
import json
import re
from zoneinfo import ZoneInfo


JAPAN = ZoneInfo("Asia/Tokyo")
CENTRAL = ZoneInfo("America/Chicago")


def parse_jleague_matches(page, source, today, end):
    schedules = []
    for script in re.finditer(r'<script>self\.__next_f\.push\((\[1,\s*".*?"\])\)</script>', page, re.S):
        decoded = json.loads(script.group(1))[1]
        for marker in re.finditer(r'"schedules":\[', decoded):
            try:
                cards, _ = json.JSONDecoder().raw_decode(decoded[marker.end() - 1:])
            except json.JSONDecodeError:
                continue
            schedules.extend(cards)
    if not schedules:
        raise ValueError("J.League official schedule payload missing")
    events = []
    seen = set()
    for section in schedules:
        if section.get("leagueDisplayName") != source["competition_name"]:
            continue
        date_text = section.get("matchDate", "")
        try:
            match_date = datetime.date.fromisoformat(date_text.removeprefix("$D")[:10])
        except ValueError:
            continue
        for match in section.get("matches", []):
            match_id = match.get("id")
            href = match.get("detailHref", "")
            names = [match.get(side, {}).get("fullName") for side in ("homeTeam", "awayTeam")]
            clock = re.fullmatch(r'(\d{1,2}):(\d{2})', match.get("time") or "")
            if not (match.get("state") == "ticket" and
                    isinstance(match_id, str) and match_id.isdigit() and
                    re.fullmatch(r'/match/' + re.escape(source["competition_path"]) + r'/2026/\d+', href) and
                    clock and all(isinstance(name, str) and name.strip() for name in names)):
                continue
            if any(re.search(r'\b(?:tbc|tbd|under[ -]?\d{1,2}s?|u[ -]?\d{1,2}s?)\b', name, re.I) for name in names):
                continue
            start = datetime.datetime.combine(match_date,
                datetime.time(int(clock.group(1)), int(clock.group(2))), JAPAN)
            if not today <= start.astimezone(CENTRAL).date() <= end or match_id in seen:
                continue
            seen.add(match_id)
            events.append({
                "id": f'{source["id"]}-{match_id}', "source_id": source["id"],
                "sport": "Soccer", "league": source["league"], "region": "Japan",
                "name": f"{names[1]} at {names[0]}",
                "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "Official J.League fixture",
                "season_stage": "CUP" if source["competition_path"] == "leaguecup" else "REGULAR SEASON",
                "location": match.get("stadiumFullName") or None,
                "source_endpoint": source["official_schedule_url"],
            })
    return events
