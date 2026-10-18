"""Offline browser/request traps for the approved named-publisher pause."""
import ast
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from scripts.publisher_access_policy import permission_hold_reason
from scripts.tennis_publisher_holds import (paused_snapshot, install_browser_hold,
    route_publisher_request, retain_paused_tournaments, mark_permission_metadata)
from scripts.usta_reference_reconciliation import reconcile_usta_references, OWNER

ROOT=Path(__file__).resolve().parents[1]


def browser_class(filename):
    tree=ast.parse((ROOT/'scripts'/filename).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Browser')
    ns={'permission_hold_reason':permission_hold_reason,'paused_snapshot':paused_snapshot,
        'install_browser_hold':install_browser_hold}
    exec(compile(ast.Module(body=[node],type_ignores=[]),filename,'exec'),ns)
    return ns['Browser']


class TennisPublisherHoldTests(unittest.TestCase):
    def test_both_snapshot_entrypoints_stop_before_browser(self):
        for filename in ['refresh_tennis_intelligence.py','refresh_tennis_age_scan.py']:
            browser=browser_class(filename).__new__(browser_class(filename))
            browser.page=Mock()
            for url in ['https://www.itftennis.com/en/players/123','https://www.usta.com/calendar.pdf',
                        'https://site.api.espn.com/x','https://reports.fiba.basketball/x']:
                result=browser.snapshot(url)
                self.assertTrue(result['permission_required']);self.assertFalse(result['ok'])
            browser.page.goto.assert_not_called()
            browser.page.on.assert_not_called()

    def test_directory_search_is_blocked_before_fill_or_goto(self):
        cls=browser_class('refresh_tennis_age_scan.py');browser=cls.__new__(cls);browser.page=Mock()
        self.assertIsNone(browser.fill_search('https://www.itftennis.com/en/players/','Example',r'/players/','itftennis.com'))
        browser.page.goto.assert_not_called();browser.page.locator.assert_not_called()

    def test_context_route_blocks_redirects_subresources_and_all_held_families(self):
        page=SimpleNamespace(context=Mock())
        install_browser_hold(page)
        pattern,handler=page.context.route.call_args.args
        self.assertEqual(pattern,'**/*')
        for host in ['itftennis.com','www.usta.com','site.api.espn.com','sdataprod.ncaa.com',
                     'reports.fiba.basketball','faw.cymru']:
            route=Mock();route.request.url='https://'+host+'/resource';route.request.method='GET'
            handler(route);route.abort.assert_called_once_with('blockedbyclient');route.continue_.assert_not_called()
        for host in ['www.atptour.com','www.wtatennis.com','app.utrsports.net','omavs.com','itftennis.com.example.org']:
            route=Mock();route.request.url='https://'+host+'/resource';route.request.method='GET'
            route.fetch.return_value.status=200;route.fetch.return_value.headers={}
            handler(route);route.fulfill.assert_called_once();route.abort.assert_not_called()
            route.fetch.assert_called_once_with(url=route.request.url,max_redirects=0)

    def test_service_workers_disabled_before_guarded_navigation(self):
        for filename in ['refresh_tennis_intelligence.py','refresh_tennis_age_scan.py']:
            cls=browser_class(filename);pw=Mock();browser=cls(pw)
            self.assertEqual(pw.chromium.launch.return_value.new_page.call_args.kwargs['service_workers'],'block')
            browser.page.context.route.assert_called_once()

    def test_retained_itf_is_stale_not_freshened_or_erased(self):
        saved={'generated_at':'2026-10-01T00:00:00Z','tournaments':[
            {'id':'keep','tour_id':'itf-men','source_url':'https://www.itftennis.com/event',
             'participants':[{'name':'Example','last_verified':'2026-09-30'}]},
            {'id':'unaffected','tour_id':'atp','source_url':'https://www.atptour.com/event'}]}
        rows=retain_paused_tournaments(saved)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['id'],'keep')
        self.assertTrue(rows[0]['source_stale']);self.assertTrue(rows[0]['collection_paused'])
        self.assertEqual(rows[0]['source_generated_at'],saved['generated_at'])
        self.assertEqual(rows[0]['participants'],saved['tournaments'][0]['participants'])
        self.assertNotIn('source_stale',saved['tournaments'][0])

    def test_usta_hold_never_fetches_and_retains_saved_reference_timestamp(self):
        get=Mock(side_effect=AssertionError('No PDF request permitted'))
        events=[{'id':'x','calendar_references':[{'owner':OWNER,'checked_at':'old','source_url':'https://www.usta.com/a.pdf'}]}]
        sources=[{'id':'tennis-usta-pro-circuit-men','reference_checked_at':'old','events':0}]
        out,states=reconcile_usta_references(events,sources,{},None,dt.datetime.now(dt.timezone.utc),get=get)
        get.assert_not_called()
        self.assertEqual(out[0]['calendar_references'][0]['checked_at'],'old')
        self.assertTrue(out[0]['calendar_references'][0]['source_stale'])
        self.assertEqual(states[0]['reference_status'],'permission-required')
        self.assertEqual(states[0]['reference_checked_at'],'old')
        self.assertNotIn('source_stale',events[0]['calendar_references'][0])

    def test_inline_probe_skips_held_sources_and_routes_subresources(self):
        text=(ROOT/'.github/workflows/verify-tennis-source-health.yml').read_text()
        self.assertIn('install_browser_hold(page)',text)
        self.assertIn('if permission_hold_reason(url):',text)
        self.assertLess(text.index('if permission_hold_reason(url):'),text.index('response=page.goto'))
        self.assertIn('service_workers="block"',text)

    def test_metadata_is_lane_specific_and_preserves_evidence_date(self):
        doc={'generated_at':'old'};mark_permission_metadata(doc,'new')
        self.assertEqual(doc['generated_at'],'old')
        self.assertEqual(doc['publisher_permission_holds'][0]['tour_ids'],['itf-men','itf-women'])

if __name__=='__main__':unittest.main()
