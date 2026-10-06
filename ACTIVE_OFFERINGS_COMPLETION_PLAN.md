# Active Offerings completion plan
Reconciled October 6, 2026 against GitHub main `6dccce1a4c659182eebc521f68797902710efab2` and its normal 10:06 UTC schedule publication. #248 recovery remains pending merge.

Priority 2 remains active. This plan records the user's request to resume league connections after the Compliance Portal work and permits one narrow U18 verification-date presentation change in both products. It does not authorize automatic aging out or a new athlete research project.

## Baseline and reconciliation
Main's refreshed linkage baseline is 733 identities: 352 configured adapters, 181 gaps, 147 official windows only, and 53 unlinked. The pending #248 recovery adds two partial team schedules, giving 354 configured and 179 gaps; the other counts remain unchanged. Therefore 379 identities still lack configured adapters. Neither linkage nor a successful source check proves full-phase coverage.

The normal October 6 10:06 UTC snapshot contains 2,122 events in the October 6–13 review window and 23 failed non-gap source checks. The regenerated inventory uses that snapshot without inventing healthy publication results for pending connections. The normal refresh workflow now rebuilds and commits inventory with the schedule and identity registry.

Soccer accounts for 143 of the 179 remaining adapter gaps. The other 36 span Rugby (8), Basketball (6), Esports (5), Rodeo (5), Volleyball (4), Tennis (3), Motorsports (2), Bowling (1), Cricket (1), and Lacrosse (1). Calendar-only and unlinked entries require separate review; event-based Boxing/Combat authorities are not automatically conventional league-feed candidates.

Season states are 221 dated, 48 descriptive, 65 documented holds, 25 event-based, 64 partial, 31 pending, and 279 recurring. Belgian Cup's incomplete calendar now has its missing explicit partial-window flag. The per-sport `pending_dates` field combines pending, no-window and partial states; do not label that combined counter as strictly pending dates or add it to coverage gaps.

## Ordered work packages
| Order | Deliverable | Reviewable completion evidence |
|---|---|---|
| 1 | Verification dates, narrowly scoped | Active Offerings general and tennis U18 sections display recorded last-verification dates; absent dates say Not recorded. Portal carries the same evidence metadata without exposing athlete identities. Sync/build timestamps remain distinct. No birthday inference, age-out, new evidence crawl, or reset to today's date. |
| 2 | Current baseline and unfinished branches | Regenerate inventory from current registry/configuration and a normal current-window publication. Reconcile PR #248 and #249 against current main, refresh their evidence and aggregate guards, and rerun checks. Record each exact identity delta; no blind addition of their advertised counts. |
| 3 | Current-window source reliability | Review current failed, stale, incomplete, and unnamed-matchup sources in publisher families. Verify correct competition, division, phase, named opponents, date/time, and unattended runner access. Repair source failures or retain actionable source warnings. |
| 4 | Remaining Priority 2 connections | Convert real gaps in material batches by provider/source family. First recover unfinished soccer/basketball batches; then rank currently active or approaching competitions by staff impact and identities resolved. Cover all 143 soccer gaps, the other 36 gaps, the 147 calendar-only entries, and the 53 unlinked entries in one explicit work register. |
| 5 | Coverage depth and Priority 2 exit audit | Audit the configured sources too: regular season, later rounds, playoffs, qualifiers, men/women, and tournament phases. For every schedulable identity require exact-scope fixture evidence; event-based authorities require an explicit event-check process. An external blocker stays unresolved and visible. |
| 6 | Priority 3 alias revalidation | Preserve existing Kambi, Caesars, and IGT work. Validate mappings against the final exact identities, including team-only IGT labels and division conflicts. Ambiguity remains staff review; do not restart the entire alias project. |
| 7 | Priority 4 catalog-change acceptance | Test a controlled addition, modification, and removal from catalog detection through staff decision, identity mapping, schedule linkage, and portal reference publication. New/changed entries stay held until the required review. |
| 8 | Priority 5 combined release verification | Run both repositories against the same approved reference snapshot. Check representative operator reports, NCAA restrictions, U18 matching, boxing/combat context, queue grouping/counts, staff controls, source warnings, and exports. Confirm deployed behavior and reference parity. |
| 9 | Priority 6 maintenance handoff | Document daily source checks, verification-date ownership, catalog changes, manual holds, refresh failures, rollback/recovery, and scheduled-job ownership. Publish the remaining external-blocker register with next-review triggers. |

## U18 date boundaries
The 64 general registry records currently have no recorded verification date. Do not use a file commit, generated_at, or import date as their last verification.

Tennis records already contain last_verified and official-profile evidence, including profiles that state age while dob is null. Display those dates as recorded; they do not establish birthdays or automatic age-out eligibility. This plan postpones comprehensive age evidence discovery and aging-out logic.

The Compliance Portal bundles hashed identity matching rather than a public athlete list. Propagate verification metadata with honest completeness information (dated versus undated records, or a date range), without presenting the newest single athlete date as the verification date of the entire list. A rebuilt bundle must not imply new verification.

## Unfinished PR recovery
- [#248](https://github.com/cornhskr1/active-offerings-review/pull/248): reconciled with current main; exactly two partial team schedules recovered. Egypt parses structured match records, exact competition, pairing and explicit ISO timezone. Saudi parses per-row dates, competition, pairings and Saudi-local clocks, including 2027 rows. Live checks found 14 and 13 upcoming fixtures respectively. Egypt contributes one current-window fixture; Saudi's next date is October 14. Neither establishes full league coverage. New Zealand remains a gap: the official page no longer renders the expected widget; its linked 2026 PDF requires exact fixture parsing and reserve-team eligibility gates. Current runner publication remains a post-merge check.
- [#249](https://github.com/cornhskr1/active-offerings-review/pull/249): returned to draft and corrected its coverage claims. Four FIBA parsers pin completed June/August/September slices, including qualifiers whose catalog scope is unverified. Chile's homepage and calendar shell no longer expose the expected server-rendered fixture cards. Rebuild this provider batch from current main only after verifying fixture payloads, year, timezone, current/next phases and exact competition scope. Do not merge its stale inventory or wholesale source-file replacement.

The next work package is current-window reliability. Group the 23 failures into publisher families, preserve warnings for external access or unpublished data, and record normal runner evidence after repairs. Continue the source-family register without counting historical fixture slices as forward coverage.

## Batch work register and gates
Each batch records: provider family; exact identity keys; coverage state before/after; evidence URL and last checked date; verified phases and missing phases; current publication results; alias preservation; unresolved blockers; next-review trigger; PR and checks.

A batch is done when the scoped implementation and evidence are reviewed and its normal publication behaves correctly. A documented hold can finish triage of a row, but cannot turn incomplete schedule coverage into Priority 2 completion.

Do not promise a completion date until the refreshed register distinguishes implementable connections from publisher-access blocks, unpublished dates, and event-specific manual checks. Continue meaningful multi-identity/provider batches; avoid a one-league merge cadence. Keep the existing priority order and user-facing staff functions.
