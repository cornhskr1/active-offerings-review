# Active Offerings completion plan
Reconciled October 6, 2026 against GitHub main `d3b9f9bcd826352e08fd90c28fb413d384bc9159`.

Priority 2 remains active. This plan records the user's request to resume league connections after the Compliance Portal work and permits one narrow U18 verification-date presentation change in both products. It does not authorize automatic aging out or a new athlete research project.

## Baseline and reconciliation
The checked-in inventory contains 733 operational identities: 352 ADAPTER_CONFIGURED, 181 ADAPTER_GAP, 147 OFFICIAL_WINDOW_ONLY, and 53 NO_LINKED_SOURCE. Thus 381 identities lack configured fixture adapters. This is a linkage snapshot, not a completion percentage. Some of the 352 configured adapters cover only a specific round, qualifier, tournament slice, or phase.

Inventory registry timestamp: October 2. Its schedule snapshot is September 29, with a September 29–October 6 window. Refresh and regenerate the inventory before using these numbers to assign current source-health work. The ledger's older current-status table still describes 731 identities; preserve historical checkpoints but update the active summary.

Soccer accounts for 145 of the 181 adapter gaps. The other 36 span Rugby (8), Basketball (6), Esports (5), Rodeo (5), Volleyball (4), Tennis (3), Motorsports (2), Bowling (1), Cricket (1), and Lacrosse (1). Unlinked and calendar-only entries must also be reconciled; they are not automatically candidates for conventional league feeds. Boxing and Combat Sports include event-based approval authorities.

The season summary reports 63 partial windows, 31 pending dates, and 66 documented holds. These overlap coverage states and must not be added to the 381. Reconcile the differing per-sport pending-date counters before presenting an aggregate date-work total.

## Ordered work packages
| Order | Deliverable | Reviewable completion evidence |
|---|---|---|
| 1 | Verification dates, narrowly scoped | Active Offerings general and tennis U18 sections display recorded last-verification dates; absent dates say Not recorded. Portal carries the same evidence metadata without exposing athlete identities. Sync/build timestamps remain distinct. No birthday inference, age-out, new evidence crawl, or reset to today's date. |
| 2 | Current baseline and unfinished branches | Regenerate inventory from current registry/configuration and a normal current-window publication. Reconcile PR #248 and #249 against current main, refresh their evidence and aggregate guards, and rerun checks. Record each exact identity delta; no blind addition of their advertised counts. |
| 3 | Current-window source reliability | Review current failed, stale, incomplete, and unnamed-matchup sources in publisher families. Verify correct competition, division, phase, named opponents, date/time, and unattended runner access. Repair source failures or retain actionable source warnings. |
| 4 | Remaining Priority 2 connections | Convert real gaps in material batches by provider/source family. First recover unfinished soccer/basketball batches; then rank currently active or approaching competitions by staff impact and identities resolved. Cover all 145 soccer gaps, the other 36 gaps, the 147 calendar-only entries, and the 53 unlinked entries in one explicit work register. |
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
- [#248](https://github.com/cornhskr1/active-offerings-review/pull/248): Egypt Premier League, Saudi First Division, and New Zealand National League. Existing checks passed on the September 29 branch; those checks do not establish compatibility or current fixture coverage on October 6.
- [#249](https://github.com/cornhskr1/active-offerings-review/pull/249): five basketball identities through shared FIBA/LNB sources. Existing checks passed on its September 29 branch. September tournament games are now historical; verify continuing utility and qualifiers' exact approval scope before counting these as forward coverage. Its Copa Chile description must reconcile with current main and recorded conflicting-match holds.

Refresh these branches rather than duplicating their adapters. Keep each provider family together in a reviewable PR, with current runner evidence and explicit partial-scope limits.

## Batch work register and gates
Each batch records: provider family; exact identity keys; coverage state before/after; evidence URL and last checked date; verified phases and missing phases; current publication results; alias preservation; unresolved blockers; next-review trigger; PR and checks.

A batch is done when the scoped implementation and evidence are reviewed and its normal publication behaves correctly. A documented hold can finish triage of a row, but cannot turn incomplete schedule coverage into Priority 2 completion.

Do not promise a completion date until the refreshed register distinguishes implementable connections from publisher-access blocks, unpublished dates, and event-specific manual checks. Continue meaningful multi-identity/provider batches; avoid a one-league merge cadence. Keep the existing priority order and user-facing staff functions.
