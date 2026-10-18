# UEFA domestic provider family: bounded schedule coverage

## Scope and operational result

One shared parser and public provider contract covers seven reviewed catalog identities across seven countries. This is not seven country adapters and does not promote all fifteen researched identities to working coverage. NCAA presentation/hidden sports, existing providers, catalog approvals, restrictions and athlete-age treatment are unchanged.

Live credential-free checks on October 18, 2026:

| Exact identity | Provider ID / season | Enabled subset | October 18–25 | Later verified |
|---|---|---|---:|---:|
| Armenian Premier League, men | 1079 / 2027 | 12 reviewed first-team identities | 5 | Not a complete future count |
| Bulgarian First Professional League, men | 1029 / 2027 | 14 reviewed first-team identities | 3 | Not a complete future count |
| Kosovo Superleague, men | 1088 / 2027 | 10 reviewed first-team identities | 2 | Not established |
| Georgian Cup, men | 5081 / 2026 | 2 exact semifinals | 0 | 2, October 27–28 |
| Norwegian Cup, men | 5045 / 2027 | 3 exact third-round ties | 0 | 3, October 28 |
| Polish Cup, men | 5046 / 2027 | 2 exact round-of-32 ties | 0 | 2, October 27 |
| Cupa României, men | 5049 / 2027 | 4 exact group-round-2 ties | 0 | 4, October 27–29 |

Thus ten current-week fixtures are live verified, plus eleven explicitly reviewed future-only cup fixtures. Normal refresh queries only its Chicago review window, so those eleven are not falsely published as current-week events. All seven sources remain partial with explicit `coverage_complete=false` and `review_window_complete=false` even when an HTTP request succeeds or returns no rows.

The eight other researched cup identities remain coverage gaps: Armenia, Azerbaijan, Bosnia-Herzegovina, Bulgaria, Estonia, Kosovo, Serbia and Slovakia. The review registry records them but the collector does not enable them. Armenia lacks adequate independently accessible phase proof (fresh FFA/Pyunik responses were HTTP 403, with no bypass); Azerbaijan/Bosnia/Serbia have midnight placeholders; Estonia's observed tie involves a reserve team; Bulgaria/Slovakia's observed ties lack two reviewed current top-flight clubs; Kosovo had no future rows. These are not declarations that the competitions have no actual fixtures.

## Public provider contract and discovery evidence

UEFA's official pages supply current competition IDs and structured match-unit records:

- https://www.uefa.com/nationalassociations/arm/domestic/league/1079/
- https://www.uefa.com/nationalassociations/bul/domestic/league/1029/
- https://www.uefa.com/nationalassociations/kos/domestic/league/1088/

Their public frontend declares `window.domesticApiUrl = https://domestic.uefa.com/`. The published `7n.15eba028.js` chunk specifies `v2/matches` and its filter/pagination parameters; `k1e.f3dbb3d0.js` specifies `v2/competitions`; `ty.071a0e6e.js` passes adult/country filters. No bundled key is extracted or used. Requests succeeded without credentials, custom headers, authentication or browser sessions.

- Directory GET: https://domestic.uefa.com/v2/competitions?age=ADULT&countryCode=ARM&limit=10&offset=0
- Match GET: https://domestic.uefa.com/v2/matches?competitionId=1079&seasonYear=2027&fromDate=2026-10-18&toDate=2026-10-26&limit=100&offset=0

UTC query bounds cover the entire Chicago review interval, including its last evening and DST. Returned records are filtered by actual future instants and Chicago dates. Pagination continues until a short page, rejects duplicate/repeated/oversized pages and fails atomically at the explicit ten-page safety bound. A short page establishes only successful bounded retrieval, never full fixture coverage. HTTP errors or malformed later pages cannot publish earlier-page events. Access denials, redirects and rate limits stop subsequent provider requests for that run; there are no alternate hosts/keys, retries or denial workarounds.

## Independent cup phase and participant proof

The UEFA payload does not include cup phase. Exact fixture-ID/home-ID/away-ID/date allowlists therefore carry separately reviewed phase proof. New matches, opponents, dates or phases require review rather than inference. Current top-flight first-team membership provides the bounded professional-club subset basis; it does not prove every athlete's professional status or age and does not establish wagering/market eligibility.

- Georgia: https://cup.gff.ge/game/1909-gag-rus and https://cup.gff.ge/game/1910-dbt-dil establish 2026 semifinals, pairings and October 27–28 dates. Reviewed pairs: Gagra–FC Rustavi and Dinamo Batumi–Dila.
- Norway: https://www.fotball.no/cupen/ labels Cupen 2027 third round and October 28 pairings. Reviewed pairs: Sarpsborg–Vålerenga, Rosenborg–HamKam and Kristiansund–Aalesund. The cup edition is 2027 while the corroborating current league edition is 2026; those are not conflated.
- Poland: https://pzpn.pl/public/system/files/articles/13659/7297-Terminarz%20rozgrywek%20%20-%20sezon%202026%20-%202027%20B1L%2BPP.pdf identifies October 27–29 as 1/16 PP, which means round of 32. https://piast.gliwice.pl/2026/09/17/piast-zagra-z-gornikiem-w-1-16-finalu-pucharu-polski/ corroborates the phase. Reviewed pairs: Piast–Górnik Zabrze and Motor Lublin–Raków. Lechia–Jagiellonia is not included: Lechia was not in the verified current top-flight set.
- Romania: https://www.frf.ro/competitii/competitii-masculin/s-au-tras-la-sorti-grupele-cupei-romaniei-betano-editia-2026-2027/ names group-round-2 pairings. Reviewed pairs: Voluntari–Univ. Craiova, CFR Cluj–U. Cluj, SC Corvinul 1921 Hunedoara–Rapid Bucureşti and UTA–Botoşani. UEFA supplies actual October 27–29 UTC kickoffs rather than a fabricated common nominal date.

`data/uefa-reviewed-scopes.json` retains exact source IDs, provider IDs, team allowlists, match IDs, dates, phases, evidence URLs and membership-witness match IDs. Regression fixtures retain only relevant public schedule metadata, not player/scorer profiles. The aggregate discovery of 100 cup rows is not an eligibility count: only eleven were adopted; 44 midnight rows and all other unreviewed participants/phases stay excluded.

## Validation and integration

Tests cover source/catalog identity, current edition, directory consistency, country/sex/sport/type/tier, stable opponent IDs/names, scored/non-upcoming status, midnight/naive/conflicting dates, future instants, changed cup IDs/dates, first-tier membership witnesses, unknown/reserve opponents, duplicate conflicts, empty partial responses, pagination bounds, denial/rate-limit stops and atomic rollback of both event rows and deduplication keys. The normal refresh push triggers include adapter and review-registry edits while preserving `queue: max` and `cancel-in-progress: false`.

No generated global schedule or coverage totals are manually replaced. Normal publication must regenerate schedule, registry, inventory and acceptance together. A configured source is not complete coverage, age clearance or authority to offer a wager.

Fresh pagination verification: Armenian season2027 queries with limit100 returned100 IDs at offset0 and98 at offset100, with zero overlap and198 total, matching the official page record count. ID-only captures and the published query-contract chunk are retained in regression fixtures. Aggregate validation after the final test addition is recorded at handoff.

Final local verification: `PYTHONPATH=/tmp/active-women-deps python -m unittest discover -s tests -q` passed all 883 tests on October 18, 2026. `git diff --check` passed. Live focused collection verified ten current-week league fixtures and eleven future-only reviewed cup fixtures. No external publication performed.
