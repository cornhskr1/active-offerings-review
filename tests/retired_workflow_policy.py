"""Hash-bound historical policy fixtures, never runnable collector entry points.

The old policy assertions remain useful regressions for source safeguards. Every
fixture access also verifies the actual corresponding app workflow is inert, so
these tests cannot silently validate historical files while a writer is restored.
Live replacement scheduling/publication contracts are tested in the data repo.
"""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/retired-app-workflows'
EXPECTED_FAMILIES=frozenset('''deep-tennis-age-scan refresh-catalog-change-queue
refresh-competition-identity-registry refresh-data refresh-global-schedule
refresh-jolpica-f1 refresh-ncaa-basketball-age-cache refresh-ncaa-basketball-rosters
refresh-ncaa-basketball refresh-ncaa-football refresh-nebraska-collegiate
refresh-priority-queue refresh-tennis-intelligence refresh-tennis-registry
refresh-tennis-review research-ncaa-basketball-ages update-catalog'''.split())

def retired_bytes(family):
    if family=='refresh-jolpica-f1':
        # MUST match data scripts.check_f1_migration_transition.RETIRED_WORKFLOW.
        return b'''name: Retired F1 collector\non:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n  retired:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "F1 collector retired; no provider collection"\n'''
    return f'''name: Retired {family}\non:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n  retired:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "Collector retired; no provider collection"\n'''.encode()

def verify_retirement():
    manifest=json.loads((FIXTURES/'manifest.json').read_text())
    if manifest['schema_version']!=1 or set(manifest['workflows'])!={f+'.yml' for f in EXPECTED_FAMILIES}:
        raise AssertionError('Retirement inventory must include exact seventeen writers')
    if {p.name for p in FIXTURES.glob('*.yml')}!=set(manifest['workflows']):
        raise AssertionError('Unexpected historical workflow fixture set')
    for name,item in manifest['workflows'].items():
        expected=retired_bytes(name.removesuffix('.yml'))
        if item['source_path']!='.github/workflows/'+name:
            raise AssertionError('Wrong retired workflow path')
        if (ROOT/item['source_path']).read_bytes()!=expected:
            raise AssertionError('Active app collector restored or retirement bytes changed: '+name)
        if hashlib.sha256(expected).hexdigest()!=item['retired_sha256']:
            raise AssertionError('Retirement evidence hash mismatch')
        if hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest()!=item['historical_sha256']:
            raise AssertionError('Historical policy fixture changed: '+name)
    return manifest

def historical_workflow_directory():
    verify_retirement()
    return FIXTURES

def historical_workflow_path(name):
    manifest=verify_retirement()
    if name not in manifest['workflows']:raise AssertionError('Not a retired writer')
    return FIXTURES/name
