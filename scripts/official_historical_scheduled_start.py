"""Optional, separately observed scheduled starts for two reviewed completed games.

No actual-start claim, calendar timestamp recycling, or location-source refresh.
HTML tests use reduced captured factual nodes; unrelated page content is omitted.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import re
try:
    from official_school_calendar import CT, instant, fetch_text
    from publisher_access_policy import require_publisher_access
except ImportError:
    from scripts.official_school_calendar import CT, instant, fetch_text
    from scripts.publisher_access_policy import require_publisher_access

TTL = 216000
PDF_SHA256 = 'b64c9ed82e4985c013dc47fd48fc59086745cf60a3d3abef9ef14d91db21546e'
PDF_DATE_EVIDENCE = 'FRIDAY, NOV. 6 • 7 P.M. CT • CHAMPAIGN, ILL. • MEMORIAL STADIUM • FIELDTURF'
PDF_URL = 'https://storage.googleapis.com/huskers-com-prod/2026/11/02/7722pedpBrvn50mWdr6tzmNFeRWsDWa0MMNPbTGO.pdf'
TIMING_SPECS = {
    '21839': {
        'source_id': 'official-nebraska-football-scheduled-20261106',
        'source_url': 'https://huskers.com/news/2026/11/2/nebraska-faces-illinois-in-friday-night-road-game',
        'title': 'Nebraska Faces Illinois in Friday Night Road Game',
        'published': 'Football November 02, 2026', 'hour': 19, 'source_time': '7 p.m. CT',
        'date_source_url': PDF_URL,
    },
    '25154': {
        'source_id': 'official-nebraska-volleyball-scheduled-20261107',
        'source_url': 'https://huskers.com/news/2026/11/05/vb-preview-at-no-12-oregon-and-no-18-washington',
        'title': 'VB Preview: at No. 12 Oregon & No. 18 Washington',
        'published': 'Volleyball November 05, 2026', 'hour': 21, 'source_time': '9 p.m. CT',
    },
}
CANCELLED = re.compile(r'\b(?:cancel(?:l)?(?:ed|ation)?|postpon(?:e|ed|ement)|suspend(?:ed)?|suspension|abandon(?:ed|ment)?)\b', re.I)


def normalize(value):
    return re.sub(r'\s+', ' ', value).strip()


class VisibleText(HTMLParser):
    """Preserve document order; never use script/JSON, hidden head or nav clocks."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = []
        self.paragraphs = []
        self.paragraph = None
    def handle_starttag(self, tag, attrs):
        if tag == 'p' and not self.skip:
            if self.paragraph is not None:
                raise ValueError('Nested preview paragraph')
            self.paragraph = []
        if tag in {'head', 'script', 'style', 'nav', 'footer'}:
            self.skip.append(tag)
        if not self.skip and tag in {'p', 'div', 'br', 'section', 'article', 'h1', 'h2', 'h3', 'li', 'time'}:
            self.parts.append(' ')
            if self.paragraph is not None:
                self.paragraph.append(' ')
    def handle_endtag(self, tag):
        if tag == 'p' and not self.skip and self.paragraph is not None:
            self.paragraphs.append(normalize(''.join(self.paragraph)))
            self.paragraph = None
        if self.skip and tag == self.skip[-1]:
            self.skip.pop()
        if not self.skip and tag in {'p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'li', 'time'}:
            self.parts.append(' ')
            if self.paragraph is not None:
                self.paragraph.append(' ')
    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)
            if self.paragraph is not None:
                self.paragraph.append(text)


def preview_text(page, timing):
    if not isinstance(page, str) or len(page) > 2_000_000:
        raise ValueError('Scheduled-start preview exceeds bounded input size')
    if timing.get('date_source_url') and not re.search(r'href=[\"\']' + re.escape(timing['date_source_url']) + r'[\"\']', page):
        raise ValueError('Official preview no longer links the reviewed dated game notes')
    parser = VisibleText(); parser.feed(page)
    text = normalize(''.join(parser.parts))
    if text.count(timing['title']) != 1 or text.count(timing['published']) != 1:
        raise ValueError('Scheduled-start article program, year, title or publication date changed')
    article = text.split(timing['title'], 1)[1]
    if CANCELLED.search(article):
        raise ValueError('Scheduled-start article has a terminal-status conflict')
    return article, parser.paragraphs


def parse_preview(page, spec):
    timing = TIMING_SPECS[spec['event_id']]
    article, paragraphs = preview_text(page, timing)
    if spec['event_id'] == '21839':
        quote = 'The game is set for a 7 p.m. CT kickoff on FOX.'
        blocks = [p for p in paragraphs if quote in p]
        if (article.count(quote) != 1 or len(blocks) != 1
                or blocks[0].count('Illinois at Memorial Stadium in Champaign, Ill.') != 1
                or not re.search(r'\bFriday\b', blocks[0])):
            raise ValueError('Football scheduled-start teams, venue or qualified kickoff changed')
        return quote
    heading = 'Saturday, Nov. 7 - No. 1 Nebraska at No. 12 Oregon'
    if article.count(heading) != 1:
        raise ValueError('Oregon scheduled-start matchup/date missing or duplicated')
    blocks = [p for p in paragraphs if heading in p]
    if len(blocks) != 1 or not blocks[0].startswith(heading + ' '):
        raise ValueError('Oregon heading and start must share one exact paragraph')
    section = blocks[0][len(heading):].strip()
    found = re.findall(r'First Serve:\s*([^\n]*?)(?=\s+(?:TV/Streaming:|Radio:)|$)', section)
    if found != ['9 p.m. CT'] or section.count('First Serve:') != 1:
        raise ValueError('Oregon has missing, duplicated or unqualified scheduled first serve')
    return heading + ' | First Serve: 9 p.m. CT'


def fetch_football_notes(get):
    """Only exact independently inspected bytes can establish the PDF facts.

    Pin reviewed from the official preview's linked PDF, page 1. A changed PDF
    needs a new review, never an automatic pin update or heuristic PDF parser.
    """
    require_publisher_access(PDF_URL)
    response = get(PDF_URL, timeout=35, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError('Official game-notes request did not return HTTP 200')
    raw = response.content
    if not raw.startswith(b'%PDF-') or len(raw) > 10_000_000:
        raise ValueError('Official game-notes PDF is invalid or exceeds bounded size')
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PDF_SHA256:
        raise ValueError('Official game-notes PDF bytes changed; dated timing needs review')
    return PDF_DATE_EVIDENCE, digest


def identity(spec):
    timing = TIMING_SPECS[spec['event_id']]
    scheduled = datetime.fromisoformat(spec['expected']['date']).replace(hour=timing['hour'], tzinfo=CT)
    return {**spec['expected'], 'evidence_kind': 'official-scheduled-start',
            'source_id': timing['source_id'], 'source_url': timing['source_url'],
            'event_id': spec['event_id'], 'historical_calendar_uid': spec['uid'],
            'historical_calendar_source_id': spec['calendar_source_id'],
            'start_time': scheduled.astimezone(timezone.utc).isoformat(),
            'timezone': 'America/Chicago', 'source_time': timing['source_time']}


def valid_saved(evidence, spec, now, *, current=False):
    if not isinstance(evidence, dict) or any(evidence.get(k) != v for k, v in identity(spec).items()):
        return False
    try:
        fetched = instant(evidence['fetched_at']); expires = instant(evidence['next_fetch_at'])
        if not fetched <= now or expires - fetched != timedelta(seconds=TTL):
            return False
        if current and (not fetched <= now < expires or evidence.get('ok') is not True
                        or evidence.get('status') not in {'current', 'cached'}):
            return False
    except (ValueError, KeyError, TypeError):
        return False
    if not re.fullmatch(r'[0-9a-f]{64}', str(evidence.get('source_sha256', ''))) or not evidence.get('evidence_text'):
        return False
    if spec['event_id'] == '21839' and (evidence.get('date_source_url') != PDF_URL
            or evidence.get('date_source_sha256') != PDF_SHA256
            or evidence.get('date_evidence_text') != PDF_DATE_EVIDENCE):
        return False
    return True


def eligible_result(row, status, spec, now):
    try:
        fetched = instant(status['fetched_at']); expires = instant(status['next_fetch_at'])
        return (row.get('source_stale') is not True and row.get('status') == 'COMPLETED'
                and row.get('evidence_kind') == status.get('evidence_kind') == 'official-historical-result'
                and row.get('source_id') == status.get('id') == spec['source_id']
                and status.get('school') == spec['expected']['school']
                and status.get('sport') == spec['expected']['sport']
                and row.get('source_url') == status.get('source_url') == spec['url']
                and row.get('historical_calendar_uid') == spec['uid']
                and row.get('historical_calendar_source_id') == spec['calendar_source_id']
                and row.get('official_result_location') == spec['official_location']
                and all(row.get(k) == v for k, v in spec['expected'].items())
                and status.get('ok') is True and status.get('status') in {'current', 'cached'}
                and fetched <= now < expires and expires - fetched <= timedelta(seconds=TTL)
                and spec['expected']['date'] < fetched.astimezone(CT).date().isoformat()
                and spec['expected']['date'] < now.astimezone(CT).date().isoformat() <= spec['expires'])
    except (KeyError, ValueError, TypeError):
        return False


def collect_scheduled_start(row, result_status, previous_cache, now, get, spec):
    """Return optional evidence/cache; never change parent location or its clock."""
    now = instant(now); previous = deepcopy(previous_cache) if isinstance(previous_cache, dict) else {}
    evidence = previous.get('evidence')
    if evidence is not None and not valid_saved(evidence, spec, now):
        evidence = None
        previous = {}
    if not eligible_result(row, result_status, spec, now):
        return (dict(evidence, ok=False, status='stale', reason='Completed-result evidence is unavailable') if evidence else None), previous
    try:
        if previous.get('retry_after') and now < instant(previous['retry_after']) <= now + timedelta(seconds=TTL):
            return (dict(evidence, ok=False, status='stale', reason=previous.get('last_error', 'Timing refresh failed')) if evidence else None), previous
        if valid_saved(evidence, spec, now, current=True):
            return dict(evidence, status='cached'), previous
        timing = TIMING_SPECS[spec['event_id']]
        page = fetch_text(timing['source_url'], get)
        quote = parse_preview(page, spec)
        provenance = {}
        if spec['event_id'] == '21839':
            date_quote, digest = fetch_football_notes(get)
            provenance = {'date_source_url': PDF_URL, 'date_source_sha256': digest, 'date_evidence_text': date_quote}
        observed = {**identity(spec), **provenance, 'evidence_text': quote,
                    'source_sha256': hashlib.sha256(page.encode('utf-8')).hexdigest(),
                    'fetched_at': now.isoformat(), 'next_fetch_at': (now + timedelta(seconds=TTL)).isoformat(),
                    'ok': True, 'status': 'current'}
        return observed, {'evidence': observed}
    except Exception as exc:
        previous.update(last_error=str(exc), retry_after=(now + timedelta(seconds=TTL)).isoformat())
        return (dict(evidence, ok=False, status='stale', reason=str(exc)) if evidence else None), previous
