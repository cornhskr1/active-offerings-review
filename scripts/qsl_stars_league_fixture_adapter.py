"""Read exact Doha Bank Stars League upcoming weeks from QSL."""

import datetime
import html
import re
from zoneinfo import ZoneInfo

from qsl_cup_fixture_adapter import TEAM

QATAR = ZoneInfo("Asia/Qatar")


def parse_qsl_stars_fixtures(page, source, now, window_end):
    if source.get("catalog_terms") != ["Qatar Stars League | Men"]:
        raise ValueError("QSL league source has the wrong catalog identity")
    if "Doha Bank Stars League" not in page or "2026-2027" not in page:
        raise ValueError("QSL league season identity changed")
    pane = re.search(r'<div class="tab-pane fade show active" id="nav-fixtures"(.*?)<div class="tab-pane fade" id="nav-result"', page, re.S)
    if not pane:
        raise ValueError("QSL league upcoming fixture pane missing")
    rows = re.findall(r'<tr class="fixture-result">(.*?)</tr>', pane.group(1), re.S)
    if len(rows) != 12:
        raise ValueError("QSL league upcoming weeks have an unexpected match count")
    events = []
    seen = set()
    dates = []
    for group_start in (0, 6):
        week_teams = set()
        for row in rows[group_start:group_start + 6]:
            match_number = re.search(r'<div class="table__date__round">\s*<span>(\d+)</span>', row)
            date_block = re.search(r'<div class="table__date__round">(.*?)</div>', row, re.S)
            date_text = html.unescape(re.sub(r'<[^>]+>', ' ', date_block.group(1))) if date_block else ''
            kickoff_match = re.search(r'(\d{2}/\d{2}/26)\s+(\d{2}:\d{2})', date_text)
            names = [html.unescape(re.search(r'<span>\s*([^<]+)</span>', anchor.group(1), re.S).group(1)).strip()
                     for anchor in TEAM.finditer(row) if re.search(r'<span>\s*([^<]+)</span>', anchor.group(1), re.S)]
            if not match_number or not kickoff_match or len(names) != 2 or match_number.group(1) in seen:
                raise ValueError("QSL league match number, kickoff, or clubs changed")
            if any(not name or re.search(r'\b(?:tbc|tbd|u\d{2})\b', name, re.I) or name in week_teams for name in names):
                raise ValueError("QSL league club is unidentified or repeated in a week")
            seen.add(match_number.group(1))
            week_teams.update(names)
            local = datetime.datetime.strptime(' '.join(kickoff_match.groups()), '%d/%m/%y %H:%M').replace(tzinfo=QATAR)
            dates.append(local.date())
            events.append({
                "id": "qsl-stars-2026-27-" + match_number.group(1),
                "source_id": source["id"], "sport": source["sport"],
                "league": source["league"], "region": source["region"],
                "name": f"{names[1]} at {names[0]}",
                "start_time": local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING", "status_detail": "QSL published league fixture",
                "season_stage": "REGULAR", "location": None,
                "source_endpoint": source["endpoint"],
            })
        if len(week_teams) != 12:
            raise ValueError("QSL league week does not include twelve distinct clubs")
    if dates != sorted(dates) or not any(
        datetime.datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")) > now for event in events
    ):
        raise ValueError("QSL league upcoming weeks are stale or out of order")
    if window_end > dates[-1]:
        raise ValueError("QSL league published weeks do not cover the full review window")
    return events
