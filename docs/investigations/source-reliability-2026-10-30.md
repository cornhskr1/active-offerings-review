# Source reliability assessment and remaining work

This is a triage checkpoint, not a statement that source reliability is complete.

## Evidence and units

The latest available normal global-schedule publication inspected here was generated at `2026-10-30T23:41:54.269339+00:00`, for 2026-10-30 through 2026-11-06. It contains 2542 saved event records and 650 unique source IDs: 445 report `ok: true`, 178 have explicit permission holds and 27 have other failure messages. An OK source can be partial or empty; a publication timestamp does not refresh retained observations.

Immutable source blob in the data repository: `4e69980359684ab6acb72866468fc35ec32b67f2` at `published/current/data/global-schedule.json`. Normal schedule workflow run: [41145950641](https://github.com/cornhskr1/active-offerings-data/actions/runs/41145950641). The later deployment run [41161732685](https://github.com/cornhskr1/active-offerings-review/actions/runs/41161732685) reports the Odds API collector still halted, zero events and zero requests, with safe reason `persistent_hold_requires_explicit_recovery`.

These are source-record counts. The earlier 23 noncurrent configured identities were a different, identity-level calculation in [the Review Today investigation](review-today-2026-10-30.md); do not equate or subtract those denominators. The unchanged latest basketball audit has 89 identities: 17 fixture-bearing, 51 calendar-only, eight failed/blocked, six fixture gaps, six scope holds and one healthy empty. It predates the released NBB fix.

## Permission-held source families

| Family | Held source records | Required next decision |
|---|---:|---|
| ESPN | 161 | Supported publisher access review; retain existing hold until explicitly authorized |
| FIBA | 2 | Supported publisher access review; retain existing hold until explicitly authorized |
| NCAA | 3 | Supported publisher access review; retain existing hold until explicitly authorized |
| USTA | 2 | Supported publisher access review; retain existing hold until explicitly authorized |
| ITF | 2 | Supported publisher access review; retain existing hold until explicitly authorized |
| FAW | 1 | Supported publisher access review; retain existing hold until explicitly authorized |
| UEFA | 7 | Supported publisher access review; retain existing hold until explicitly authorized |

The seven UEFA records have a configured access hold; this is not a blanket assertion about every UEFA publisher. The [source-by-source register](source-reliability-register-2026-10-30.csv) records all 205 failed IDs, original check dates, saved errors, categories and next actions. No held publisher was collected from during this assessment.

## Remaining non-permission failures

| Source ID | Saved failure | Triage | Next action |
|---|---|---|---|
| basketball-ph-governors | 403 Client Error: Forbidden for url: https://www.pba.ph/news/familiar-faces-new-imports-coming-over-for-govern | Access/TLS unresolved | Retain access warning. Review supported access or valid publisher TLS; no retries through alternate identities, TLS disabling, or unapproved mirrors. |
| basketball-br-nbb | NBB fixture identity or pairing changed | Released; normal publication pending | Observe the next normal scheduled publication using #322/#20; require healthy NBB status and exact in-window fixtures before counting recovery. |
| basketball-ph-pba | 403 Client Error: Forbidden for url: https://www.pba.ph/schedule | Access/TLS unresolved | Retain access warning. Review supported access or valid publisher TLS; no retries through alternate identities, TLS disabling, or unapproved mirrors. |
| volleyball-italy-superlega | SuperLega round identity changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| volleyball-italy-serie-a1-women | Serie A1 five-round publication horizon ended | Evidence horizon expired | Review a newly published exact round/team/date scope and tests before extending the evidence horizon. |
| tennis-atp-challenger | ATP Challenger publisher access blocked; manual verification required | Access/TLS unresolved | Retain access warning. Review supported access or valid publisher TLS; no retries through alternate identities, TLS disabling, or unapproved mirrors. |
| ncaa-water-polo-di-men | NCAA exact-team evidence window expired or invalid | Evidence horizon expired | Review a newly published exact round/team/date scope and tests before extending the evidence horizon. |
| ncaa-ice-hockey-di-women | NCAA exact-team evidence window expired or invalid | Evidence horizon expired | Review a newly published exact round/team/date scope and tests before extending the evidence horizon. |
| soccer-afc-malaysia-malaysia-super-league-men | MFL published round does not cover the full review window | Evidence horizon expired | Review a newly published exact round/team/date scope and tests before extending the evidence horizon. |
| soccer-afc-qatar-qatar-stars-league-men | QSL league upcoming weeks have an unexpected match count | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| soccer-afc-qatar-qsl-cup-men | QSL Cup: 9 published pairings lack date/kickoff | Publisher timing incomplete | Await official date and kickoff for the published pairings; do not infer a time. |
| soccer-afc-united-arab-emirates-uae-pro-league-men | UAE fixture detail identity missing | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| concacaf-soccer-canada-canadian-premier-league-men | HTTPSConnectionPool(host='www1.canpl.ca', port=443): Max retries exceeded with url: /watch (Caused by SSLError | Access/TLS unresolved | Retain access warning. Review supported access or valid publisher TLS; no retries through alternate identities, TLS disabling, or unapproved mirrors. |
| concacaf-soccer-canada-canadian-championship-men | Canada Soccer final pairing, venue, or kickoff changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| conmebol-soccer-uruguay-copa-uruguay-men | AUF competition phases changed: OCTAVOS DE FINAL | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| soccer-conmebol-libertadores-femenina | CONMEBOL 2026 women's fixture section is missing | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men | AFFA notice contained no timed senior fixtures | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men | BiH Wwin League page contained no timed fixtures | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-georgia-erovnuli-liga-men | Georgian senior upcoming match fields changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-iceland-besta-deild-karla-rvalsdeild-men | KSÍ date, venue or competition changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-ireland-league-of-ireland-premier-division-men | LOI fixture grouping changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-lithuania-a-lyga-men | Lithuanian LFF senior 2026 competition changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-portugal-ta-a-da-liga-men | Allianz Cup competition page identity changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-spain-supercopa-de-espa-a-men | RFEF Supercopa 2027 page identity changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-sweden-svenska-cupen-women | SvFF women's cup current round has no exact fixtures | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-switzerland-swiss-challenge-league-men | SFL publisher's current PDF link changed | Publisher structure/identity requires revalidation | Inspect the current official response; verify competition, division, edition, phase, named opponents, and time before a focused adapter change. |
| uefa-soccer-switzerland-swiss-cup-men | 403 Client Error: Forbidden for url: https://www.football.ch/en/schweizer-cup/spiele-resultate.aspx | Access/TLS unresolved | Retain access warning. Review supported access or valid publisher TLS; no retries through alternate identities, TLS disabling, or unapproved mirrors. |

The 27 records break down into five access/TLS failures, one released repair awaiting normal publication (NBB), four expired evidence horizons, one incomplete timing publication and 16 structure/identity candidates. These are triage categories from saved evidence, not new live publisher validation. A phase change, empty page or expired notice is not proof of an off-season or absent fixtures.

## Ordered repair decisions

1. Confirm NBB via normal publication; #322 and data #20 are merged and the app deployment passed. Captured-payload replay retained 13 review-window games; do not add them to live totals before publication.
2. Verify Italian SuperLega men and Serie A1 women as one publisher-family batch: the saved error is a round identity change / expired five-round horizon. Preserve distinct competitions, current edition, named opponents and Rome-local kickoff evidence. Do not extend the old dates mechanically.
3. Revalidate the permitted soccer round/phase/link candidates by publisher family, followed by the two exact NCAA team evidence subsets. Retain each unresolved scope and lack of participant-age evidence.
4. Keep QSL Cup undated fixtures and access/TLS failures visible until real publisher timing or supported access is available.
5. Odds API recovery requires a separate owner-reviewed decision: original cause was not retained in historical evidence. New diagnostic preservation cannot reconstruct it, and a green deployment cannot clear it.

No provider holds, source configuration, catalog restrictions, age checks, zero-quota limits, workflows or observation dates were changed for this assessment. No manual collection or recovery was initiated.

## Original cross-repository checklist

| Item | Outcome at this checkpoint |
|---|---|
| Tennis publication failure | Data #17 merged; latest successful tennis-family publication still requires its own normal-run confirmation |
| Source reliability | Assessment complete; underlying source repairs and external access remain open in the register |
| Wager performance / progress | Portal #172 merged |
| Evidence-bound saved reviews | Portal #171 merged |
| Old PR cleanup | Portal #76 closed as superseded by #181/#182; #168 closed as superseded by #178 |
| Documentation / maintenance handoff | This checkpoint and [operations handoff](../operations-handoff.md) document the remaining obligations; external blockers are not marked resolved |
| Roger Care #29 | Separate app; still open and outside this compliance change |

The cleanup was checked against portal main `0650d5984767bebaef3f2eabcd3863cacdefde97`. Seven relevant implementation/test files match the tested bytes. All 36 calendar-v2, NCAA historical-seed and location-drilldown tests passed. The old branches were not merged or deleted. #168's standalone document was absent from main, but its operational safety requirements are represented in the handoff; its implementation was carried forward by #178.
