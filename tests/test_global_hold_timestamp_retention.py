"""Execute only actual held-source branches with synthetic inputs, no providers."""
import ast
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import unittest
from scripts.publisher_access_policy import retained_source_events

ROOT=Path(__file__).resolve().parents[1]


def branch_code(marker):
    module=ast.parse((ROOT/'scripts/refresh_global_schedule.py').read_text())
    loop=next(node for node in module.body if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='source')
    branch=next(node for node in loop.body if isinstance(node,ast.If) and marker in ast.unparse(node.test))
    isolated=ast.Module(body=[ast.For(target=ast.Name(id='source',ctx=ast.Store()),iter=ast.List(elts=[ast.Name(id='source',ctx=ast.Load())],ctx=ast.Load()),body=[branch],orelse=[])],type_ignores=[])
    return compile(ast.fix_missing_locations(isolated),str(ROOT/'scripts/refresh_global_schedule.py'),'exec')


class GlobalHoldTimestampTests(unittest.TestCase):
    def context(self,source,prior):
        class PausedClient:
            def fetch(self,*args):raise PermissionError('Permission required: synthetic paused publisher')
        return dict(source=source,previous_schedule={'sources':prior,'events':[]},source_status=[],events=[],tour_calendars=[],
                    retained_source_events=retained_source_events,deepcopy=deepcopy,hold_reason='Permission required',
                    NOW_UTC=datetime(2026,10,24,10,tzinfo=timezone.utc),TODAY=None,END=None,UEFA_DOMESTIC_CLIENT=PausedClient(),
                    errors=[],seen=set(),count=0)

    def test_general_hold_retains_both_saved_times_and_null(self):
        for value in ('2026-10-01T00:00:00Z',None):
            with self.subTest(value=value):
                env=self.context({'id':'held','endpoint':'https://example.test'},[{'id':'held','hold_recorded_at':value,'checked_at':value}])
                exec(branch_code('hold_reason'),env)
                row=env['source_status'][0]
                self.assertEqual(row['hold_recorded_at'],value);self.assertEqual(row['checked_at'],value)
                self.assertTrue(row['collection_paused']);self.assertTrue(row['stale']);self.assertFalse(row['ok'])

    def test_first_hold_records_administration_not_source_observation(self):
        env=self.context({'id':'held'},[]);exec(branch_code('hold_reason'),env)
        self.assertIsNone(env['source_status'][0]['checked_at'])
        self.assertEqual(env['source_status'][0]['hold_recorded_at'],env['NOW_UTC'].isoformat())

    def test_paused_uefa_preserves_checked_or_unknown(self):
        for prior in ([],[{'id':'uefa','checked_at':None}],[{'id':'uefa','checked_at':'2026-10-01T00:00:00Z'}]):
            with self.subTest(prior=prior):
                env=self.context({'id':'uefa','source_type':'official-uefa-domestic-reviewed','access_status':'permission_required'},prior)
                exec(branch_code('official-uefa-domestic-reviewed'),env)
                row=env['source_status'][0]
                self.assertEqual(row['checked_at'],prior[0].get('checked_at') if prior else None)
                self.assertEqual(row['access_status'],'permission_required');self.assertFalse(row['ok']);self.assertEqual(row['events'],0)

if __name__=='__main__':unittest.main()
