"""Two explicitly reviewed historical results; original calendar rows stay intact."""
from copy import deepcopy
from datetime import timedelta
from html.parser import HTMLParser
import re
try:
    from official_school_calendar import instant, fetch_text, CT
except ImportError:
    from scripts.official_school_calendar import instant, fetch_text, CT

SOURCE_ID = 'official-nebraska-football-historical-20261106'
URL = 'https://huskers.com/sports/football/schedule'
UID = '0c8e7b0f4cd7798f7b8ec32fc8b2dad8d24b1127@calendar.wmt.digital'
TTL = 216000
EXPECTED = {'school': 'Nebraska', 'sport': 'Football', 'date': '2026-11-06',
            'opponent': 'Illinois', 'location': 'Champaign, Ill.', 'site': 'AWAY'}

SPECS = (
    {'source_id': SOURCE_ID, 'url': URL, 'uid': UID, 'calendar_source_id': 'official-nebraska-football',
     'expected': EXPECTED, 'event_id': '21839', 'date_label': 'Nov 6',
     'official_location': 'Champaign, Ill.', 'original_statuses': ('REMOVED',), 'expires': '2027-02-04'},
    {'source_id': 'official-nebraska-volleyball-historical-20261107',
     'url': 'https://huskers.com/sports/volleyball/schedule',
     'uid': '51779525590b99f6ab7414b3ff5ab9a07c47c04b@calendar.wmt.digital',
     'calendar_source_id': 'official-nebraska-volleyball',
     'expected': {'school': 'Nebraska', 'sport': 'Volleyball', 'date': '2026-11-07',
                  'opponent': 'Oregon', 'location': 'Eugene, Ore.', 'site': 'AWAY'},
     'event_id': '25154', 'date_label': 'Nov 7',
     'official_location': 'Eugene, Ore. / Matthew Knight Arena',
     'original_statuses': ('CONFIRMED', 'SCHEDULED', 'REMOVED'), 'expires': '2027-02-05'},
)

class FactsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'attrs': {}, 'children': [], 'text': ''}
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': [], 'text': ''}
        self.stack[-1]['children'].append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        self.stack[-1]['text'] += data

def walk(node):
    yield node
    for child in node['children']:
        yield from walk(child)

def content(node):
    return re.sub(r'\s+', ' ', ' '.join(n['text'] for n in walk(node))).strip()

def by_class(node, name):
    return [n for n in walk(node) if name in n['attrs'].get('class', '').split()]

def single_text(node, name):
    found = by_class(node, name)
    if len(found) != 1:
        raise ValueError('Historical result has ambiguous ' + name)
    return content(found[0])

def parse_result(page, spec=None):
    spec = spec or SPECS[0]
    expected = spec['expected']
    if len(page) > 2_000_000:
        raise ValueError('Historical schedule exceeds bounded input size')
    parser = FactsParser(); parser.feed(page)
    titles = [content(n) for n in walk(parser.root) if n.get('tag') == 'title']
    if titles != [expected['sport'] + ' 2026 - University of Nebraska - Official Athletics Website']:
        raise ValueError('Historical football season identity changed')
    blocks = []
    for node in by_class(parser.root, 'schedule-event-item'):
        identities = [c for c in walk(node) if c['attrs'].get('entity-id') == spec['event_id']
                      and c['attrs'].get('entity-name') == 'schedule-events']
        opponents = by_class(node, 'schedule-event-item-default__opponent-name')
        dates = by_class(node, 'schedule-event-date__label')
        same_matchup = (any(content(n) == expected['opponent'] for n in opponents)
                        and any(content(n) == spec['date_label'] for n in dates))
        if identities or same_matchup:
            if len(identities) != 1:
                raise ValueError('Historical matchup has a conflicting official identity')
            blocks.append(node)
    if len(blocks) != 1:
        raise ValueError('Historical result identity missing or duplicated')
    block = blocks[0]
    checks = {'schedule-event-date__label': spec['date_label'],
              'schedule-event-venue__type-label': 'Away',
              'schedule-event-item-default__opponent-name': expected['opponent'],
              'schedule-event-item-default__divider': 'at',
              'schedule-event-location': spec['official_location']}
    for name, expected_text in checks.items():
        if single_text(block, name) != expected_text:
            raise ValueError('Historical result facts changed: ' + name)
    result = single_text(block, 'schedule-event-item-result__label')
    if not re.fullmatch(r'(?:\d+-\d+ (?:L Loss|W Win|T Tie)|(?:L Loss|W Win|T Tie) \d+-\d+)', result):
        raise ValueError('Historical official result is not completed')
    if re.search(r'\b(?:cancel(?:l)?(?:ed|ation)?|postpon(?:e|ed|ement)|suspend(?:ed)?|suspension|abandon(?:ed|ment)?)\b', content(block), re.I):
        raise ValueError('Historical result has a cancellation, postponement, suspension or abandonment conflict')
    return {**expected, 'id': spec['source_id'] + ':' + spec['event_id'], 'source_id': spec['source_id'], 'uid': 'official-result-' + spec['event_id'],
            'historical_calendar_uid': spec['uid'], 'historical_calendar_source_id': spec['calendar_source_id'], 'status': 'COMPLETED',
            'source_url': spec['url'], 'source': spec['url'], 'official_result_location': spec['official_location'], 'evidence_kind': 'official-historical-result',
            'date_only': True, 'time_unknown': True, 'start_time': None, 'time': 'TBA'}

def collect_result(calendar_rows, previous_cache, now, get, spec=None):
    """Require each exact reviewed original observation, leaving it untouched."""
    spec = spec or SPECS[0]
    expected = spec['expected']
    now = instant(now); previous = deepcopy(previous_cache or {})
    base = {'id': spec['source_id'], 'school': expected['school'], 'sport': expected['sport'], 'source_url': spec['url'], 'evidence_kind': 'official-historical-result'}
    matches = [r for r in calendar_rows if r.get('uid') == spec['uid']]
    if (len(matches) != 1 or any(matches[0].get(k) != v for k, v in expected.items())
            or matches[0].get('source_id') != spec['calendar_source_id']
            or matches[0].get('status') not in spec['original_statuses']
            or not expected['date'] < now.astimezone(CT).date().isoformat() <= spec['expires']):
        return [], {**base, 'ok': False, 'status': 'not-applicable', 'reason': 'Exact reviewed original observation not eligible'}, ({} if len(matches) == 1 and matches[0].get('status') == 'COMPLETED' else previous)
    until = previous.get('retry_after') or previous.get('next_fetch_at')
    if until and now < instant(until):
        healthy = not previous.get('retry_after')
        return ([dict(e, source_stale=not healthy) for e in previous.get('events', [])],
                {**base, 'ok': healthy, 'status': 'cached' if healthy else 'stale',
                 'fetched_at': previous.get('fetched_at'), 'next_fetch_at': until,
                 'reason': previous.get('last_error', 'Historical verification refresh interval has not elapsed')}, previous)
    try:
        row = parse_result(fetch_text(spec['url'], get), spec)
        stamp = now.isoformat(); until = (now + timedelta(seconds=TTL)).isoformat()
        row.update(fetched_at=stamp, next_fetch_at=until)
        cache = {'events': [row], 'fetched_at': stamp, 'next_fetch_at': until}
        return [row], {**base, 'ok': True, 'status': 'current', 'fetched_at': stamp,
                       'next_fetch_at': until, 'reason': 'Separate exact completed official result; calendar removal retained'}, cache
    except Exception as exc:
        previous.update(last_error=str(exc), retry_after=(now + timedelta(seconds=TTL)).isoformat())
        return ([dict(e, source_stale=True) for e in previous.get('events', [])],
                {**base, 'ok': False, 'status': 'stale', 'reason': str(exc),
                 'fetched_at': previous.get('fetched_at'), 'next_fetch_at': previous['retry_after']}, previous)


def collect_results(calendar_rows, previous_cache, now, get):
    rows, statuses, cache = [], [], {}
    for spec in SPECS:
        events, status, saved = collect_result(calendar_rows, previous_cache.get(spec['source_id'], {}), now, get, spec)
        rows.extend(events); statuses.append(status); cache[spec['source_id']] = saved
    return rows, statuses, cache
