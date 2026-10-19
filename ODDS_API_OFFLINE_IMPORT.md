# Offline event import: The Odds API

The pure adapter normalizes **event snapshots only**. The separate approved deployment collector requests only zero-quota event endpoints; neither component requests odds or reactivates held sources. Bookmakers, markets, prices, links and arbitrary raw fields are discarded. No captured provider sample belongs in the repository.

## Exact scope

`data/odds-api-catalog-mappings.json` contains 85 direct documented provider-key/catalog-identity pairs. This is a routing allowlist, not a claim that all 85 have current events or complete coverage. Conditional keys, futures, generic combat-sport feeds and generic tour mappings fail closed. The NCAA FBS key is conditional and is not included. Existing Nebraska and athlete-age checks remain authoritative; this import does not supply ages, physical venues or event phase.

The configured region is empty rather than inferred from a provider's marketing region. A US odds-request region describes bookmakers, not where an event takes place.

## Pure function boundary

`normalize_snapshots(snapshots, observed_at, mappings)` takes explicit in-memory inputs. Each snapshot has `provider_key`, its original `observed_at`, and `events`. Use the original observation timestamp, not import time, so importing an old file cannot make it fresh.

The session bundle has schema version 1, provider label `The Odds API`, an observation timestamp, normalized events, coverage notes and safe rejection records. It is not a substitute for the catalog and does not clear any restriction.

- Only exact allowlisted provider-key/catalog-identity pairs are accepted.
- UTC-aware provider kickoff times are retained; naive or malformed dates are rejected.
- Participants remain the named away and home teams.
- Event status is unknown; elapsed start time does not prove live or completed status.
- Saved observations remain snapshots; no refresh or completeness guarantee is made.
- Unknown raw fields and all bookmaker data are excluded from the output.

The browser validates normalized identity pairs again, avoids duplicating existing identity/participant/time matches, and preserves existing restriction fields. It never stores a provider key or calls a provider endpoint.

## Validation

Only synthetic provider events are committed in tests. Retained authorized samples may be replayed outside the repository for local proof. Provider access, persistent credentials, live integration and publication require separate approval.

## Automatic dashboard delivery

The deployed dashboard reads a minimal event snapshot generated during GitHub Pages staging. Page views and Reload Published Data do not call The Odds API. The optional local importer was used only for development and has been removed from the staff workflow.

The main-branch deployment uses the repository Actions secret `ODDS_API_KEY`. The key is never written to tracked files, the deployment output, or logs. Pull-request verification receives no key. The existing serialized Pages workflow runs every three hours; source cache gates prevent unrelated deployments from multiplying requests.

Only the documented zero-quota sports directory and exact allowlisted event endpoints may be requested. No odds, scores, historical data, participants, or betting links are collected. A missing or unexpected nonzero quota-cost header stops further collection. This cannot undo a provider charge already reported by the first changed-cost response. Authentication failures and quota changes persist as a halt in the next snapshot instead of silently retrying every deployment.

The current dashboard snapshot is the cache. Raw responses stay in runner memory; only bounded normalized current-window events and safe source-health metadata enter the deployment artifact. No provider data is committed to Git. On failures, last-good event observations keep their real timestamps and stale warnings. Expired observations fall out of the review window; disappearance is not asserted cancellation. The previous snapshot must be recovered before collection; a missing cache after activation fails closed rather than resetting a persistent halt. The existing Pages artifact retains its one-day retention setting; no additional provider archives are created.

The exact public directory mapping adds The Odds API labels to matching catalog entries, without changing season windows, approvals, restrictions, or existing source-health warnings. Observed event counts are distinct from documented identity matches. The eight-day Review Today window can differ from the seven-day research count.

Events merge by exact catalog identity, explicit timestamp, and two exact participant names (order-independent, case/whitespace normalized). Existing canonical two-party `Away at Home` / `A vs B` titles can supply names where old feeds lack participant arrays. No fuzzy alias is guessed. A match receives only an additional source observation; its original status, age evidence, restriction flags, and stale markers remain unchanged. Unknown phase/preseason, venue, age, and event status never become approval.

The approved school calendars and all publisher permission holds remain unchanged. The Odds API terms permit user-facing dashboard display but prohibit standalone raw-data redistribution. This application publishes only the incidental data required for its review interface, not a downloadable source-data service.

If deployment fails after a provider request, the next run is blocked before key exposure by read-only GitHub workflow-history checks. Reruns also stop by default. The owner must review the failed run before selecting the explicit resume_after_review workflow input. This prevents an old public cache from silently losing a newly observed quota/authentication halt. Missing or uncertain workflow history fails closed.
