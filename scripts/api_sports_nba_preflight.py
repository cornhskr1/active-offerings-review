"""One daily authenticated NBA capability check; never emits approved fixtures.

The provider's free/current-season access and exact response identities must be
reviewed before activating a fixture adapter. Never log response bodies or keys.
"""
import datetime as dt
import re

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
        raise ValueError('NBA API rejected request; current-season access unverified')
    if payload.get('get') not in ('games', 'games/') or payload.get('parameters') != {'league': 'standard', 'season': str(season)}:
        raise ValueError('NBA response query identity changed')
    rows = payload.get('response')
    if not isinstance(rows, list) or not 0 < len(rows) <= 5000 or type(payload.get('results')) is not int or payload['results'] != len(rows):
        raise ValueError('NBA response incomplete or empty; access unverified')
    seen = set(); previews = []; stages = {}; states = {}; ids = {}
    for row in rows:
        if not isinstance(row, dict) or not positive(row.get('id')) or row['id'] in seen or row.get('league') != 'standard' or type(row.get('season')) is not int or row['season'] != season:
            raise ValueError('NBA game identity or season changed')
        seen.add(row['id'])
        when = aware((row.get('date') or {}).get('start'))
        if not dt.datetime(season, 7, 1, tzinfo=UTC) <= when < dt.datetime(season + 1, 8, 1, tzinfo=UTC):
            raise ValueError('NBA game outside requested season')
        stage = row.get('stage'); state = (row.get('status') or {}).get('short')
        if type(stage) is not int or not 1 <= stage <= 10 or type(state) is not int or state not in range(1, 7):
            raise ValueError('NBA phase or state unrecognized')
        teams = row.get('teams') or {}; pair = []
        for side in ('visitors', 'home'):
            team = teams.get(side) or {}; tid = team.get('id'); name = team.get('name')
            if not positive(tid) or name not in TEAM_NAMES or (tid in ids and ids[tid] != name) or (name in ids.values() and ids.get(tid) != name):
                raise ValueError('NBA senior club identity unverified')
            ids[tid] = name; pair.append({'id': tid, 'name': name})
        if pair[0]['id'] == pair[1]['id']:
            raise ValueError('NBA duplicate participant')
        stages[str(stage)] = stages.get(str(stage), 0) + 1
        states[str(state)] = states.get(str(state), 0) + 1
        if now < when <= now + dt.timedelta(days=8) and len(previews) < 8:
            previews.append({'provider_game_id': row['id'], 'start_time': when.isoformat(), 'stage': stage, 'status_code': state, 'visitors': pair[0], 'home': pair[1]})
    if not previews:
        raise ValueError('NBA current review-window observations unavailable')
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
            return result
    if source.get('id') != SOURCE_ID or source.get('source_type') != 'api-sports-nba-preflight' or source.get('endpoint') != ENDPOINT or source.get('coverage_status') != 'pending-fixture-review':
        result['errors'] = ['NBA preflight configuration changed; no request made']; return result
    if not isinstance(key, str) or not key or key != key.strip() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        result['errors'] = ['API_SPORTS_KEY unavailable or invalid; no request made']; return result
    result.update(api_attempted_at=now.isoformat(), requests_this_run=1)
    season = now.year if now.month >= 7 else now.year - 1
    try:
        response = get(ENDPOINT, params={'league': 'standard', 'season': str(season)},
                       headers={'x-apisports-key': key}, timeout=25, allow_redirects=False)
        status = response.status_code
        result['api_http_status'] = status
        if status != 200:
            result['errors'] = ['NBA API HTTP response rejected; no redirect or retry']; return result
        limit = response.headers.get('x-ratelimit-requests-limit', '')
        remaining = response.headers.get('x-ratelimit-requests-remaining', '')
        if not str(limit).isdigit() or not str(remaining).isdigit() or not 1 <= int(limit) <= 100 or not 0 <= int(remaining) < int(limit):
            result['errors'] = ['NBA free-plan quota headers unverified']; return result
        result.update(quota_limit=int(limit), quota_remaining=int(remaining))
        result['preflight_evidence'] = inspect_payload(response.json(), season, now)
        result['checked_at'] = now.isoformat()
    except Exception:
        # requests/JSON exceptions can contain credentials, URL parameters or bodies.
        result['errors'] = ['NBA preflight transport or response validation failed; no retry']
    return result
