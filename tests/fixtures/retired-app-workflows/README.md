# Historical collector policy fixtures — not executable workflows

These seventeen byte-for-byte source workflows preserve pre-retirement regression
assertions (source bounds, held publishers, cadence, serialization, old publication
ordering). They are outside `.github/workflows` and cannot be activated by GitHub.
`manifest.json` binds their exact bytes and the corresponding inert app files.

`tests.retired_workflow_policy` validates **every actual retired app entry point**
before returning any historical fixture. `test_retired_app_collectors.py` also
checks actual retirement directly and rejects changed entry points or fixtures.
No historical assertion establishes current collection or runtime acceptance.

Replacement data scheduling, protected source selection, source cadence/holds,
complete snapshot ownership and normal non-force publication are independently
tested in the data repository's reviewed migration package. In particular, old
push-trigger, rebase and two-commit tests here describe historical behavior, not
the replacement's deferred-config and single-atomic-commit policy.

This batch only retires app collectors. Pages stays unchanged; private collector
activation, branch protection and consumer cutover require their separate verified
prerequisites. A no-op manual invocation never collects or persists source data;
it cannot satisfy the F1 migration persistence proof.
