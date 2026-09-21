#!/usr/bin/env python3
"""Pure quality-gate helpers for Tennis Intelligence refreshes."""


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
