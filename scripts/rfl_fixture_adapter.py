"""Exact senior RFL match fixtures from the governing body's match centre."""

import datetime
import html
import re
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")
LONDON = ZoneInfo("Europe/London")


def clean(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def parse_rfl_match_centre(page, source, today, end):
    """Accept only cards bearing the exact configured senior division label."""
    if "match-centre" not in page or "matches" not in page:
        raise ValueError("RFL match-centre response has no match listing")
    parsed = []
    sections = re.split(r'(?=<h3 class="comp-divider")', page)
    for section in sections[1:]:
        heading = re.search(r'<h3 class="comp-divider"[^>]*>(.*?)</h3>', section, re.S)
        if not heading:
            continue
        try:
            date_text = re.sub(r"(\d+)(?:st|nd|rd|th)\b", r"\1", clean(heading.group(1)))
            local_date = datetime.datetime.strptime(date_text, "%a %d %B %Y").date()
        except ValueError:
            continue
        for card in re.split(r'(?=<div data-matchid="[^"]*"[^>]*class="[^"]*fixture-card)', section)[1:]:
            division = re.search(r'<span class="division-label"[^>]*>(.*?)</span>', card, re.S)
            if not division or clean(division.group(1)) != source["division_label"]:
                continue
            teams = [clean(name) for name in re.findall(
                r'<span class="team-name d-none d-lg-block"[^>]*>(.*?)</span>', card, re.S
            )]
            if len(teams) != 2 or any(not team or team.casefold() in {"tbc", "tbd"} or
                                      re.search(r"\b(?:under|u)[ -]?\d{1,2}s?\b", team, re.I)
                                      for team in teams):
                continue
            match_id = re.search(r'/match-centre/match-preview/(\d+)', card)
            kickoff = re.search(r'<span class="text-center ko d-block"[^>]*>\s*(\d{1,2}:\d{2})\s*</span>', card)
            # RFL labels a Championship promotion play-off with the same
            # senior division text as the Super League final. Its card has no
            # competition round; never infer approval from the label alone.
            round_label = re.search(r'Round:\s*([^<\n]+)', card)
            if not match_id or not kickoff or not round_label or re.search(r'promotion', round_label.group(1), re.I):
                continue
            try:
                clock = datetime.time.fromisoformat(kickoff.group(1))
                start = datetime.datetime.combine(local_date, clock, tzinfo=LONDON)
            except ValueError:
                continue
            central_date = start.astimezone(CENTRAL).date()
            if not today <= central_date <= end:
                continue
            venue = re.search(r'<span class="venue-label"[^>]*>Venue:\s*(.*?)</span>', card, re.S)
            parsed.append({
                "id": f'{source["id"]}-{match_id.group(1)}',
                "source_id": source["id"],
                "sport": source["sport"],
                "league": source["league"],
                "region": source.get("region"),
                "name": f"{teams[1]} at {teams[0]}",
                "start_time": start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "UPCOMING",
                "status_detail": clean(round_label.group(1)) if round_label else "Official RFL fixture",
                "season_stage": "POSTSEASON" if round_label and re.search(r"final|play.?off", round_label.group(1), re.I) else "REGULAR SEASON",
                "location": clean(venue.group(1)) if venue else None,
                "source_endpoint": source["official_schedule_url"],
            })
    return parsed
