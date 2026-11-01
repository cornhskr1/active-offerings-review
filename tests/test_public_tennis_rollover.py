"""Complete verified-publication -> site staging, synthetic athletes only."""
import copy
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_full_private_snapshot as fixtures
from scripts.prepare_full_private_preview import prepare_full_preview
from scripts.snapshot_semantic_guards import validate_change

NOW=datetime(2026,11,1,18,tzinfo=timezone.utc)
REG='data/tennis-u18-registry.json'
INTEL='data/tennis-intelligence.json'


def athlete(name,dob):
    return {'name':name,'source_url':'https://synthetic.example/ranking.pdf',
            'age_evidence':{'status':'verified_dob','dob':dob,'checked_at':'2026-10-14',
                            'review':{'id':'synthetic-only'}}}


class PublicRolloverTests(unittest.TestCase):
    def stage(self,change=None,legacy=False,clock=NOW):
        case=fixtures.FullSnapshotTests();case.setUp()
        try:
            old={p:json.loads(case.raw[p]) for p in (REG,INTEL)}
            adult=athlete('Synthetic Adult','2008-11-01');child=athlete('Synthetic Child','2009-11-01')
            old[REG].update(records=[adult,child],verified_u18=[adult,child])
            old[INTEL].update(live_u18_registry=[adult,child],tournaments=[{'id':'held','permission_required':True,'source_generated_at':'2026-10-01T00:00:00Z'}])
            new=copy.deepcopy(old)
            for doc in new.values():doc['generated_at']='2026-11-01T17:06:00Z'
            new[REG]['verified_u18']=[copy.deepcopy(child)];new[INTEL]['live_u18_registry']=[copy.deepcopy(child)]
            if change:change(new)
            for p in (REG,INTEL):
                (case.previous/p).write_text(json.dumps(old[p]))
                raw=json.dumps(new[p]).encode();(case.bundle/p).write_bytes(raw)
                case.manifest['files'][p]=hashlib.sha256(raw).hexdigest()
            case.save_previous();case.save_manifest()
            before=fixtures.snapshot(case.previous);candidate=fixtures.snapshot(case.bundle)
            try:
                if legacy:
                    with patch('scripts.prepare_full_private_preview.retention_baselines',side_effect=lambda a,b,n:a):
                        prepare_full_preview(case.site,case.bundle,case.preview,now=clock,**case.kw)
                else:prepare_full_preview(case.site,case.bundle,case.preview,now=clock,**case.kw)
                self.assertEqual((case.preview/REG).read_bytes(),(case.bundle/REG).read_bytes())
                self.assertEqual((case.preview/INTEL).read_bytes(),(case.bundle/INTEL).read_bytes())
            except ValueError:
                self.assertFalse(case.preview.exists())
                raise
            finally:
                self.assertEqual(before,fixtures.snapshot(case.previous));self.assertEqual(candidate,fixtures.snapshot(case.bundle))
                self.assertEqual(case.before,fixtures.snapshot(case.site))
        finally:case.tearDown();case.doCleanups()

    def test_full_stage_reproduces_original_failure_then_accepts_exact_durable_rollover(self):
        with self.assertRaisesRegex(ValueError,'retained identity'):self.stage(legacy=True)
        self.stage()

    def test_underage_durable_loss_duplicates_or_altered_evidence_reject_before_staging(self):
        changes=[lambda d:d[INTEL].update(live_u18_registry=[]),
                 lambda d:d[REG]['records'].pop(0),
                 lambda d:d[REG]['records'].append(copy.deepcopy(d[REG]['records'][0])),
                 lambda d:d[REG]['records'][0]['age_evidence'].update(dob='2007-11-01'),
                 lambda d:d[REG]['records'][0]['age_evidence']['review'].update(id='changed'),
                 lambda d:d[REG]['records'][0].update(name='Changed Name')]
        for i,change in enumerate(changes):
            with self.subTest(i=i),self.assertRaises(ValueError):self.stage(change)

    def test_held_timestamp_hold_clear_stale_or_future_proof_reject(self):
        changes=[lambda d:d[INTEL]['tournaments'][0].update(permission_required=False),
                 lambda d:d[INTEL]['tournaments'][0].update(source_generated_at='2026-11-01T17:00:00Z'),
                 lambda d:d[REG].update(generated_at='2026-10-31T17:00:00Z'),
                 lambda d:d[REG].update(generated_at='2026-11-02T17:00:00Z'),
                 lambda d:d[REG]['records'][0].update(permission_required=True)]
        for i,change in enumerate(changes):
            with self.subTest(i=i),self.assertRaises(ValueError):self.stage(change)

    def test_shared_document_never_combines_reviewed_people_or_loses_identity(self):
        a=athlete('One','2009-01-01');b=athlete('Two','2009-01-01')
        validate_change({'records':[a,b]},{'records':[a,b]},now=NOW)
        for rows in ([a],[a,a]):
            with self.assertRaises(ValueError):validate_change({'records':[a,b]},{'records':rows},now=NOW)

    def test_naive_clock_cannot_authorize_a_rollover(self):
        with self.assertRaisesRegex(ValueError,"aware staging clock"):
            self.stage(clock=NOW.replace(tzinfo=None))
