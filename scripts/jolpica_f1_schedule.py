"""Inactive, injectable Jolpica schedule adapter. No default transport or CLI.

Data remains a separate CC BY-NC-SA 4.0 dataset. Nothing imports this module
from a collector or workflow. The caller must separately authorize activation.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo

SOURCE = 'jolpica-f1'
IDENTITY = 'motorsports-intl-f1'
ENDPOINT = 'https://api.jolpi.ca/ergast/f1/current/races/'
LICENSE = {
    'id': 'CC-BY-NC-SA-4.0',
    'url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'attribution': 'F1 schedule data: Jolpica-F1',
    'source_url': 'https://github.com/jolpica/jolpica-f1',
    'terms_url': 'https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md',
    'changes': 'Selected race schedule facts; normalized dates and filtered review window.',
    'notice': 'Provided without warranty; Jolpica does not endorse this tool.',
}
MAX_ROWS = 100
MAX_BYTES = 2_000_000
CACHE_HOURS = 24


def aware(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('aware_timestamp_required')
    return value.astimezone(timezone.utc)


def stamp(value):
    return aware(value).isoformat().replace('+00:00', 'Z')


def text(value, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('invalid_text')
    if any(ord(c) < 32 for c in value):
        raise ValueError('invalid_text')
    return value.strip()


def positive(value):
    if isinstance(value, bool) or not re.fullmatch(r'[1-9][0-9]{0,3}', str(value)):
        raise ValueError('invalid_integer')
    return int(value)


def review_window(now):
    local = aware(now).astimezone(ZoneInfo('America/Chicago'))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc), (start + timedelta(days=8)).astimezone(timezone.utc)


def normalize_races(payload, observed_at, window_start, window_end, now=None):
    """Validate one complete current-season response; emit race facts only."""
    observed = aware(observed_at)
    now = aware(now) if now is not None else observed
    start, end = aware(window_start), aware(window_end)
    if observed > now or end <= start:
        raise ValueError('invalid_observation_or_window')
    if not isinstance(payload, dict) or not isinstance(payload.get('MRData'), dict):
        raise ValueError('invalid_payload')
    root = payload['MRData']
    if root.get('series') != 'f1' or str(root.get('offset')) != '0':
        raise ValueError('invalid_series_or_offset')
    table = root.get('RaceTable')
    if not isinstance(table, dict):
        raise ValueError('invalid_table')
    season = positive(table.get('season'))
    rows = table.get('Races')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError('empty_or_oversized_schedule')
    if positive(root.get('total')) != len(rows):
        raise ValueError('incomplete_schedule')
    if season < now.year or season > now.year + 1:
        raise ValueError('unexpected_season')
    by_round = {}
    for raw in rows:
        if not isinstance(raw, dict) or positive(raw.get('season')) != season:
            raise ValueError('mixed_season')
        round_no = positive(raw.get('round'))
        circuit = raw.get('Circuit')
        if not isinstance(circuit, dict):
            raise ValueError('missing_circuit')
        cid = text(circuit.get('circuitId'), 80)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', cid):
            raise ValueError('invalid_circuit')
        date = text(raw.get('date'), 10)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            raise ValueError('invalid_date')
        day = datetime.strptime(date, '%Y-%m-%d').date()
        if day.year != season:
            raise ValueError('season_date_conflict')
        time = raw.get('time')
        if time is not None:
            if not isinstance(time, str) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}Z', time):
                raise ValueError('invalid_time')
            kickoff = aware(date + 'T' + time)
            in_window = start <= kickoff < end
        else:
            kickoff = None
            in_window = start.astimezone(ZoneInfo('America/Chicago')).date() <= day < end.astimezone(ZoneInfo('America/Chicago')).date()
        location = circuit.get('Location') or {}
        if not isinstance(location, dict):
            raise ValueError('invalid_location')
        event = {
            'id': f'{SOURCE}:{season}:{round_no}:{cid}', 'source_id': SOURCE,
            'catalog_identity_key': IDENTITY, 'provider': 'Jolpica-F1',
            'sport': 'Motorsports', 'league': 'Formula One (F1)',
            'name': text(raw.get('raceName')), 'season': str(season),
            'round': round_no, 'circuit_id': cid,
            'circuit': text(circuit.get('circuitName')), 'date': date,
            'start_time': stamp(kickoff) if kickoff else None,
            'date_only': kickoff is None, 'status': 'UNKNOWN',
            'observed_at': stamp(observed), 'source_stale': False,
            'source_url': ENDPOINT, 'coverage_status': 'partial',
            'coverage_complete': False, 'license_id': LICENSE['id'],
            'source_updated_at': None,
        }
        for field in ('locality', 'country'):
            if location.get(field) is not None:
                event[field] = text(location[field])
        if round_no in by_round and by_round[round_no][0] != event:
            raise ValueError('conflicting_round')
        by_round[round_no] = (event, in_window)
    events = [event for event, keep in by_round.values() if keep]
    events.sort(key=lambda x: (x['date'], x['start_time'] or '', x['id']))
    return {'schema_version': 1, 'provider': 'Jolpica-F1', 'source_id': SOURCE,
            'catalog_identity_key': IDENTITY, 'season': str(season),
            'observed_at': stamp(observed), 'window_start': stamp(start),
            'window_end': stamp(end), 'events': events,
            'license': deepcopy(LICENSE), 'dataset_scope': 'isolated_jolpica_f1_only',
            'source_health': {'status': 'partial', 'event_count': len(events),
                              'season_rows': len(by_round), 'reason': 'race_schedule_only'}}


def _validate_previous(previous, now):
    if previous == {} and isinstance(previous, dict):
        return {}
    if not isinstance(previous, dict) or previous.get('source_id') != SOURCE:
        raise ValueError('invalid_previous')
    if previous.get('schema_version') != 1 or type(previous.get('schema_version')) is not int or previous.get('provider') != 'Jolpica-F1' or previous.get('catalog_identity_key') != IDENTITY or previous.get('dataset_scope') != 'isolated_jolpica_f1_only':
        raise ValueError('invalid_previous_schema')
    if previous.get('observed_at') is not None and aware(previous['observed_at']) > now:
        raise ValueError('invalid_previous_observation')
    state = previous.get('collector_state')
    if not isinstance(state, dict) or type(state.get('halted')) is not bool:
        raise ValueError('invalid_previous_state')
    last, nxt = aware(state['last_attempt_at']), aware(state['next_fetch_at'])
    if last > now or nxt < last + timedelta(hours=CACHE_HOURS):
        raise ValueError('invalid_cooldown')
    if previous.get('license') != LICENSE or not isinstance(previous.get('events'), list) or len(previous['events']) > MAX_ROWS:
        raise ValueError('invalid_previous_dataset')
    for event in previous['events']:
        if event.get('source_id') != SOURCE or event.get('catalog_identity_key') != IDENTITY or aware(event['observed_at']) > now:
            raise ValueError('invalid_previous_event')
    allowed_top = ('schema_version', 'provider', 'source_id', 'catalog_identity_key',
                   'season', 'observed_at', 'window_start', 'window_end', 'events',
                   'license', 'dataset_scope', 'source_health')
    clean = {key: deepcopy(previous[key]) for key in allowed_top if key in previous}
    clean['collector_state'] = {'halted': state['halted'],
                                'last_attempt_at': stamp(last), 'next_fetch_at': stamp(nxt)}
    allowed_event = {'id', 'source_id', 'catalog_identity_key', 'provider', 'sport', 'league',
                     'name', 'season', 'round', 'circuit_id', 'circuit', 'date', 'start_time',
                     'date_only', 'status', 'observed_at', 'source_stale', 'source_url',
                     'coverage_status', 'coverage_complete', 'license_id', 'source_updated_at',
                     'locality', 'country'}
    for event in clean['events']:
        for key in list(event):
            if key not in allowed_event:
                del event[key]
        season, round_no = positive(event['season']), positive(event['round'])
        cid = text(event['circuit_id'], 80)
        if event['id'] != f'{SOURCE}:{season}:{round_no}:{cid}' or event['status'] != 'UNKNOWN':
            raise ValueError('invalid_previous_identity')
        datetime.strptime(event['date'], '%Y-%m-%d')
        if event['start_time'] is not None:
            parsed = aware(event['start_time'])
            if str(parsed.date()) != event['date']:
                raise ValueError('invalid_previous_date')
        if type(event.get('date_only')) is not bool or event['date_only'] != (event['start_time'] is None):
            raise ValueError('invalid_previous_precision')
        if type(event.get('source_stale')) is not bool or event.get('license_id') != LICENSE['id']:
            raise ValueError('invalid_previous_metadata')
        if event.get('coverage_complete') is not False or event.get('source_url') != ENDPOINT:
            raise ValueError('invalid_previous_scope')
    clean['license'] = deepcopy(LICENSE)
    old_health = previous.get('source_health', {})
    if not isinstance(old_health, dict) or old_health.get('status') not in ('partial', 'stale', 'paused', 'cached'):
        raise ValueError('invalid_previous_health')
    clean['source_health'] = {'status': old_health['status'], 'event_count': len(clean['events']),
                              'reason': 'cached_schedule' if old_health['status'] in ('partial', 'cached') else 'retained_source_hold'}
    return clean


def collect_schedule(previous, now, get=None):
    """Injectable only. get(url, timeout, allow_redirects, max_bytes) -> dict.

    Transport response: {status_code:int, headers:dict, payload:dict, body_bytes:int}.
    Caller must enforce max_bytes while reading. No default network transport.
    """
    now = aware(now)
    if get is None:
        raise ValueError('transport_not_configured')
    previous = _validate_previous(previous, now)
    state = previous.get('collector_state', {})
    start, end = review_window(now)
    if state.get('halted') or (state and now < aware(state['next_fetch_at'])):
        previous['events'] = [e for e in previous['events'] if _in_window(e, start, end)]
        previous['window_start'], previous['window_end'] = stamp(start), stamp(end)
        previous['source_health']['event_count'] = len(previous['events'])
        if state.get('halted'):
            previous['source_health'].update(status='paused', reason='persistent_access_hold')
            for event in previous['events']:
                event['source_stale'] = True
        return previous
    attempted = get is not None
    reason, halted = 'not_activated', False
    fresh = None
    cooldown = timedelta(hours=CACHE_HOURS)
    if attempted:
        try:
            response = get(ENDPOINT, timeout=30, allow_redirects=False, max_bytes=MAX_BYTES)
            code = response['status_code']
            if code in (401, 403) or 300 <= code < 400:
                reason, halted = 'access_hold', True
            elif code == 429:
                reason = 'rate_limit_hold'
                retry = response.get('headers', {}).get('Retry-After')
                if retry is not None:
                    if not str(retry).isdigit() or int(retry) > 7 * 86400:
                        halted = True
                    else:
                        cooldown = max(cooldown, timedelta(seconds=int(retry)))
            elif code != 200:
                reason = 'provider_error'
            elif type(response.get('body_bytes')) is not int or not 0 <= response['body_bytes'] <= MAX_BYTES:
                reason = 'response_size_hold'
            else:
                fresh = normalize_races(response['payload'], now, start, end, now=now)
        except Exception:
            reason = 'invalid_or_unavailable_schedule'
    if fresh:
        all_rows = response['payload']['MRData']['RaceTable']['Races']
        fresh_ids = {f"{SOURCE}:{positive(r['season'])}:{positive(r['round'])}:{r['Circuit']['circuitId']}" for r in all_rows}
        # Same round with changed circuit is ambiguous; do not silently replace it.
        old_rounds = {(e['season'], e['round']): e['circuit_id'] for e in previous.get('events', [])}
        if any(old_rounds.get((str(r['season']), positive(r['round'])), r['Circuit']['circuitId']) != r['Circuit']['circuitId'] for r in all_rows):
            fresh, reason = None, 'identity_conflict'
        else:
            # Omission does not prove cancellation, even across season rollover.
            for old in previous.get('events', []):
                if old['id'] not in fresh_ids and _in_window(old, start, end):
                    saved = deepcopy(old); saved['source_stale'] = True
                    fresh['events'].append(saved)
    result = fresh or deepcopy(previous) or {
        'schema_version': 1, 'provider': 'Jolpica-F1', 'source_id': SOURCE,
        'catalog_identity_key': IDENTITY, 'events': [], 'license': deepcopy(LICENSE),
        'dataset_scope': 'isolated_jolpica_f1_only', 'observed_at': None,
    }
    result['window_start'], result['window_end'] = stamp(start), stamp(end)
    result['events'] = [e for e in result['events'] if _in_window(e, start, end)]
    if not fresh:
        for event in result['events']:
            event['source_stale'] = True
    result['source_health'] = {'status': 'partial' if fresh else 'paused' if halted or not attempted else 'stale',
                               'reason': 'race_schedule_only' if fresh else reason,
                               'event_count': len(result['events']),
                               'stale_event_count': sum(e['source_stale'] for e in result['events'])}
    # No transport is installed: no attempt, so no polling cooldown fabricated.
    if attempted:
        result['collector_state'] = {'halted': halted, 'last_attempt_at': stamp(now),
                                     'next_fetch_at': stamp(now + cooldown)}
    elif not state:
        result['collector_state'] = {'halted': False, 'last_attempt_at': stamp(now),
                                     'next_fetch_at': stamp(now + timedelta(hours=CACHE_HOURS)),
                                     'activation_required': True}
    return result


def _in_window(event, start, end):
    if event.get('start_time'):
        return start <= aware(event['start_time']) < end
    day = datetime.strptime(event['date'], '%Y-%m-%d').date()
    zone = ZoneInfo('America/Chicago')
    return start.astimezone(zone).date() <= day < end.astimezone(zone).date()
