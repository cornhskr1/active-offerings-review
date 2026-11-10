"""Minimal factual markup, not copies of the publisher's full pages."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from official_school_results import parse_results

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT / 'data/official-school-calendar-sources.json').read_text())['sources']
STAMP = '2026-11-09T12:00:00+00:00'


def config(slug='football', **extras):
    source = deepcopy(next(s for s in SOURCES if s['id'] == 'official-nebraska-' + slug))
    return {**source, 'season': '2026', **extras}


def event(number='21839', day='Nov 6', opponent='Illinois', result='31-24 L Loss',
          location='Champaign, Ill.', site='Away'):
    def field(cls, value):
        return '' if value is None else f'<span class="{cls}">{value}</span>'
    return '<div class="schedule-event-item">' + ''.join([
        f'<div entity-id="{number}" entity-name="schedule-events"></div>',
        field('schedule-event-date__label', day),
        field('schedule-event-item-default__opponent-name', opponent),
        field('schedule-event-item-result__label', result),
        field('schedule-event-location', location),
        field('schedule-event-venue__type-label', site),
        f'<a href="/boxscore/{number}">Box Score</a>',
        '<a href="/news/2026/11/6/result">Recap</a>',
        '<a href="https://untrusted.example/news/story">Other</a>',
        '<span>Broadcast 7:00 PM CT</span>',
    ]) + '</div>'


def page(*events, sport='Football', season='2026'):
    return f'<title>{sport} {season} - University of Nebraska - Official Athletics Website</title>' + ''.join(events)


class OfficialSchoolResultsTests(unittest.TestCase):
    def test_generic_multiple_ids_dates_opponents(self):
        rows = parse_results(page(event(), event('99999', 'Oct 3', 'New Opponent', 'W Win 14-7')), config(), STAMP)
        self.assertEqual([r['publisher_event_id'] for r in rows], ['99999', '21839'])
        self.assertEqual(rows[1]['date'], '2026-11-06')
        self.assertEqual(rows[1]['location'], 'Champaign, Ill.')
        self.assertEqual(rows[1]['result'], 'L Loss')
        self.assertEqual(rows[1]['source_links'], ['https://huskers.com/boxscore/21839', 'https://huskers.com/news/2026/11/6/result'])
        self.assertFalse({'start_time', 'actual_start', 'venue', 'scheduled_start_evidence'} & rows[1].keys())

    def test_volleyball_and_all_configured_programs(self):
        for slug in ('football', 'volleyball', 'baseball', 'softball', 'mens-basketball', 'womens-basketball'):
            source = config(slug)
            rows = parse_results(page(event(result='3-0 W Win'), sport=source['sport']), source, STAMP)
            self.assertEqual(rows[0]['sport'], source['sport'])

    def test_no_elapsed_time_inference(self):
        for result in (None, 'Final', '7-0', 'TBA', 'Live 7-0', 'Red, 3 - White, 1'):
            self.assertEqual(parse_results(page(event(result=result)), config(), '2030-01-01T00:00:00Z'), [])

    def test_clock_does_not_create_completion(self):
        self.assertEqual(len(parse_results(page(event()), config(), '2020-01-01T00:00:00Z')), 1)

    def test_missing_location_is_unknown_not_inferred_from_away(self):
        row = parse_results(page(event(location=None)), config(), STAMP)[0]
        self.assertIsNone(row['location'])
        self.assertEqual(row['site'], 'AWAY')

    def test_neutral_named_location_preserved(self):
        row = parse_results(page(event(location='Arlington, Texas / AT&amp;T Stadium', site='Neutral')), config(), STAMP)[0]
        self.assertEqual(row['location'], 'Arlington, Texas / AT&T Stadium')
        self.assertEqual(row['site'], 'NEUTRAL')

    def test_exact_season_program_source(self):
        for source, html in [(config(), page(event(), season='2025')),
                             (config(), page(event(), sport='Volleyball')),
                             (config(schedule_url='https://example.com'), page(event())),
                             (config(school='Omaha'), page(event())),
                             (config(season=''), page(event()))]:
            with self.assertRaises(ValueError):
                parse_results(html, source, STAMP)

    def test_cross_year_requires_reviewed_unambiguous_bounds(self):
        source = config('mens-basketball', season='2026-27')
        html = page(event(day='Jan 4'), sport=source['sport'], season='2026-27')
        with self.assertRaises(ValueError):
            parse_results(html, source, STAMP)
        source.update(season_start='2026-07-01', season_end='2027-06-30')
        self.assertEqual(parse_results(html, source, STAMP)[0]['date'], '2027-01-04')

    def test_invalid_dates(self):
        for day in ('Feb 30', 'Nov 6, 2025', 'Nov 6-7', 'TBD'):
            with self.assertRaises(ValueError):
                parse_results(page(event(day=day)), config(), STAMP)

    def test_duplicate_or_conflicting_ids_rejected(self):
        for html in (page(event(), event()),
                     page(event(), event(result=None)),
                     page(event()).replace('entity-id="21839"', 'entity-id=""'),
                     page(event()).replace('/boxscore/21839', '/boxscore/99')):
            with self.assertRaises(ValueError):
                parse_results(html, config(), STAMP)

    def test_inactive_conflicts_rejected(self):
        for state in ('Cancelled', 'Postponed', 'Suspended', 'Abandoned'):
            with self.assertRaises(ValueError):
                parse_results(page(event().replace('Broadcast', state)), config(), STAMP)

    def test_ambiguous_field_and_naive_observation(self):
        with self.assertRaises(ValueError):
            parse_results(page(event().replace('</div>', '<span class="schedule-event-item-result__label">7-0 W Win</span></div>')), config(), STAMP)
        with self.assertRaises(ValueError):
            parse_results(page(event()), config(), '2026-11-09')

    def test_input_bounds(self):
        for html in ('x' * 2_000_001, '<div>' * 102, page(*(event(str(n+1)) for n in range(251)))):
            with self.assertRaises(ValueError):
                parse_results(html, config(), STAMP)


class ResultPollingTests(unittest.TestCase):
    def collect(self, html=None, previous=None, now=STAMP, source=None, status=200):
        from official_school_results import collect_program_results
        self.calls = []

        class Response:
            status_code = status
            text = page(event()) if html is None else html

        def get(url, **kwargs):
            self.calls.append((url, kwargs))
            return Response()
        return collect_program_results(source or config(), previous, now, get)

    def test_success_discovers_season_and_no_redirects(self):
        result = self.collect(source=config(season='2025'))
        self.assertEqual(result['cache']['season'], '2026')
        self.assertEqual(result['source_status']['status'], 'current')
        self.assertEqual(result['cache']['next_fetch_at'], '2026-11-12T00:00:00+00:00')
        self.assertEqual(self.calls[0][1], {'timeout': 35, 'allow_redirects': False})

    def test_ttl_no_fetch_and_no_mutation(self):
        old = self.collect()['cache']
        saved = deepcopy(old)
        result = self.collect(previous=old, now='2026-11-10T12:00:00Z')
        self.assertEqual(self.calls, [])
        self.assertEqual(result['source_status']['status'], 'cached')
        self.assertEqual(result['cache'], saved)
        self.assertEqual(old, saved)

    def test_failure_retains_last_good_and_retry_no_fetch(self):
        old = self.collect()['cache']
        failed = self.collect(status=503, previous=old, now='2026-11-12T00:00:00Z')
        self.assertFalse(failed['source_status']['ok'])
        self.assertEqual(failed['events'], old['events'])
        self.assertEqual(failed['cache']['fetched_at'], old['fetched_at'])
        self.assertEqual(failed['cache']['retry_after'], '2026-11-14T12:00:00+00:00')
        again = self.collect(previous=failed['cache'], now='2026-11-13T00:00:00Z')
        self.assertEqual(self.calls, [])
        self.assertEqual(again['source_status']['status'], 'stale')
        recovered = self.collect(previous=failed['cache'], now='2026-11-14T12:00:00Z')
        self.assertEqual(recovered['source_status']['status'], 'current')
        self.assertNotIn('retry_after', recovered['cache'])

    def test_empty_success_drops_current_rows_not_cancellation(self):
        old = self.collect()['cache']
        result = self.collect(page(event(result=None)), previous=old, now='2026-11-12T00:00:00Z')
        self.assertEqual(result['events'], [])
        self.assertEqual(result['cache']['events'], [])
        self.assertEqual(result['source_status']['status'], 'current')
        self.assertTrue(result['source_status']['ok'])
        self.assertEqual(len(old['events']), 1)

    def test_cross_year_review_bounds_required(self):
        source = config('mens-basketball')
        html = page(event(day='Jan 4'), sport=source['sport'], season='2026-27')
        result = self.collect(html, source=source)
        self.assertEqual(result['source_status']['status'], 'stale')
        self.assertIn('reviewed date bounds', result['source_status']['reason'])
        source.update(result_season_start='2026-07-01', result_season_end='2027-06-30')
        result = self.collect(html, source=source)
        self.assertTrue(result['source_status']['ok'])
        self.assertEqual(result['events'][0]['date'], '2027-01-04')

    def test_cross_year_bounds_from_reviewed_calendar_dates(self):
        source = config('mens-basketball', result_season_dates=[
            '2026-10-20', '2027-03-15', '2025-12-01'])
        html = page(event(day='Nov 6'), event('99', day='Jan 4'),
                    sport=source['sport'], season='2026-27')
        result = self.collect(html, source=source)
        self.assertTrue(result['source_status']['ok'])
        self.assertEqual([row['date'] for row in result['events']],
                         ['2026-11-06', '2027-01-04'])

    def test_cross_year_insufficient_or_overbroad_calendar_dates_fail(self):
        for dates in ([], ['2026-10-20', '2026-12-31'],
                      ['2027-01-01', '2027-03-15'],
                      ['2026-01-01', '2027-12-31'], ['bad-date']):
            source = config('mens-basketball', result_season_dates=dates)
            html = page(event(day='Jan 4'), sport=source['sport'], season='2026-27')
            self.assertFalse(self.collect(html, source=source)['source_status']['ok'])

    def test_explicit_cross_year_bounds_override_calendar_dates(self):
        source = config('mens-basketball', result_season_dates=['bad-date'],
                        result_season_start='2026-10-01', result_season_end='2027-04-01')
        html = page(event(day='Jan 4'), sport=source['sport'], season='2026-27')
        self.assertTrue(self.collect(html, source=source)['source_status']['ok'])

    def test_ttl_floor_and_prior_longer_interval(self):
        result = self.collect(source=config(minimum_poll_seconds=1))
        self.assertEqual(result['cache']['ttl_seconds'], 216000)
        old = {**result['cache'], 'ttl_seconds': 300000}
        result = self.collect(previous=old, now='2026-11-12T00:00:00Z')
        self.assertEqual(result['cache']['ttl_seconds'], 300000)

    def test_redirect_wrong_program_and_source_cache_rejected(self):
        from official_school_results import collect_program_results
        self.assertFalse(self.collect(status=302)['source_status']['ok'])
        self.assertFalse(self.collect(page(event(), sport='Volleyball'))['source_status']['ok'])
        with self.assertRaises(ValueError):
            collect_program_results(config(), {'source_id': 'other'}, STAMP, None)
        with self.assertRaises(ValueError):
            collect_program_results(config(schedule_url='https://example.com'), {}, STAMP, None)

    def test_integrity_hold_persists_through_retry_and_clears_on_success(self):
        old = self.collect()['cache']
        for html in (page(event().replace('Broadcast', 'Cancelled')),
                     page(event(), event()),
                     page(event().replace('entity-id="21839"', 'entity-id=""'))):
            failed = self.collect(html, previous=old, now='2026-11-12T00:00:00Z')
            self.assertTrue(failed['source_status']['integrity_hold'])
            self.assertTrue(failed['cache']['integrity_hold'])
            self.assertEqual(failed['events'], old['events'])
            retry = self.collect(previous=failed['cache'], now='2026-11-13T00:00:00Z')
            self.assertEqual(self.calls, [])
            self.assertTrue(retry['source_status']['integrity_hold'])
            unavailable = self.collect(previous=failed['cache'], status=503,
                                       now='2026-11-14T12:00:00Z')
            self.assertTrue(unavailable['source_status']['integrity_hold'])
            recovered = self.collect(previous=failed['cache'], now='2026-11-14T12:00:00Z')
            self.assertFalse(recovered['source_status']['integrity_hold'])
            self.assertNotIn('integrity_hold', recovered['cache'])

    def test_network_failure_does_not_create_integrity_hold(self):
        old = self.collect()['cache']
        failed = self.collect(previous=old, status=503, now='2026-11-12T00:00:00Z')
        self.assertFalse(failed['source_status']['integrity_hold'])
        self.assertNotIn('integrity_hold', failed['cache'])

    def test_publisher_guard_precedes_get(self):
        from unittest.mock import patch
        with patch('official_school_calendar.require_publisher_access', side_effect=PermissionError('test hold')):
            result = self.collect()
        self.assertFalse(result['source_status']['ok'])
        self.assertEqual(self.calls, [])

    def test_oversized_result_cache_holds_without_expanding_private_limit(self):
        body = page(*(event(number=str(50000+i), opponent='Opponent '+str(i)+'x'*150,
                           location='City, Iowa / '+'Arena '*25) for i in range(200)))
        result = self.collect(html=body)
        self.assertFalse(result['source_status']['ok'])
        self.assertTrue(result['source_status']['integrity_hold'])
        self.assertIn('capacity', result['source_status']['reason'])


if __name__ == '__main__':
    unittest.main()
