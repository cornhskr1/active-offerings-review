# Season boundary recheck — November 6, 2026

## Result and review scope

Reconciled against main commit `32568df4ca8ca99d2a0e755822a299f523a6adf7` (November 4), including the changes after the November 3 checkpoint. All 157 ledger keys resolve in the current season map, and every complete/incomplete designation agrees. The open basketball discovery PR #249 is unrelated to this date-only proposal and was not incorporated.

Nine existing incomplete records were rechecked. One previously missing season boundary is now established: the 2026/27 Italian LBA opening date. One additional phase boundary is recorded separately: USL League One regular-season completion. **No full-season endpoint was newly verified.**

The research ledger still contains 157 reviewed identities: 65 verified-complete, 52 awaiting-published-dates, 9 manual-verification-needed, 24 source-access-held, 5 scope-conflict and 2 not-scheduled. These are research-checkpoint counts, not classifications of all 735 catalog identities.

The existing catalog presentation model, evaluated for November 6 with the repository's saved source statuses, remains at **319 of 735 identities with usable dated season windows** (143 in season, 49 upcoming, 127 out of season; 416 undetermined). This is an offline model check, not verification of the deployed website or a fresh audit of the other 726 identities. The increase in verified opening-date detail does not increase the complete-window indicator.

## Confirmed corrections

| Competition / edition | Proposed change | Evidence and limitation |
| --- | --- | --- |
| Italian LBA, men, 2026/27 | Add `season_start_date: 2026-09-26`, replacing an unresolved September 26–27 opening weekend. | [Treviso's September 4 revised schedule](https://trevisobasket.it/lba-date-e-orari-delle-prime-cinque-giornate/) fixes its first game on September 26. The [LBA first-round Reyer–Cantu preview](https://www.legabasket.it/news/139544/preview-reyer-venezia-cantu) corroborates that date in its indexed official text; direct article extraction produced a page shell. Retain `season_window_complete: false`; May 9 is only the regular-season endpoint. |
| USL League One, men, 2026 | Add `regular_season_end_date: 2026-10-24`. | [U.S. Soccer's October 28 playoff guide](https://www.ussoccer.com/stories/2026/10/federation/everything-you-need-to-know-about-the-2026-usl-league-one-playoffs) identifies the regular-season phase. This field does not set `season_end_date`. |

## Unresolved findings and next evidence needed

| Competition / edition | Recorded opening | Closing-date result / next action |
| --- | --- | --- |
| Australian NBL, men, NBL27 / 2026/27 | September 19, 2026 | The [league announcement](https://www.nbl.com.au/news/nbl-unveils-exciting-2026-27-schedule) remains a regular-season publication. The [current schedule page](https://www.nbl.com.au/schedule) did not expose the deciding championship fixture, and the announcement's linked PDF could not be retrieved. Await an edition-specific postseason schedule. |
| German BBL, men, 2026/27 | September 18, 2026 | The [league announcement](https://easycredit-bbl.de/de/n/news/2026/august/easycredit-bbl-veroeffentlicht-vorlaeufigen-spielplan-fuer-saison-26-27-heimpartie-des-deutschen-meisters-alba-berlin-als-eroeffnung) gives a June 11 finals start. Visual inspection confirms that the [framework PDF](https://cms.easycredit-bbl.de/wp-content/uploads/2026/07/CD_RTP_2627-1.pdf) still leaves postseason cells blank. [Rostock's official club calendar](https://www.seawolves.de/voller-terminkalender-bei-den-seawolves/) supplies a June 11–19 best-of-five planning range, but no numbered deciding-game date. June 19 is retained as a research lead, pending league corroboration; the club page also has an unrelated cup-date inconsistency. |
| Italian LBA, men, 2026/27 | September 26, 2026 — newly established | A dated 2027 championship schedule, including conditional European-competition scenarios, remains missing. The [retrieved Finals notice](https://www.legabasket.it/news/138370/date-lba-playoff-unipol-2026) is for the 2026 postseason and is excluded from the 2026/27 endpoint. |
| NBA, men, 2026/27 | October 20, 2026 | [Finals endpoint unverified](https://www.nba.com/news/key-dates). |
| Unrivaled, women, 2027 / season three | January 8, 2027 | The [November 4 announcement](https://www.unrivaled.basketball/news/unrivaled-announces-2027-club-rosters-j51bz0hxvcux) identifies a November 6 matchup reveal. The [retrieved schedule](https://www.unrivaled.basketball/schedule?season=2027) does not identify the championship fixture. Recheck that reveal and subsequent postseason notices; keep the one-on-one tournament separate. |
| Mexican LNBP, men, 2026 | July 23, 2026 | The [official club calendar](https://diablosrojosbasquetbol.com.mx/calendario) supports the opener, but the [league site](https://lnbp.mx/) yielded no readable schedule and the [club playoff page](https://diablosrojosbasquetbol.com.mx/calendario/playoffs) lists zero fixtures. New secondary reporting identifies possible Game 7 on November 23; direct league/finalist confirmation remains required. No endpoint was added. |
| USL League One, men, 2026 | March 7, 2026 | U.S. Soccer retains a November 13–15 final window. The [Charlotte ticket page](https://tickets.charlotteindependence.com/event/usl-league-one-playoffs-round-3-charlotte-indepe-6li5m1) contradicts itself: November 14 in its event header/date, November 15 in its descriptions, opponent TBD. The league playoff page returned 403. Require a consistent league or confirmed-host announcement after the semifinals. |
| Damallsvenskan, women, 2026 | March 28, 2026 | The [SvFF opener](https://www.svenskfotboll.se/nyheter/serier/2026/01/avsparkstider-omgang-1-11-i-obos-damallsvenskan/) is exact. The [qualification document](https://www.svenskfotboll.se/4a5e9d/globalassets/svff/dokumentdokumentblock/tavling/gruppindelningar-och-spelordningar-for-kvalspelet-2026.pdf) still gives a November 19–22 allocation, without separately dating the return leg. The November 20/23 notice found in search belongs to 2025. |
| Copa Paraguay, men, 2026 | June 2, 2026 | The [opening announcement](https://www.apf.org.py/noticias/la-copa-paraguay-2026-tiene-definidas-sus-primeras-semanas-de-disputa) and [cup hub](https://www.apf.org.py/copa-paraguay) establish the opening and semifinal progression. No exact final date was established; the roadmap graphic's dates were not exposed in retrieved text. Await final programming or a readable official calendar graphic. |

## Data treatment

All nine records retain an incomplete calendar and an unset full-season closing date. Their ledger entries now explicitly state the edition, recorded opening and null closing date, alongside current findings, sources and next actions. Existing historical checkpoint metadata is preserved; `reconciled_against_commit` records this pass's base separately.

The NBA source-mapping duplicate is kept consistent with its catalog identity. No identity keys, aliases, approval scope, restrictions, source IDs, publisher holds, feed observations or recurring estimates are changed. Sources from an excluded edition and secondary leads are explained as such in the findings; their presence in the research reference list does not verify a boundary. No held publisher was queried, and no rejected source access was bypassed.

Season evidence describes timing only. It neither authorizes wagering nor refreshes event-feed coverage.

## Validation and publication state

- Full existing regression suite: **1,402 tests run: 1,401 passed, one skipped**. The skipped test requires local browser tooling; that tooling is unavailable here. No new application code or browser behavior is introduced.
- All 157 ledger keys and status classifications reconcile with the map; the nine changed identity records agree on edition, dates, findings and references.
- Identity projection remains 735. All nine incomplete records return `unknown`, a null closing date and no progress percentage in the presentation model. The overall 319/735 dated-window count is unchanged.
- Diff audit confirms only date/research fields changed in nine identities and the existing NBA source-mapping duplicate; identity, restriction and hold fields are preserved. JSON parsing and `git diff --check` pass.

This is a proposed repository update. Merge and deployment require the user's approval. No deployed-site verification is claimed; the November 3 publication-recovery note has not been treated as a current deployment diagnosis.
