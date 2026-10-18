# Soccer fixture connection batch

## Scope and acceptance

This batch connects two exact approved catalog identities using accessible official publisher sources: Zambia Super League (Men) and Czech Cup (Men). It does not alter approval scope or convert participant/age uncertainty into clearance. Existing Basketball and shared-provider improvements are preserved.

The starting inventory has 143 explicit Soccer adapter gaps and 26 calendar-only identities. Those are not one missing master feed: they span separate governing bodies, league publishers, editions and competition phases. A configured connection, a healthy source, a current fixture and complete season coverage remain different claims.

Acceptance for each new connection requires an ordinary unauthenticated source response; exact competition/edition checks; named opponents and explicit dates; no invented kickoff or timezone; failure/placeholder handling; a successful normal-run publication; and visible Review Today coverage limitations. No fixtures in the current review dates must not become an offseason inference.

## Verified source opportunities

- Czech Cup: the official MOL Cup results/fixtures page publishes eight named upcoming fixtures from October 27 through November 11, 2026. These are one delayed third-round fixture and seven round-of-16 fixtures, not a complete future bracket. Publisher timezone evidence has not been established, so dates must remain date-only rather than inventing UTC kickoffs. There are no published fixtures in the October 18–25 review window.
- Zambia Super League: the official league publisher exposes public calendar feeds with explicit UTC timestamps and competition identifiers. The 2026 transitional streams must remain inside the exact senior league scope, without importing cup, reserve or women's fixtures. Current-window results require normal publication verification before being called live.

## Families that remain unresolved

- Sweden: official Damallsvenskan, Superettan and Svenska Cupen fixture destinations denied unattended retrieval. Separately published league articles provide manual reference information but do not establish a reliable unattended feed. Cup phase dates alone are not named fixtures.
- Portugal women's competitions: Liga BPI, Taça de Portugal Feminina and Taça da Liga Feminina remain gaps. Current FPF schedule/results routes denied unattended retrieval; a competition-format PDF and isolated club match notice do not establish league-wide fixture coverage.
- South Africa: the MTN8 final is already completed; the latest official Carling Knockout launch says fixture dates will be announced. No future fixture is inferred from those facts.
- Montenegro Cup: the current official page lists completed October first-round games and dated November quarterfinal placeholders without opponents. The placeholders are not fixtures.
- Qatar Cup: the official page identifies the December final but still marks kickoff TBD. This research did not convert it to a timed fixture.
- France Seconde Ligue: the current official revised calendar is a graphic-only PDF. It was not converted using unverified OCR, and no unattended adapter is claimed from it.

These findings preserve explicit manual work and gaps. They are not a completion percentage, not proof that no wagering is offered, and not a reason to bypass publisher access controls.

## Source references

- Czech Cup: https://www.molcup.cz/vysledky and https://www.molcup.cz/clanek/714-terminy-mol-cupu-2026-2027
- Zambia league publisher: https://zpl.co.zm/
- Montenegro Cup: https://fscg.me/takmicenja/kup-crne-gore/
- Qatar Cup: https://www.qsl.qa/en/qatar-cup-fixtures-results
- France revised calendar notice: https://www.fff.fr/article/17085-communique-sur-la-seconde-ligue-et-la-coupe-lffp.html

Publication and normal-run evidence will determine the release result; source research alone does not establish live coverage.

## Implementation validation

The Zambia adapter inventories all 20 senior clubs across both publisher streams, reconciles both club copies of every fixture, and rejects contradictory or missing copies. The October 18 capture reconciles 180 unique fixtures from 360 league copies, excludes four cup copies, excludes 29 completed results, and holds 11 past unresolved fixtures. It retains 140 future confirmed fixtures, including 10 in the October 18–25 review window. This is one approved catalog identity, not two new leagues.

Both source configurations remain partial. Czech fixtures retain literal dates because printed clocks do not establish a timezone. The collector filters date-only dates literally and timed kickoffs in America/Chicago, buffering each source atomically so a late malformed record cannot leak preceding records. Empty current-week coverage is distinguished from a failed source and from offseason.

Adapter, collector and regression tests cover exact scope, edition changes, duplicate/conflicting records, missing dates and times, cancelled/tentative/completed matches, unresolved opponents, and atomic failures. Independent review found no merge-blocking issue. Release verification must still establish the normal runner's published snapshot and deployed Review Today behavior.

Prepublication validation on October 18, 2026: all 641 regression tests pass. An isolated run of the actual collector, using ordinary live publisher requests and the configured October 18–25 window, reports both sources healthy with no errors: Zambia publishes 10 current-window fixtures from 180 reconciled published fixtures; Czech Cup publishes zero current-window cards while retaining evidence of eight upcoming pairings. Both remain partial. This local collector result is not a claim of deployed coverage.
