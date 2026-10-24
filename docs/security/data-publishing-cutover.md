# Active Offerings: controlled data publishing cutover

Status: **DESIGN ONLY — NOT AUTHORIZED FOR PRODUCTION CUTOVER**

## Security objective

A compromised scheduled provider-collection job must not be able to modify the application
code, workflows, or GitHub Pages deployment definition. Today's direct-to-`main`
`GITHUB_TOKEN` with `contents: write` cannot enforce this: staged-file guards are helpful
against mistakes but can be bypassed by malicious code running in the same job.

## Current contracts to preserve

- App source, static assets, source scripts, approved catalog mappings and workflows
  are maintained in `cornhskr1/active-offerings-review`.
- Deployment currently checks out `main` and stages `index.html`, `_headers`,
  `assets/`, and `data/` using `scripts/stage_odds_pages.py`. Some generated
  outputs are checked into `main`; odds observation JSON is injected during the
  Pages job and uses carefully constrained prior-public-cache recovery.
- Numerous schedule and manual workflows write specific files directly to `main`.
  Some produce overlapping outputs (notably the competition identity registry);
  some create an intermediate PDF and then JSON; some trigger each other.
- A deploy triggered on workflow completion must not publish stale/unverified data.
- Pages safety checks pin the entire deployment workflow Git blob; every
  modification requires reviewing and updating the audited fingerprint and
  running the offline regression suite.

## Proposed security boundary

1. **App repository (this repository):** app code, reviewable configuration,
   workflow definitions and deployment logic only. Protect `main` with required
   checks and PR review after data writers are migrated. All provider collectors
   in this repository are read-only with respect to this repository.
2. **Data repository (new, dedicated):** versioned generated, public-safe
   `data/` outputs only. *No deploy secrets, production workflows, app source,
   or privileged cross-repository credentials.* Data publishers get write access
   exclusively to this repository, not the app repository. Its branch protections
   and publish policy must account for automated updates.
3. **Pages deploy:** keep deploying from the protected app repo with read-only
   app access and Pages/OIDC permissions. Download a specifically identified data
   revision through a read-only channel, validate against a **positive manifest**
   of paths, content types, sizes, and schema contracts, then stage only approved
   public files. Fail closed on missing, malformed, stale, partial, or unexpected
   output. Never execute code from the data revision.
4. **Credentials:** prefer `GITHUB_TOKEN` scoped to the *data repository* when
   collectors run there. If cross-repo transport becomes necessary, use a
   GitHub App installation token with the narrowest repository and permission
   scope, not a personal access token shared with the app workflow. Separate
   deployment secrets from untrusted data processing. Do not print tokens or
   provider payloads in CI logs.
5. **Trigger:** after successful validated data publication, dispatch/request
   a deployment through a narrowly scoped trusted integration, or poll the latest
   validated data revision on the existing Pages cadence. Do not grant collector
   jobs write access to app workflows or trigger via untrusted PR code. Pin the
   data commit SHA that the deployment validates and publishes.

## Migration order (no flag-day cutover)

### Phase A — inventory and contracts (read only)
- Enumerate every `contents: write` workflow, its exact output paths and run
  triggers, all other consumers, and overlaps/conflicts.
- Identify files referenced by the dashboard and by downstream portal reference
  syncs. A file absent from the new data repo must not silently disappear.
- Build manifest validation and offline synthetic fixtures; malicious filename,
  traversal, symlink, oversized file, malformed JSON/PDF, partial publish and
  unexpected keys must be rejected.
- Keep the current production path unchanged.

### Phase B — shadow data publication
- Create the dedicated data repository with no sensitive material and
  publication restrictions; migrate one low-risk collector first.
- Compare generated **hashes and schema/semantic results** with the present
  repository artifacts using synthetic and known-good fixtures.
- Keep Pages reading `main`; shadow publishes do not affect users or consume
  additional provider quota solely for testing.
- Expand shadow publication only after audit of dependent scripts and workflow
  triggers.

### Phase C — controlled deploy integration
- Add a staged data-revision fetch and manifest gate to Pages behind an
  explicit opt-in flag, defaulting to the established path.
- Verify full CI, a synthetic hostile-data suite, a zero-quota deployment
  dry run, and a normal live refresh without duplicate provider calls.
- Confirm rollback can select the last known-good validated data revision.
- Because the Pages workflow blob changes, review the concurrency contract and
  update its audited fingerprint in the *same tested PR*.

### Phase D — cutover and protection
- Switch Pages to the validated data revision and observe normal refresh
  schedules for each source family; record exact run IDs and output evidence.
- Remove direct-to-main data commits from all collector workflows; then make
  their app-repo tokens read-only or move them out of the app repository.
- **Only then** activate app `main` branch protection/rulesets with required
  checks/reviews, without granting a broad refresh bypass. Verify attempts
  from the data publisher cannot modify app workflows or source files.
- Monitor and document rollback; retain previous working release until proven.

## Acceptance tests

- [ ] A scheduled collector cannot push or open executable workflow changes
      to the app's protected `main`, even when its runtime is compromised.
- [ ] App deployment cannot execute data-repository content as code.
- [ ] Only positively enumerated, schema-valid public data files appear.
- [ ] No provider API quota is spent by security-only test runs.
- [ ] Required portal reference syncs and staff dashboard links work.
- [ ] Missing/invalid/older/partial data fails closed, retaining the last
      known-good publication rather than publishing an empty snapshot.
- [ ] Deploy concurrency and prior-failure protections still pass.
- [ ] Regular refresh and Pages deployment complete at least once for each
      changed collector group after cutover.
- [ ] Rollback path is rehearsed without weakening app-repo protections.

## Explicit non-goals

- No claim that pinning Python versions or checking staged files isolates a
  compromised job holding repo-wide write permission.
- No automatic migration of any nonpublic operator, patron, or agency data.
- No change to Cloudflare Access or private wagering portal hosting.
- No immediate branch-protection toggle while automation still pushes to main.

## Decision / prerequisite

This connector can read and update existing repositories, but does not expose
a repository-creation or branch-ruleset configuration action. The owner must
create/authorize the dedicated data repository and configure protection.
Until then, *do not claim the permission-isolation objective is met*.
