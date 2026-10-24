# Guarded private Pages source checkpoint

The initial baseline is the actual last successful legacy publication, run
`40088052843`, artifact `12558087093`, archive SHA-256
`7016e439786c633852f3eac8a7a26182c8ecc16fbc2b4bae1583f43c34838a57`.
The authenticated job checked out app commit
`97527b26ef964bf67fd3d67b06eb3dc7c0b85a42`; all 31 root public files were
captured and hashed without modification. This bootstrap is exact-anchor-bound,
not a fallback for any future missing publication manifest.

Only in this legacy bootstrap, `public_manifest.data_commit` denotes that
**application repository data-source commit**, not a private repository seed.
Normal generated manifests use the actual immutable private data repository SHA.
All 17 applied configuration revisions are unknown (`null`) and pending; the
bootstrap does not invent per-family collection provenance.

The legacy publication does **not** contain the later old-global persistence
`db0b390a726539615d13f5f024abc83bd2b8264d`. The new private seed may retain those
legitimate updates, but its candidate is independently checked against this
actual published last-good state for holds, identities and evidence invariants.

The owner-approved source checkpoint binds the exact reviewed workflow blob
`0f76ca30ca7789aaa14eeebbda2e1858d078ca13`. Before preparing this activation,
the coordinating release owner verified GitHub API evidence at
2026-10-24 11:15:51 UTC: app main `protected: true`, enforcement for everyone,
and required `full-regression` from GitHub Actions (application ID 15368).
Owner save confirmation and settings evidence also showed strict up-to-date
checks and no bypass. This records the observed release checkpoint, not a claim
that repository settings can never change. Private seed publication and exact-head
CI must complete before this source-switch PR is merged.

This checkpoint grants no credentials or scope changes. Existing source holds and
zero-quota collector policy remain unchanged. The approved source and bootstrap
files are fail-closed inputs, not an override for the previous-deployment guard.

## Held-time reconciliation

The final old global run advanced 171 held-source `hold_recorded_at` values and
seven paused UEFA `checked_at` values without new observations. The unchanged
protected gate correctly rejected those differences. The collector now retains
those prior values (including unknown/null), while first-time holds may record
an administrative hold time without inventing a source check. The raw final
snapshot is preserved separately; only an explicitly audited seed reconciliation
may restore those exact 178 fields from this authenticated publication. It must
leave every other final-run field and file intact. This is not new collection,
a permission release, or a relaxed timestamp guard.
