"""One public UEFA domestic contract; exact reviewed scopes, never blanket approval.

Directory and match routes come from UEFA's published frontend. Requests are
credential-free. An ADULT competition flag does not clear athlete age or markets.
"""
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = 'https://domestic.uefa.com/v2/'
SOURCE_TYPE = 'official-uefa-domestic-reviewed'
SCOPES = json.loads((Path(__file__).resolve().parents[1] / 'data/uefa-reviewed-scopes.json').read_text())['scopes']
CENTRAL = ZoneInfo('America/Chicago')
BAD_NAME = re.compile(r'\b(?:tbc|tbd|unknown|winner|bye|u\s*[- ]?\d\d|under\s*\d\d|reserve|youth)\b|\s(?:II|B)$', re.I)


def source_config(source_id):
    s = SCOPES[source_id]
    if not s['enabled']:
        raise ValueError('UEFA candidate scope has no reviewed working subset')
    return {'id': source_id, 'sport': 'Soccer', 'league': s['league'], 'region': s['region'],
            'source_type': SOURCE_TYPE, 'coverage_status': 'partial', 'coverage_complete': False,
            'endpoint': BASE + 'matches', 'official_schedule_url': f"https://www.uefa.com/nationalassociations/{s['country'].lower()}/domestic/{s['type'].lower()}/{s['competition_id']}/",
            'catalog_terms': [s['league']], 'source_note': s['scope_note']}


def validate_source(source):
    ident = source.get('id')
    if ident not in SCOPES:
        raise ValueError('Unknown UEFA catalog identity')
    for key, value in source_config(ident).items():
        if source.get(key) != value:
            raise ValueError('UEFA source scope changed: ' + key)
    return SCOPES[ident]


def validate_competition(comp, spec):
    expected = {'id': spec['competition_id'], 'countryCode': spec['country'], 'age': 'ADULT',
                'sex': 'MALE', 'sportsType': 'FOOTBALL', 'teamCategory': 'CLUB',
                'region': 'DOMESTIC', 'type': spec['type']}
    if spec['type'] == 'LEAGUE':
        expected['tier'] = 'FIRST'
    if not isinstance(comp, dict) or any(comp.get(k) != v for k, v in expected.items()):
        raise ValueError('UEFA competition identity/category changed')
    if comp.get('metaData', {}).get('name') != spec['publisher_name']:
        raise ValueError('UEFA competition name changed')


def validate_directory(directory, spec):
    if not isinstance(directory, list) or not all(isinstance(x, dict) for x in directory):
        raise ValueError('UEFA directory schema changed')
    exact = [x for x in directory if x.get('id') == spec['competition_id']]
    if len(exact) != 1:
        raise ValueError('UEFA exact competition missing or duplicated in directory')
    validate_competition(exact[0], spec)


def parse_matches(payload, directory, source, now, start, end):
    spec = validate_source(source)
    validate_directory(directory, spec)
    if now.tzinfo is None or start > end:
        raise ValueError('UEFA review clock/window invalid')
    if not isinstance(payload, list) or not all(isinstance(x, dict) for x in payload):
        raise ValueError('UEFA match schema changed')
    counts, seen, events = Counter(), {}, []
    for row in payload:
        ident = row.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
            raise ValueError('UEFA stable match ID missing')
        if ident in seen:
            if row != seen[ident]:
                raise ValueError('UEFA conflicting duplicate match')
            counts['duplicate_records'] += 1
            continue
        seen[ident] = row
        validate_competition(row.get('competition'), spec)
        if row.get('seasonYear') != spec['season']:
            raise ValueError('UEFA fixture edition changed')
        counts['published_records'] += 1
        if row.get('status') != 'UPCOMING':
            counts['non_upcoming_holds'] += 1
            continue
        if (row.get('score') not in (None, {}) or row.get('winner') not in (None, {})
                or row.get('playerEvents', {}).get('scorers')):
            counts['scored_holds'] += 1
            continue
        kickoff = row.get('kickOffTime')
        if not isinstance(kickoff, dict):
            raise ValueError('UEFA kickoff evidence missing')
        date = dt.date.fromisoformat(kickoff.get('date', ''))
        value = kickoff.get('dateTime')
        if value is None or (isinstance(value, str) and value.endswith('T00:00:00Z')):
            counts['untimed_holds'] += 1
            continue
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
            raise ValueError('UEFA explicit UTC kickoff invalid')
        instant = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if instant.date() != date or instant.second or not dt.date.fromisoformat(spec['edition_start']) <= date <= dt.date.fromisoformat(spec['edition_end']):
            raise ValueError('UEFA date/UTC/season conflict')
        if instant <= now:
            counts['past_upcoming_holds'] += 1
            continue
        if not start <= instant.astimezone(CENTRAL).date() <= end:
            counts['outside_review_window'] += 1
            continue
        teams = []
        for key in ('homeTeam', 'awayTeam'):
            team = row.get(key)
            if not isinstance(team, dict) or not isinstance(team.get('id'), str) or not isinstance(team.get('internationalName'), str):
                raise ValueError('UEFA stable opponent identity missing')
            teams.append(team)
        if teams[0]['id'] == teams[1]['id']:
            raise ValueError('UEFA identical opponents')
        if any(t.get('isPlaceHolder') is not False or BAD_NAME.search(t['internationalName']) for t in teams):
            counts['placeholder_or_non_senior_holds'] += 1
            continue
        if any(spec['teams'].get(t['id']) != t['internationalName'] for t in teams):
            counts['unreviewed_participant_holds'] += 1
            continue
        stage = 'Reviewed first-tier league fixtures'
        if spec['type'] == 'CUP':
            approved = spec['reviewed_pairs'].get(ident)
            if not approved or approved['home_id'] != teams[0]['id'] or approved['away_id'] != teams[1]['id'] or approved['date'] != date.isoformat():
                counts['unreviewed_cup_phase_holds'] += 1
                continue
            stage = approved['phase']
        events.append({'id': source['id'] + '-' + ident, 'source_id': source['id'], 'sport': 'Soccer',
                       'league': source['league'], 'region': source['region'],
                       'name': teams[1]['internationalName'] + ' at ' + teams[0]['internationalName'],
                       'start_time': value, 'status': 'UPCOMING', 'status_detail': 'Official UTC fixture; no athlete-age clearance',
                       'season_stage': stage, 'source_endpoint': source['official_schedule_url']})
    return events, {**counts, 'coverage_status': 'partial', 'coverage_complete': False,
                    'review_window_complete': False, 'remaining_unplayed_fixtures': len(events),
                    'coverage_note': 'Exact reviewed provider subset only; empty response is not offseason or completeness. Athlete age, unreviewed phases and participants remain unresolved.'}


class ProviderClient:
    """Bounded pagination, no credentials/redirects/retries; stop family on denial."""
    def __init__(self, get=None):
        if get is None:
            import requests
            get = requests.get
        self.get, self.blocked = get, False
        self.directories = {}

    def page(self, route, params):
        if self.blocked:
            raise ValueError('UEFA provider stopped after access denial/rate limit')
        response = self.get(BASE + route, params=params, timeout=35, allow_redirects=False)
        if response.status_code in (401, 403, 429) or 300 <= response.status_code < 400:
            self.blocked = True
            raise ValueError('UEFA provider access/redirect/rate-limit hold: ' + str(response.status_code))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, list):
            raise ValueError('UEFA paged list schema changed')
        return result

    def pages(self, route, query, size):
        result, seen = [], set()
        for page in range(10):
            rows = self.page(route, {**query, 'limit': size, 'offset': page * size})
            if len(rows) > size:
                raise ValueError('UEFA page exceeded requested bound')
            ids = [r.get('id') for r in rows if isinstance(r, dict)]
            if len(ids) != len(rows) or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids) or seen.intersection(ids):
                raise ValueError('UEFA pagination duplicate/invalid identities')
            seen.update(ids); result.extend(rows)
            if len(rows) < size:
                return result, page + 1
        raise ValueError('UEFA pagination bound reached; incomplete collection held')

    def fetch(self, source, now, start, end):
        spec = validate_source(source)
        if not dt.date(2026, 10, 18) <= now.date() <= dt.date(2027, 6, 30):
            raise ValueError('UEFA reviewed editions require renewal')
        country = spec['country']
        if country not in self.directories:
            self.directories[country] = self.pages('competitions', {'age': 'ADULT', 'countryCode': country}, 10)[0]
        # Query UTC dates covering the whole Chicago review window, including DST.
        lower = dt.datetime.combine(start, dt.time.min, CENTRAL).astimezone(dt.timezone.utc).date()
        upper = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, CENTRAL).astimezone(dt.timezone.utc).date()
        payload, pages = self.pages('matches', {'competitionId': spec['competition_id'], 'seasonYear': spec['season'],
                                              'fromDate': lower.isoformat(), 'toDate': upper.isoformat()}, 100)
        events, proof = parse_matches(payload, self.directories[country], source, now, start, end)
        proof.update({'successful_match_pages': pages, 'request_window_start_utc': lower.isoformat(), 'request_window_end_utc': upper.isoformat()})
        return events, proof
