"""Complete31 publication cache independent of the candidate's private history."""
import hashlib
import json
import unittest
from tests import test_full_private_snapshot as full_fixture
from scripts.public_data_snapshot import build_public_snapshot,read_public_snapshot,SNAPSHOT_ROOT,POINTER

class PublicDataSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.f=full_fixture.FullSnapshotTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
    def build(self):
        return build_public_snapshot(self.f.site,app_commit='a'*40,data_commit='d'*40,
            data_contract_app_commit=self.f.spec['app_commit'],configuration_state=self.f.manifest['configuration'],publisher_run_id=12345)
    def test_complete_publication_manifest_binds_run_and_all31_files(self):
        result=self.build();root=self.f.site/SNAPSHOT_ROOT/result['snapshot_sha256']
        values,manifest=read_public_snapshot(root,expected_digest=result['snapshot_sha256'])
        self.assertEqual(len(values),31);self.assertEqual(manifest['publisher_run_id'],12345)
        self.assertEqual(manifest['app_commit'],'a'*40);self.assertEqual(manifest['data_commit'],'d'*40)
        self.assertNotIn('BASKETBALL_COVERAGE_STATUS.md',values)
        self.assertEqual(json.loads((self.f.site/POINTER).read_text())['snapshot_sha256'],result['snapshot_sha256'])
        self.assertEqual(self.build(),result)
    def test_untrusted_digest_or_changed_cache_is_rejected(self):
        result=self.build();root=self.f.site/SNAPSHOT_ROOT/result['snapshot_sha256']
        for digest in ('0'*64,'latest',None):
            with self.assertRaises(ValueError):read_public_snapshot(root,expected_digest=digest)
        path=root/'data/status.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):read_public_snapshot(root,expected_digest=result['snapshot_sha256'])
        with self.assertRaises(ValueError):self.build()
    def test_prior_publication_required_no_git_or_private_fallback(self):
        self.f.kw['expected_previous_snapshot_sha256']='0'*64
        self.f.reject()
        self.f.save_previous();(self.f.previous/'data/status.json').unlink();self.f.reject()
    def test_run_identity_must_be_positive_integer(self):
        for value in (0,-1,True,'12345'):
            with self.assertRaises(ValueError):build_public_snapshot(self.f.site,app_commit='a'*40,data_commit='d'*40,
                data_contract_app_commit=self.f.spec['app_commit'],configuration_state=self.f.manifest['configuration'],publisher_run_id=value)

if __name__=='__main__':unittest.main()
