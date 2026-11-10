"""Link exact official results to saved calendars without changing either source."""
from copy import deepcopy
import re
try:
    from school_event_history import capture_history
except ImportError:
    from scripts.school_event_history import capture_history


def compatible_location(calendar, result):
    """Literal same location or added venue detail; no geographical guessing."""
    def norm(value):
        return re.sub(r'\s+', ' ', str(value or '').casefold().replace('.', '')).strip()
    left, right = norm(calendar), norm(result)
    return bool(left and right and (left == right or right.startswith(left + ' / ') or right.startswith(left + ', ')))


def normalized_result(row, source, calendar_rows):
    result = {k: deepcopy(row[k]) for k in ('id', 'source_id', 'publisher_event_id', 'school', 'sport',
              'date', 'opponent', 'status', 'result', 'score', 'location', 'site', 'source_url',
              'source_links', 'evidence_kind')}
    result.update(uid='official-result-' + row['publisher_event_id'], school_id=source['school_id'],
                  sport_id=source['sport_id'], season_id='official-result:' + row['season'],
                  calendar_url=source['calendar_url'], date_only=True, time_unknown=True, start_time=None)
    matches = [r for r in calendar_rows if all(r.get(k) == result.get(k)
               for k in ('source_id', 'school', 'sport', 'date', 'opponent'))]
    result['calendar_link_status'] = 'unlinked' if not matches else 'ambiguous'
    if len(matches) == 1:
        match = matches[0]
        result.update(historical_calendar_uid=match['uid'], historical_calendar_source_id=source['id'],
                      calendar_location=match.get('location'))
        # REMOVED means absent, not cancelled. Explicit cancellation remains a
        # contradiction even if the independent result reports completion.
        result['calendar_link_status'] = ('exact' if compatible_location(match.get('location'), result['location'])
            and match.get('status') not in ('CANCELLED', 'CANCELED') else 'conflict')
    return result


def capture_result_history(source, calendar_cache, previous_results, collected, calendar_rows):
    """Append result versions/tombstones to the program ledger, never live rows."""
    current = [normalized_result(row, source, calendar_rows) for row in collected['events']]
    # Calendar subscriptions roll forward. Preserve a previously established
    # exact link when its row disappears; inspect its UID for contrary updates
    # instead of silently discarding linkage after a date/opponent correction.
    old_facts = {o['facts']['uid']: o['facts'] for o in calendar_cache.get('event_history', {}).get('observations', [])
                 if o.get('kind') == 'published'}
    for row in current:
        prior = old_facts.get(row['uid'], {})
        linked_uid = prior.get('historical_calendar_uid')
        if not linked_uid:
            continue
        linked = [r for r in calendar_rows if r.get('source_id') == source['id'] and r.get('uid') == linked_uid]
        if len(linked) == 1 and (any(linked[0].get(k) != row.get(k) for k in ('date', 'opponent'))
                or linked[0].get('status') in ('CANCELLED', 'CANCELED')
                or not compatible_location(linked[0].get('location'), row['location'])):
            row.update(historical_calendar_uid=linked_uid, historical_calendar_source_id=source['id'],
                       calendar_location=linked[0].get('location'), calendar_link_status='conflict')
        elif not linked and row['calendar_link_status'] == 'unlinked':
            row.update(historical_calendar_uid=linked_uid, historical_calendar_source_id=source['id'],
                       calendar_location=prior.get('calendar_location'),
                       calendar_link_status=prior.get('calendar_link_status', 'unlinked') if compatible_location(prior.get('calendar_location'), row['location']) else 'conflict')
    for row in current:
        linked_uid = row.get('historical_calendar_uid')
        if not linked_uid:
            continue
        linked_history = [o['facts'] for o in calendar_cache.get('event_history', {}).get('observations', [])
                          if o['facts'].get('uid') == linked_uid]
        times = {r.get('start_time') for r in linked_history if r.get('start_time')}
        if len(times) > 1 or any(
            any(r.get(k) != row.get(k) for k in ('source_id', 'school_id', 'school', 'sport_id', 'sport', 'date', 'opponent'))
            or r.get('status') in ('CANCELLED', 'CANCELED')
            or (r.get('site') in ('HOME', 'AWAY', 'NEUTRAL') and row.get('site') in ('HOME', 'AWAY', 'NEUTRAL') and r['site'] != row['site'])
            or (r.get('location') and row.get('location') and not compatible_location(r['location'], row['location']))
            for r in linked_history):
            row['calendar_link_status'] = 'conflict'
    rows = list(current)
    status = collected['source_status']
    if status.get('ok') and status.get('status') == 'current':
        ids = {row['uid'] for row in current}
        current_season = collected['cache'].get('season')
        for prior in previous_results.get('events', []):
            old = normalized_result(prior, source, calendar_rows)
            if old['uid'] not in ids and prior.get('season') == current_season:
                rows.append({**old, 'status': 'REMOVED', 'removal_observed_at': status['fetched_at']})
        # Old season records remain immutable. Absence after season rollover
        # does not assert disappearance from that old season's own schedule.
    wrapper = {'events': rows, 'source_status': deepcopy(status), 'cache': deepcopy(calendar_cache),
               'history_origin': 'validated-official-result'}
    captured = capture_history(calendar_cache, wrapper, source['id'])
    if status.get('integrity_hold'):
        captured['cache']['history_capture'].update(capture_status='degraded',
            reason='Official result source reported conflicting identity or result evidence; manual review required')
    return captured['cache']


REVIEWED_SEED_OBSERVED_AT = '2026-11-09T18:45:36.631287+00:00'


def seed_reviewed_result(source, calendar_cache, historical_cache, now, calendar_rows):
    """Migrate only the two already-reviewed real observations, without fetching.

    The existing adapters verified exact 2026 program/season titles and explicit
    completed results. Their caches did not retain a score: none is invented.
    This is a narrowly bounded migration, not a new per-game result collector.
    """
    try:
        from official_historical_school_result import SPECS
        from official_school_calendar import instant
    except ImportError:
        from scripts.official_historical_school_result import SPECS
        from scripts.official_school_calendar import instant
    for spec in SPECS:
        if source['id'] != spec['calendar_source_id']:
            continue
        saved = historical_cache.get(spec['source_id'], {})
        rows = saved.get('events', [])
        if len(rows) != 1 or saved.get('retry_after') or saved.get('last_error'):
            continue
        old = rows[0]
        stamp = saved.get('fetched_at')
        try:
            valid_time = (stamp == REVIEWED_SEED_OBSERVED_AT and old.get('fetched_at') == stamp
                and old.get('next_fetch_at') == saved.get('next_fetch_at')
                and instant(stamp) <= instant(now) < instant(saved['next_fetch_at']))
        except (ValueError, KeyError, TypeError):
            continue
        if not valid_time or old.get('source_stale'):
            continue
        exact = {**spec['expected'], 'source_id':spec['source_id'],
                 'id':spec['source_id'] + ':' + spec['event_id'],
                 'uid':'official-result-' + spec['event_id'], 'status':'COMPLETED',
                 'source_url':spec['url'], 'evidence_kind':'official-historical-result',
                 'historical_calendar_uid':spec['uid'],
                 'historical_calendar_source_id':spec['calendar_source_id'],
                 'official_result_location':spec['official_location']}
        if any(old.get(key) != value for key, value in exact.items()):
            continue
        if any(o['facts'].get('uid') == old['uid'] for o in calendar_cache.get('event_history', {}).get('observations', [])):
            continue
        candidates = [r for r in calendar_rows if r.get('uid') == spec['uid'] and
                      r.get('source_id') == source['id']]
        if len(candidates) != 1 or candidates[0].get('status') not in spec['original_statuses']:
            continue
        if any(candidates[0].get(key) != value for key, value in spec['expected'].items()):
            continue
        row = {'id':source['id'] + ':result:' + spec['event_id'], 'source_id':source['id'],
               'uid':old['uid'], 'publisher_event_id':spec['event_id'],
               'school':source['school'], 'school_id':source['school_id'],
               'sport':source['sport'], 'sport_id':source['sport_id'],
               'season_id':'official-result:2026', 'date':old['date'], 'opponent':old['opponent'],
               'location':old['official_result_location'], 'site':old['site'], 'status':'COMPLETED',
               'source_url':old['source_url'], 'calendar_url':source['calendar_url'],
               'evidence_kind':'official-school-result', 'date_only':True, 'time_unknown':True, 'start_time':None,
               'historical_calendar_uid':spec['uid'], 'historical_calendar_source_id':source['id'],
               'calendar_location':old['location'], 'calendar_link_status':'exact',
               'original_source_id':old['source_id'], 'original_event_id':old['id']}
        wrapper = {'events':[row], 'source_status':{'ok':True,'status':'current','fetched_at':stamp},
                   'cache':deepcopy(calendar_cache), 'history_origin':'reviewed-result-cache'}
        calendar_cache = capture_history(calendar_cache, wrapper, source['id'])['cache']
    return calendar_cache
