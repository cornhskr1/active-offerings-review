"""Exact revised senior fixture; missing old cards do not prove completion."""
import ast,copy,datetime as dt,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from lxml import html
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from dynamic_league_fixture_adapter import parse_malta_tickets
SOURCE=next(s for s in json.loads((ROOT/'data/soccer-uefa-domestic-sources.json').read_text())['sources'] if s['id']=='uefa-soccer-malta-maltese-premier-league-men')
PAGE=(ROOT/'tests/fixtures/malta_senior_nov2_2026.html').read_bytes()
DAY=dt.date(2026,11,1)
def parse(page=PAGE,day=DAY):return parse_malta_tickets(page,SOURCE,today=day)
class MaltaRescheduledTests(unittest.TestCase):
 def test_exact_revised_primary_card_and_detail(self):
  rows=parse();self.assertEqual(1,len(rows));r=rows[0]
  self.assertEqual('Marsaxlokk FC at Gzira United FC',r['name']);self.assertEqual('2026-11-02T19:00:00Z',r['start_time'])
  self.assertEqual('Tony Bezzina Stadium',r['location']);self.assertFalse(r['coverage_complete']);self.assertIn('unverified',r['coverage_warning'])
  d=html.fromstring((ROOT/'tests/fixtures/malta_gzira_marsaxlokk_nov2_2026.html').read_bytes());text=' '.join(d.text_content().split())
  self.assertEqual(['Tickets — Gzira United FC - Marsaxlokk FC - VBet Malta Premier League 2026/2027'],d.xpath('//title/text()'))
  self.assertIn('Monday November 02, 2026 at 20:00',text);self.assertIn('Tony Bezzina Stadium',text)
 def test_changed_fields_fail(self):
  for old,new in [(b'20:00',b'00:00'),(b'>02<',b'>03<'),(b'Tony Bezzina Stadium',b'Unknown'),(b'Gzira United FC',b'Gzira U17'),(b'2026/2027',b'2027/2028'),(b'2026-11-02',b'2026-11-03'),(b'href="/matches/gzira',b'href="https://foreign.test/matches/gzira')]:
   self.assertIn(old,PAGE)
   with self.subTest(change=new),self.assertRaises(ValueError):parse(PAGE.replace(old,new,1))
 def test_missing_duplicate_extra_split_and_old_card_reject(self):
  for action in ('missing','duplicate','extra','split','old'):
   d=html.fromstring(PAGE);card=d.xpath('//article')[0]
   if action=='missing':card.getparent().remove(card)
   elif action=='split':d.xpath('//section')[0].append(card)
   else:
    c=copy.deepcopy(card)
    if action in ('extra','old'):c.xpath('.//h3/a')[0].set('href','/matches/floriana-fc-vs-valletta-fc-2026-11-01' if action=='old' else '/matches/other')
    card.getparent().append(c)
   with self.subTest(action=action),self.assertRaises(ValueError):parse(html.tostring(d))
 def test_youth_cannot_supply_missing_senior_clock_and_no_renewal(self):
  self.assertEqual(1,len(parse(PAGE.replace(b'00:00',b'20:00'))))
  with self.assertRaises(ValueError):parse(PAGE.replace(b'20:00 - Tony',b'TBD - Tony'))
  for day in (dt.date(2026,10,31),dt.date(2026,11,2),dt.date(2026,11,3)):
   with self.subTest(day=day),self.assertRaises(ValueError):parse(day=day)
 def test_actual_collector_branch_one_fixture_or_zero_on_damage_access(self):
  tree=ast.parse((ROOT/'scripts/refresh_global_schedule.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="source.get('source_type') == 'official-malta-ticket-fixtures'")
  wrapper=ast.Module(body=[ast.For(target=ast.Name(id='source',ctx=ast.Store()),iter=ast.List(elts=[ast.Name(id='configured_source',ctx=ast.Load())],ctx=ast.Load()),body=[node],orelse=[])],type_ignores=[])
  program=compile(ast.fix_missing_locations(wrapper),'<actual Malta collector>','exec')
  for status,page,expected in [(200,PAGE,1),(200,PAGE.replace(b'20:00',b'TBD',1),0),(403,PAGE,0)]:
   response=Mock(content=page);response.raise_for_status.side_effect=ValueError('HTTP403') if status==403 else None;get=Mock(return_value=response)
   c=dict(configured_source=SOURCE,requests=SimpleNamespace(get=get),parse_malta_tickets=parse_malta_tickets,TODAY=DAY,END=dt.date(2026,11,8),NOW_UTC=dt.datetime(2026,11,1,22,10,tzinfo=dt.timezone.utc),TZ=dt.timezone(dt.timedelta(hours=-6)),datetime=dt,HEADERS={},errors=[],source_status=[],events=[],seen=set(),count=0)
   exec(program,c);self.assertEqual(expected,len(c['events']));self.assertEqual(bool(expected),c['source_status'][0]['ok']);self.assertEqual(1,get.call_count)
