"""Bounded 2026 NZ men's championship, not regional/final or age clearance.

Sporty's public widget uses read-only POST queries. Naive publisher datetimes
remain date-only. ResultStatus=0 also occurs on scored games: scores win.
"""
import datetime as dt
import json
import re
from collections import Counter
from html import unescape

SOURCE_ID = 'ofc-soccer-new-zealand-national-league-men'
PAGE = 'https://www.nzfootball.co.nz/COMPETITIONS/Football/dettol-national-league-championship'
BASE = 'https://www.nzfootball.co.nz/api/v2/competition/widget/'
ANNOUNCEMENT = 'https://www.nzfootball.co.nz/newsarticle/170010?newsfeedId=671503'
TEAMS = {
    417204: ('Auckland City FC', 27559),
    429207: ("WPX Academy Men's Reserve Team", 23204),
    417219: ('Auckland United FC', 6880),
    430307: ('Ferrymead Bays', 9637),
    425816: ('Eastern Suburbs AFC', 9728),
    428699: ('Thirsty Whale Napier City Rovers', 8405),
    430324: ('Monsoon Poon Miramar Rangers', 8517),
    425812: ('Auckland FC Reserves', 27792),
    430326: ('Wellington Olympic AFC', 8107),
    425814: ('Birkenhead United AFC', 10190),
    430302: ('Cashmere Technical FC', 10016),
}
QUERY = {'CompIds': [13413], 'OrgIds': [], 'GradeIds': [705173],
         'From': '2026-09-01T00:00:00', 'To': '2026-12-31T23:59:59'}


def source_config():
    return {'id': SOURCE_ID, 'sport': 'Soccer', 'league': 'New Zealand National League | Men',
            'region': 'New Zealand', 'source_type': 'official-nz-men-championship',
            'coverage_status': 'partial', 'coverage_complete': False, 'endpoint': PAGE, 'official_schedule_url': PAGE,
            'edition_evidence_url': ANNOUNCEMENT,
            'catalog_terms': ['New Zealand National League | Men'],
            'source_note': 'Exact 2026 senior men’s eleven-club National League Championship round-robin only. Date-only: publisher timestamps have no verified timezone. Regional phases, final and later editions remain uncovered; no participant-age or market eligibility clearance. Chatham Cup is not included.'}


def validate_source(source):
    for key, expected in source_config().items():
        if key != 'source_note' and source.get(key) != expected:
            raise ValueError('NZ championship source scope changed: ' + key)


def validate_widget(page):
    if isinstance(page, bytes):
        page = page.decode('utf-8')
    configs = [json.loads(unescape(x)) for x in re.findall(r'<widgets-wrapper[^>]+widgetsettings="([^"]+)"', page)]
    exact = [c for c in configs if c.get('CompetitionIds') == '13413']
    if len(exact) != 1 or exact[0].get('SeasonId') != '35' or exact[0].get('SportId') != '28' or exact[0].get('OwnerIds') != '14667':
        raise ValueError('NZ championship current widget edition changed')


def validate_metadata(metadata):
    comps = metadata.get('Competitions', [])
    matches = [c for c in comps if c.get('Id') == 13413]
    if matches != [{'Id': 13413, 'Name': "Dettol Men's National League 2026", 'SportId': 28}]:
        raise ValueError('NZ championship competition metadata changed')
    if metadata.get('GradesPerComp', {}).get('13413') != [{'Id': 705173, 'Name': 'Senior Men', 'Order': 1}]:
        raise ValueError('NZ championship senior grade changed')


def parse_fixtures(payload, metadata, source, today):
    validate_source(source)
    validate_metadata(metadata)
    rows = payload.get('Fixtures')
    if not isinstance(rows, list) or not rows:
        raise ValueError('NZ championship fixture response missing or empty')
    events, seen = [], {}
    counts = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('NZ championship malformed fixture')
        if (row.get('CompId'), row.get('SectionId'), row.get('GradeId')) != (13413, 235801, 705173):
            counts['out_of_scope_records'] += 1
            continue
        if row.get('SportId') != 28 or row.get('CompOrgId') != 14667 or row.get('GradeName') != 'Senior Men':
            raise ValueError('NZ championship row scope contradicts identifiers')
        ident = row.get('Id')
        if type(ident) is not int or ident <= 0:
            raise ValueError('NZ championship stable fixture identifier missing')
        if ident in seen:
            if row != seen[ident]:
                raise ValueError('NZ championship conflicting duplicate fixture')
            counts['duplicate_records'] += 1
            continue
        seen[ident] = row
        counts['published_championship_records'] += 1
        if not re.fullmatch(r'ROUND (?:[1-9]|10|11)', row.get('RoundName', '')):
            counts['unreviewed_stage_holds'] += 1
            continue
        home, away = row.get('HomeTeamId'), row.get('AwayTeamId')
        if home is None or away is None or any(row.get(s + 'TeamName', '').strip().upper() == 'BYE' for s in ('Home', 'Away')):
            counts['placeholder_or_bye_holds'] += 1
            continue
        if home == away or any((row.get(side + 'TeamName', '').strip(), row.get(side + 'OrganisationId')) != TEAMS.get(row.get(side + 'TeamId')) for side in ('Home', 'Away')):
            counts['unknown_team_holds'] += 1
            continue
        counts['published_named_fixtures'] += 1
        # Missing score fields cannot silently turn a result into a fixture.
        required = ('HomeScore', 'AwayScore', 'CustomScoreDisplay', 'ResultStatus', 'InGame', 'Status', 'StatusName', 'From', 'To')
        if any(key not in row for key in required):
            raise ValueError('NZ championship required status/date evidence missing')
        if row['HomeScore'] is not None or row['AwayScore'] is not None or row['CustomScoreDisplay'] or row['ResultStatus'] != 0 or row['InGame']:
            counts['completed_or_live_skipped'] += 1
            continue
        if row['Status'] != 2 or row['StatusName'] != 'Confirmed':
            counts['unconfirmed_holds'] += 1
            continue
        if not all(isinstance(row[k], str) and re.fullmatch(r'2026-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', row[k]) for k in ('From', 'To')):
            raise ValueError('NZ championship explicit 2026 publisher date changed')
        start, end = (dt.datetime.fromisoformat(row[k]) for k in ('From', 'To'))
        if not dt.date(2026, 9, 26) <= start.date() <= dt.date(2026, 12, 31) or not dt.timedelta(0) < end - start <= dt.timedelta(hours=4):
            raise ValueError('NZ championship fixture date or duration outside reviewed scope')
        if start.date() < today:
            counts['past_unresolved_holds'] += 1
            continue
        events.append({'id': f'{SOURCE_ID}-{ident}', 'source_id': SOURCE_ID,
                       'sport': source['sport'], 'league': source['league'], 'region': source['region'],
                       'name': f'{TEAMS[away][0]} at {TEAMS[home][0]}',
                       'start_time': start.date().isoformat(), 'date_only': True,
                       'status': 'UPCOMING', 'status_detail': 'Official named fixture; kickoff timezone unverified',
                       'season_stage': 'CHAMPIONSHIP ' + row['RoundName'], 'source_endpoint': PAGE})
    if not counts['published_named_fixtures']:
        raise ValueError('NZ championship no recognized named championship fixtures')
    evidence = dict(counts)
    evidence.update({'remaining_unplayed_fixtures': len(events), 'coverage_status': 'partial',
                     'review_window_complete': False, 'coverage_complete': False,
                     'coverage_note': '2026 eleven-club men’s championship round-robin only. Date-only; no regional/final/next-edition or participant-age clearance.'})
    return events, evidence


def fetch_fixtures(source, today, get=None, post=None):
    import requests
    validate_source(source)
    if not dt.date(2026, 9, 1) <= today <= dt.date(2026, 12, 31):
        raise ValueError('NZ championship 2026 adapter needs fresh edition review')
    get, post = get or requests.get, post or requests.post
    page = get(PAGE, timeout=35)
    page.raise_for_status()
    validate_widget(page.content)
    metadata = post(BASE + 'metadata/', json=['13413'], timeout=35)
    metadata.raise_for_status()
    data = post(BASE + 'fixture/Dates', json=QUERY, timeout=35)
    data.raise_for_status()
    return parse_fixtures(data.json(), metadata.json(), source, today)
