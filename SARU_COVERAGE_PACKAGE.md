# SA Rugby exact-identity coverage package

## Scope and limits

This package connects the existing approved `Women’s USA Rugby Events | Women` identity to the USA Women's subset of the 2026 WXV Global Series, and adds the missing First Division to the existing approved `Currie Cup | Men` identity. It does not approve WXV as a new competition, other national teams, youth, Varsity Cup, or a future edition.

The existing Currie Cup Premier Division source is preserved. All added feeds remain partial: a publisher's match centre is not proof of complete catalog coverage. A successful empty response is not proof that no wagering opportunities exist. Only exact competition, season and team identities may produce fixtures; unknown opponents, missing times, cancellation, postponement and unresolved records remain held.

## Official evidence checked October 18, 2026

- SA Rugby public match centre: https://springboks.rugby/match-centre/
- The match centre's public fixture API: https://springboks.rugby/api/match-centre/matches
- 2026 WXV Global Series competition `669f0a5d-fc63-4c08-855e-2cbcf51dd401`, season `513e569c-09fd-46da-ad91-bd91ec0b1476`, USA Women team `23f44fd1-36cb-4f3e-8d1b-20882b5b631d`.
- 2026 Carling Currie Cup First Division competition `56038bac-544a-482e-a5da-6351054efc5d`, season `e2b76a5f-d3e9-42f8-a5cd-4df2b469bd22`.
- Independent World Rugby match page corroborates October 24 USA Women vs Italy Women, 20:15 UTC: https://www.world.rugby/wxv/en/match/39ca0cc5-5b4c-4b30-a9a4-3f7572212cb2

The API returned 30 WXV matches. Only five belong to USA Women; two have future confirmed dates at the time of verification: October 24 at 20:15 UTC against Italy Women and October 30 at 21:15 UTC against England Women. The normal October 18–25 Review Today window includes only the October 24 match. Other WXV teams do not activate the USA approval.

The First Division feed contains 18 dated 2026 records from June 13 through July 24, with scores. Those completed matches are evidence for exact source identity and the elapsed edition, not new upcoming fixtures. No 2027 dates are inferred.

Varsity Cup's distinct competition listing returned no current-edition fixtures. Its existing gap is retained. The broad SARU approval label cannot substitute for an exact competition feed.

## Verification

- Full Python test discovery: 662 tests passed after rebasing onto soccer package PR269.
- Focused scope tests include source/competition/season/team identity changes, unknown status, strict forfeit flags, scored records, gender/youth/placeholders, UTC/Chicago boundaries, duplicate IDs, changing pagination totals, second-page denial and atomic failures.
- Live collection: two successful requests, six WXV rows filtered to one USA Women fixture; First Division returned zero current-window rows. Both sources remain partial.
- Isolated full collector and catalog rebuild: one exact USA fixture, zero catalog-rejected events; Varsity remains ADAPTER_GAP. USA moves from OFFICIAL_WINDOW_ONLY to ADAPTER_CONFIGURED, which denotes connection, not complete coverage. Currie was already configured and does not increase that numerator.
- Existing Premier Division adapter, source restrictions and the 733-identity denominator are unchanged. Exact dated 2026 season windows prevent accidental annual recurrence.
- Independent review completed before publication. Normal workflow publication and live deployment must be verified after merge; no generated schedule or inventory files are manually rewritten by this package.
