# Current soccer publication recovery

Three saved source failures had distinct causes and were checked against one successful permitted request per official directory, plus exact Georgian match detail pages. Transport success alone was not treated as usable fixture coverage.

## Canadian Championship

The exact 2026 men's final (`6384`, CF Montréal / Forge, October 21, Stade Saputo) is now marked `past-match`, with an explicit original offset-bearing timestamp, numeric scores and `Full Time`. Validate that completed evidence and return no upcoming fixture. Do not require the earlier visible `19:00 EDT` label after it becomes a full-time label. Changed teams, venue, match identity, date, completed timestamp, missing scores or conflicting upcoming status still fail closed. Existing upcoming-final behavior remains.

Evidence: https://canadasoccer.com/championship/canChamp/2026/

## Spain Supercopa

Read the official five-column schedule table, including its explicit peninsular-Spain timezone label. Bind each semifinal to its exact row, date, time, named opponents and published venue rather than searching for independent strings anywhere in prose. Normalize Unicode composition only; do not infer a new alias or missing kickoff. The exact unknown final row stays excluded. The two verified February 2027 semifinals are outside the current review window and must not inflate today's count.

Evidence: https://rfef.es/es/noticias/definida-la-hoja-de-ruta-de-la-supercopa-2027-que-se-celebrara-en-estambul

## Georgian Erovnuli Liga

The calendar's November 9 game had an unpublished venue outside the review window; that rejected the entire source before October 31–November 2 games could be verified. Keep full identity/date/clock validation for every row, but require a venue only in the existing inclusive local-date candidate envelope (review dates plus one day for timezone boundaries). An unknown venue inside that envelope still fails the source. Linked details continue to verify exact teams, round, venue and UTC/local kickoff.

Evidence: https://www.erovnuliliga.ge/en/calendar

All eight candidate detail pages in the October 30–November 6 envelope were retrieved and independently matched by the existing verifier. Five fall inside the actual Central Time review window. Their IDs are 9407, 9409, 9408, 9401 and 9410. No result or missing venue was guessed.

## Qatar Stars League

Evidence: https://www.qsl.qa/en/doha-bank-stars-league-fixtures-results

The October 31 official 2026–27 Doha Bank Stars League page splits week 8 across three scored results (match numbers 43–45) and three named, timed upcoming fixtures (46–48), followed by all six named, timed week 9 fixtures (49–54). The adapter now combines only those exact result and fixture panes to validate each complete six-match senior week. It rejects partial weeks, duplicate or unknown clubs, future/non-numeric results, unexpected match-number spans and horizons beyond the last published kickoff.

## Swiss Challenge League

The SFL directory now links the October 23 revision of the exact 2026/27 dieci Challenge League PDF. That revision publishes 18 complete five-match rounds (90 pairings), replacing the September 7 document with 17 rounds. Bind collection to the unique current directory link, exact revision, senior competition title, complete round count, ten distinct eligible clubs per round, published weekday and Europe/Zurich kickoff. The adapter remains limited to the published first phase; later phases and the interdivision barrage are not inferred. The separate Swiss Cup source remains on its existing access hold.

Evidence: https://sfl.ch/de/anspielzeiten

## Malaysia Super League

The current MFL article links the October 21 revision of the exact 2026/27 Unifi Liga Super PDF. Validate all match numbers 31–66 across LS6–LS11 as six complete senior-club rounds. Two LS6 matches (31–32) were explicitly advanced to August for ACL scheduling; four fixtures remain in the October 30–November 6 review window. Later moved fixtures retain their published match numbers and dates through December 30. The parser stops at the published LS12–LS22 boundary and does not import the unreviewed second phase, Malaysia Cup, Charity Shield or lower-tier participants.

Evidence: https://www.malaysianfootballleague.com/Content/Post/Watch/6542

## Validation and release boundary

Full app suite: 1,244 tests passed, one existing skip. Focused Canada, RFEF and Georgia tests: 11 passed. New cases cover completed-date/score/status contradictions, exact table dates/times/timezone/final hold, absent table evidence and in-window versus out-of-window venue requirements. Existing catalog, age, phase, publisher-access and zero-quota safeguards are unchanged.

The Swiss Challenge League follow-up retains the same release boundary. Its focused regressions cover the unique current PDF link, revision and 18-round completeness, plus rejection of stale/competing links, incomplete schedules and youth participants. Normal scheduled publication remains the live-output authority.

Release the app before its exact trusted-code companion, using the owner's ongoing scoped approval. No normal scheduled collector or provider recovery is manually triggered. Observe normal publication before claiming live coverage gains; Canada is expected to be healthy empty and Spain out of window, not new current fixtures.
