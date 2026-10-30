# Review Today: low event count investigation

The published Odds API collector is in a persistent safety hold, not actively
supplying fixtures. The current global schedule also retains many old observations
from permission-held sources. Successful workflow execution does not establish
successful source collection or complete fixture coverage.

## Evidence boundary

Application main: `668e21e84ab73e92a3af21db66b42b0a46c13023`.
Read-only copies of the deployed site's JSON were inspected October 30, 2026,
and evaluated for October 30 through November 6, inclusive, in America/Chicago.
Freshness was evaluated at `2026-10-30T19:00:00Z` (2 p.m. CDT).
No provider API requests, workflow reruns, hold recovery, merges or deployments
were performed for this investigation. Raw provider events are not committed.

Primary evidence:

- [Successful catalog refresh](https://github.com/cornhskr1/active-offerings-data/actions/runs/40936358851)
- [Successful deployment, including collection step](https://github.com/cornhskr1/active-offerings-review/actions/runs/40983023902)
- [Published Odds API snapshot](https://cornhskr1.github.io/active-offerings-review/data/odds-api-events.json)
- [Published global schedule](https://cornhskr1.github.io/active-offerings-review/data/global-schedule.json)
- [Published coverage inventory](https://cornhskr1.github.io/active-offerings-review/data/priority2-coverage-inventory.json)
- [Published season and identity mapping](https://cornhskr1.github.io/active-offerings-review/data/catalog-season-map.json)
- [Published F1 observations](https://cornhskr1.github.io/active-offerings-review/data/jolpica-f1-events.json)

The published public-data pointer identifies snapshot
`953771d7ebbff4024a56182190bf15659803838d6ce259713eec6d5ae29fac6a`.
The global schedule was generated at `2026-10-30T14:04:22.118371+00:00`;
the coverage inventory at `2026-10-30T14:11:43.156612+00:00`.
These observations are newer than the supplied overnight workflow evidence;
they do not reconstruct exactly what the user saw on October 29.

## Confirmed trace

1. **Catalog and routing:** the coverage inventory contains 733 operational
   identities. Its configuration categories are 372 adapter-configured, 168
   adapter gaps, 47 without a linked source and 146 official-window-only.
   All 85 Odds API allowlisted identity keys resolve in this inventory and
   the season map. No unknown mapping key was found. Configuration categories
   are not counts of working sources or current fixtures.
2. **Provider collection:** the deployed Odds API bundle was generated at
   `2026-10-30T18:06:55.809700Z`. It reports `collection_halted: true`,
   `persistent_hold_requires_explicit_recovery`, zero requests this run and
   zero retained events. The persisted stop timestamp is
   `2026-10-22T23:28:23.561076Z`; the latest source observation is also October 22.
   The 85 historical source records comprise 51 `ok`, 33
   `not_active_in_directory`, and one `failed`; all are currently stale.
   Historical `ok` records and a new bundle timestamp do not establish a fresh
   source observation. The failed record is the Copa Libertadores key, but
   sanitized persisted state does not establish the original failure cause.
3. **Other source collection:** the global schedule contains 650 source
   records, including 171 explicitly permission-held records. Its NFL, NBA,
   NHL and MLB ESPN records retain October 18 checks and are paused. Their
   old events no longer supply this review window. The separate seven-source
   health probe is a website/access check, not a 733-competition fixture audit.
   Its newer October 30 check still reports five healthy of seven, ATP HTTP
   403 and ITF permission-required. These sources were not retried here.
4. **Window filtering:** the global JSON contains 2,570 event records, but
   only 355 start within October 30–November 6 in Central Time. The remaining
   2,215 fall outside that interval. All 355 in-window records have `LIVE` or
   `UPCOMING` status. The current `buildTodayModel()` produces 356 records:
   those 355 plus one stale retained F1 race. The separate basketball dataset
   has zero events and an expired October 18–25 window. No held or completed
   observation was made fresh by this analysis.
5. **Deduplication:** the current Odds API session validates but contains zero
   events, so its additive overlay removes or adds no events. Its identity,
   exact participant and timestamp matching is not the cause of this low
   provider contribution. Existing merge tests also preserve canonical
   restriction, status, age and stale fields. No fuzzy aliases were added.
6. **Presentation:** Review Today correctly anchors to the current Central
   date, rather than the feed's saved dates, and includes today plus seven
   days. The seven-day research count is not interchangeable. Stale records
   remain visible with warnings; freshness does not itself suppress them.
   However, the provider halt was buried in collapsed details, and
   `feedCollectionPaused()` did not recognize either published provider halt
   field. A successful reload could therefore understate the collector hold.

The dashboard model's counts by date are 59, 99, 57, 32, 22, 35, 15 and 37.
These are published review records, not proof of all expected sporting events.

## Actual identity coverage

Evaluated using the existing `CatalogHealthSummary.build()` with both production
F1 projections (`JolpicaF1.global` and `JolpicaF1.coverage`), the published
snapshots, and the same eight-day window as Review Today:

| Evidence state | Identities | Meaning |
| --- | ---: | --- |
| Fresh event observations | 74 | At least one fresh saved observation, still partial coverage |
| Stale event observations only | 1 | F1 retained race, observation older than 24 hours |
| Healthy source, no event observed | 95 | A working check without window events; no off-season inference |
| Configured route, current check unavailable | 23 | Failed, expired or otherwise noncurrent source |
| Reference only | 315 | Calendar/window/gap reference, without usable fixture routing |
| No usable fixture route | 225 | Includes permission-held and provider-held configurations |
| **Total** | **733** | **193 usable routes configured; 540 without a usable route** |

There are 347 fresh fixture observations, one stale fixture observation and
eight reference records. Together they explain the model's 356 displayed
records. Fifteen observations are date-only. No observed event was unassigned
after exact production source linking; no mapping key was unknown. Thirteen
shared source IDs have multiple catalog owners; they require explicit scope
and are not automatically mapping defects.

The [complete identity-level inventory](review-today-coverage-2026-10-30.csv)
names every competition, source link, held/failed source and observed-count
state. `mapped` means technical fixture routing, not catalog approval. In
particular, a held source can remain documented in configuration while not
qualifying as a usable route. Aggregate counts here are not a complete-coverage
percentage or a denominator of competitions expected to play this week.

## Competitions needing fixture work

| Competition or group | Confirmed limitation | Smallest reliable next step |
| --- | --- | --- |
| NFL, NBA, NHL, MLB | Legacy ESPN collection held; provider alternative also halted; no usable current fixture observations on these routes | Review original provider stop evidence and allowed recovery before resuming the existing collector; do not reset the cache |
| NCAA basketball | Empty retained dataset, expired window, publisher permission hold | Continue permitted school-calendar verification; obtain approved fixture access before expanding automated collection |
| ITF / ATP tennis | ITF paused; ATP access probe 403; provider generic tour mappings intentionally excluded | Keep holds and age checks; use authorized official evidence, not a generic tour substitution |
| Brazilian NBB | Adapter rejects changed fixture identity/pairing | Review current official pairing and identifiers before changing the parser |
| Women's Division I ice hockey and men's Division I water polo reviewed team subsets | Explicit October 23–25 evidence windows expired | Review a new exact team/date subset; do not extend evidence dates mechanically |
| Italian Serie A1 women / SuperLega men | Five-round horizon ended / round identity changed | Review the next official round with exact division and kickoff evidence |
| QSL Cup | Nine published pairings lack date/kickoff | Await or verify dated official fixtures; do not invent kickoff times |
| Malaysia Super League | Published round does not cover full review window | Verify the next published round before extending coverage |
| Swiss Challenge League / Swiss Cup | Current PDF link changed / HTTP 403 | Review an authorized current PDF; retain Swiss Cup access boundary |
| Copa Chile, PBA National Tour, RLCS, PLL Championship Series and many domestic soccer cups | Reference/gap records without dependable fixture adapters | Prioritize current-season competitions using the inventory; confirm publisher access and exact identity before adding an adapter |

All 23 noncurrent configured routes are named in the CSV. Other examples include
A Lyga, Azerbaijan Premier League, Besta deild, Canadian Championship, Canadian
Premier League, Copa Libertadores Femenina, Copa Uruguay, Erovnuli Liga,
Virsliga, Bosnia's Premier League, Supercopa de España, Svenska Cupen women,
Taça da Liga and UAE Pro League. Their rejection messages differ: changed
identity/round, missing timed fixtures, expired publication horizons, TLS failure
or access denial. None alone proves the competition has no fixtures.

## Focused correction and limits

The accompanying change puts a persistent provider safety hold or invalid
provider snapshot in the existing visible Review Today warning area, even when
all saved schedule windows cover the dates. The general reload status also
recognizes the two published provider halt fields. The notice does not clear
the hold, rewrite timestamps, initiate requests or alter event eligibility.

Validation: 118 tests covering staff views, division coverage, published-data
status, identity health, exact mappings, browser overlay and the synthetic
zero-quota collector passed. New regression cases cover both hold fields,
all-current date windows, reload behavior, invalid-snapshot notice and
nonmutation of collector state.

This corrects a confirmed visibility defect; it does **not** add fixtures. The
smallest likely coverage gain is recovery of the already approved collector
after original-stop review, followed by repairs to currently permitted,
high-yield adapters with expired reviewed rounds. Neither step should be
performed from a green workflow badge alone. Current snapshots cannot prove
the exact original stop reason, how many events the provider would return
after recovery, or the total expected real-world fixtures. No new publisher
access, broader endpoints, betting odds requests or weakening of catalog,
age, Nebraska, venue, phase or access safeguards is proposed.

## Snapshot fingerprints

SHA-256 of the inspected public bytes (no raw provider samples retained in Git):

| File | SHA-256 |
| --- | --- |
| global-schedule.json | `ce239f1393f900db793a5a274697485937ffca5c9cfe66391c63046faa10800c` |
| priority2-coverage-inventory.json | `572dfab4859080303eeaa1f79c59e3292b1c2297276025451cd6c2bcbd02fb8b` |
| catalog-season-map.json | `a4c3fc779c068434c2cb24ae9323b10ee8900b29cd53cda27444fb4939cbd9ee` |
| jolpica-f1-events.json | `3c34b0c51cdcf7b1b70e8649676aaa9785347c33b91551518a07d718e27f1eb8` |
| odds-api-events.json | `9d577950249dc18893ab13cf00d810de824cc40cf0d4d2e921bb689b00756034` |
