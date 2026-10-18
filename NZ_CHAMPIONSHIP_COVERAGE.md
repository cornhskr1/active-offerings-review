# New Zealand men's National League Championship: bounded fixture connection

## Exact scope

One existing identity, `ofc-soccer-new-zealand-national-league-men`, changes from a gap to **partial** championship round-robin coverage. Chatham Cup remains a gap. No other source or approval scope changes.

The official championship page now includes Sporty widget configuration with sport 28, season 35, competition 13413 and owner 14667. Its public widget JavaScript declares read-only JSON POST metadata and fixture queries. Live metadata names competition 13413 `Dettol Men's National League 2026` and grade 705173 `Senior Men`. Section 235801 contains the exact eleven-club championship roster corroborated by NZ Football's September 9 announcement. The same competition also contains September section 267766 records involving other clubs: those are excluded rather than expanding scope. Competition 14997 is women's and is excluded.

The accepted roster includes Auckland FC Reserves and Wellington Phoenix's reserve team because NZ Football explicitly identifies them as participants in this senior championship. That does not establish athlete ages or clear athlete-specific markets. Regional phases, grand final, and 2027's changed format are not covered. The generic introduction page's ten-club description is stale; use the explicit 2026 announcement instead.

## Verified capture, October 18, 2026

The bounded September–December public query yields 55 named championship fixtures and 11 BYEs. Twenty named fixtures have score evidence; 35 remain unscored through December 6. Five date-only fixtures fall within October 18–25; thirty are later:

- October 23: Ferrymead Bays–Cashmere Technical.
- October 24: Auckland City–Auckland United.
- October 25: Auckland FC Reserves–Birkenhead United; Napier City Rovers–Wellington Phoenix reserves; Eastern Suburbs–Miramar Rangers.

The independent Chatham Cup query found a completed September 5 final and no future fixtures; this is not counted as a working source. No claim of full season, current-week completeness, or no actual games is made.

## Integrity and failure handling

- Gate current official widget edition, competition metadata, senior grade, section, stage, exact team ID/name/organization tuples and source configuration.
- Preserve dates literally. Publisher clocks have no offset and no verified timezone basis, so UTC kickoff times are not invented.
- Suppress scored/live records even when `ResultStatus=0` and `Status=Confirmed`: both appear on completed games in the capture. Missing required result fields fail closed.
- Hold BYEs, unknown opponents, other sections, final/unreviewed rounds, non-confirmed fixtures, and unresolved past records. Reject invalid dates, contradictory row scope and conflicting duplicate IDs.
- Buffer the collector's events and deduplication keys until all rows pass. A late error leaks neither cards nor seen keys.
- Empty response fails closed; a valid source with no in-window fixture remains partial, never inferred offseason.
- The adapter expires outside the bounded 2026 review period and must not roll dates into another edition.

## Official sources and reproducibility

- Championship page: https://www.nzfootball.co.nz/COMPETITIONS/Football/dettol-national-league-championship
- Explicit 2026 roster and phase announcement: https://www.nzfootball.co.nz/newsarticle/170010?newsfeedId=671503
- Public widget JavaScript: linked `/bundles/widgetswrappermain` on the championship page.
- Metadata: POST https://www.nzfootball.co.nz/api/v2/competition/widget/metadata/ with `["13413"]`.
- Fixtures: POST https://www.nzfootball.co.nz/api/v2/competition/widget/fixture/Dates with `{"CompIds":[13413],"OrgIds":[],"GradeIds":[705173],"From":"2026-09-01T00:00:00","To":"2026-12-31T23:59:59"}`.

Test captures in `tests/fixtures/nz_20261018` preserve the relevant source fields and both public widget tags; irrelevant HTML, personal official assignments and location fields were removed. The retained Dates capture includes the separate Chatham query and other section rows specifically to test exclusion. It is not an adapter fallback.

The separately linked Sporty PDF download returned HTTP 403. It was not retried, bypassed, or used by this adapter. The independently published public widget pages and read-only JSON queries returned HTTP 200 normally.

Local tests and fresh live retrieval are prepublication evidence only. Normal runner publication and deployed verification remain required after merge.

Validation: all 837 regression tests pass using the existing dependency environment. A fresh invocation of the production fetcher on October 18 returned 55 named championship fixtures, 11 BYEs, 20 scored exclusions and 35 unscored future rows, of which five fall in October 18–25. The exact men's-only production query excluded three other-section records. No source failures occurred. This is still local evidence, not normal-run publication.
