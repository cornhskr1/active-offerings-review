# USTA calendar provenance without duplicate tournaments

## What this changes

Seven existing ITF tournament records can carry an additional, exact USTA Pro
Circuit calendar reference. No fixture is added, copied or reassigned. The ITF
source, catalog identity, dates, participant review, U18 warnings and restrictions
remain unchanged. USTA men's and women's identities remain separate and retain
`ADAPTER_GAP`: a bounded set of shared references is not full circuit coverage.

The reviewed official 2026 men's and women's PDFs are both dated August 26.
USTA's columns establish division, grade, city, surface and week-start only.
The existing ITF snapshot supplies tournament edition URLs and end dates; the
USTA calendar must never be cited as evidence for those end dates.

## Reviewed overlaps

- Men, October 12 week: M15 Lexington and M25 Austin.
- Women, October 12 week: W100 Edmond and W35 Redding.
- Men, October 19 week: M15 Ithaca.
- Women, October 19 week: W35 Bakersfield and W50 Austin.

All seven already appeared exactly once in both the tennis and global schedule
at the reviewed October 18 snapshot. The new reference count is not a new-fixture
count. Fort Worth ATP 75 is present on USTA's October 19 calendar but absent from
the canonical Challenger feed, so this package expressly does not close USTA's
coverage gap.

## Fail-closed safeguards

Every refresh checks the exact reviewed PDF bytes and reconciles a fresh canonical
ITF record by its exact edition URL, division, tour, grade/name and original date
range. A live tournament's displayed review date is not its original start date.
A changed PDF, denied request, stale/degraded ITF lane, duplicate identity, date
mismatch or missing tournament yields no new reference and an explicit diagnostic.
Canonical ITF cards survive an optional provenance failure unchanged.

References expire with their verified date ranges and are rebuilt rather than
accumulated. They do not verify a participant field, establish adult-only status,
approve a market or clear an existing restriction. In particular, the W50 Austin
pre-draw U18 warning remains intact.

The current canonical snapshot reports healthy ITF men's/women's lanes. Two
upcoming women's individual fact-sheet pages were not independently readable
in this research pass. Their existing canonical records are only cross-referenced
against USTA's week/grade/city evidence, not recertified as fresh fact-sheet reads.

## Official sources

- https://www.usta.com/content/dam/usta/pro-circuit/2026/2026-mens-pro-circuit-calendar.pdf
- https://www.usta.com/content/dam/usta/pro-circuit/2026/2026-womens-pro-circuit-calendar.pdf

Exact PDF hashes, reviewed rows and ITF edition URLs are recorded in
`data/usta-reviewed-references.json`. Source and coverage inventory outputs carry
separate `crosslisted_reference_count` and canonical event IDs; ordinary event
counts and adapter coverage totals are unaffected.

## Verification before publication

The scoped normal collector retrieved both current PDFs successfully and attached
seven references (three men, four women). All 57 canonical ITF cards, IDs and
original fields compare exactly equal to the prior published snapshot after
removing only the new reference metadata. The two USTA sources still report zero
owned events and retain their coverage-gap classifications. Independent review
confirmed these invariants. Normal post-merge refresh and deployment must still
be verified separately; this paragraph records local acceptance evidence only.
