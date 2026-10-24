"""Public reference producer protocol; fixtures only, no publish/network."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.build_public_reference_snapshot import build_reference_snapshot,REFERENCE_FILES,POINTER,SNAPSHOT_ROOT,canonical


def files(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


class ReferenceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'stage';self.root.mkdir();self.raw={}
        for i,name in enumerate(REFERENCE_FILES):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
            raw=json.dumps({'generated_at':'2026-10-01T00:00:00Z','synthetic':i}).encode()
            path.write_bytes(raw);self.raw[name]=raw

    def build(self):return build_reference_snapshot(self.root,app_commit='a'*40,data_commit='d'*40)

    def test_digest_addresses_exact_manifest_and_all_seven_bytes(self):
        result=self.build();digest=result['snapshot_sha256']
        pointer=json.loads((self.root/POINTER).read_text())
        self.assertEqual(pointer,{'schema_version':1,'contract':'public-reference-pointer/v1','snapshot_sha256':digest})
        base=self.root/SNAPSHOT_ROOT/digest
        raw=(base/'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
        manifest=json.loads(raw);self.assertEqual(canonical(manifest),raw)
        self.assertEqual(set(manifest),{'schema_version','contract','app_commit','data_commit','files'})
        self.assertEqual(set(manifest['files']),set(REFERENCE_FILES))
        for name,data in self.raw.items():
            self.assertEqual((base/name).read_bytes(),data)
            self.assertEqual(manifest['files'][name],hashlib.sha256(data).hexdigest())
            self.assertEqual((self.root/name).read_bytes(),data)
        before=files(self.root);self.assertEqual(self.build(),result);self.assertEqual(before,files(self.root))

    def test_new_revision_keeps_old_snapshot_and_changes_pointer(self):
        first=self.build();old=self.root/SNAPSHOT_ROOT/first['snapshot_sha256'];before=files(old)
        name=REFERENCE_FILES[0];(self.root/name).write_bytes(b'{"generated_at":"2026-10-02T00:00:00Z"}')
        second=self.build();self.assertNotEqual(first['snapshot_sha256'],second['snapshot_sha256'])
        self.assertEqual(before,files(old))
        self.assertEqual(json.loads((self.root/POINTER).read_text())['snapshot_sha256'],second['snapshot_sha256'])

    def test_tampered_retained_snapshot_is_never_overwritten(self):
        result=self.build();path=self.root/SNAPSHOT_ROOT/result['snapshot_sha256']/REFERENCE_FILES[0]
        path.write_bytes(b'bad');before=files(self.root)
        with self.assertRaises(ValueError):self.build()
        self.assertEqual(before,files(self.root))

    def test_missing_or_linked_reference_and_bad_revision_rejected(self):
        path=self.root/REFERENCE_FILES[0];raw=path.read_bytes();path.unlink()
        with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/POINTER).exists())
        path.symlink_to(self.root/REFERENCE_FILES[1])
        with self.assertRaises(ValueError):self.build()
        path.unlink();path.write_bytes(raw)
        with self.assertRaises(ValueError):build_reference_snapshot(self.root,app_commit='main',data_commit='d'*40)
        self.assertFalse((self.root/POINTER).exists())

if __name__=='__main__':unittest.main()
