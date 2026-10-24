# Prepared Pages migration adapters — no activation

These application-owned adapters complete the dormant transport/staging path.
They do not alter the live Pages workflow, source selection, guards, credentials,
retention, provider schedule or quota policy. The private repository never
supplies executable validation code. No real activation/bootstrap checkpoint is
shipped, and absent checkpoints fail before source collection.

## Complete private candidate

`fetch_full_private_candidate.py` uses the existing `DATA_REPO_READ_TOKEN` only
with fixed GitHub API paths in `cornhskr1/active-offerings-data`. It resolves main
once to an immutable commit, requires a complete nontruncated Git tree, and
accepts exactly the protected 32 files plus manifest under `published/current/`.
It rejects executable modes, symlinks, extra/missing files and unexpected blobs.
Each bounded base64 Git blob is independently checked against its Git object hash
and protected size limit; the complete v2 snapshot then passes the app-owned
manifest/hash/type validator. This supports binary PDF and files over 1 MB without
relying on the Contents API's inline-file behavior. Redirects are refused and no
private token is sent to raw file URLs or third-party storage. Output is a new,
atomically completed candidate, not a deployment.

## Independently proven previous publication

`restore_public_snapshot.py` requires the existing publication guard's
`odds-recovery-proof.json`, bound to the current run and successful anchor. It
independently rechecks that anchor's first-attempt job/steps through the same
reviewed guard contract. It selects the anchor's unique `github-pages` artifact,
checks authenticated run/head metadata and SHA-256, then reads its bounded ZIP/TAR
without extracting arbitrary archive paths. Linked/special/duplicate/traversing
members are rejected.

From that **same successful artifact**, it restores:

- the exact 31 public generated outputs and protected public snapshot manifest;
- the exact `odds-api-events.json` control state, including holds and cooldowns.

Normal migrated publications require the immutable public31 manifest and matching
root bytes; its `publisher_run_id` must equal the independently proved anchor.
Neither frozen app Git files nor newer private candidate files can substitute for
previous publication. The anchor's execution SHA may differ from the checkout SHA
because Pages checks out latest main; artifact metadata binds the former while
the protected output manifest records the latter.

JSON API redirects are refused. The authenticated artifact endpoint may provide
one HTTPS signed storage redirect to GitHub Actions/Azure Blob; the download uses
a **fresh request without the GitHub Authorization header**. Archive digest,
size, exact selected paths and subsequent public manifest/file hashes remain
mandatory. A second or unapproved redirect fails closed.

## Initial bootstrap and outage recovery

An initial legacy artifact has no new full-public manifest. That absence is not
permission to synthesize a baseline from private/latest data. A separately
reviewed `migration/activation/pages-bootstrap.json` must bind exactly:

- `repository`: `cornhskr1/active-offerings-review`;
- `anchor_run_id`, `artifact_id`, and authenticated `artifact_sha256`;
- `public_manifest`: the complete protected public31 manifest, including the exact
  legacy bytes' hashes, publisher run ID, immutable seed provenance and family
  configuration state;
- `public_snapshot_sha256`: SHA-256 of that canonical manifest.

Only that exact artifact can bootstrap; once a normal public pointer exists, its
manifest is required. Malformed pointers never invoke the bootstrap exception.
There is no perpetual missing-manifest or first-run reset.

Pages artifact retention remains **one day**, unchanged. If the anchor artifact
expires, collection blocks. An explicit retained archive may be supplied only
with an exact reviewed recovery checkpoint and still-authenticated matching
artifact metadata/digest. It cannot substitute an older run or alter odds state.
If authenticated metadata or exact retained bytes are unavailable, recovery stays
blocked for a separately reviewed owner decision; it never guesses from mutable
public files. Restoring public31 alone would be insufficient to authenticate odds
hold state, so no partial public-URL fallback is attempted.

## Inactive activation package

`migration/workflows/deploy-pages.yml.inactive` preserves existing concurrency,
step names/order and the original later zero-quota collector command. Only the
staging implementation changes, using the existing scoped read credential.
`migration/pages-activation-plan.json` records the exact template Git blob and
`migration/check_odds_deploy_safety.patch.inactive` prepares the matching audited
workflow pin change. Neither is applied to live code/workflows.

The stage additionally requires a reviewed `migration/activation/pages.json`
with exactly `schema_version: 1`, `source: "private-complete-snapshot/v1"`, and
`approved_workflow_blob` matching the activated workflow. Creating that file,
applying the template/guard pin together, and selecting production data is a
**separate owner-authorized cutover**, after exact-head CI/review and draining old
Pages work. No credential scope or branch-rule expansion is inferred.

At approved runtime the stage restores prior state, fetches/validates the complete
candidate, stages current protected app assets, runs protected prior-publication
invariants, emits public31 and Portal7 snapshots, and supplies unchanged prior
odds bytes to the existing later collector. It neither calls that provider itself
nor labels retained observations fresh. Any stage failure occurs before the
provider step; later publication failures remain subject to the unchanged guard.

Local staging assumes a trusted single-writer runner workspace. No live provider
or network testing is performed by the synthetic adapter suite.
