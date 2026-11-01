"""Exact November 1 results, retained round scope and no live requests."""
import ast,copy,datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from lxml import html
from scripts.nzs_prvaliga_fixture_adapter import next_round,verified_match,NOV1_RESULTS,ROUND14,ROOT_PATH
from tests.test_nzs_prvaliga_fixture_adapter import SOURCE
ROOT=Path(__file__).resolve().parents[1];FIX=ROOT/'tests/fixtures'
NOW=dt.datetime(2026,11,1,19,tzinfo=dt.timezone.utc);DAY=dt.date(2026,11,1)
BRAVO='nk-bravo-fc-koper-1snl2627-2026-11-02-170000'
def page():return (FIX/'nzs-scored-20261101.html').read_bytes()

class NovemberResultTests(unittest.TestCase):
 def parse(self,data=None,day=DAY,now=NOW):return next_round(page() if data is None else data,SOURCE,day,now)
 def test_exact_result_rows_leave_one_located_future_fixture_and_hold_later_rounds(self):
  rows,count=self.parse();self.assertEqual((1,20),(len(rows),count));self.assertEqual(ROOT_PATH+BRAVO,rows[0][2])
  event=verified_match((FIX/f'nzs-selected-{BRAVO}.html').read_bytes(),rows[0],SOURCE)
  self.assertEqual('2026-11-02T16:00:00Z',event['start_time']);self.assertEqual('Koper at Bravo Ljubljana',event['name'])
 def test_independent_official_details_bind_completed_state_and_original_identity_clock_venue(self):
  for key,score in NOV1_RESULTS.items():
   data=(FIX/f'nzs-selected-{key}.html').read_bytes();doc=html.fromstring(data);home,away,date,clock,venue=ROUND14[key]
   self.assertIn('Končano',' '.join(doc.xpath('//div[@class="match-data-score"]//text()')))
   self.assertEqual(score.split(' (')[0].split(' : '),[s.strip() for s in doc.xpath('//div[@class="match-data-score"]//span[@class="score"]/text()')])
   row=(dt.date.fromisoformat(date),14,ROOT_PATH+key,[home,away],venue,clock)
   self.assertEqual(venue,verified_match(data,row,SOURCE)['location'])
 def test_changed_score_missing_or_swapped_detail_and_identity_fail(self):
  for old,new in [(b'4 : 0 (3 : 0)',b'4 : 1 (3 : 0)'),(b'0 : 0 (0 : 0)',b'P : P'),
                  (b'nk-celje-nd-lendava-1903',b'nk-celje-unknown'),(b'datetime="17:30"',b'datetime="17:00"')]:
   self.assertIn(old,page())
   with self.subTest(old=old),self.assertRaises(ValueError):self.parse(page().replace(old,new))
  for action in ('missing','duplicate','unlink','location'):
   d=html.fromstring(page());r=d.xpath('//strong[@class="match-score"][contains(text(),"4 : 0")]/ancestor::tr')[0]
   if action=='missing':r.getparent().remove(r)
   elif action=='duplicate':r.getparent().append(copy.deepcopy(r))
   elif action=='unlink':r.xpath('.//strong[@class="match-score"]')[0].getparent().tag='span'
   else:r.xpath('.//strong[@class="match-score"]')[0].set('class','match-location')
   with self.subTest(action=action),self.assertRaises(ValueError):self.parse(html.tostring(d))
 def test_future_naive_historical_and_later_review_dates_reject_new_score_proof(self):
  for now in (NOW.replace(tzinfo=None),NOW.replace(hour=15)):
   with self.subTest(now=now),self.assertRaises(ValueError):self.parse(now=now)
  for day in (dt.date(2026,10,31),dt.date(2026,11,2)):
   with self.subTest(day=day),self.assertRaises(ValueError):self.parse(day=day)
 def test_actual_collector_branch_emits_nothing_for_score_detail_or_access_failure(self):
  tree=ast.parse((ROOT/'scripts/refresh_global_schedule.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="source.get('source_type') == 'official-nzs-prvaliga-next-round'")
  wrapper=ast.Module(body=[ast.For(target=ast.Name(id='source',ctx=ast.Store()),iter=ast.List(elts=[ast.Name(id='configured',ctx=ast.Load())],ctx=ast.Load()),body=[node],orelse=[])],type_ignores=[]);program=compile(ast.fix_missing_locations(wrapper),'<actual NZS collector>','exec')
  detail=(FIX/f'nzs-selected-{BRAVO}.html').read_bytes()
  for mode,expected in [('valid',1),('score',0),('detail',0),('access',0)]:
   response=Mock(content=page().replace(b'4 : 0 (3 : 0)',b'P : P') if mode=='score' else page());d=Mock(content=detail.replace(b'02.11.2026, 17:00',b'02.11.2026, 18:00') if mode=='detail' else detail)
   if mode=='access':response.raise_for_status.side_effect=ValueError('HTTP403')
   get=Mock(side_effect=[response,d]);context=dict(configured={**SOURCE,'endpoint':'https://www.nzs.si/klubi/moski/prva-liga-telemach/tekme','source_type':'official-nzs-prvaliga-next-round'},nzs_next_round=next_round,nzs_verified_match=verified_match,ThreadPoolExecutor=ThreadPoolExecutor,requests=SimpleNamespace(get=get),HEADERS={},TODAY=DAY,END=dt.date(2026,11,8),NOW_UTC=NOW,datetime=dt,TZ=dt.timezone(dt.timedelta(hours=-6)),errors=[],seen=set(),events=[],source_status=[],count=0)
   exec(program,context);self.assertEqual(expected,len(context['events']));self.assertEqual(mode in ('valid','detail') and 2 or 1,get.call_count)
