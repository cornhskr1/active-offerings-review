"""Optional USTA provenance cannot change canonical tennis review output."""
import datetime
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'scripts/refresh_global_schedule.py').read_text()
BLOCK = SCRIPT[SCRIPT.index('# Optional calendar provenance'):SCRIPT.index('events.sort(key=')]

class UstaCollectorSafetyTests(unittest.TestCase):
    def run_block(self, events, sources, fn, files=True):
        with TemporaryDirectory() as directory:
            data = Path(directory)
            if files:
                for name in ('tennis-schedule.json','usta-reviewed-references.json'):
                    (data/name).write_text('{}')
            ns = dict(events=deepcopy(events),source_status=deepcopy(sources),
                      DATA=data,json=json,deepcopy=deepcopy,NOW_UTC=datetime.datetime(2026,10,18,18,tzinfo=datetime.timezone.utc),
                      reconcile_usta_references=fn)
            exec(BLOCK, ns)
            return ns['events'], ns['source_status']

    def test_optional_failure_preserves_all_canonical_fields(self):
        event = dict(id='canonical',source_id='tennis-itf-world-tour-women',
                     status_detail='REVIEW — U18 IN PRE-DRAW ACCEPTANCE POOL',
                     u18_risk=False,restriction_risk=True,restriction_signals=['existing'],
                     catalog_approval='EXPLICIT SOURCE MAPPING')
        source = dict(id='tennis-usta-pro-circuit-women',source_type='coverage-gap',
                      approved_catalog=True,ok=True,events=0)
        def fail(candidate_events, candidate_sources, *args):
            candidate_events[0]['status_detail'] = 'incorrect clearance'
            candidate_sources[0]['events'] = 100
            raise ValueError('official PDF unavailable')
        events,sources = self.run_block([event],[source],fail)
        self.assertEqual([event],events)
        self.assertEqual('unavailable',sources[0]['reference_status'])
        self.assertEqual(0,sources[0]['crosslisted_reference_count'])
        for key,value in source.items(): self.assertEqual(value,sources[0][key])

    def test_missing_manifest_does_not_erase_tennis(self):
        event={'id':'unchanged'}
        source={'id':'tennis-usta-pro-circuit-men','approved_catalog':True,'events':0}
        events,sources=self.run_block([event],[source],lambda *args: self.fail('must not call'),files=False)
        self.assertEqual([event],events)
        self.assertEqual('unavailable',sources[0]['reference_status'])

    def test_unapproved_or_unselected_usta_does_not_fetch(self):
        for sources in ([],[{'id':'tennis-usta-pro-circuit-men','approved_catalog':False}]):
            events,out=self.run_block([{'id':'unchanged'}],sources,lambda *args:self.fail('must not call'))
            self.assertEqual([{'id':'unchanged'}],events)
            self.assertEqual(sources,out)

if __name__=='__main__': unittest.main()
