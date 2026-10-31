# Italian volleyball current-calendar recovery

The October 30 normal source publication rejected SuperLega men because the publisher moved its round heading from a specific row ID to a classed heading. The women’s adapter still pointed at a September bulletin covering only the first five rounds through October 28.

One permitted successful request to each configured/current official page established the replacement evidence:

- Men: https://ww2.legavolley.it/Calendario.asp?Anno=2026&IdCampionato=999&Fase=1
- Women: https://www.legavolleyfemminile.it/calendario/

The men’s repair selects exactly one direct round-heading span, then retains all existing edition, division, round order, six-match, team and kickoff guards. The women’s live-calendar adapter requires exact A1 competition text, regular-season leg/round, publisher game and club identities, explicit full date/time, current configured edition, same-publisher HTTPS match-center link, seven games and 14 distinct teams per round, and contiguous published rounds. Serie A2 rows are excluded. Unknown competition/phase, missing rounds, changed identities or missing timing rejects the whole source. The collector passes bytes so the publisher’s encoding declaration is retained. The historical five-round bulletin parser remains tested against its historical configuration.

Actual collector-branch replay of the captured responses, at the October 30–November 6 Central Time window, produced 11 men’s and eight women’s fixtures without errors. The payloads contain 66 men’s first-leg fixtures through December 20, 2026 and 147 women’s published fixtures through March 14, 2027. These figures are prepublication checks, not a guarantee of all phases, final broadcaster scheduling, age eligibility or wagering approval. Women’s future published times can be revised by the publisher. Men’s return leg and both playoffs remain outside this implementation.

The exact women’s configuration changes endpoint and season identity, so the basketball/operational pattern of matching current adapters to normal publication is preserved; old bulletin results are not evidence of the new calendar’s health. No source snapshot is hand-edited to claim recovery.

Regression tests retain the original bulletin coverage, exercise current women’s factual A1/A2 records and both legs, and reject wrong scope/edition, missing kickoff or club/link identity, duplicate games, missing fixtures/rounds and an expired horizon. Catalog, U18, Nebraska, publisher access and zero-quota checks are unchanged. No held publisher or API recovery was requested.

The owner authorized autonomous scoped review, tests, companion manifest updates, merges and deployments in this compliance work. Merge this app change before its exact data-manifest companion; observe normal publication before counting the recovered fixtures in production.
