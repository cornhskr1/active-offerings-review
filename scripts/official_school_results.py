"""Bounded factual WMT result observations, independent of calendar/start evidence.

Pure parsing plus bounded publisher-policy-aware polling. Callers own durable
persistence and validated calendar date evidence. This does not grant crawling or redistribution rights.
No prose, images, broadcasts, scheduled starts or inferred venues are retained.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import re
import json
from urllib.parse import urljoin, urlsplit

try:
    from official_historical_school_result import FactsParser, walk, content, by_class
    from official_school_calendar import fetch_text, instant
except ImportError:
    from scripts.official_historical_school_result import FactsParser, walk, content, by_class
    from scripts.official_school_calendar import fetch_text, instant

PROGRAMS = {
    'football': 'Football', 'volleyball': 'Volleyball', 'baseball': 'Baseball',
    'softball': 'Softball', 'mens-basketball': "Men's Basketball",
    'womens-basketball': "Women's Basketball",
}
MONTHS = dict(zip(('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
                   'Sep', 'Oct', 'Nov', 'Dec'), range(1, 13)))
CONFLICT = re.compile(r'\b(?:cancel(?:l)?(?:ed|ation)?|postpon(?:e|ed|ement)|suspend(?:ed)?|suspension|abandon(?:ed|ment)?)\b', re.I)


class BoundedParser(FactsParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > 50000 or len(self.stack) > 100:
            raise ValueError('Official schedule exceeds structural bounds')
        super().handle_starttag(tag, attrs)


def _text(node, cls, optional=False):
    found = by_class(node, cls)
    if optional and not found:
        return None
    if len(found) != 1:
        raise ValueError('Missing or ambiguous result field: ' + cls)
    value = content(found[0])
    if not value or len(value) > 250:
        raise ValueError('Invalid result field: ' + cls)
    return value


def _program(config):
    slug = config.get('sport_slug')
    if (slug not in PROGRAMS or config.get('school') != 'Nebraska'
            or config.get('school_id') != 'nebraska'
            or config.get('sport') != PROGRAMS[slug]
            or config.get('sport_id') != slug
            or config.get('id') != 'official-nebraska-' + slug
            or config.get('discovery_kind') != 'wmt-rolling'
            or config.get('schedule_url') != f'https://huskers.com/sports/{slug}/schedule'):
        raise ValueError('Unreviewed official WMT program identity')


def _scope(config):
    _program(config)
    season = str(config.get('season', ''))
    if not re.fullmatch(r'20\d{2}(?:-\d{2})?', season):
        raise ValueError('Explicit official season required')
    year = int(season[:4])
    if '-' in season:
        if int(season[-2:]) != (year + 1) % 100:
            raise ValueError('Invalid official season')
        # A cross-year title alone does not say which year each month belongs to.
        if not config.get('season_start') or not config.get('season_end'):
            raise ValueError('Cross-year season requires reviewed date bounds')
    start = date.fromisoformat(config.get('season_start', f'{year}-01-01'))
    end = date.fromisoformat(config.get('season_end', f'{year}-12-31'))
    last_year = year + ('-' in season)
    if start > end or start.year != year or end.year != last_year or (end-start).days > 365:
        raise ValueError('Invalid bounded official season')
    return season, start, end


def _day(label, start, end):
    match = re.fullmatch(r'([A-Z][a-z]{2}) (\d{1,2})(?:, (20\d{2}))?', label)
    if not match or match[1] not in MONTHS:
        raise ValueError('Unconfirmed official event date')
    candidates = []
    for year in range(start.year, end.year + 1):
        if match[3] and year != int(match[3]):
            continue
        try:
            day = date(year, MONTHS[match[1]], int(match[2]))
        except ValueError:
            continue
        if start <= day <= end:
            candidates.append(day)
    if len(candidates) != 1:
        raise ValueError('Ambiguous or out-of-season official event date')
    return candidates[0].isoformat()


def parse_results(page, config, observed_at):
    """Return allowlisted completed facts for one exact configured season.

    `config` is an existing Nebraska WMT source plus `season`; cross-year
    seasons additionally require reviewed ISO `season_start`/`season_end`.
    `observed_at` must be timezone-aware. It records observation, never decides
    completion. Missing/unsupported result labels are held, not inferred.
    Missing location stays unknown; a city-only location is not a named venue.
    Any malformed completed row or duplicate publisher ID fails this source.
    """
    season, start, end = _scope(config)
    stamp = (observed_at if isinstance(observed_at, datetime)
             else datetime.fromisoformat(str(observed_at).replace('Z', '+00:00')))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Observation must have an explicit timezone')
    if not isinstance(page, str) or len(page.encode('utf-8')) > 2_000_000:
        raise ValueError('Official schedule exceeds bounded input size')
    parser = BoundedParser()
    parser.feed(page)
    titles = [content(n) for n in walk(parser.root) if n.get('tag') == 'title']
    if titles != [f"{config['sport']} {season} - University of Nebraska - Official Athletics Website"]:
        raise ValueError('Official schedule program or season changed')
    blocks = by_class(parser.root, 'schedule-event-item')
    if not blocks or len(blocks) > 250:
        raise ValueError('Official schedule event bounds changed')
    rows, seen = [], set()
    for block in blocks:
        identities = [n['attrs'].get('entity-id') for n in walk(block)
                      if n['attrs'].get('entity-name') == 'schedule-events']
        if len(identities) != 1 or not re.fullmatch(r'[1-9]\d{0,11}', identities[0] or ''):
            raise ValueError('Missing or ambiguous official event identity')
        event_id = identities[0]
        if event_id in seen:
            raise ValueError('Duplicate official event identity')
        seen.add(event_id)
        label = _text(block, 'schedule-event-item-result__label', optional=True)
        if label is None:
            continue
        match = re.fullmatch(r'(?:(\d{1,3}-\d{1,3}) (W Win|L Loss|T Tie)|(W Win|L Loss|T Tie) (\d{1,3}-\d{1,3}))', label)
        if not match:
            continue
        if CONFLICT.search(content(block)):
            raise ValueError('Explicit result conflicts with inactive event status')
        opponent = _text(block, 'schedule-event-item-default__opponent-name')
        day_label = _text(block, 'schedule-event-date__label')
        day = _day(day_label, start, end)
        location = _text(block, 'schedule-event-location', optional=True)
        site = _text(block, 'schedule-event-venue__type-label', optional=True)
        if site not in (None, 'Home', 'Away', 'Neutral'):
            raise ValueError('Unrecognized official site designation')
        # Retain only exact published links from this event, never construct an
        # event URL from an ID or ingest linked documents without separate review.
        links = set()
        for n in walk(block):
            if n.get('tag') != 'a':
                continue
            href = n['attrs'].get('href', '')
            url = urljoin(config['schedule_url'], href)
            parts = urlsplit(url)
            if (parts.scheme == 'https' and parts.netloc == 'huskers.com'
                    and not parts.query and not parts.fragment
                    and (re.fullmatch(r'/boxscore/\d+', parts.path)
                         or re.fullmatch(r'/news/[\w/-]+', parts.path))):
                if parts.path.startswith('/boxscore/') and parts.path != '/boxscore/' + event_id:
                    raise ValueError('Conflicting official box score identity')
                links.add(url)
        rows.append({
            'id': config['id'] + ':result:' + event_id,
            'source_id': config['id'], 'publisher_event_id': event_id,
            'school': config['school'], 'sport': config['sport'], 'season': season,
            'date': day, 'opponent': opponent, 'status': 'COMPLETED',
            'result': match[2] or match[3], 'score': match[1] or match[4],
            'location': location, 'site': site.upper() if site else None,
            'source_url': config['schedule_url'], 'source_links': sorted(links),
            'observed_at': stamp.isoformat(), 'evidence_kind': 'official-school-result',
            'evidence': {'event_id': event_id, 'date_label': day_label,
                         'result_label': label, 'location_label': location},
        })
    return sorted(rows, key=lambda row: (row['date'], row['publisher_event_id']))


def collect_program_results(source, previous_cache, now, get):
    """Refresh one permitted schedule, retaining last-good facts on failure.

    Successful empty snapshots are returned empty for the caller's missing-result
    comparison. They are not cancellations. Cache hits do not create new evidence.
    Season comes solely from the exact program title, not the observation clock.
    """
    _program(source)  # Never fetch an arbitrary endpoint supplied in configuration.
    now = instant(now)
    previous = deepcopy(previous_cache or {})
    if previous.get('source_id') not in (None, source['id']):
        raise ValueError('Result cache belongs to another source')
    ttl = max(216000, int(source.get('minimum_poll_seconds', 216000)),
              int(previous.get('ttl_seconds', 0)))
    base = {key: source[key] for key in ('id', 'school', 'sport')}
    base['source_url'] = source['schedule_url']

    def response(cache, status, ok, until, reason):
        return {
            'events': deepcopy(cache.get('events', [])),
            'source_status': {**base, 'ok': ok, 'status': status,
                              'fetched_at': cache.get('fetched_at'),
                              'next_fetch_at': until, 'season': cache.get('season'),
                              'reason': reason, 'event_count': len(cache.get('events', [])),
                              'integrity_hold': cache.get('integrity_hold') is True},
            'cache': cache,
        }

    try:
        retry = previous.get('retry_after')
        if retry and now < instant(retry):
            return response(previous, 'stale', False, retry,
                            previous.get('last_error', 'Result refresh retry interval'))
        until = previous.get('next_fetch_at')
        if not retry and until and now < instant(until):
            return response(previous, 'cached', True, until, 'Publisher refresh interval has not elapsed')
        page = fetch_text(source['schedule_url'], get)
        if len(page.encode('utf-8')) > 2_000_000:
            raise ValueError('Official schedule exceeds bounded input size')
        parser = BoundedParser()
        parser.feed(page)
        titles = [content(n) for n in walk(parser.root) if n.get('tag') == 'title']
        pattern = re.escape(source['sport']) + r' (20\d{2}(?:-\d{2})?) - University of Nebraska - Official Athletics Website'
        match = re.fullmatch(pattern, titles[0]) if len(titles) == 1 else None
        if not match:
            raise ValueError('Official schedule program or season title changed')
        season = match[1]
        config = {**source, 'season': season}
        # Reviewed bounds apply to the exact title season, never another season.
        for key in ('season_start', 'season_end'):
            config.pop(key, None)
            if source.get('result_' + key):
                config[key] = source['result_' + key]
        if '-' in season and not (config.get('season_start') or config.get('season_end')):
            # Caller supplies only independently validated, nonstale calendar
            # dates for this exact program. The title limits the year domain;
            # the observation clock and conventional season months play no role.
            supplied = source.get('result_season_dates', [])
            if not isinstance(supplied, list) or len(supplied) > 250:
                raise ValueError('Invalid reviewed calendar season dates')
            dates = []
            first_year = int(season[:4])
            for value in supplied:
                if not isinstance(value, str) or not re.fullmatch(r'20\d{2}-\d{2}-\d{2}', value):
                    raise ValueError('Invalid reviewed calendar season date')
                day = date.fromisoformat(value)
                if day.year in (first_year, first_year + 1):
                    dates.append(day)
            if dates:
                config['season_start'] = min(dates).isoformat()
                config['season_end'] = max(dates).isoformat()
        events = parse_results(page, config, now)
        stamp = now.isoformat()
        until = (now + timedelta(seconds=ttl)).isoformat()
        cache = {'source_id': source['id'], 'season': season, 'events': events,
                 'fetched_at': stamp, 'next_fetch_at': until, 'ttl_seconds': ttl}
        encoded = json.dumps(cache, indent=2, ensure_ascii=False)
        if len(encoded.encode()) + 6 * (encoded.count('\n') + 1) > 100_000:
            raise ValueError('Official result cache capacity exceeded; new snapshot not retained')
        return response(cache, 'current', True, until,
                        'Observed official completed results' if events else 'Observed no explicit completed results')
    except Exception as exc:
        # A failed request is not contradictory evidence. An observed malformed
        # identity or explicit conflict is: preserve the hold through retries
        # until a complete successful snapshot establishes current facts.
        if isinstance(exc, ValueError) and re.search(r'conflict|duplicate|ambiguous|capacity exceeded', str(exc), re.I):
            previous['integrity_hold'] = True
        previous.update(source_id=source['id'], last_error=str(exc), ttl_seconds=ttl,
                        retry_after=(now + timedelta(seconds=ttl)).isoformat())
        return response(previous, 'stale', False, previous['retry_after'], str(exc))
