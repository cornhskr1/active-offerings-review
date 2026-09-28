#!/usr/bin/env python3
"""Pure quality-gate helpers for Tennis Intelligence refreshes."""

import datetime
import re


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
