# Complete writer snapshot and Portal reference preparation

**Inactive implementation. No live collection, schedule, credential, access rule,
Pages source selection, or Portal synchronization workflow is activated here.**

## Protected complete-snapshot gate

`prepare_full_private_preview.prepare_full_preview` validates all **32 outputs
from 17 writer families** against the application-owned
`contracts/private-snapshot-files.json`. The private snapshot contains data and
its v2 manifest only; it cannot supply executable validation code or its own
allowlist. This application contract copies reviewed inventory metadata, not the
private repository's collector commands. Its application pin identifies the
inventoried contract revision, **not the observation date of every file**.

The complete manifest has exactly:

- `schema_version: 2`
- `contract: "complete-collector-snapshot/v1"`
- `app_commit`: inventoried application contract revision
- `files`: all 32 exact relative paths mapped to SHA-256 digests
- `configuration`: `target_app_commit` and exactly 17 `families` entries, each
  with `applied_app_commit` (40-hex or null for an unverified seed) and Boolean
  `pending_configuration` equal to applied revision differing from target.

The gate checks exact complete inventory, immutable identity agreement, hashes,
per-file sizes (including existing larger age caches), a 256 MB aggregate cap,
symlink/regular-file safety, JSON duplicate/nonfinite rejection and
observed top-level field types. It captures the verified bytes before staging.
The root Markdown evidence file `BASKETBALL_COVERAGE_STATUS.md` is not published;
The catalog PDF check confirms its existing allowed format signature, digest and
size; it is not a malware/active-PDF sanitizer or permission to publish arbitrary
documents.

31 public generated outputs are overlaid into an isolated copy of the trusted
site. App-owned static references, assets and application code are never supplied
or replaced by the private candidate.

### Do not confuse structural validation with semantic acceptance

The contracts preserve existing trusted collector semantics and tests; they do
not re-certify sporting facts or invent new freshness windows. The protected
application additionally compares candidate JSON with the independently trusted
previous publication: rights holds and their saved observations cannot disappear
or be relabeled fresh; schema-2 durable identities and reviewed age evidence are
retained; observation timestamps must be valid and nonfuture; URL-bearing fields
reject executable schemes and control characters. Computed age/exposure status
may advance without changing authoritative identity/evidence. Previously held
files may intentionally remain old: no blanket freshness cutoff is invented.
Normal source-family refresh, retention and production rollback still require
operational acceptance before activation.
The preview deliberately preserves timestamps and contents; it never labels old
observations fresh because packaging completed. The stronger two-file public
source-status pilot gate is documented separately in
[inactive pilot acceptance](inactive-pilot-acceptance.md).

Receipts expose the contract revision, trusted staged target revision, reported
per-family applied revision and pending family IDs. A matching top-level pin is
not proof that all families collected against that revision. Pending is computed
against the current staged target; null applied identity always remains pending.
The trusted fetch/checkout caller must independently establish the commit IDs;
format/equality checks are not signatures. `production_enabled` remains false.

## One immutable public reference snapshot for Portal consumers

The full preview invokes application-owned
`build_public_reference_snapshot.build_reference_snapshot` inside its unpublished
temporary stage. It combines these **seven** references from the final staged
site, preserving exact source bytes and dates:

- `data/known-u18.json` — protected app-owned
- `data/catalog-season-map.json` — protected app-owned
- `data/tennis-u18-registry.json`
- `data/tennis-age-cache.json`
- `data/competition-identity-registry.json`
- `data/catalog-live.json`
- `data/nebraska-collegiate-live.json`

`data/public-reference-current.json` contains exactly:

```json
{"schema_version":1,"contract":"public-reference-pointer/v1","snapshot_sha256":"<64 lowercase hex>"}
```

The immutable directory is `data/reference-snapshots/<snapshot_sha256>/`.
Its `manifest.json` contains exactly `schema_version: 1`,
`contract: "public-reference-snapshot/v1"`, `app_commit`, `data_commit`, and `files`
(the exact seven original relative paths mapped to SHA-256). Manifest bytes are
UTF-8 JSON with sorted keys, separators `(',', ':')`, and one trailing newline.
The directory selector is SHA-256 of these bytes. There is no cyclic hash.

Files reside under that immutable directory at their original `data/...` paths.
Consumers pin the expected digest, validate the pointer/manifest, and fetch all
files from **that single directory**, never mix mutable latest-file URLs. Retained
snapshot directories are not overwritten or repaired if their bytes differ.
The new pointer advances only in the unpublished stage; actual activation still
requires an approved production workflow change.

## Independently anchored complete previous publication

`prepare_full_preview` requires `previous_publication` and an independently
verified `expected_previous_snapshot_sha256`, separately from the current app
`site`. Frozen Git data or the untrusted private candidate cannot stand in for
last-good published data. The protected gate validates every prior public file
before semantic comparisons. The mixed football file additionally retains current
protected configuration; only the original collector's generated fields may vary.

Every preview emits `data/public-data-current.json`, with exact fields
`schema_version: 1`, `contract: "public-data-pointer/v1"`, and
`snapshot_sha256`. The immutable directory is
`data/complete-snapshots/<snapshot_sha256>/`. Its canonical `manifest.json` has
exactly eight fields: `schema_version: 1`, `contract: "public-data-snapshot/v1"`,
`app_commit`, `data_commit`, `data_contract_app_commit`, `configuration`, `files`
(the exact 31 public output paths and SHA-256 values), and `publisher_run_id`.
The positive integer run ID comes from the trusted workflow, never the candidate.
Manifest canonicalization matches the seven-file reference manifest above.

The dormant restoration adapter must bind this manifest to the deployment guard's
proved successful run, via authenticated Pages artifact or the fixed-origin
immutable public snapshot and matching publisher run ID. An approved first-cutover
bootstrap is explicit, bound to a reviewed anchor and seed digests, and cannot
be reused after a newer success. Missing subsequent manifests fail closed.
The dormant workflow/profile must be reviewed and explicitly activated; this PR
changes no live workflow, credentials, branch rules, or production source.

## Last-good and deployment limitations

Preview destinations must be new and outside inputs. `..` aliases and symlinks
are rejected/canonicalized before containment checks. Copy/validation failure
cleans temporary directories and leaves the source site and existing preview
unchanged. This assumes a trusted, single-writer local staging parent; it is not
an adversarial multi-process filesystem lock or a production publication pointer.
The surrounding CI job must serialize writers. Publication retention and actual
Pages rollback still require acceptance; this code does not deploy.

## Verification

Run:

```sh
python -m unittest tests.test_private_pilot_acceptance tests.test_full_private_snapshot tests.test_public_reference_snapshot -v
```

Synthetic tests exercise all 17-family/32-file structural coverage, missing/extra
files, tampering, wrong types, applied/pending state consistency, static-reference
preservation, timestamp ownership, absolute freshness, provenance mismatch,
symlinks/path aliases, failed copy, immutable snapshots and unchanged prior output.
The exact current saved public baseline also passes the full gate without
changing observation timestamps, identities or hold markers. Full repository CI,
protected/private cross-contract parity, Portal producer/
consumer protocol tests and independent exact-head review remain release gates.
