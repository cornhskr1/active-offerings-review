"""Validate a publisher's complete timed batch before changing published state.

Competition-specific parsers remain responsible for approval, edition, and
participant scope. This boundary never promotes date-only evidence to kickoff.
"""
import datetime


def stage_timed_fixtures(fixtures, source_id, now, first_day, last_day, timezone, seen):
    staged, local_seen, staged_keys = [], {}, set()
    for event in fixtures:
        if event.get('source_id') != source_id or not event.get('id'):
            raise ValueError('Publisher fixture source identity changed')
        if event.get('date_only'):
            raise ValueError('Date-only evidence cannot enter the timed fixture batch')
        start = datetime.datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError('Publisher fixture timezone is missing')
        key = (event['id'], event['start_time'])
        if key in local_seen and local_seen[key] != event:
            raise ValueError('Publisher fixture duplicate has conflicting evidence')
        local_seen[key] = event
        if start <= now or not first_day <= start.astimezone(timezone).date() <= last_day:
            continue
        if key not in seen and key not in staged_keys:
            staged.append((key, event))
            staged_keys.add(key)
    return staged
