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
    from school_event_history import project_history
    from official_school_results import collect_program_results
    from school_result_history import capture_result_history, seed_reviewed_result
    from publisher_access_policy import install_network_guards
    from official_historical_school_result import collect_results
except ModuleNotFoundError:
    from scripts.official_school_calendar import collect_school_calendar
    from scripts.school_event_history import project_history
    from scripts.official_school_results import collect_program_results
    from scripts.school_result_history import capture_result_history, seed_reviewed_result
    from scripts.publisher_access_policy import install_network_guards
    from scripts.official_historical_school_result import collect_results

CT = ZoneInfo('America/Chicago')
ROOT = Path(__file__).resolve().parents[1]
CORE_SPORTS = {"Men's Basketball", "Women's Basketball", 'Volleyball', 'Baseball', 'Softball'}
EXPECTED = {(school, sport) for school in ('Nebraska', 'Creighton', 'Omaha') for sport in CORE_SPORTS} | {('Nebraska', 'Football')}
STALE_NOTE = 'Saved observation; this program is not refreshed by the sixteen-calendar package.'



# Physical jurisdiction tokens must be explicit at a comma/location boundary.
# All fifty states and DC; familiar postal and AP forms do not imply venue.
STATE_NAMES = {
 'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
 'CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia',
 'HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas',
 'KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts',
 'MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana',
 'NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico',
 'NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
 'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina',
 'SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont',
 'VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin',
 'WY':'Wyoming','DC':'District of Columbia',
}
STATE_AP = {'AL':'Ala.','AZ':'Ariz.','AR':'Ark.','CA':'Calif.','CO':'Colo.','CT':'Conn.',
 'DE':'Del.','FL':'Fla.','GA':'Ga.','IL':'Ill.','IN':'Ind.','KS':'Kan.','KY':'Ky.',
 'LA':'La.','MD':'Md.','MA':'Mass.','MI':'Mich.','MN':'Minn.','MS':'Miss.',
 'MO':'Mo.','MT':'Mont.','NE':'Neb.','NV':'Nev.','NH':'N.H.','NJ':'N.J.',
 'NM':'N.M.','NY':'N.Y.','NC':'N.C.','ND':'N.D.','OK':'Okla.','OR':'Ore.',
 'PA':'Pa.','RI':'R.I.','SC':'S.C.','SD':'S.D.','TN':'Tenn.','VT':'Vt.',
 'VA':'Va.','WA':'Wash.','WV':'W.Va.','WI':'Wis.','WY':'Wyo.','DC':'D.C.'}


def physical_states(location):
    return {code for code, name in STATE_NAMES.items() if re.search(
        r'(?:^|[,/])\s*(?:' + '|'.join(re.escape(v) for v in
            (code, name, STATE_AP.get(code, code))) + r')(?=\s*(?:$|,|\(|/))', location, re.I)}


def classify_location(event):
    """Physical state evidence only. HOME and ambiguous venue names are not evidence."""
    row = deepcopy(event)
    location = str(row.get('location') or '').strip()
    states = physical_states(location)
    in_state = 'NE' in states
    outside = bool(states - {'NE'})
    row['played_in_nebraska'] = in_state
    if states == {'NE'}:
        row.update(site_test='NOT PERMISSIBLE', site_color='red', regulatory_site_label='PLAYED IN NEBRASKA')
    elif len(states) == 1 and outside:
        row.update(site_test='OK · OUTSIDE NEBRASKA', site_color='green', regulatory_site_label='OUTSIDE NEBRASKA')
    else:
        row.update(site_test='MANUAL LOCATION REVIEW', site_color='amber', regulatory_site_label='LOCATION UNRESOLVED')
        if len(states) > 1:
            row['played_in_nebraska'] = False
            row['location_conflict_reason'] = 'Calendar location contains conflicting state evidence.'
    row['matchup_label'] = 'AT' if row.get('site') == 'AWAY' else 'VS' if row.get('site') in ('HOME', 'NEUTRAL') or row['played_in_nebraska'] else 'VS'
    return row


def build_snapshot(config, previous, previous_cache, now, get=requests.get):
    if now.tzinfo is None:
        raise ValueError('An aware refresh time is required')
    # The existing narrow timing adapters and generalized result collector may
    # use the same official page. One permitted request per URL per run.
    original_get, responses = get, {}
    def get(url, **kwargs):
        if url not in responses:
            try:
                responses[url] = (True, original_get(url, **kwargs))
            except Exception as exc:
                responses[url] = (False, exc)
        ok, value = responses[url]
        if not ok:
            raise value
        return value
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
    official_result_cache, official_result_status = {}, []
    for source in sources:
        if source.get('discovery_kind') != 'wmt-rolling':
            continue
        cache[source['id']] = seed_reviewed_result(source, cache[source['id']],
            previous_cache.get('historical_result', {}), now, calendar_events)
        saved = previous_cache.get('official_results', {}).get(source['id'], {})
        if not saved:
            # Starting the general collector does not reset an existing page's
            # publisher cooldown established by the narrow result adapters.
            old_results = previous_cache.get('historical_result', {})
            matching = [entry for entry in old_results.values() if any(
                row.get('source_url') == source['schedule_url'] for row in entry.get('events', []))]
            deadlines = [entry.get('retry_after') or entry.get('next_fetch_at') for entry in matching]
            deadlines = [deadline for deadline in deadlines if deadline]
            if deadlines:
                saved = {'source_id': source['id'], 'events': [], 'next_fetch_at': max(deadlines)}
        result_source = {**source, 'result_season_dates': sorted({row['date'] for row in calendar_events
            if row.get('source_id') == source['id'] and not row.get('source_stale') and row.get('date')})}
        result = collect_program_results(result_source, saved, now, get)
        official_result_cache[source['id']] = result['cache']
        official_result_status.append(result['source_status'])
        cache[source['id']] = capture_result_history(source, cache[source['id']], saved, result, calendar_events)

    historical_rows, historical_status, historical_cache = collect_results(
        calendar_events, previous_cache.get('historical_result', {}), now, get)
    historical_rows = [classify_location(row) for row in historical_rows]
    coverage = {school: {'configured': sum(s['school'] == school for s in statuses), 'loaded': sum(s['school'] == school and bool(s.get('ok')) for s in statuses)} for school in ('Nebraska', 'Creighton', 'Omaha')}
    return ({'schema_version': 2, 'generated_at': now.isoformat(), 'timezone': 'America/Chicago',
             'window_start': today.isoformat(), 'window_end': end.isoformat(), 'events': events,
             'calendar_events': calendar_events,
             'event_history': project_history(cache, today, classify_location),
             'historical_events': historical_rows, 'historical_sources': historical_status,
             'official_result_sources': official_result_status,
             'projection_note': 'The review window rolls over saved calendar rows without changing their source observation dates.',
             'sources': statuses, 'coverage': coverage, 'calendar_programs': [{'school': s, 'sport': p} for s, p in sorted(EXPECTED)],
             'calendar_note': 'Official calendar facts; refresh timestamps are not guarantees that the publisher updated its schedule. Unrelated saved programs remain stale.'},
            {'schema_version': 1, 'sources': cache, 'historical_result': historical_cache, 'official_results': official_result_cache})


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
