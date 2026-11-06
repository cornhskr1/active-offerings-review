# Catalog-wide verification continuation — November 6, 2026

## Reconciliation and checkpoint

Base: main `b1aabd1c9533e69dfc266a577dc758443c0e6b73` (approved PR #400). Its Pages deployment run `42208084141` completed successfully. That deployment does not include this proposal.

All **735** displayed competition identities, including split children, reconcile to the season map and identity registry. The starting ledger covered **157**, leaving **578 without a research-ledger disposition**. This is different from the 416 identities with undetermined timing in the saved-source presentation model: some existing dated calendars had never been entered into the research ledger.

This batch adds **11 reviews**, bringing the proposed ledger to **168/735 (22.9%)**, with **567 still unreviewed**. Existing evidence was checked before reconciling previously dated entries; absence from the ledger was not treated as proof that dates were unavailable.

| Reviewed-ledger status | Before | Proposed |
| --- | ---: | ---: |
| Verified complete | 65 | 73 |
| Awaiting published dates | 52 | 54 |
| Manual verification needed | 9 | 9 |
| Source access held | 24 | 24 |
| Scope conflict | 5 | 6 |
| Not scheduled | 2 | 2 |
| Total reviewed | 157 | 168 |

## Newly resolved calendars

| Catalog identity / edition | Opening | Closing | Evidence |
| --- | --- | --- | --- |
| Turkish Super Cup, men, **2026 edition played in January 2027** | 2027-01-04 | 2027-01-09 | [TFF, September 30](https://www.tff.org/Default.aspx?ftxtId=51493&pageId=200): two semifinal days and the final. |
| UAE Super Cup, men, 2026/27 | 2026-11-29 | 2026-11-29 | [UAE Pro League, October 20](https://uaeproleague.ae/en/news-and-gallery/uae-pro-league-announces-date-for-emaar-super-cup-between-al-ain-and-shabab-al-ahli-1): the single senior EMAAR Super Cup match. |

Only these two missing-date season holds are removed. No publisher or wagering restriction is removed. They change the saved-source timing projection from **319 dated / 416 undetermined** to **321 dated / 414 undetermined**: 143 in season, 51 upcoming and 127 out of season. These are offline proposed-data counts, not a claim about the deployed website.

## Existing calendars reconciled into the ledger

| Competition | Edition | Verified window | Endpoint |
| --- | --- | --- | --- |
| NBL Ignite Cup | NBL27 / 2026/27 | 2026-09-30–2027-02-21 | Scheduled cup final; separate from the NBL championship series |
| Canadian Elite Basketball League | 2026 | 2026-05-09–2026-08-15 | Actual single championship game after revised finals format |
| USL Cup | 2026 | 2026-04-25–2026-10-04 | Actual cup final |
| USL Super League / Gainbridge Super League, women | Fall 2026 transition season | 2026-08-15–2026-12-12 | Scheduled final for the standalone transition season |
| FIFA World Cup, men | 2026 finals | 2026-06-11–2026-07-19 | Completed tournament |
| FIFA World Cup, women | Brazil 2027 finals | 2027-06-24–2027-07-25 | Scheduled tournament final |

The ledger records official URLs, publication dates where established, exact editions and endpoint types. The USL fall transition is a complete championship, not an incomplete portion of an August-May season. Its 2027 calendar remains separate. USL's indexed format guide was readable in search, but direct retrieval returned 403; no bypass was attempted. The finalist club's October 4 report independently confirms the cup final. FIGC's readable Council announcement corroborates the women's World Cup calendar when the existing FIFA article exposes no readable text.

## Unresolved findings

- **FIFA Club World Cup, women — scope conflict.** [FIFA's October 22 publication](https://inside.fifa.com/organisation/fifa-council/media-releases/bureau-council-elevate-womens-football-competitions-stakeholders) distinguishes two competitions. The saved source attached to this catalog child instead follows the Champions Cup. Both calendars are recorded separately in the ledger, with neither applied to the catalog. A season-scope hold is added; the saved source assignment and ESPN publisher hold are preserved. Confirm the intended approved competition before assigning dates or changing the source.
- **Thai FA Cup, 2026/27 — partial.** FAT's revised qualifying announcement gives September 22–23, but no final was established. An earlier application notice also listed September 8–9; the later qualifying announcement takes precedence. A third-party May 2027 date expressly based on an annual pattern was excluded.
- **Thai League Cup / Muangthai Cup, 2026/27 — partial.** FAT gives September 5–6 qualifying and later round-of-32 dates, but no final. Neither Thai record is promoted to a complete window. Their recorded starts describe published qualifying windows; verify individual opening fixtures if actual-match dates are needed. Lower-tier and age checks remain separate.

The previously documented NBL, BBL, LBA and other missing endpoints are unchanged. This continuation prioritizes identities absent from the ledger rather than repeatedly counting the same unresolved reviews.

## Validation and continuation

The full existing suite initially found two assertions requiring the now-obsolete Turkey/UAE date holds. Those assertions were updated to verify the officially dated editions while retaining fixture-adapter-gap checks. No application logic changes are proposed. The historical October coverage inventory and saved event observations are not regenerated by this season review.

Validation results are recorded in the draft PR. All 168 ledger identities resolve in the map, complete/incomplete designations agree, and the projected 735 identity keys, labels, source assignments and wagering restrictions are unchanged. The only timing classifications changed are the two newly resolved Super Cups. JSON parsing and diff whitespace checks pass.

The recurring verification task is resumed to work through successive batches and durable review-branch checkpoints. Future runs should inspect this branch/PR and latest main, then continue with the remaining 567 identities. Do not call unreviewed placeholders complete reviews. Present changes and tests before requesting merge or deployment approval; keep researching independent records while a batch awaits review.
