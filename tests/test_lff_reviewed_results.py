"""Bounded November 1 official result/next-round evidence, with no network."""
import ast
import copy
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from lxml import html
from scripts.lff_virsliga_fixture_adapter import next_round, NOVEMBER_ROUNDS
from tests.test_lff_virsliga_fixture_adapter import SOURCE

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'
DAY = dt.date(2026, 11, 1)
NOW = dt.datetime(2026, 11, 1, 16, tzinfo=dt.timezone.utc)


def page():
    return (FIXTURES / 'lff-round35-results-round36-20261101.html').read_bytes()


class ReviewedLffTests(unittest.TestCase):
    def parse(self, data=None, day=DAY, now=NOW, source=SOURCE):
        return next_round(page() if data is None else data, source, day, now)

    def changed(self, query, transform):
        doc = html.fromstring(page())
        nodes = doc.xpath(query)
        self.assertTrue(nodes, query)
        for node in nodes:
            transform(node)
        return html.tostring(doc)

    def test_complete_scored_round_is_excluded_before_selecting_five_exact_future_games(self):
        rows, count, held = self.parse()
        self.assertEqual((5, 180, 0), (len(rows), count, held))
        self.assertEqual({f'lff-virsliga-{n}' for n in range(23300244, 23300249)}, {r['id'] for r in rows})
        self.assertEqual({'2026-11-08T11:00:00Z'}, {r['start_time'] for r in rows})
        self.assertEqual('Ogre United at FS Jelgava', rows[0]['name'])
        self.assertEqual('FK Jelgava Sporta bāzes mākslīgais laukums', rows[0]['location'])
        self.assertEqual('FC RFS at Riga FC', rows[-1]['name'])
        self.assertEqual('Skonto stadions', rows[-1]['location'])

    def test_five_independent_official_detail_heads_confirm_results_edition_clock_and_stadium(self):
        doc = html.fromstring((FIXTURES / 'lff-round35-result-heads-20261101.html').read_bytes())
        articles = doc.xpath('//article')
        self.assertEqual(5, len(articles))
        for article in articles:
            spec = NOVEMBER_ROUNDS[article.get('data-id')]
            self.assertEqual(['01 nov', '13:00'], article.xpath('.//li[@class="date"]/b/text()'))
            self.assertEqual(['"Tonybet" virslīga 2026', '35. kārta'], article.xpath('.//li[@class="competition"]/span/text()'))
            self.assertEqual(spec['links'], article.xpath('.//div[@class="clubs"]//a/@href'))
            self.assertEqual(spec['names'], article.xpath('.//div[@class="clubs"]//a/span/text()'))
            self.assertEqual(spec['scores'], article.xpath('.//div[@class="result"]/div[@class="res"]/text()'))
            self.assertTrue(article.xpath('.//span[@class="stadium"]/text()')[0].startswith(spec['venue'] + ','))

    def test_missing_duplicate_extra_or_unknown_identity_rejects_entire_round(self):
        for key in ('23300239', '23300244'):
            query = f'//*[@id="tabContent_1_1"]//*[@data-id="{key}"]'
            for action in (lambda n: n.getparent().remove(n),
                           lambda n: n.getparent().append(copy.deepcopy(n)),
                           lambda n: n.set('data-id', '99999999')):
                with self.subTest(key=key, action=action), self.assertRaises(ValueError):
                    self.parse(self.changed(query, action))
        with self.assertRaises(ValueError):
            self.parse(self.changed('//*[@id="tabContent_1_2"]//*[@data-id="23300248"]', lambda n: n.getparent().remove(n)))

    def test_changed_club_scope_clock_venue_round_date_or_link_fails_in_either_view(self):
        for pane in ('tabContent_1_1', 'tabContent_1_2'):
            for key in ('23300239', '23300244'):
                base = f'//*[@id="{pane}"]//*[@data-id="{key}"]'
                changes = [('.//div[@class="stadium"]', lambda n: setattr(n, 'text', 'Unknown')),
                           ('.//div[@class="clubs"]//a', lambda n: n.set('href', '/klubi/u17/?cid=23300000')),
                           ('.//div[@class="title"]//a', lambda n: setattr(n, 'text', 'U17 team'))]
                changes += [('.//div[@class="matchday"]/h4', lambda n: setattr(n, 'text', '14:00')),
                            ('.//div[@class="matchday"]/h5', lambda n: setattr(n, 'text', '37'))] if pane.endswith('1_1') else [
                            ('.//div[@class="date"]/h5', lambda n: setattr(n, 'text', '9')),
                            ('.//div[@class="date"]/div[@class="h7"]', lambda n: setattr(n, 'text', '14:00'))]
                for query, action in changes:
                    with self.subTest(pane=pane,key=key,query=query), self.assertRaises(ValueError):
                        self.parse(self.changed(base + query[1:], action))
        with self.assertRaises(ValueError):
            self.parse(self.changed('//h1', lambda n: setattr(n, 'text', 'Tonybet Virslīga U17')))
        with self.assertRaises(ValueError):
            self.parse(self.changed('//*[@id="tabContent_1_1"]//*[@data-id="23300239"]//a[starts-with(@href,"/speles/")]', lambda n: n.set('href', '/speles/other-23300239/')))

    def test_unknown_changed_mixed_or_future_score_is_not_silently_dropped(self):
        for key in ('23300239', '23300244'):
            for value in (('P', '-', '9', '') if key == '23300239' else ('P', '0', '9', '')):
                with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                    self.parse(self.changed(f'//*[@data-id="{key}"]//span[@class="res1"]', lambda n: setattr(n,'text',value)))
        for now in (NOW.replace(tzinfo=None), NOW.replace(hour=10), None):
            with self.subTest(now=now), self.assertRaises(ValueError):
                self.parse(now=now)

    def test_historical_expired_and_inconsistent_review_dates_fail_closed(self):
        for day in (dt.date(2026, 10, 31), dt.date(2026, 11, 2), dt.date(2026, 11, 8)):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.parse(day=day,now=dt.datetime.combine(day, dt.time(16),dt.timezone.utc))
        with self.assertRaises(ValueError):self.parse(now=NOW+dt.timedelta(days=1))

    def test_actual_collector_branch_keeps_all_or_nothing_after_parse_or_access_failure(self):
        tree = ast.parse((ROOT/'scripts/refresh_global_schedule.py').read_text())
        node = next(n for n in ast.walk(tree) if isinstance(n,ast.If)
                    and ast.unparse(n.test) == "source.get('source_type') == 'official-lff-virsliga-next-round'")
        wrapper = ast.Module(body=[ast.For(target=ast.Name(id='source',ctx=ast.Store()),
                    iter=ast.List(elts=[ast.Name(id='configured_source',ctx=ast.Load())],ctx=ast.Load()),
                    body=[node],orelse=[])],type_ignores=[])
        program = compile(ast.fix_missing_locations(wrapper),'<actual LFF branch>','exec')
        damaged = self.changed('//*[@data-id="23300239"]//span[@class="res1"]',lambda n:setattr(n,'text','9'))
        for status,data,expected in ((200,page(),5),(200,damaged,0),(403,page(),0)):
            response = Mock();response.text = data.decode('ascii')
            if status == 403:response.raise_for_status.side_effect = ValueError('HTTP403')
            get = Mock(return_value=response)
            context = dict(configured_source={**SOURCE,'source_type':'official-lff-virsliga-next-round','endpoint':SOURCE['official_schedule_url']},
                           lff_next_round=next_round,TODAY=DAY,END=dt.date(2026,11,8),NOW_UTC=NOW,
                           datetime=dt,TZ=dt.timezone(dt.timedelta(hours=-6)),requests=SimpleNamespace(get=get),
                           HEADERS={},events=[],seen=set(),source_status=[],count=0,errors=[])
            exec(program,context)
            self.assertEqual(expected,len(context['events']));self.assertEqual(1,get.call_count)
            self.assertEqual(bool(expected),context['source_status'][0]['ok'])


if __name__ == '__main__':unittest.main()
