#!/usr/bin/env python3
"""Pure quality-gate helpers for Tennis Intelligence refreshes."""

import datetime
import re


def publisher_access_issue(status, body):
    """Recognize a transport/block page before treating it as a calendar."""
    if status in (401, 403, 429):
        return f"PUBLISHER_HTTP_{status}"
    text = str(body or "").lower()
    if "sorry, you have been blocked" in text or "unable to access atptour.com" in text:
        return "PUBLISHER_ACCESS_BLOCKED"
    return None


def schedule_source_warning(payload, tour_ids, now):
    """Keep a blocked tour unhealthy even when other tours refresh the cache."""
    generated = payload.get("generated_at")
    if not generated:
        return "Tennis intelligence schedule has no generation time"
    try:
        checked = datetime.datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return "Tennis intelligence schedule has an invalid generation time"
    if now - checked.astimezone(datetime.timezone.utc) > datetime.timedelta(hours=72):
        return "Tennis intelligence schedule is more than 72 hours old; retaining last known good events"
    for lane in (payload.get("quality_gate") or {}).get("degraded_lanes") or []:
        if lane.get("tour_id") in set(tour_ids or []):
            return lane.get("reason") or "Tennis publisher access blocked; manual verification required"
    return None


def parse_date(value):
    value = " ".join(str(value or "").split())
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def date_range(value):
    """Read the three date-range layouts used on official tour calendars."""
    value = " ".join(str(value or "").split())
    patterns = (
        r'(\d{1,2})\s+([A-Za-z]+)\s+(?:to|[-–])\s+(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',
        r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})',
        r'([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})',
    )
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, value, re.I)
        if not match:
            continue
        if index == 0:
            day1, month1, day2, month2, year = match.groups()
            start, end = parse_date(f"{day1} {month1} {year}"), parse_date(f"{day2} {month2} {year}")
        elif index == 1:
            day1, day2, month, year = match.groups()
            start, end = parse_date(f"{day1} {month} {year}"), parse_date(f"{day2} {month} {year}")
        else:
            month, day1, day2, year = match.groups()
            start, end = parse_date(f"{day1} {month} {year}"), parse_date(f"{day2} {month} {year}")
        if start and end:
            return start, end
    return None, None


def challenger_score_event_url(url):
    """Collapse ATP's score tabs to one official Challenger event page."""
    match = re.search(r'(/en/scores/current-challenger/[^/?]+/\d+)(?:/|$)', url or '', re.I)
    if not match:
        return None
    return (url or '')[:match.start(1)] + match.group(1) + '/live-scores'


def challenger_calendar_card_dates(card, context, year):
    """Read an ATP calendar card only when its year is explicitly established.

    The calendar often prints the year in the month heading and omits it from
    individual cards. Do not borrow a date from a neighboring event or infer a
    year from the computer clock alone.
    """
    card = " ".join(str(card or "").split())
    context = " ".join(str(context or "").split())
    direct = date_range(card)
    if all(direct):
        return direct if direct[0].year == year else (None, None)
    months = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    patterns = (
        rf"\b\d{{1,2}}\s+{months}\s*(?:to|[-–])\s*\d{{1,2}}\s+{months}\b",
        rf"\b\d{{1,2}}\s*[-–]\s*\d{{1,2}}\s+{months}\b",
        rf"\b{months}\s+\d{{1,2}}\s*[-–]\s*\d{{1,2}}\b",
    )
    fragments = [m.group() for pattern in patterns for m in re.finditer(pattern, card, re.I)]
    if len(fragments) != 1:
        return None, None
    headings = re.findall(rf"\b({months})\s*,\s*(20\d{{2}})\b", context, re.I)
    if not headings or any(int(found_year) != year for _, found_year in headings):
        return None, None
    dates = date_range(f"{fragments[0]}, {year}")
    if not all(dates) or dates[0] > dates[1]:
        return None, None
    return dates


def calendar_discovery_issue(health, has_events):
    """Return a WTA discovery failure code, or None for a valid empty window.

    A calendar containing annual tournament links is not evidence that an event
    overlaps Today+7. The gate should fail only when the adapter cannot resolve
    any candidate dates, or when a confirmed overlapping tournament produces no
    published event.
    """
    health = health or {}
    if has_events or not health.get("ok"):
        return None

    candidate_links = int(health.get("candidate_tournament_links") or 0)
    dated_links = int(health.get("dated_candidate_links") or 0)
    overlapping_links = int(health.get("overlapping_candidate_links") or 0)

    if overlapping_links > 0:
        return "OVERLAP_WITHOUT_EVENT"
    if candidate_links > 0 and dated_links == 0:
        return "DATES_UNRESOLVED"
    return None
