# Women's soccer: verified next published rounds

## Scope

This package extends the existing FIGC Serie A Women source and connects the exact
DFB-Pokal Frauen round-of-16 source. It does not create new catalog approvals,
combine men's and women's competitions, or treat a configured adapter as complete
operational coverage.

- **FIGC Serie A Women:** the September 28 official announcement contains 18
  fixtures across rounds 4–6, October 24–November 8, 2026. The prior rounds 2–3
  parser remains supported for regression checks. Each announcement is selected
  explicitly by its reviewed URL; six games and all twelve exact clubs must
  reconcile in every round. Europe/Rome conversion preserves the October 25
  daylight-saving transition and the Monday, November 2 fixture.
- **DFB-Pokal Frauen:** the October 5 official announcement contains all eight
  named round-of-16 fixtures, October 30–November 2, 2026. The printed clocks have
  no independently verified timezone, so cards retain literal dates and printed
  clock evidence without inventing timestamps. All eight pairings and sixteen
  clubs must reconcile before any records are returned.

Both sources remain **partial**. Later rounds, participant ages, professional
status and actual market eligibility remain separate review work. A healthy
source with no fixtures in the review week is not evidence of offseason or an
all-clear. Expired or malformed publications fail visibly.

## Official sources

- FIGC: https://www.figc.it/it/serie-a-women/news/date-e-orari-dalla-4-alla-6-giornata-juventus-roma-sabato-24-ottobre-alle-1830-il-derby-di-milano-sabato-7-novembre-alle-15-iefuxgby
- DFB: https://www.dfb.de/news/pokalachtelfinale-zeitgenau-angesetzt-topspiel-bayern-gegen-leverkusen-live-bei-sky-und-im-ard-livestream

## Preserved holds

Italy's women's Coppa Italia and Supercoppa still have only round/event windows,
not verified individual match dates. England's legacy Championship identity must
not duplicate the existing WSL2 fixture stream. Neither is promoted by this batch.

## Acceptance

For the October 18–25 review window, the expected scoped collection is six FIGC
fixtures and zero DFB fixtures. DFB still has eight verified future fixtures.
The scoped normal collector verified both sources healthy and exactly these counts on October 18 at 17:24 UTC. This is prepublication evidence, not a claim of deployed data. The normal refresh
workflow must publish source health and counts after merge; deployment and a
fresh dashboard check must then be verified separately.

The collector buffers each source atomically: a malformed later record cannot
leave earlier rows published as if collection had succeeded. Tests cover exact
scope, complete rounds, duplicate/missing clubs, date/time boundaries, stale
horizons, literal-date handling, and collector rollback.
