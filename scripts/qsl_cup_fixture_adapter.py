"""Read named, timed 2026–27 QSL Cup fixtures from the league authority."""

import datetime
import html
import re
from zoneinfo import ZoneInfo

QATAR = ZoneInfo("Asia/Qatar")
TEAM = re.compile(r'<a\b[^>]*href=/?en/[^ >]+[^>]*class="(?:table__result__team linked-club|linked-club table__result__team)"[^>]*>(.*?)</a>', re.S)


def parse_qsl_cup_fixtures(page, source, now):
    if source.get("catalog_terms") != ["QSL Cup | Men"]:
        raise ValueError("QSL Cup source has the wrong catalog identity")
    if "QSL cup" not in page or "2026-2027" not in page:
        raise ValueError("QSL Cup season identity changed")
    pane = re.search(r'<div class="tab-pane fade show active" id="group-121-fixtures-tab".*?<table[^>]*>(.*?)</table>', page, re.S)
    if not pane:
        raise ValueError("QSL Cup upcoming fixture pane missing")
    rows = re.findall(r'<tr>(.*?)</tr>', pane.group(1), re.S)
    if len(rows) != 9:
        raise ValueError("QSL Cup published round has an unexpected fixture count")
    events = []
    seen = set()
    teams_seen = set()
    dates = []
    for row in rows:
        round_id = re.search(r'<div class="table__date__round">\s*<span>(\d+)</span>', row)
        date_block = re.search(r'<div class="table__date__round">(.*?)</div>', row, re.S)
        date_text = html.unescape(re.sub(r'<[^>]+>', ' ', date_block.group(1))) if date_block else ''
        kickoff_match = re.search(r'(\d{2}/\d{2}/26)\s*-\s*(\d{2}:\d{2})', date_text)
        names = [html.unescape(re.search(r'<span>\s*([^<]+)</span>', anchor.group(1), re.S).group(1)).strip()
                 for anchor in TEAM.finditer(row) if re.search(r'<span>\s*([^<]+)</span>', anchor.group(1), re.S)]
        if not round_id or not kickoff_match or len(names) != 2 or round_id.group(1) in seen:
            raise ValueError("QSL Cup match number, kickoff, or clubs changed")
        if any(not name or re.search(r'\b(?:tbc|tbd|u\d{2})\b', name, re.I) or name in teams_seen for name in names):
            raise ValueError("QSL Cup club is unidentified or repeated in the round")
        seen.add(round_id.group(1))
        teams_seen.update(names)
        local = datetime.datetime.strptime(' '.join(kickoff_match.groups()), '%d/%m/%y %H:%M').replace(tzinfo=QATAR)
        dates.append(local.date())
        events.append({
            "id": "qsl-cup-2026-27-" + round_id.group(1),
            "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{names[1]} at {names[0]}",
            "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "QSL published cup fixture",
            "season_stage": "REGULAR", "location": None,
            "source_endpoint": source["endpoint"],
        })
    if dates != sorted(dates) or not any(
        datetime.datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")) > now for event in events
    ):
        raise ValueError("QSL Cup upcoming round is stale or out of order")
    return events
