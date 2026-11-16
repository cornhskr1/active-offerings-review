"""Two event-bound scheduled times, observed separately from immutable history."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import re
try:
    from official_school_calendar import instant, fetch_text
    from official_historical_scheduled_start import VisibleText, normalize, CANCELLED, TTL
except ImportError:
    from scripts.official_school_calendar import instant, fetch_text
    from scripts.official_historical_scheduled_start import VisibleText, normalize, CANCELLED, TTL

SPECS = {
    '21843': dict(program='football', sport='Football', opponent='Michigan State', date='2026-09-26',
        location='East Lansing, Mich.', start_time='2026-09-26T21:00:00+00:00', source_time='4 p.m. CT',
        source_url='https://huskers.com/news/2026/09/14/huskers-spartans-football-kickoff-time-set',
        title='Huskers-Michigan State Football Kickoff Time Set', published='Football September 14, 2026'),
    '25155': dict(program='volleyball', sport='Volleyball', opponent='Washington', date='2026-11-08',
        location='Seattle, Wash. / Alaska Airlines Arena', start_time='2026-11-08T23:30:00+00:00', source_time='5:30 p.m. CT',
        source_url='https://huskers.com/news/2026/11/05/vb-preview-at-no-12-oregon-and-no-18-washington',
        title='VB Preview: at No. 12 Oregon & No. 18 Washington', published='Volleyball November 05, 2026'),
}


def binding(event_id, row):
    s = SPECS[event_id]
    return dict(event_id=event_id, result_id=f"official-nebraska-{s['program']}:result:{event_id}",
        result_source_id=f"official-nebraska-{s['program']}", result_observation_id=row['observation_id'],
        school='Nebraska', sport=s['sport'], opponent=s['opponent'], date=s['date'], location=s['location'], site='AWAY',
        source_id=f"official-nebraska-{s['program']}-scheduled-{s['date'].replace('-', '')}",
        source_url=s['source_url'], start_time=s['start_time'], source_time=s['source_time'], timezone='America/Chicago',
        evidence_kind='official-recorded-event-scheduled-start', start_time_kind='scheduled', actual_start_verified=False)


def eligible(row, event_id):
    s = SPECS[event_id]
    return (row.get('id') == f"official-nebraska-{s['program']}:result:{event_id}"
        and row.get('uid') == 'official-result-' + event_id and row.get('publisher_event_id') == event_id
        and row.get('source_id') == f"official-nebraska-{s['program']}"
        and row.get('source_url') == f"https://huskers.com/sports/{s['program']}/schedule"
        and row.get('season_id') == 'official-result:2026' and row.get('school') == 'Nebraska'
        and all(row.get(k) == s[k] for k in ('sport', 'opponent', 'date', 'location'))
        and row.get('site') == 'AWAY' and row.get('status') == 'COMPLETED'
        and row.get('evidence_kind') == 'recorded-official-school-result'
        and row.get('archive_latest_kind') == 'published' and row.get('archive_conflict_fields') == []
        and re.fullmatch(r'[a-f0-9]{64}', str(row.get('observation_id', ''))) is not None)


def parse_preview(page, event_id):
    s = SPECS[event_id]
    if not isinstance(page, str) or len(page) > 2_000_000:
        raise ValueError('Timing article exceeds input bounds')
    p = VisibleText(); p.feed(page)
    text = normalize(''.join(p.parts))
    if text.count(s['title']) != 1 or text.count(s['published']) != 1:
        raise ValueError('Timing article program, title or publication date differs')
    article = text.split(s['title'], 1)[1]
    if CANCELLED.search(article):
        raise ValueError('Timing article has cancellation or postponement evidence')
    if event_id == '21843':
        exact = 'Nebraska’s Big Ten opener at Michigan State on Saturday, Sept. 26, will kickoff at 4 p.m. (CT)'
        blocks = [b for b in p.paragraphs if exact in b]
        if article.count(exact) != 1 or len(blocks) != 1:
            raise ValueError('Michigan State exact matchup, date or kickoff missing/duplicated')
        return 'Nebraska at Michigan State | Sept. 26, 2026 | 4 p.m. CT'
    heading = 'Sunday, Nov. 8 - No. 1 Nebraska at No. 18 Washington'
    blocks = [b for b in p.paragraphs if heading in b]
    if article.count(heading) != 1 or len(blocks) != 1 or not blocks[0].startswith(heading + ' '):
        raise ValueError('Washington exact matchup/date paragraph missing or duplicated')
    section = blocks[0][len(heading):].strip()
    times = re.findall(r'First Serve:\s*([^\n]*?)(?=\s+(?:TV/Streaming:|Radio:)|$)', section)
    if times != ['5:30 p.m. CT'] or section.count('First Serve:') != 1:
        raise ValueError('Washington scheduled first serve changed or is unqualified')
    return 'Nebraska at Washington | Nov. 8, 2026 | 5:30 p.m. CT'


def valid_saved(e, expected, now):
    try:
        return (isinstance(e, dict) and all(e.get(k) == v for k, v in expected.items())
            and e.get('ok') is True and e.get('status') in ('current', 'cached')
            and re.fullmatch(r'[a-f0-9]{64}', e.get('source_sha256', '')) is not None
            and bool(e.get('evidence_text'))
            and instant(e['fetched_at']) <= now < instant(e['next_fetch_at'])
            and instant(e['next_fetch_at']) - instant(e['fetched_at']) == timedelta(seconds=TTL))
    except (KeyError, ValueError, TypeError):
        return False


def collect_starts(history, previous, now, get):
    """No old observation, calendar UID, venue decision or actual start is rewritten."""
    now = instant(now); saved = deepcopy(previous) if isinstance(previous, dict) else {}
    output = []
    rows = history.get('events', []) if isinstance(history, dict) else []
    for event_id, spec in SPECS.items():
        matches = [r for r in rows if r.get('publisher_event_id') == event_id]
        if len(matches) != 1 or not eligible(matches[0], event_id):
            continue
        expected = binding(event_id, matches[0]); old = saved.get(event_id, {})
        if not isinstance(old, dict): old = {}
        evidence = old.get('evidence')
        if valid_saved(evidence, expected, now):
            output.append(dict(evidence, status='cached')); continue
        try:
            if old.get('retry_after') and now < instant(old['retry_after']) <= now + timedelta(seconds=TTL):
                continue
            page = fetch_text(spec['source_url'], get)
            quote = parse_preview(page, event_id)
            observed = dict(expected, evidence_text=quote, source_sha256=hashlib.sha256(page.encode('utf-8')).hexdigest(),
                fetched_at=now.isoformat(), next_fetch_at=(now + timedelta(seconds=TTL)).isoformat(), ok=True, status='current')
            saved[event_id] = {'evidence': observed}; output.append(observed)
        except Exception as exc:
            saved[event_id] = dict(old, last_error=str(exc), retry_after=(now + timedelta(seconds=TTL)).isoformat())
    return output, saved
