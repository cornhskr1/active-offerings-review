"""Fail closed when an ESPN league scoreboard changes competition scope."""

import re


def verified_events(payload, source):
    leagues = payload.get("leagues") or []
    expected_id = str(source["espn_league_id"])
    expected_slug = source["espn_league_slug"]
    if len(leagues) != 1 or str(leagues[0].get("id")) != expected_id or leagues[0].get("slug") != expected_slug:
        raise ValueError("ESPN league identity does not match configured competition")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("ESPN league event list is missing")
    if len(events) >= 1000:
        raise ValueError("ESPN league event list may be truncated")
    for event in events:
        uid = str(event.get("uid") or "")
        if not re.search(r"(?:^|~)l:" + re.escape(expected_id) + r"(?:~|$)", uid):
            raise ValueError("ESPN event belongs to a different competition")
        competitors = (event.get("competitions") or [{}])[0].get("competitors") or []
        if (not event.get("id") or not event.get("date") or len(competitors) != 2
                or not all((side.get("team") or {}).get("displayName") for side in competitors)):
            raise ValueError("ESPN league event lacks an exact named match")
    return events
