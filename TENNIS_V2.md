# Tennis V2

Tennis V2 answers one operational question:

> Is a verified U18 athlete in an active draw or order of play for an explicitly approved tennis competition in the review window?

## Staff-facing behavior

- `Review Today` displays only verified U18 active-field exposure and exact-identity DOB reviews.
- `Coverage Control` displays source health, approved tournament coverage, active fields, and fields still pending.
- Tennis V2 alerts are delivered through `Review Today`; the temporary legacy validation tab was retired after shadow validation completed.
- Legacy tennis data and workflows remain available behind the dashboard during the rollback period and continue to appear in source-health reporting.

Acceptance lists, schedules, tournament names, and source availability never create catalog approval. `data/catalog-season-map.json` remains the approval gate.

## Refresh lanes

1. `.github/workflows/refresh-tennis-intelligence.yml` refreshes current tournaments and fields. It reuses the durable U18 registry and has its own concurrency group, so it cannot block global dashboard data.
2. `.github/workflows/refresh-tennis-registry.yml` performs the slower ranking and U18-registry maintenance weekly in the isolated tennis pipeline.
3. `.github/workflows/refresh-tennis-review.yml` rebuilds the focused feed after catalog/configuration changes without browser work.
4. `.github/workflows/deep-tennis-age-scan.yml` resolves targeted identity exceptions in a separate maintenance group.

## Fail-closed rules

- A tour must map through `data/tennis-v2-config.json` to a Tennis source ID explicitly present in `data/catalog-season-map.json`.
- A participant must be extracted from an active field. An acceptance pool is never an active field.
- RED requires an exact match to `data/tennis-u18-registry.json`.
- A targeted junior identity can produce AMBER, never RED.
- An unknown player does not create an alert without a specific U18 indicator.
- A stale tennis source retains the last known good tournament set, marks it stale, and requires manual verification instead of deleting coverage.

## Cutover and rollback

The existing tennis data files remain intact. The new staff feed is `data/tennis-review.json`; the dashboard falls back to confirmed legacy RED records only if that feed cannot load. Rollback therefore requires only removing the focused feed from `index.html` and restoring the former workflow concurrency settings.
