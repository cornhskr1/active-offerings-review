# Temporary publisher collection holds

The owner requested a temporary pause of automated collection from ESPN, NCAA.com, ITF, USTA, FIBA and FAW while access permissions are reviewed. This operational precaution is not a finding of liability or a claim that public availability establishes reuse permission. It does not resolve the separate question of previously published data. No paid services, outreach, new credentials, data deletion or changes to catalog approval are included.

## Exact scope

The policy matches these hostnames and their subdomains: `espn.com`, `ncaa.com` (including `sdataprod.ncaa.com`), `itftennis.com`, `usta.com`, `fiba.basketball`, `fiba3x3.com`, and `faw.cymru`. It does not match lookalike substrings, independent university athletics sites, NCAA.org, ATP, WTA or UTR. An informational NCAA.com link does not pause an otherwise separate NCAA.org collection endpoint. The previously approved UEFA no-network hold remains separate and active.

## Boundaries

- The HTTP dispatch guard covers Requests sessions and urllib openers, including redirected requests and imported adapters. The global schedule collector, public-source health checker, NCAA basketball schedules/team mapping/rosters, basketball age research, football and Nebraska collegiate collectors install it.
- The global collector skips held network sources, preserves their saved events without inventing dates, marks them stale, and records explicit permission-required source failures. Shared endpoints do not duplicate another source's events; only explicit routed identities may be retained across an endpoint.
- Dedicated NCAA basketball schedule, team-map and ESPN roster refreshes preserve their snapshots and original observation timestamps. Derived basketball intelligence and age-cache outputs disclose their paused underlying observations rather than claiming a new collection.
- ESPN age research records permission-required instead of claiming the profile was researched or lacked DOB evidence. Independently permitted school-bio work remains separate.
- Tennis browser collection and the standalone source-health workflow guard held publishers. ITF lanes and USTA calendar references retain saved evidence and original check times, but are marked paused/stale rather than cleared or reverified. A blocked optional USTA check never deletes canonical ITF events or changes athlete-age evidence.

## User-visible state

A persistent notice identifies the paused publishers, says saved information may be stale, and directs staff to verify current details. Feed freshness disclosure recognizes paused metadata. Retained events carry the existing `source_stale` flag, so event rows say “STALE SOURCE — VERIFY.” Source errors remain visible; loading a published file successfully is not fresh source clearance. Catalog and manual tools remain available. College events intentionally excluded from Review Today stay excluded.

The owner instructed that the already-running refresh may finish. This change applies to collectors using the merged code; it does not retroactively change a job that checked out earlier code. Verify the next normal refresh and deployment before claiming its statuses are published. This package does not remove saved public records or publish site legal terms.

## Browser verification and compatibility

Browser routing disables automatic HTTP redirects, checks each destination, and follows only bounded permitted GET/HEAD hops. Other redirect methods fail closed. There is no unguarded continuation fallback. A synthetic Chromium test uses only a local test server and verifies both direct and redirected held targets receive zero requests; CI requires this test rather than accepting a local environment skip.

Manually fulfilled allowed redirects retain the original browser document URL. Relative-link resolution can therefore degrade on publishers that redirect across paths or hosts; existing exact-scope and completeness checks still apply. A failed unrelated source must remain a visible failure, not be reported as recovered. This safety change is not a claim of perfect compatibility with every unheld publisher.
