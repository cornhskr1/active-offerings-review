"""Bounded schedule-only collector. Tests inject transport; imports perform no I/O.

Only the sports directory and exact event-list routes exist here. No odds route,
bookmaker payload, credential persistence, or cancellation inference is supported.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
try:
    from .odds_api_adapter import normalize_snapshot, _mapping_index, _timestamp, _iso
except ImportError:
    from odds_api_adapter import normalize_snapshot, _mapping_index, _timestamp, _iso

ORIGIN = 'https://api.the-odds-api.com'
INTERVAL = dt.timedelta(hours=3)
UTC = dt.timezone.utc
CT = ZoneInfo('America/Chicago')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Response:
    def __init__(self, response):
        self.response = response
        self.status_code = response.code
        self.headers = dict(response.headers)
    def json(self):
        body = self.response.read(8_000_001)
        if len(body) > 8_000_000:
            raise ValueError('response_too_large')
        return json.loads(body)
    def close(self):
        self.response.close()

def provider_get(url, params, timeout=30, allow_redirects=False):
    """The only credential transmission point. Never log URL or exceptions."""
    if allow_redirects or not re.fullmatch(re.escape(ORIGIN) + r'/v4/(?:sports/|sports/[a-z0-9_]+/events)', url):
        raise ValueError('unsupported_provider_route')
    request = Request(url + '?' + urlencode(params), method='GET')
    try:
        return Response(build_opener(NoRedirect()).open(request, timeout=timeout))
    except HTTPError as response:
        return Response(response)


def _due(value, now):
    if not value:
        return True
    try:
        return now >= _timestamp(value)
    except ValueError:
        return False  # Corrupt cooldown cannot silently authorize another call.


def _clean_state(raw, keys):
    """Never republish arbitrary prior metadata, raw errors, or credentials."""
    raw = raw if isinstance(raw, dict) else {}
    state = {'schema_version': 1, 'sources': {}, 'directory': {}}
    if (raw.get('schema_version') != 1 or type(raw.get('schema_version')) is not int
            or not isinstance(raw.get('sources'), dict) or not isinstance(raw.get('directory'), dict)
            or set(raw.get('sources', {})) != set(keys)):
        state.update(halted=True, stop_reason='invalid_control_state')
    if 'halted' in raw and type(raw['halted']) is not bool:
        state.update(halted=True, stop_reason='invalid_control_state')
    if raw.get('halted') is True:
        state['halted'] = True
        state['stop_reason'] = 'persistent_hold_requires_explicit_recovery'
    for field in ('stopped_at', 'family_next_fetch_at'):
        if field in raw:
            try: state[field] = _iso(_timestamp(raw[field]))
            except ValueError:
                state.update(halted=True, stop_reason='invalid_control_state')
    def record(value):
        if not isinstance(value, dict):
            state.update(halted=True, stop_reason='invalid_control_state')
            return {}
        clean = {}
        if value.get('status') in ('ok','failed'):
            required = {'last_attempt_at','next_fetch_at'}
            if value['status'] == 'ok': required.update({'observed_at','last_request_credits'})
            if value['status'] == 'failed' and raw.get('halted') is not True:
                required.add('last_request_credits')
            if not required.issubset(value): state.update(halted=True, stop_reason='invalid_control_state')
        elif value.get('status') not in (None,'not_active_in_directory','not_checked'):
            state.update(halted=True, stop_reason='invalid_control_state')
        for field in ('observed_at','last_attempt_at','next_fetch_at'):
            if field in value:
                try: clean[field] = _iso(_timestamp(value[field]))
                except ValueError: state.update(halted=True, stop_reason='invalid_control_state')
        status = value.get('status')
        if status in ('ok','failed','not_active_in_directory','not_checked'):
            clean['status'] = status
        if status != 'ok': clean['reason'] = 'previous_observation_not_current'
        for field in ('last_request_credits','received_events'):
            if field in value and (type(value[field]) is not int or value[field] < 0):
                state.update(halted=True, stop_reason='invalid_control_state')
            if type(value.get(field)) is int and value[field] >= 0:
                clean[field] = value[field]
                if field == 'last_request_credits' and value[field] != 0:
                    state.update(halted=True, stop_reason='previous_cost_not_zero')
        return clean
    source_rows = raw.get('sources', {})
    if isinstance(source_rows, dict):
        state['sources'] = {k:record(source_rows[k]) for k in keys if k in source_rows}
    directory = raw.get('directory', {})
    state['directory'] = record(directory)
    if isinstance(directory, dict) and isinstance(directory.get('sports'), dict):
        state['directory']['sports'] = {k:v for k,v in directory['sports'].items() if k in keys and type(v) is bool}
    return state


def collect_events(config, previous, now, api_key, get=provider_get):
    """Return a minimal public snapshot with nonsecret persistent control metadata.

    `previous` is the prior automated snapshot. Only an explicit empty object
    bootstraps collection. A public UI snapshot lacking valid collector control
    state seeds stale observations but fails closed until explicit recovery.
    Persistent halt requires explicit operator recovery of the cache; time alone
    never clears it. All failures retain original observations as stale.
    """
    if not isinstance(now, dt.datetime) or now.tzinfo is None:
        raise ValueError('aware_now_required')
    now = now.astimezone(UTC)
    _mapping_index(config)
    keys = [m['provider_key'] for m in config['mappings']]
    if len(keys) != 85:
        raise ValueError('exact_85_mapping_required')
    bootstrap = isinstance(previous, dict) and previous == {}
    prior = previous if isinstance(previous, dict) else {'collector_state':None}
    control = {'schema_version':1,'sources':{key:{} for key in keys},'directory':{}} if bootstrap else prior.get('collector_state')
    state = _clean_state(control, keys)
    for record in [state['directory'], *state['sources'].values()]:
        if any(field in record and _timestamp(record[field]) > now for field in ('observed_at','last_attempt_at')):
            state.update(halted=True, stop_reason='invalid_control_state')
        if 'last_attempt_at' in record and 'next_fetch_at' in record and _timestamp(record['next_fetch_at']) < _timestamp(record['last_attempt_at']) + INTERVAL:
            state.update(halted=True, stop_reason='invalid_control_state')
    held = state.get('halted') is True
    today = now.astimezone(CT).date()
    start = dt.datetime.combine(today, dt.time(), CT).astimezone(UTC)
    end = dt.datetime.combine(today + dt.timedelta(days=8), dt.time(), CT).astimezone(UTC)
    # Preserve only allowlisted normalized fields from old public/cache data.
    old = prior.get('events', [])
    if not isinstance(old, list):
        old = []
    saved = {}
    for key in keys:
        group = [e for e in old if isinstance(e, dict) and e.get('provider_key') == key]
        clean = []
        for e in group:
            try:
                observed = _timestamp(e.get('observed_at'))
                if observed > now: continue
                raw = {'id': e.get('provider_event_id'), 'sport_key': key,
                       'away_team': e.get('participants', [])[0], 'home_team': e.get('participants', [])[1],
                       'commence_time': e.get('start_time')}
                clean.extend(normalize_snapshot([raw], key, _iso(observed), config)['events'])
            except (ValueError, IndexError, TypeError):
                continue
        saved[key] = clean
    requests = 0
    def stop(reason, persistent=True):
        nonlocal held
        held = True
        state['stop_reason'] = reason
        state['stopped_at'] = _iso(now)
        if persistent: state['halted'] = True
        else: state['family_next_fetch_at'] = _iso(now + INTERVAL)
    def request(path, record):
        nonlocal requests
        record['last_attempt_at'] = _iso(now)
        record['next_fetch_at'] = _iso(now + INTERVAL)
        record['status'] = 'failed'
        response = None
        try:
            requests += 1
            response = get(ORIGIN + path, {'apiKey': api_key}, timeout=30, allow_redirects=False)
            status = response.status_code
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            if status in (401, 403):
                record['reason'] = 'provider_auth_or_access_hold'; stop(record['reason']); return None
            cost = headers.get('x-requests-last')
            if cost is None or not re.fullmatch(r'\d+', cost) or int(cost) != 0:
                record['reason'] = 'zero_credit_header_not_verified'; stop(record['reason']); return None
            record['last_request_credits'] = 0
            if 300 <= status < 400:
                record['reason'] = 'redirect_rejected'; stop(record['reason']); return None
            if status == 429:
                retry = headers.get('retry-after', '')
                delay = max(10800, int(retry)) if re.fullmatch(r'\d+', retry) else 10800
                record['reason'] = 'rate_limit_cooldown'
                if delay > 604800:
                    stop('rate_limit_manual_recovery_required')
                else:
                    stop(record['reason'], False)
                    state['family_next_fetch_at'] = _iso(now + dt.timedelta(seconds=delay))
                    record['next_fetch_at'] = state['family_next_fetch_at']
                return None
            if status != 200:
                record['reason'] = 'provider_http_failure'; return None
            body = response.json()  # Never read a body until last-request cost is zero.
            if not isinstance(body, list):
                record['reason'] = 'invalid_response_shape'; return None
            return body
        except Exception:
            # Exception text can contain the credential-bearing URL: never retain it.
            record['reason'] = 'request_outcome_unverified'; stop(record['reason']); return None
        finally:
            if response is not None and callable(getattr(response, 'close', None)):
                try: response.close()
                except Exception: pass
    directory = state['directory']
    if not isinstance(api_key, str) or not api_key.strip():
        held = True
        state['stop_reason'] = 'credential_not_configured'
    if not _due(state.get('family_next_fetch_at'), now):
        held = True
    if not held and _due(directory.get('next_fetch_at'), now):
        body = request('/v4/sports/', directory)
        if body is not None:
            valid = all(isinstance(r, dict) and isinstance(r.get('key'), str) and type(r.get('active')) is bool for r in body)
            if not valid:
                directory['reason'] = 'invalid_directory'; stop('invalid_directory', False)
            else:
                directory['sports'] = {r['key']: r['active'] for r in body if r['key'] in keys}
                directory.update(status='ok', observed_at=_iso(now), reason='')
    sports = directory.get('sports', {})
    directory_usable = directory.get('status') == 'ok' and isinstance(sports, dict)
    for key in keys:
        record = state['sources'].setdefault(key, {})
        if held or not directory_usable or not _due(record.get('next_fetch_at'), now): continue
        if sports.get(key) is not True:
            record.update(status='not_active_in_directory', reason='No event request made; this does not establish offseason or cancellation.')
            continue
        body = request('/v4/sports/' + key + '/events', record)
        if body is None: continue
        result = normalize_snapshot(body, key, _iso(now), config)
        if result['rejected']:
            record.update(status='failed', reason='event_validation_failed'); continue
        # Omission is not cancellation. Retain prior IDs, with original times/stale.
        current = {e['provider_event_id']: e for e in result['events']}
        for e in saved[key]:
            current.setdefault(e['provider_event_id'], e)
        saved[key] = list(current.values())
        record.update(status='ok', observed_at=_iso(now), reason='', received_events=len(body))
    events, health = [], []
    for key in keys:
        record = state['sources'].get(key, {})
        for e in saved[key]:
            if not start <= _timestamp(e['start_time']) < end: continue
            event = dict(e)
            event['source_stale'] = held or record.get('status') != 'ok' or e['observed_at'] != record.get('observed_at') or _due(record.get('next_fetch_at'), now)
            events.append(event)
        health.append({'provider_key':key, 'status':record.get('status','not_checked'),
                       'observed_at':record.get('observed_at'), 'last_attempt_at':record.get('last_attempt_at'), 'next_fetch_at':record.get('next_fetch_at'),
                       'event_count':sum(e['provider_key']==key for e in events),
                       'reason':record.get('reason',''), 'stale':held or record.get('status')!='ok' or _due(record.get('next_fetch_at'),now)})
    snapshot = {'schema_version':1,'provider':'The Odds API','observed_at':_iso(now),
                'window_start':today.isoformat(),'window_end':(today+dt.timedelta(days=7)).isoformat(),
                'events':sorted(events,key=lambda e:(e['start_time'],e['id'])), 'sources':health,
                'coverage':{'coverage_complete':False,'coverage_status':'partial','collection_halted':bool(state.get('halted')),
                            'stop_reason':state.get('stop_reason',''),'requests_this_run':requests,
                            'note':'Schedule observations only. Omitted events are not inferred cancelled; original observation times are retained.'}}
    # Cache contains normalized window events and control metadata only; never raw responses.
    snapshot['collector_state'] = state
    return snapshot


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Schedule-only, zero-credit-guarded event refresh')
    parser.add_argument('--config', required=True)
    parser.add_argument('--previous', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        previous = json.loads(Path(args.previous).read_text())
        result = collect_events(json.loads(Path(args.config).read_text()), previous,
                                dt.datetime.now(UTC), os.environ.get('ODDS_API_KEY'))
        for path, body in ((args.output,result),):
            target=Path(path); target.parent.mkdir(parents=True, exist_ok=True)
            temporary=target.with_name(target.name+'.tmp'); temporary.write_text(json.dumps(body,indent=2)+'\n'); temporary.replace(target)
    except Exception:
        raise SystemExit('Schedule refresh failed; details suppressed to protect credentials.') from None

if __name__ == '__main__':
    main()
