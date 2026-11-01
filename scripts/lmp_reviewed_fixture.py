"""One reviewed LMP regular-season game; all other published identities held."""
import datetime as dt
from zoneinfo import ZoneInfo

URL = 'https://api.lmp.mx/3.0.0/scoreboard/2026/11/01'
UTC = dt.timezone.utc
CENTRAL = ZoneInfo('America/Chicago')
MEXICO = ZoneInfo('America/Mexico_City')
# boxscore: (publisher identity, away ID/abbr/name, home ID/abbr/name, venue, UTC)
ROWS = {
    850501: ('6a04a29e3d4aa25b2', 673, 'MXC', 'Águilas', 676, 'NAV', 'Mayos', 'Estadio Yaquis', '2026-11-01 23:00:00'),
    850495: ('6ae5081a128686bee', 673, 'MXC', 'Águilas', 676, 'NAV', 'Mayos', 'Estadio Yaquis', '2026-11-01 23:00:00'),
    850502: ('6a04a4225bf7f41d3', 677, 'HER', 'Naranjeros', 675, 'MOC', 'Cañeros', 'Chevron Park', '2026-11-02 00:00:00'),
    850497: ('6a04a73999ee817f8', 680, 'OBR', 'Yaquis', 5482, 'GSV', 'Algodoneros', 'Kuroda Park', '2026-11-02 00:00:00'),
    850503: ('6a04a740212d9506d', 680, 'OBR', 'Yaquis', 5482, 'GSV', 'Algodoneros', 'Kuroda Park', '2026-11-02 00:00:00'),
    850487: ('6a04c71d930217078', 6483, 'NAY', 'Jaguares', 679, 'MAZ', 'Venados', 'Estadio Teodoro Mariscal', '2026-11-02 00:00:00'),
    850500: ('6a04ad877e5adba28', 674, 'JAL', 'Charros', 678, 'CUL', 'Tomateros', 'Estadio Juan Ley Fong', '2026-11-02 00:05:00'),
}
FIELDS = ('id', 'awayTeamId', 'awayTeam', 'awayTeamShort', 'homeTeamId', 'homeTeam', 'homeTeamShort', 'stadium', 'utcFullDate')


def validate(source, today, end, now):
    if (source.get('id') != 'lmp' or source.get('sport') != 'Baseball'
            or source.get('league') != 'Mexican Pacific League' or source.get('region') != 'Mexico'
            or source.get('catalog_terms') != ['Mexican Pacific League', 'Liga Mexicana del Pacífico']
            or source.get('source_type') != 'official-lmp-reviewed-fixture'
            or source.get('endpoint') != URL
            or type(source.get('max_requests_per_run')) is not int or source['max_requests_per_run'] != 1
            or type(source.get('max_events_per_run')) is not int or source['max_events_per_run'] != 1):
        raise ValueError('LMP reviewed source identity or caps changed')
    if (now.tzinfo is None or now.utcoffset() is None
            or today != dt.date(2026, 11, 1) or end != dt.date(2026, 11, 8)
            or now.astimezone(CENTRAL).date() != today):
        raise ValueError('LMP exact reviewed window expired or clock invalid')


def parse(payload, source, today, end, now):
    validate(source, today, end, now)
    rows = payload.get('response') if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 7 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('LMP complete reviewed day missing')
    ids = [r.get('boxScore') for r in rows]
    if any(type(i) is not int for i in ids) or set(ids) != set(ROWS) or len(set(ids)) != 7:
        raise ValueError('LMP exact fixture identities missing, added or duplicated')
    selected = None
    for row in rows:
        expected = ROWS[row['boxScore']]
        if tuple(row.get(k) for k in FIELDS) != expected:
            raise ValueError('LMP fixture pairing, venue or UTC identity changed')
        if (row.get('season') != '2026' or type(row.get('league_id')) is not int or row['league_id'] != 132
                or type(row.get('sport_id')) is not int or row['sport_id'] != 17 or row.get('gameType') != 'R'
                or type(row.get('gameStatus')) is not int or row['gameStatus'] != 0
                or type(row.get('awayRuns')) is not int or row['awayRuns'] != 0
                or type(row.get('homeRuns')) is not int or row['homeRuns'] != 0):
            raise ValueError('LMP edition, regular phase or unstarted status changed')
        start = dt.datetime.strptime(expected[-1], '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC)
        local = start.astimezone(MEXICO)
        if (row.get('localFullDate') != local.strftime('%Y-%m-%d %H:%M:%S')
                or row.get('spFullDate') != expected[-1] or row.get('gameDate') != local.date().isoformat()
                or row.get('gameTimeH') != local.strftime('%H:%M:%S')):
            raise ValueError('LMP UTC and local clock evidence disagree')
        if row['boxScore'] == 850500:
            selected = start
    # Four same-pairing identities have unresolved separate kickoffs. Two games
    # are outside this single-game review. Validate their rows, emit none of them.
    fixtures = []
    if selected > now and today <= selected.astimezone(CENTRAL).date() <= end:
        fixtures.append({'id': 'lmp-2026-27-850500', 'source_id': source['id'],
                         'sport': source['sport'], 'league': source['league'], 'region': source['region'],
                         'name': 'Charros de Jalisco at Tomateros de Culiacán',
                         'start_time': selected.isoformat().replace('+00:00', 'Z'), 'status': 'UPCOMING',
                         'status_detail': 'LMP exact reviewed regular-season fixture', 'season_stage': 'REGULAR',
                         'location': 'Estadio Juan Ley Fong', 'source_endpoint': URL,
                         'coverage_status': 'partial', 'coverage_complete': False})
    return fixtures, {'ok': True, 'errors': [], 'coverage_status': 'partial', 'coverage_complete': False,
                      'fixtures_held': 6, 'published_scoped_fixtures': 1,
                      'coverage_warning': 'One exact game reviewed; four ambiguous pairing identities and two unreviewed games held. No full-window or offseason coverage.'}


def collect(source, today, end, now, get, headers):
    validate(source, today, end, now)
    response = get(URL, headers=headers, timeout=30, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError('LMP official scoreboard unavailable; no retry or redirect')
    return parse(response.json(), source, today, end, now)
