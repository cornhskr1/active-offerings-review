# Compliance tools operations handoff

## Ownership and evidence

Nich is the release decision owner. A passing check permits review; it does not independently authorize merging, deployment, publisher access or recovery from a provider hold. Keep the app PR and its data-manifest companion in one review package. Record exact source commits, test results, deployment outcome and normal-publication evidence.

- Active Offerings app: https://github.com/cornhskr1/active-offerings-review
- Data publishing: https://github.com/cornhskr1/active-offerings-data
- Compliance / Wager Analysis portal: https://github.com/cornhskr1/wagering-compliance-portal
- Current source assessment: [source register and decisions](investigations/source-reliability-2026-10-30.md)
- Portal architecture and privacy: the portal repository's ARCHITECTURE.md, SECURITY.md and docs/report-data-flow.md.

These repositories have different roles. The app owns executable collectors, reviewed configuration and the dashboard. The data repository publishes validated complete snapshots using reviewed app code. The portal consumes approved public references and processes operator reports locally. Do not commit operator reports, patron records, credentials or browser session state as recovery artifacts.

## Routine publication review

1. Check the data workflow's conclusion and the actual published manifest, source-commit receipt and snapshot timestamp. The normal schedule collector is `Refresh Approved Sports Schedule`, configured hourly at minute 7 UTC; GitHub may delay it. A successful workflow alone does not mean every source succeeded.
2. Compare review-window dates, per-source `ok`, saved check/observation dates, errors, retained-stale flags and fixture count. A regenerated bundle or retained event must not acquire a new verification date by inference.
3. Review the basketball acceptance register and readable report. Distinguish exact fixtures, partial coverage, calendar-only records, missing connections, scope holds, failed sources and a healthy empty window. None grants wagering approval.
4. Check the visible Odds API safety-hold notice and bounded deployment summary. A held run may legitimately publish successfully with zero requests and zero events. Do not clear the cache or rerun collection to make the badge green.
5. For the portal, inspect bundled reference windows and the U18 review/coverage warning. A successful app release does not resolve overdue age evidence or missing source observations.

## Changing collector code

Prepare one focused app PR with exact competition/edition/phase evidence and failure cases. Preserve catalog restrictions, participant-age checks, Nebraska location/timing rules, source holds, original observation dates and zero-quota API checks. A fixture feed is not participant eligibility evidence.

The data repository's `contracts/trusted-app-code.json` must match every selected executable/test blob. Its unchanged selector excludes `data/`, `docs/` and Markdown. Changes to runtime code, tests or fixtures usually need a companion manifest; a documentation-only PR under `docs/` does not. Replay the exact proposed tree, verify unapproved changes remain pending, and run the data repository's tests. Do not expand selector permissions to avoid updating the manifest.

After owner approval, merge the app first, then its companion manifest. Verify the app merge tree and manifest against the reviewed heads, app deployment and data publishing-boundary checks. Observe normal scheduled output before reporting production fixture gains. Never reset a provider safety stop as part of a manifest update.

## Failed refresh or deployment

Keep the last verified complete snapshot, original timestamps and explicit warnings. Inspect the failed step before any retry. Distinguish revision-selection failure, parser/identity rejection, incomplete publisher evidence, permission hold, TLS/access failure, packaging validation and deployment failure.

- Revision mismatch: reconcile the exact reviewed app tree and manifest; do not trust arbitrary new blobs.
- Parser/identity rejection: capture only permitted public evidence, verify exact scope and test changed/ambiguous cases before repair. Do not silently drop inconvenient malformed rows or extend expired dates.
- Publisher access or timing: retain the block/manual check. Do not disable TLS, alter identities to evade access controls, use an unapproved mirror, or invent dates/times.
- Odds API uncertain stop: preserve state and original safe reason. Historical lost cause cannot be recreated by a new diagnostic. Obtain explicit owner recovery review before any action that resumes collection.
- Failed app deployment: inspect the existing deployment safety gate and prior provider usage. Do not bypass the gate, broaden credentials or rerun provider collection without the required review.

## Rollback and backup

Keep immutable reviewed commit SHAs and the last verified snapshot/manifest. Use the existing validated complete-snapshot recovery path; do not assemble mixed-date output files or relabel stale data as fresh. Rollback is a release decision requiring owner approval and the same manifest, compatibility and deployment checks as forward release. Restoring older code does not authorize clearing provider holds or weakening restrictions.

Operator reports remain local originals. Preserve original reports and saved review exports before changing workstation or portal version. V1 saved review states reopen decisions under the current evidence-binding model while retaining notes; V2 states are not supported by older portal builds. Do not rename schema markers to force compatibility. Mapping-only publication is distinct from a full Learning workspace, which can contain report context; follow the portal's mapping review process.

## Acceptance and unfinished work

A released parser is implemented, not operationally confirmed, until a normal publication uses that exact reviewed code and produces healthy, correctly scoped observations. Retain missing phases, incomplete dates and participant-age limits even after fixtures appear. External blockers can complete triage without completing coverage.

Portal #76 is superseded by #181/#182. Portal #168 is superseded by #178: current calendar matching preserves source health, stale/cancelled/removed observations, unknown venue/time and original provenance; requires the reported event date; compares offset timestamps in Central time; and keeps amber or conflicting locations in review. Location context uses full reported property/terminal denominators and does not infer patron identity or coordination.

Roger Care is separate from this compliance handoff. Its open PRs, cloud records and medication data are not part of these releases.
