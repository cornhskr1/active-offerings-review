# Priority 2 source reliability register

Baseline: normal publication `2026-10-06T12:50:19.469603+00:00`, review window 2026-10-06–2026-10-13, 2,138 event cards and 21 failed non-gap source checks. This register records source failures, not distinct catalog identity totals; shared publishers are grouped below. [Normal run after #262](https://github.com/cornhskr1/active-offerings-review/actions/runs/37466144707) succeeded.

## Current batch: Gulf fixture scope

- UAE: the official homepage fixture slice is ADIB Cup, not ADNOC league. Select the exact 2026/27 ADNOC competition from the fixture directory and read its league-filter API; reject Cup/U23/Super Cup responses. October 6 live evidence: 182 records, 35 completed, 56 upcoming with published kickoffs, 91 untimed holds. Next timed league fixture October 16: zero cards in this review window. Normal runner verification remains pending after merge.
- Qatar: the current QSL Cup pane contains nine named pairings with TBD dates/kickoffs. Replace old round-number pinning with unique publisher match identity checks and an explicit unpublished-kickoff warning. Keep the source unresolved until dates and times are published.
- No linkage-count increase or full-season coverage claim.

## Verified changed-round soccer repairs

- #262 normal publication verifies Montenegro healthy with five current-window fixtures and Czech First League healthy with eight (17 publisher records across multiple rounds). Both remain partial publisher-panel feeds; date changes preserve stable fixture IDs. These two warnings are removed from the current failure register.
- Egypt and Saudi remain healthy after #248; partial team schedules do not establish full league coverage.
- Portugal's live Allianz Cup page returned no matches; the warning remains unresolved.

## Current batch: dynamic federation feeds

- AFFA: October 6 live listing discovers a September 17 appointment article containing only September 18–20 fixtures. Truncated UTF-8 metadata blocked the old parser. The correction reads the article body, pairs each team record with its own stadium kickoff, derives the year from publication, and reports past-only evidence as unavailable. No current fixture or health recovery is claimed.
- Bosnia and Herzegovina: October 6 league page exposes standings but no timed fixtures. The parser now preserves publisher home/away order and row year and checks the exact catalog term; the live source warning remains until a verified fixture payload is found.
- Both sources remain configured and partial. This batch does not increase connection counts. Verify normal runner behavior after merge.

## Remaining publisher work

### Publisher access blocked

| Publisher | Source | Published failure | Next evidence gate |
|---|---|---|---|
| www.pba.ph | `basketball-ph-governors` | 403 Client Error: Forbidden for url: https://www.pba.ph/news/familiar-faces-new-imports-coming-over-for-govern | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| lnb.com.br | `basketball-br-nbb` | 403 Client Error: Forbidden for url: https://lnb.com.br/nbb/tabela-de-jogos | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| www.pba.ph | `basketball-ph-pba` | 403 Client Error: Forbidden for url: https://www.pba.ph/schedule | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| vpf.vn | `soccer-afc-vietnam-vleague-1-men` | 403 Client Error: Forbidden for url: https://vpf.vn/mobile/ | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| www.fai.ie | `uefa-soccer-ireland-fai-cup-men` | 403 Client Error: Forbidden for url: https://www.fai.ie/latest/fixtures-confirmed-club-orange-mens-fai-cup-sem | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| rfef.es | `uefa-soccer-spain-supercopa-de-espa-a-men` | 403 Client Error: Forbidden for url: https://rfef.es/es/noticias/definida-la-hoja-de-ruta-de-la-supercopa-2027 | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| rfef.es | `uefa-soccer-spain-primera-federaci-n-femenina-women` | 403 Client Error: Forbidden for url: https://rfef.es/es/noticias/calendario-completo-primera-federacion-femeni | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| rfef.es | `uefa-soccer-spain-supercopa-de-espa-a-femenina-women` | 403 Client Error: Forbidden for url: https://rfef.es/es/noticias/repasa-las-fechas-clave-del-futbol-femenino-p | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |
| www.football.ch | `uefa-soccer-switzerland-swiss-cup-men` | 403 Client Error: Forbidden for url: https://www.football.ch/en/schweizer-cup/spiele-resultate.aspx | Verify unattended access to an official fixture/export route; retain the warning until runner verification. |

### Changed fixture, scope, or incomplete review window

| Publisher | Source | Published failure | Next evidence gate |
|---|---|---|---|
| www.laliganacional.com.ar | `basketball-ar-lnb` | Argentina LNB response crossed the requested date window | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| www.provincial.rugby | `rugby-nzr-farah-palmer-2026` | Farah Palmer Cup final publication changed | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| pflmma.com | `combat-pfl-mena` | PFL event date changed | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| www.malaysianfootballleague.com | `soccer-afc-malaysia-malaysia-fa-cup-men` | MFL published round does not cover the full review window | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| www.qsl.qa | `soccer-afc-qatar-qsl-cup-men` | QSL Cup published round has an unexpected fixture count | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| www.uaeproleague.ae | `soccer-afc-united-arab-emirates-uae-pro-league-men` | published kickoff changed: United - Hatta | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |
| www.ligaportugal.pt | `uefa-soccer-portugal-ta-a-da-liga-men` | Allianz Cup competition page identity changed | Recheck current competition/phase, fixture dates and names; support changes without inventing or silently dropping evidence. |

### Discovery or parsing unavailable

| Publisher | Source | Published failure | Next evidence gate |
|---|---|---|---|
| Tennis intelligence | `tennis-atp-challenger` | ATP Challenger official calendar dates unresolved; manual verification required | Resolve official tournament date discovery; pass the tennis quality gate before publication. |
| www.affa.az | `uefa-soccer-azerbaijan-azerbaijan-premier-league-apl-men` | AFFA latest appointment publication contains only past fixtures | Discover current appointments; exact current fixture parsing and normal-run proof. |
| www.nfsbih.ba | `uefa-soccer-bosnia-and-herzegovina-premier-league-of-bosnia-and-herzegovina-men` | BiH Wwin League page contained no timed fixtures | Locate official timed league payload; exact row scope, opponents, year and timezone. |

### Connection or certificate failure

| Publisher | Source | Published failure | Next evidence gate |
|---|---|---|---|
| www1.canpl.ca | `concacaf-soccer-canada-canadian-premier-league-men` | HTTPSConnectionPool(host='www1.canpl.ca', port=443): Max retries exceeded with url: /watch (Caused by SSLError | Verify the official current endpoint and certificate/connection; keep TLS validation enabled. |
| www.lff.lt | `uefa-soccer-lithuania-a-lyga-men` | HTTPSConnectionPool(host='www.lff.lt', port=443): Max retries exceeded with url: /varzybos/23198513/ (Caused b | Verify the official current endpoint and certificate/connection; keep TLS validation enabled. |

## Batch order and completion gate

1. Complete current federation-discovery corrections and verify their warnings on a normal run.
2. Finish Gulf scope repair and normal runner verification; retain Qatar and Portugal evidence holds. Czech/Montenegro are verified partial repairs.
3. Review rugby finals, Argentina basketball, PFL date changes and Malaysia round-window gaps with their exact official fixture evidence.
4. Review access and connection failures by shared publisher (PBA, RFEF, LNB, then remaining federation hosts); a successful retry is not full coverage.
5. Resolve ATP Challenger through its separate tennis workflow and quality gate.

For each repaired family record scoped fixtures, holds, focused results, normal publication, inventory health and next review trigger. A source with no current timed fixture evidence stays unresolved. Priority 2 remains in progress.
