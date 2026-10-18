# Basketball coverage package

## Fixed scope and finish line

This package reconciles the **89 Basketball competition/event identities** in catalog version 10.1.26, including separate men/women identities. It does not mean 89 distinct leagues. NCAA Basketball is a separate sport and is unchanged.

Acceptance requires every identity to have an exact approved scope, its fixture/calendar/source state, current publication evidence, missing coverage and a next action. A configured adapter is not finished operational coverage. A documented blocker completes triage, not the underlying connection. No missing, blocked or empty result grants approval or an all-clear.

The [staff-readable status report](BASKETBALL_COVERAGE_STATUS.md) and machine-readable [acceptance register](data/basketball-coverage-acceptance.json) is rebuilt with each normal global-schedule publication. It keeps linkage state separate from operational state, preserves source failure details, and cannot attribute old-adapter publication results to a replacement adapter. It contains public reference information only.

## Starting point, October 18

- 22 configured fixture connections, 55 calendar-only sources, 6 explicit adapter gaps, 6 unlinked identities.
- The 13:35 UTC publication supported actual fixtures for only 3 identities; 21 identities had a failed source (including 2 calendar-only sources), 53 were calendar-only, 6 were connection gaps and 6 had documented scope holds.
- Existing configured sources must still be checked for later rounds, playoffs, qualifiers, women/men and season rollover. A current-window fixture count is not a full-phase coverage claim.
- Six explicit gaps: FIBA World Cup men/women, FIBA 3x3 World Cup men/women, Chile LNB and Copa Chile.

## Work packages within this one review

1. FIBA official fixture/report evidence: current/next editions and exact competition scope, not completed historical slices from draft #249.
2. Chile official Liga Uno/LNB and Copa Chile: exact competition, year, named opponents and publisher timezone; preserve access blocks rather than reuse old assumed UTC dates.
3. EuroLeague/EuroCup official fixture family: replace calendar-only/failed-provider evidence only when a current supported payload is verified.
4. All 89 identities reconciled in one acceptance register, including explicit holds and shared-provider failures.

The shared TheSportsDB family is tracked separately as a provider-sized repair rather than 17 independent basketball league PRs. PBA and NBB publisher access failures are not silently cleared. No held draft #249 content is merged wholesale.

## Release evidence

For each implemented connection require exact scope/identity tests; missing date/time, contradictory scope and source failures must fail closed. Verify actual normal-run output and published Review Today behavior after an authorized merge. Before that publication, a new adapter is pending normal verification, not operationally complete.

This package does not claim the entire Basketball sport is complete while externally blocked or calendar-only identities remain. Use the register's per-identity next action, rather than restarting league discovery or repeatedly asking for one-league merges.

### Verified implementation and remaining limits

- EuroLeague and EuroCup now use the publisher's public Media Game Center API. Full regular-season payloads contain 380 and 224 fixtures, respectively; the adapter verifies every row before emitting unplayed games. The API does not establish postseason or next-season coverage.
- EuroLeague Women and Basketball Champions League now use the current official FIBA competition reports, with exact edition, geometric table columns, complete first regular-phase inventory, report freshness and UTC/date-only protections. Future unnamed playoff slots remain held. Opponent abbreviations are preserved exactly as printed, not expanded by guesswork.
- An isolated live run of the actual global collector on October 18 produced 42 fixtures for October 18–25: 10 EuroLeague, 16 EuroCup, 8 EuroLeague Women and 8 BCL. All four sources returned healthy statuses and no errors. The actual Review Today model retained all 42 fixtures. This is prepublication evidence; the register deliberately keeps all four connections pending until the normal runner publishes them.
- Current phase limits: EuroLeague through April 16, 2027; EuroCup through January 13, 2027; named first-phase FIBA fixtures through December 2 and December 23, 2026. All four retain visible partial-coverage warnings. No age clearance follows from a fixture feed.
- Chile LNB and Copa Chile remain manual checks because public pages do not expose unattended fixture records and the backend requires authentication. Copa Chile now points to its own calendar, not Liga Uno. World Cup and 3x3 finals are not replaced by qualifiers or old editions.
- The next shared-provider repair should assess 27 remaining approved TheSportsDB source entries after this package replaces EuroCup and BCL. Treat that as one provider-family task, not repeated league-specific merges; API limits and actual successful output must be reported independently of configuration.
