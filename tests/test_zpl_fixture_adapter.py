"""Zambia's official transitional streams stay in one exact senior identity."""
import datetime
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from zpl_fixture_adapter import (CALENDAR_BASE, HOME, STREAMS, fetch_zambia_fixtures,
                                 parse_zpl_calendars, source_config, team_calendar_requests)

FIXTURES = ROOT / "tests/fixtures/zpl_20261018"
NOW = datetime.datetime(2026, 10, 18, 15, 42, tzinfo=datetime.timezone.utc)


class ZplFixtureTests(unittest.TestCase):
    def setUp(self):
        self.page = (FIXTURES / "directory.html").read_text()
        self.feeds = {int(f.stem): f.read_text() for f in FIXTURES.glob("*.ics")}
        self.source = source_config()

    def parse(self, **kwargs):
        return parse_zpl_calendars(kwargs.get('page', self.page), kwargs.get('feeds', self.feeds),
                                   kwargs.get('source', self.source), kwargs.get('now', NOW),
                                   include_evidence=kwargs.get('evidence', False))

    def edit_fixture(self, ident, old, new):
        for team, body in self.feeds.items():
            self.feeds[team] = re.sub(r'BEGIN:VEVENT\n(?:(?!END:VEVENT).)*UID:fixture-' + str(ident)
                                     + r'@zpl.co.zm(?:(?!END:VEVENT).)*END:VEVENT',
                                     lambda m: m[0].replace(old, new), body, flags=re.S)

    def test_complete_inventory_both_streams_exact_utc_and_dedup(self):
        teams = team_calendar_requests(self.page, self.source)
        self.assertEqual(20, len(teams))
        events, evidence = self.parse(evidence=True)
        self.assertEqual(140, len(events))
        self.assertEqual(140, len({e['id'] for e in events}))
        self.assertEqual(180, evidence['published_fixtures'])
        self.assertEqual(360, evidence['reconciled_calendar_copies'])
        self.assertEqual(4, evidence['excluded_other_competition_copies'])
        self.assertEqual(20, evidence['team_calendars_checked'])
        self.assertEqual('partial', evidence['coverage_status'])
        self.assertEqual('Power Dynamos FC at FC MUZA', events[0]['name'])
        self.assertEqual('2026-10-24T13:00:00Z', events[0]['start_time'])
        self.assertEqual('Mutondo Stars at ZESCO United', events[9]['name'])
        self.assertEqual('2026-10-25T13:00:00Z', events[9]['start_time'])
        self.assertTrue(all(e['source_id'] == self.source['id'] and e['league'] == self.source['league'] for e in events))

    def test_catalog_identity_and_country_fail_closed(self):
        for update in ({'id':'caf-soccer-zambia-absa-cup-men'}, {'region':'South Africa'},
                       {'catalog_terms':['Barclays Cup | Men']}, {'league':'National League | Men'},
                       {'sport':'Basketball'}, {'coverage_status':'complete'}, {'endpoint':'https://example.com/'}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.parse(source={**self.source, **update})

    def test_edition_membership_and_inventory_fail_closed(self):
        for old, new in [('Transitional 2026','Transitional 2027'),
                         ('Men - Stream B - MTN Super League','Women - Stream B - MTN Super League'),
                         ('"id":81,','"id":85,'), ('"name":"Chirundu United"','"name":"Chirundu United U20"')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.parse(page=self.page.replace(old,new))

    def test_missing_team_calendar_fails(self):
        self.feeds.pop(81)
        with self.assertRaisesRegex(ValueError,'twenty'):
            self.parse()

    def test_cross_stream_or_unknown_opponent_fails(self):
        for wrong in ('Red Arrows', 'TBD', 'FC MUZA Women'):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                self.parse(feeds={**self.feeds,85:self.feeds[85].replace('SUMMARY:FC MUZA vs Power Dynamos FC','SUMMARY:FC MUZA vs '+wrong)})

    def test_timezone_floating_date_old_year_fail(self):
        for old, new in [('X-WR-TIMEZONE:Africa/Lusaka','X-WR-TIMEZONE:UTC'),
                         ('DTSTART:20261024T130000Z','DTSTART:20261024T130000'),
                         ('DTSTART:20261024T130000Z','DTSTART:20251024T130000Z')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.parse(feeds={**self.feeds,85:self.feeds[85].replace(old,new)})

    def test_opponent_copies_must_agree(self):
        for old,new in [('DTSTART:20261024T130000Z','DTSTART:20261024T140000Z'),
                        ('LOCATION:Nakambala Stadium','LOCATION:Other Stadium')]:
            with self.subTest(new=new), self.assertRaisesRegex(ValueError,'disagree'):
                self.parse(feeds={**self.feeds,85:self.feeds[85].replace(old,new)})

    def test_missing_or_duplicate_fixture_copy_fails(self):
        event = re.search(r'BEGIN:VEVENT\nUID:fixture-9921@zpl.co.zm.*?END:VEVENT\n',self.feeds[85],re.S)[0]
        with self.assertRaisesRegex(ValueError,"other team's"):
            self.parse(feeds={**self.feeds,85:self.feeds[85].replace(event,'')})
        with self.assertRaisesRegex(ValueError,'duplicate fixture'):
            self.parse(feeds={**self.feeds,85:self.feeds[85].replace(event,event+event)})

    def test_cancelled_tentative_and_completed_never_emit(self):
        self.edit_fixture(9921,'STATUS:CONFIRMED','STATUS:CANCELLED')
        self.edit_fixture(9922,'STATUS:CONFIRMED','STATUS:TENTATIVE')
        self.edit_fixture(9923,' | Matchweek 5',' | Matchweek 5 | Result: 1-0')
        events, evidence = self.parse(evidence=True)
        self.assertEqual(137,len(events))
        self.assertFalse({'zpl-9921','zpl-9922','zpl-9923'} & {e['id'] for e in events})
        self.assertEqual(1,evidence['cancelled_fixtures'])
        self.assertEqual(1,evidence['tentative_fixtures_held'])

    def test_cup_women_reserve_national_and_old_unsplit_league_not_conflated(self):
        event = re.search(r'BEGIN:VEVENT\nUID:fixture-9921@zpl.co.zm.*?END:VEVENT\n',self.feeds[85],re.S)[0]
        for other in ('Charity Shield - Men - Super','ABSA Cup','Barclays Cup','MTN Super League',
                      'Women - North - Super League','Men - North - National League','Reserve League'):
            extra=event.replace(STREAMS[0],other).replace('fixture-9921','fixture-99999')
            with self.subTest(other=other):
                events=self.parse(feeds={**self.feeds,85:self.feeds[85].replace('END:VCALENDAR',extra+'END:VCALENDAR')})
                self.assertEqual(140,len(events))

    def test_healthy_empty_short_window_not_unpublished_future(self):
        events,evidence=self.parse(evidence=True)
        self.assertEqual([], [e for e in events if e['start_time'] < '2026-10-24'])
        self.assertEqual(140,evidence['future_confirmed_fixtures'])
        with self.assertRaisesRegex(ValueError,'not evidence of offseason'):
            self.parse(now=datetime.datetime(2027,2,1,tzinfo=datetime.timezone.utc))

    def test_bad_calendar_and_naive_now_fail_closed(self):
        for body in ('<html>Login</html>',self.feeds[85].replace('END:VCALENDAR',''),
                     self.feeds[85].replace('UID:fixture-9921@zpl.co.zm','UID:fixture-9921@zpl.co.zm\nUID:fixture-9921@zpl.co.zm')):
            with self.subTest(body=body[:20]),self.assertRaises(ValueError):
                self.parse(feeds={**self.feeds,85:body})
        with self.assertRaises(ValueError):self.parse(now=NOW.replace(tzinfo=None))

    def test_fetch_public_inventory_once_each(self):
        calls=[]
        class Response:
            def __init__(self,content):self.content=content.encode()
            def raise_for_status(self):pass
        def get(url,timeout):
            calls.append(url)
            return Response(self.page if url==HOME else self.feeds[int(url.split('=')[-1])])
        events,evidence=fetch_zambia_fixtures(self.source,NOW,get=get)
        self.assertEqual(21,len(calls));self.assertEqual(21,len(set(calls)))
        self.assertEqual(140,len(events));self.assertEqual(20,evidence['team_calendars_checked'])

    def test_fetch_http_denial_stops_without_retry(self):
        calls=[]
        class Response:
            content=self.page.encode()
            def raise_for_status(inner):
                if len(calls)>1:raise RuntimeError('HTTP 403 Forbidden')
        def get(url,timeout):calls.append(url);return Response()
        with self.assertRaisesRegex(RuntimeError,'403'):
            fetch_zambia_fixtures(self.source,NOW,get=get)
        self.assertEqual([HOME,CALENDAR_BASE+'81'],calls)


if __name__ == '__main__':
    unittest.main()
