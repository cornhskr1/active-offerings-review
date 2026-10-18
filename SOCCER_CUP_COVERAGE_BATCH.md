# Official cup fixture coverage batch

## Fixed scope

This package connects two previously unmapped approved identities and repairs one existing connection. It preserves all other sports and source configurations, including the recent basketball, shared-provider, Zambia/Czech and rugby packages. No generated schedule snapshot is manually published.

| Exact approved identity | Official publication | Expected October 18–25 cards | Coverage boundary |
|---|---|---:|---|
| Croatian Cup, Men | HNS Semafor 2026/27 cup listing | 1 | Seven named unplayed round-of-16 fixtures; preliminary rounds and completed results excluded |
| Latvian Cup / Latvijas Kauss, Men | LFF men's 2026 cup, full and upcoming views cross-checked | 0 | One November 20 final, not a claim of current-week activity |
| Malaysia FA Cup, Men | MFL October 12 semifinal PDF | 2 | Four senior-club semifinal legs replace expired quarterfinal coverage; not Malaysia Cup |

These are date-only cards. Published full dates are retained literally; no kickoff timezone is inferred. The collector applies the application's America/Chicago review-day boundary without turning a date into a midnight timestamp. Every source remains partial, and fixture publication does not clear participant age, professional status, or actual sportsbook market eligibility.

Slovenia's retained official landing page contains 16 explicitly dated national-round fixtures, but the later fresh request returned HTTP 403. Its parser work is held outside this release. Captured fixtures are not being claimed as a working connection.

## Safeguards

Exact source identity, competition, edition, phase, named opponents and date consistency must pass. Contradictory or incomplete required publication structures fail closed. Held placeholders or youth/reserve/amateur indicators remain explicit. Source results are buffered atomically, so a malformed final row cannot publish preceding rows. A future fixture outside the review week can produce healthy empty weekly coverage, but an expired publication is not evidence of offseason.

## Unresolved sources, not counted as working

Qatar Cup's retained public page identifies a December final with TBD kickoff, but the fresh source request returned HTTP 403. Parser research is held outside this release and the source remains a gap. Singapore and Vietnam official routes also denied the fresh request; no alternate access route was used.

Estonia's 2026/27 cup calendar provides month-level future phases, while linked stage feeds contain completed matches or empty future stages. No exact future pairing is inferred. Malaysia Cup's official calendar places its draw in December and opening in January; this is separate from Malaysia FA Cup and remains a gap.

## Official sources

- Croatia: https://semafor.hns.family/natjecanja/114492931/supersport-hnk/
- Latvia: https://lff.lv/sacensibas/viriesi/latvijas-kauss/
- Malaysia FA Cup: https://www.malaysianfootballleague.com/Content/Post/Watch/6495

## Release acceptance

Source research and local fixture counts are not deployed coverage. Acceptance requires passing aggregate tests, independent review, exact-head CI, normal runner publication, deployment, and a live Review Today check that preserves partial-coverage warnings. Final verification is pending while this package is prepared.

Prepublication verification on October 18, 2026: all 713 regression tests pass. An isolated run of the actual collector against all three live official sources succeeds with no source errors and three current-window cards (Croatia one, Malaysia two, Latvia zero). All three sources remain partial. These local results do not establish deployed coverage; normal-run and live-screen verification still follow merge.
