"""Verify current Cymru Premier phase-one cards against FAW match centres."""

import datetime
import html
import re
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
LONDON = ZoneInfo("Europe/London")
CARD = re.compile(
    r'<div class="is-style-match-card-v2 ([^"]+)" data-match-id="(\d+)" '
    r'data-match-kickoff-utc="(\d+)"><div class="match-link__wrapper">'
    r'<a class="match-link" href="(https://faw\.cymru/cymru-leagues/match/[^\"]+)"', re.I
)
TITLE = re.compile(
    r'<title>(.*?) vs\. (.*?) \| Cymru Premier 26/27 - Phase One - Cymru Leagues</title>', re.I | re.S
)


def parse_phase_one_fixtures(page, source, today, window_end, now, fetch_match):
    if source.get("catalog_terms") != ["Cymru Premier | Men"]:
        raise ValueError("FAW source does not target the exact Cymru Premier identity")
    if "Novira Cymru Premier" not in page or "Fixtures and Results" not in page:
        raise ValueError("FAW Cymru Premier page heading changed")
    cards = list(CARD.finditer(page))
    if not cards or len(cards) > 100 or len(cards) != len(re.findall(
        r'<div class="is-style-match-card-v2 [^"]+" data-match-id=', page
    )):
        raise ValueError("FAW fixture cards missing or changed")
    last = None
    seen = set()
    events = []
    for index, card in enumerate(cards):
        match_id, milliseconds, link = card.group(2), int(card.group(3)), html.unescape(card.group(4))
        kickoff = datetime.datetime.fromtimestamp(milliseconds / 1000, datetime.timezone.utc)
        if milliseconds % 60000 or (last and kickoff < last) or match_id in seen:
            raise ValueError("FAW match ID or kickoff ordering changed")
        last = kickoff
        seen.add(match_id)
        central_day = kickoff.astimezone(CENTRAL).date()
        if not today <= central_day <= window_end or kickoff <= now:
            continue
        scope = page[card.end():cards[index + 1].start() if index + 1 < len(cards) else card.end() + 2500]
        local_time = kickoff.astimezone(LONDON).strftime("%H:%M")
        if "fixture" not in card.group(1).split() or not re.search(
            r'<p class="kickoff__time preloader">' + re.escape(local_time) + r'</p>', scope[:600]
        ):
            raise ValueError("FAW fixture status or visible kickoff changed")
        if not link.endswith("-cymru-premier-26-27-phase-one/"):
            raise ValueError("FAW match link is outside the current phase")
        match_page = fetch_match(link)
        title = TITLE.search(match_page)
        identity = re.search(r'data-match-id="(\d+)" data-comp-id="(\d+)"', match_page)
        if not title or not identity or identity.groups() != (match_id, "107679230"):
            raise ValueError("FAW match centre identity or competition changed")
        home, away = (html.unescape(team).strip() for team in title.groups())
        if not home or not away or home == away or any(re.search(r'\b(?:tbc|tbd)\b', t, re.I) for t in (home, away)):
            raise ValueError("FAW match centre has unidentified clubs")
        events.append({
            "id": match_id, "source_id": source["id"], "sport": source["sport"],
            "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}",
            "start_time": kickoff.isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "FAW Cymru Premier phase-one fixture",
            "season_stage": "REGULAR", "location": None, "source_endpoint": link,
        })
    if last.astimezone(CENTRAL).date() <= window_end:
        raise ValueError("FAW rolling page may omit fixtures inside review window")
    return events
