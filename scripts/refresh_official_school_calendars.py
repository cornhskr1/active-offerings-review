#!/usr/bin/env python3
"""Refresh the sixteen approved school calendars without roster or HTML scraping."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo
import requests
try:
    from official_school_calendar import collect_school_calendar
    from publisher_access_policy import install_network_guards
except ModuleNotFoundError:
    from scripts.official_school_calendar import collect_school_calendar
    from scripts.publisher_access_policy import install_network_guards

CT = ZoneInfo('America/Chicago')
ROOT = Path(__file__).resolve().parents[1]
CORE_SPORTS = {"Men's Basketball", "Women's Basketball", 'Volleyball', 'Baseball', 'Softball'}
EXPECTED = {(school, sport) for school in ('Nebraska', 'Creighton', 'Omaha') for sport in CORE_SPORTS} | {('Nebraska', 'Football')}
STALE_NOTE = 'Saved observation; this program is not refreshed by the sixteen-calendar package.'


def classify_location(event):
    """Physical state evidence only. HOME and ambiguous venue names are not evidence."""
    row = deepcopy(event)
    location = str(row.get('location') or '').strip()
    in_state = bool(re.search(r'(?:^|,)\s*(?:Nebraska|Neb\.|NE)(?=\s*(?:$|,|\())', location, re.I))
    outside_states = r'AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC|Iowa|Kansas|Missouri|Colorado|South Dakota|North Dakota|Minnesota|Wisconsin|Illinois|Indiana|Michigan|Ohio|Pennsylvania|Texas|California|Florida|Arizona|Oregon|Washington|Kentucky|Tennessee|Oklahoma|Utah|Nevada|Wis\.|Ill\.|Ind\.|Mich\.|Minn\.|Colo\.|Calif\.|Fla\.|Ariz\.|Pa\.|Tenn\.|Okla\.|Ore\.|Wash\.|Kan\.|Mo\.|S\.D\.|N\.D\.|N\.Y\.|N\.J\.|Conn\.|R\.I\.'
    outside = bool(re.search(r'(?:^|,)\s*(?:' + outside_states + r')(?=\s*(?:$|,|\())', location, re.I))
    row['played_in_nebraska'] = in_state
    if in_state and not outside:
        row.update(site_test='NOT PERMISSIBLE', site_color='red', regulatory_site_label='PLAYED IN NEBRASKA')
    elif outside and not in_state:
        row.update(site_test='OK · OUTSIDE NEBRASKA', site_color='green', regulatory_site_label='OUTSIDE NEBRASKA')
    else:
        row.update(site_test='MANUAL LOCATION REVIEW', site_color='amber', regulatory_site_label='LOCATION UNRESOLVED')
        if in_state and outside:
            row['played_in_nebraska'] = False
            row['location_conflict_reason'] = 'Calendar location contains conflicting state evidence.'
    row['matchup_label'] = 'AT' if row.get('site') == 'AWAY' else 'VS' if row.get('site') in ('HOME', 'NEUTRAL') or row['played_in_nebraska'] else 'VS'
    return row


def build_snapshot(config, previous, previous_cache, now, get=requests.get):
    if now.tzinfo is None:
        raise ValueError('An aware refresh time is required')
    sources = config['sources']
    keys = [(s['school'], s['sport']) for s in sources]
    if len(keys) != 16 or set(keys) != EXPECTED:
        raise ValueError('Calendar configuration must contain the exact sixteen approved programs')
    today = now.astimezone(CT).date()
    end = today + timedelta(days=7)
    events, calendar_events, statuses, cache = [], [], [], {}
    prior_rows = previous.get('events', [])
    prior_calendar_rows = previous.get('calendar_events', prior_rows)
    for source in sources:
        key = (source['school'], source['sport'])
        old_cache = previous_cache.get('sources', {}).get(source['id'], {})
        result = collect_school_calendar(source, old_cache, now, get)
        status = {**result['source_status'], 'id': source['id'], 'school': key[0], 'sport': key[1]}
        rows = result['events']
        cache[source['id']] = result['cache']
        if not rows and not status.get('ok'):
            rows = [dict(e, source_stale=True, calendar_status='saved-before-calendar-integration') for e in prior_calendar_rows if (e.get('school'), e.get('sport')) == key]
        active_rows = [r for r in rows if str(r.get('status', '')).upper() not in {'CANCELLED', 'CANCELED', 'REMOVED', 'COMPLETED'}]
        dates = sorted(str(r['date']) for r in active_rows if r.get('date'))
        status['events_in_window'] = sum(today.isoformat() <= day <= end.isoformat() for day in dates)
        status['calendar_first_date'] = dates[0] if dates else None
        status['calendar_last_date'] = dates[-1] if dates else None
        status['coverage_note'] = ('Calendar contains only past dates; a future season has not been verified.' if dates and dates[-1] < today.isoformat() else 'No active calendar rows in this review window; absence of games is not established.' if not status['events_in_window'] else 'Published calendar rows in the review window; other eligibility checks still apply.')
        statuses.append(status)
        for event in rows:
            row = classify_location(event)
            row.update(source_id=source['id'], school=key[0], sport=key[1])
            if not status.get('ok'):
                row['source_stale'] = True
            calendar_events.append(deepcopy(row))
            if str(row.get('status', '')).upper() in {'CANCELLED', 'CANCELED', 'REMOVED', 'COMPLETED'}:
                continue
            if today.isoformat() <= str(row.get('date') or '') <= end.isoformat():
                events.append(row)
    # Preserve unrelated saved facts, clearly stale and never relabeled refreshed.
    for event in prior_rows:
        if (event.get('school'), event.get('sport')) not in EXPECTED:
            row = deepcopy(event)
            row.update(source_stale=True, collection_status_note=STALE_NOTE)
            if today.isoformat() <= str(row.get('date') or '') <= end.isoformat():
                events.append(row)
    seen = set()
    for row in events:
        identity = (row['school'], row['sport'], row.get('uid') or row.get('id') or (row.get('date'), row.get('opponent'), row.get('time')))
        if identity in seen:
            raise ValueError('Duplicate school-calendar event identity')
        seen.add(identity)
    events.sort(key=lambda e: (e.get('date', ''), e.get('start_time') or 'Z', e['school'], e['sport']))
    coverage = {school: {'configured': sum(s['school'] == school for s in statuses), 'loaded': sum(s['school'] == school and bool(s.get('ok')) for s in statuses)} for school in ('Nebraska', 'Creighton', 'Omaha')}
    return ({'schema_version': 2, 'generated_at': now.isoformat(), 'timezone': 'America/Chicago',
             'window_start': today.isoformat(), 'window_end': end.isoformat(), 'events': events,
             'calendar_events': calendar_events,
             'projection_note': 'The review window rolls over saved calendar rows without changing their source observation dates.',
             'sources': statuses, 'coverage': coverage, 'calendar_programs': [{'school': s, 'sport': p} for s, p in sorted(EXPECTED)],
             'calendar_note': 'Official calendar facts; refresh timestamps are not guarantees that the publisher updated its schedule. Unrelated saved programs remain stale.'},
            {'schema_version': 1, 'sources': cache})


def retain_futures(saved):
    result = deepcopy(saved)
    result.update(source_stale=True, collection_status_note='Saved cutoff evidence retained. Calendar subscriptions do not establish a complete regular-season or postseason opener; this package does not infer a new cutoff from the first future event.')
    for program in result.get('programs', []):
        program['source_stale'] = True
    return result


def main():
    install_network_guards()
    data = ROOT / 'data'
    def read(name, default):
        path = data / name
        return json.loads(path.read_text()) if path.exists() else default
    config = read('official-school-calendar-sources.json', {})
    snapshot, cache = build_snapshot(config, read('nebraska-collegiate-live.json', {}), read('official-school-calendar-cache.json', {}), datetime.now(timezone.utc))
    outputs = {'nebraska-collegiate-live.json': snapshot, 'official-school-calendar-cache.json': cache,
               'nebraska-collegiate-futures.json': retain_futures(read('nebraska-collegiate-futures.json', {}))}
    for name, payload in outputs.items():
        path = data / name
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(payload, indent=2) + '\n')
        temporary.replace(path)
    print(json.dumps({'programs': len(snapshot['sources']), 'healthy': sum(bool(s.get('ok')) for s in snapshot['sources']), 'events': len(snapshot['events'])}))


if __name__ == '__main__':
    main()
