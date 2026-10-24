# Inactive public-source pilot acceptance

**Not wired into Pages. No production source switch, workflow permissions,
credentials, schedules, or provider execution are changed.**

For the full writer inventory and consistent Portal reference snapshot, see
[complete snapshot preparation](complete-snapshot-preview.md). It is also inactive
and does not replace per-family semantic review.

## Existing three-milestone finish line

1. **Collector migration and output ownership.** The private two-file pilot is
   working; 17 application-repository writer workflows still require grouped
   migration. `review-data.json` is shared with NCAA football; migrating public
   refresh alone must not replace football-owned event evidence. The private
   repository's consolidated inventory identifies the other shared-output groups.
2. **Validated Pages integration and rollback.** The protected application now
   contains an offline pilot acceptance gate and immutable isolated staging.
   It is preparation, not production integration or a completed live rollback.
3. **Permission lockdown and acceptance.** Old app writers, branch protections,
   credential lifecycle, normal refresh evidence, Portal sync and final recovery
   acceptance remain outstanding. Access/credential changes and production
   cutover require specific owner approval; these scripts do not perform them.

## Protected code and trust boundary

`scripts/prepare_private_pilot_preview.py:prepare_preview` takes a trusted staged
application site, a downloaded v1 pilot bundle, a **new** preview destination,
explicit aware `now` and maximum status age (1–86400 seconds), and matching
expected/observed immutable application and data commit IDs. The caller must
independently establish the observed identities via trusted checkout and
pinned authenticated retrieval. Strings or the returned receipt are not
signatures and do not establish authenticity themselves.

The semantic contract is application-owned `scripts/pilot_data_contract.py`,
reviewed alongside the private repository's `prepare_pilot_candidate.py`.
No module, workflow or executable from the data repository is imported or run.
The original `verify_external_data_candidate.py` and preview/manual preflight
remain compatible; this stronger gate is **not automatically activated**.

### What it validates

- Exactly `data/status.json` and `data/review-data.json` plus the v1 hash manifest;
  no extra files, symlinks, non-regular inputs, duplicate JSON keys, NaN/Infinity,
  oversized files, incomplete inventories or digest mismatch.
- Exact status root fields, unique preserved source IDs/URLs/name/priority,
  reviewed source-row fields, strict counts/booleans/HTTP metadata, preserved
  permission-required publisher holds.
- Status `generated_at` and review `background_checked_at` agree, are neither
  future nor stale, and do not regress from the trusted retained site.
- Every review field except `background_checked_at` remains type-sensitively
  identical to the retained review, including football events, older
  `generated_at`, age evidence, warnings and discovery fields. A background
  availability check must not relabel old event evidence as fresh.

Freshness refers **only to background source-status checks**, not complete or
current event/age evidence. This contract does not validate other data families.

### Failure and rollback behavior

Validation captures exact verified candidate bytes before copying. It stages
in a temporary sibling directory and renames a complete result to a new preview
path. Any validation/copy failure cleans the partial stage and preserves the
original site. Existing previews are never intentionally replaced; callers must
allocate unique destinations and serialize access to their parent directory.
No deployment pointer, live publication or retained bundle is advanced.
The returned receipt stays outside the published site and records immutable
identities and manifest hash with `production_enabled: false`.

This is last-known-good **preservation**, not proof that a production Pages
rollback, data revision selection or retention policy has been implemented.

## Acceptance before production activation

- Resolve shared `review-data.json` publication ownership with football; use a
  complete consistent revision rather than a stale two-file partial overwrite.
- Complete reviewed schemas, freshness semantics, writer dependencies and
  authenticated revision transport for every migrated family.
- Review the actual production workflow diff and Pages concurrency fingerprint;
  preserve failure history, verified cache recovery and source holds.
- Obtain explicit approval for production switch and any credential/access
  changes; do not broaden the current token's permissions implicitly.
- Verify ordinary scheduled runs without duplicate provider calls or paid odds
  credits, downstream Portal reference sync, last-good retention and rollback.
- Remove app write access only after replacement publication is proven; then
  apply reviewed branch protections and close the bounded acceptance record.

## Offline verification

`python -m unittest tests.test_private_pilot_acceptance -v`

Tests use synthetic data only, including hostile payloads, timestamps, lost
publisher holds, review ownership violations, provenance mismatch, failed copy,
immutable output preservation and changed input after validation. Full repository
regression and independent review are still required for the exact proposed head.
