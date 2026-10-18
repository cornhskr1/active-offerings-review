import datetime as dt
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from mfl_fa_semifinal_adapter import source_config,parse_fixtures,fetch_fixtures,PDF,ARTICLE
TEXT=(ROOT/'tests/fixtures/mfl_fa_semifinals_2026.txt').read_text()
NOW=dt.datetime(2026,10,18,16,tzinfo=dt.timezone.utc)
class MflSemifinalTests(unittest.TestCase):
    def test_exact_semifinal_dates_and_separate_identity(self):
        events,evidence=parse_fixtures(TEXT,source_config(),NOW)
        self.assertEqual(4,len(events));self.assertEqual(['2026-10-23']*2+['2026-11-08']*2,[e['start_time'] for e in events])
        self.assertTrue(all(e['date_only'] and e['season_stage']=='SEMIFINAL' for e in events))
        self.assertEqual('partial',evidence['coverage_status']);self.assertFalse(evidence['review_window_complete'])
    def test_catalog_identity_and_competition_stay_exact(self):
        for key,value in [('id','other'),('league','Malaysia Cup | Men'),('sport','Basketball'),('region','Singapore'),('catalog_terms',['Charity Shield | Men'])]:
            with self.subTest(key=key),self.assertRaises(ValueError):parse_fixtures(TEXT,{**source_config(),key:value},NOW)
    def test_missing_duplicate_unknown_club_wrong_edition_and_clock_fail(self):
        cases=[TEXT.replace('2026','2027'),TEXT.replace('25 DPMM','26 DPMM'),TEXT.replace('DPMM FC','KELANTAN CITY FC'),
          TEXT.replace('8.15 PM','13.15 PM'),TEXT.replace('Jumaat','Ahad'),TEXT.replace('12 OKTOBER','13 OKTOBER'),
          TEXT.replace('SEPARUH AKHIR','SUKU AKHIR'),TEXT.replace('v SELANGOR FC','v DPMM FC'),
          TEXT.replace('23 Oktober','24 Oktober'),TEXT.replace('FA SF (2)','FA QF (2)'),
          '\n'.join(TEXT.splitlines()[:-2]),TEXT+'unexpected fixture\n']
        for text in cases:
            with self.subTest(text=text[:40]),self.assertRaises(ValueError):parse_fixtures(text,source_config(),NOW)
    def test_expired_publication_fails_not_offseason(self):
        with self.assertRaises(ValueError):parse_fixtures(TEXT,source_config(),NOW.replace(month=11,day=9))
    def test_completed_first_leg_dates_drop_without_inventing_results(self):
        events,evidence=parse_fixtures(TEXT,source_config(),NOW.replace(month=10,day=24))
        self.assertEqual(2,len(events));self.assertEqual(4,evidence['published_fixtures'])
    def test_denial_stops_before_pdf_without_retry(self):
        calls=[]
        def get(url,**kwargs):
            calls.append(url)
            def denied():raise RuntimeError('HTTP403')
            return SimpleNamespace(raise_for_status=denied)
        with self.assertRaisesRegex(RuntimeError,'403'):fetch_fixtures(source_config(),NOW,get)
        self.assertEqual([ARTICLE],calls)
    def test_wrong_attachment_stops_before_download(self):
        calls=[]
        def get(url,**kwargs):
            calls.append(url);return SimpleNamespace(raise_for_status=lambda:None,text='<a href="https://other.example/schedule.pdf">')
        with self.assertRaises(ValueError):fetch_fixtures(source_config(),NOW,get)
        self.assertEqual([ARTICLE],calls)

    def test_review_day_is_central_not_utc(self):
        events,_=parse_fixtures(TEXT,source_config(),dt.datetime(2026,10,24,0,30,tzinfo=dt.timezone.utc))
        self.assertEqual(4,len(events))
        with self.assertRaises(ValueError):parse_fixtures(TEXT,source_config(),dt.datetime(2026,10,18))
