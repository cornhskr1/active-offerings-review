"""The FIGC collector publishes all valid in-window records or none."""
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

TEXT = (Path(__file__).parents[1] / 'scripts/refresh_global_schedule.py').read_text()
START = TEXT.index('    if source.get("source_type")=="official-figc-serie-a-women-fixtures":')
END = TEXT.index('    if source.get("source_type")=="official-qsl-cup-fixtures":', START)
CODE = 'for source in configured:\n' + TEXT[START:END]

class FigcCollectorTests(unittest.TestCase):
    def run_branch(self, fixtures):
        response = SimpleNamespace(text='fixture', raise_for_status=lambda: None)
        ns = {'configured': [{'id': 'figc', 'source_type': 'official-figc-serie-a-women-fixtures',
              'endpoint': 'https://www.figc.it/', 'coverage_status': 'partial'}],
              'requests': SimpleNamespace(get=lambda *a, **kw: response), 'HEADERS': {},
              'parse_figc_rounds': lambda *args: fixtures, 'datetime': dt,
              'NOW_UTC': dt.datetime(2026, 10, 18, 17, tzinfo=dt.timezone.utc),
              'TODAY': dt.date(2026, 10, 18), 'END': dt.date(2026, 10, 25),
              'TZ': ZoneInfo('America/Chicago'), 'events': [], 'source_status': [],
              'seen': set(), 'errors': [], 'count': 0}
        exec(compile(CODE, 'figc-collector', 'exec'), ns)
        return ns['events'], ns['source_status'][0]

    def test_invalid_later_record_does_not_publish_earlier_records(self):
        good = {'id': 'a', 'start_time': '2026-10-24T16:30:00Z'}
        for bad in ['invalid', '2026-10-24T16:30:00']:
            with self.subTest(bad=bad):
                events, status = self.run_branch([good, {'id': 'b', 'start_time': bad}])
                self.assertEqual([], events)
                self.assertFalse(status['ok'])
                self.assertEqual(0, status['events'])

    def test_window_uses_chicago_date_and_excludes_elapsed_games(self):
        rows = [{'id': str(i), 'start_time': value} for i, value in enumerate([
            '2026-10-18T16:00:00Z', '2026-10-24T16:30:00Z',
            '2026-10-26T01:00:00Z', '2026-10-26T06:00:00Z'])]
        events, status = self.run_branch(rows)
        self.assertEqual(['1', '2'], [row['id'] for row in events])
        self.assertTrue(status['ok'])
        self.assertEqual('partial', status['coverage_status'])
        self.assertEqual(4, status['published_fixtures'])

    def test_deduplication_and_future_only_health(self):
        row = {'id': 'a', 'start_time': '2026-10-24T16:30:00Z'}
        events, status = self.run_branch([row, row])
        self.assertEqual(1, len(events))
        events, status = self.run_branch([{'id': 'b', 'start_time': '2026-11-02T17:00:00Z'}])
        self.assertEqual([], events)
        self.assertTrue(status['ok'])
        self.assertEqual('partial', status['coverage_status'])
