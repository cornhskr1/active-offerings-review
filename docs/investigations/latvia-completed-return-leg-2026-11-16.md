# Latvia completed return leg: November 16, 2026

Prepared from USL confirmation head `fbfde2326eb8664f2af1e45a31b1cd27959b973d`, intended to follow PR #455. Exact key: `soccer-latvia-latvian-higher-league-virsl-ga-men` (senior men, 2026).

## Consumed material trigger

[LFF article 19365](https://lff.lv/zinas/19365/virsligas-parspeles-uzvar-fk-tukums-2000/), published November 14, 2026 at 14:55, confirms Tukums won the return leg at Valmiera 1–0 and the tie 2–0 on aggregate. Checked November 16. This is the exact result publication named in the existing revisit trigger. The ledger records its source/version and consumed status. The map and source note distinguish the completed return leg from the separately scheduled Latvian Cup.

March 6–November 14 boundaries remain unchanged; only scheduled-to-actual endpoint evidence changes. Newly resolved calendars: **0**; prior evidence reconciled: **0**; first-time unresolved: **0**; triggered rechecks: **1**. Dates, statuses, 735 reviewed prior identities, one separately added pending WTA 125 key, and 327 dated / 409 undetermined current-catalog membership are unchanged.

## Release blocker

The existing Latvia regression asserts the old scheduled endpoint type. This PR updates that assertion to actual. [AGENTS.md](../../AGENTS.md) requires every test change to be coordinated with the collector trusted-app manifest release. The current request forbids other-repository writes. **Keep this PR unmerged until that dependency is coordinated.** No companion PR or other-repository write was performed; no trust gate is relaxed.

The local process service could not start a command (No such file or directory). Required GitHub checks validate this prepared branch. Publication/live verification can occur only after the release dependency is resolved and the reviewed passing head merges.

## Discovery checkpoint: no additional calendar resolution

Exact key `basketball-us-nba`: the [NBA key-date page](https://www.nba.com/news/key-dates), version updated November 14, 2026 at 2:58 PM, still omits the 2027 last-possible Finals date. Version inspected November 16 and consumed as a discovery lead only; no boundary, status or reviewed date changed and no calendar recheck progress was counted. Wait for a materially new Finals-boundary publication. Other targeted recent publication searches exposed no new qualifying PBA, Canada women's cup or Portugal women's cup boundary release; unchanged/secondary results were not promoted and their reviewed identities were not reopened.
