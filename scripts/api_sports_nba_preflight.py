"""One daily authenticated NBA capability check; never emits approved fixtures.

The provider's free/current-season access and exact response identities must be
reviewed before activating a fixture adapter. Never log response bodies or keys.
"""
import datetime as dt
import re
try:
    from .preflight_diagnostics import PreflightError, record_failure, restore_failure, validate_quota
except ImportError:
    from preflight_diagnostics import PreflightError, record_failure, restore_failure, validate_quota

ENDPOINT = 'https://v2.nba.api-sports.io/games'
SOURCE_ID = 'api-sports-nba-preflight'
UTC = dt.timezone.utc
TEAM_NAMES = frozenset(('Atlanta Hawks|Boston Celtics|Brooklyn Nets|Charlotte Hornets|Chicago Bulls|Cleveland Cavaliers|Dallas Mavericks|Denver Nuggets|Detroit Pistons|Golden State Warriors|Houston Rockets|Indiana Pacers|LA Clippers|Los Angeles Lakers|Memphis Grizzlies|Miami Heat|Milwaukee Bucks|Minnesota Timberwolves|New Orleans Pelicans|New York Knicks|Oklahoma City Thunder|Orlando Magic|Philadelphia 76ers|Phoenix Suns|Portland Trail Blazers|Sacramento Kings|San Antonio Spurs|Toronto Raptors|Utah Jazz|Washington Wizards').split('|'))


def aware(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)', value):
        raise ValueError('NBA date lacks an explicit timezone')
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)


def positive(value):
    return type(value) is int and value > 0


def inspect_payload(payload, season, now):
    """Whitelist schedule diagnostics only; no personnel, scores, logos or raw errors."""
    if not isinstance(payload, dict) or payload.get('errors') not in ([], {}):
        raise PreflightError('nba_provider_rejected')
    if payload.get('get') not in ('games', 'games/') or payload.get('parameters') != {'league': 'standard', 'season': str(season)}:
        raise PreflightError('nba_query_changed')
    rows = payload.get('response')
    if isinstance(rows, list) and not rows and type(payload.get('results')) is int and payload['results'] == 0:
        raise PreflightError('nba_rows_empty')
    if not isinstance(rows, list) or not 0 < len(rows) <= 5000 or type(payload.get('results')) is not int or payload['results'] != len(rows):
        raise PreflightError('nba_rows_invalid')
    seen = set(); previews = []; stages = {}; states = {}; ids = {}
    for row in rows:
        if not isinstance(row, dict) or not positive(row.get('id')) or row['id'] in seen or row.get('league') != 'standard' or type(row.get('season')) is not int or row['season'] != season:
            raise PreflightError('nba_identity_changed')
        seen.add(row['id'])
        try:
            when = aware((row.get('date') or {}).get('start'))
        except (ValueError, TypeError, AttributeError):
            raise PreflightError('nba_start_invalid') from None
        if not dt.datetime(season, 7, 1, tzinfo=UTC) <= when < dt.datetime(season + 1, 8, 1, tzinfo=UTC):
            raise PreflightError('nba_date_outside_season')
        stage = row.get('stage'); state = (row.get('status') or {}).get('short')
        if type(stage) is not int or not 1 <= stage <= 10 or type(state) is not int or state not in range(1, 7):
            raise PreflightError('nba_state_unrecognized')
        teams = row.get('teams') or {}; pair = []
        for side in ('visitors', 'home'):
            team = teams.get(side) or {}; tid = team.get('id'); name = team.get('name')
            if not positive(tid) or name not in TEAM_NAMES or (tid in ids and ids[tid] != name) or (name in ids.values() and ids.get(tid) != name):
                raise PreflightError('nba_participant_unverified')
            ids[tid] = name; pair.append({'id': tid, 'name': name})
        if pair[0]['id'] == pair[1]['id']:
            raise PreflightError('nba_participant_duplicate')
        stages[str(stage)] = stages.get(str(stage), 0) + 1
        states[str(state)] = states.get(str(state), 0) + 1
        if now < when <= now + dt.timedelta(days=8) and len(previews) < 8:
            previews.append({'provider_game_id': row['id'], 'start_time': when.isoformat(), 'stage': stage, 'status_code': state, 'visitors': pair[0], 'home': pair[1]})
    if not previews:
        raise PreflightError('nba_window_empty')
    return {'response_games': len(rows), 'stages': stages, 'status_codes': states, 'schedule_preview': previews, 'catalog_identity_key': 'basketball-us-nba'}


def collect(source, previous, now, key, get):
    """At most one request in any rolling 24h; sanitized evidence only, no events."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('NBA preflight requires an aware clock')
    now = now.astimezone(UTC)
    result = {**source, 'approved_catalog': True, 'ok': False, 'events': 0,
              'coverage_complete': False, 'review_required': True, 'requests_this_run': 0,
              'errors': ['NBA connection pending current-season and fixture-scope review'],
              'checked_at': previous.get('checked_at')}
    if previous.get('api_attempted_at'):
        try:
            attempted = aware(previous['api_attempted_at'])
        except (TypeError, ValueError):
            result['errors'] = ['NBA previous quota receipt invalid; no request made']; return result
        if now < attempted or now - attempted < dt.timedelta(hours=24):
            for field in ('api_attempted_at', 'preflight_evidence', 'api_http_status', 'quota_limit', 'quota_remaining'):
                if field in previous: result[field] = previous[field]
            restore_failure(result, previous)
            return result
    if source.get('id') != SOURCE_ID or source.get('source_type') != 'api-sports-nba-preflight' or source.get('endpoint') != ENDPOINT or source.get('coverage_status') != 'pending-fixture-review':
        result['errors'] = ['NBA preflight configuration changed; no request made']; return result
    if not isinstance(key, str) or not key or key != key.strip() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        result['errors'] = ['API_SPORTS_KEY unavailable or invalid; no request made']; return result
    result.update(api_attempted_at=now.isoformat(), requests_this_run=1)
    season = now.year if now.month >= 7 else now.year - 1
    stage = 'schedule_request'
    try:
        response = get(ENDPOINT, params={'league': 'standard', 'season': str(season)},
                       headers={'x-apisports-key': key}, timeout=25, allow_redirects=False)
        status = response.status_code
        result['api_http_status'] = status
        if status != 200:
            raise PreflightError('http_rejected')
        stage = 'schedule_quota'
        limit, remaining = validate_quota(response.headers, 'x-ratelimit-requests-limit',
                                          'x-ratelimit-requests-remaining', 100)
        result.update(quota_limit=limit, quota_remaining=remaining)
        stage = 'schedule_json'
        payload = response.json()
        stage = 'schedule_validation'
        result['preflight_evidence'] = inspect_payload(payload, season, now)
        result['checked_at'] = now.isoformat()
    except PreflightError as error:
        record_failure(result, stage, error.code)
    except Exception:
        # requests/JSON exceptions can contain credentials, URL parameters or bodies.
        code = {'schedule_request': 'transport_failed', 'schedule_json': 'json_invalid'}.get(stage, 'validation_unexpected')
        record_failure(result, stage, code)
    return result
