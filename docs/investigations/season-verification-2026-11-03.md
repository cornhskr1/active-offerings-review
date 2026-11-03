# Season verification checkpoint — November 3, 2026

Current research continues from main, with PRs #380–#387 confirmed merged before this run. PRs #388–#396 are merged after passing required checks. This next batch reviews seven additional European league identities.

- Baseline rendered total: 284 of 735; latest confirmed live total: 310 of 735 after #394.
- #395–#396 contain seven more complete windows, bringing main to 317; this batch resolves Finland and Ireland to 319.
- Ledger grows from 69 to 157 reviewed identities in this run (88 additional reviews). Unlisted keys remain unreviewed, not impossible.
- Canonical season map and ledger contain exact keys, dates, URLs, scope and next action. No source identity, approval, age, cutoff, quota or publisher/compliance hold was relaxed.

## Publication blocker

Run 41645153517 first attempt failed during pinned snapshot restoration: `Complete private publication blocked: prior state or candidate evidence unavailable. No provider request made.` Refresh, upload and deployment were skipped. The available log does not expose the inner cause.

Its retry (job 125950505436) and successor run 41645948456 (job 125951927410) failed at deployment-history verification, before staging or provider collection. Current safety code admits only first attempts and does not automatically exempt retried runs. Do not repeat the rerun.

The existing workflow provides a new `workflow_dispatch` with `resume_after_review=true` after reviewing failed-run API usage. This GitHub connector exposes reruns but no workflow dispatch. A reviewed new dispatch must still validate the latest successful anchor, complete private candidate and original control state; it must not bypass restoration checks, reset the persistent provider halt or alter the separate data repository. If restoration fails again, inspect the candidate/anchor evidence without weakening validation.

No successful publication is claimed for #395 onward. Live verification is required after recovery.

## Newly identified manual items

| Soccer country / competition | Exact missing fact | Official source and next action |
| --- | --- | --- |
| International / women's Copa Sudamericana and women's Recopa Sudamericana | Exact intended approved women's competitions; official CONMEBOL editions were not established | [CONMEBOL](https://www.conmebol.com/): reconcile the two approval identities; do not substitute men's dates. |
| Portugal / women's Taça de Portugal and Taça da Liga | 2026/27 earliest qualifier and final for each cup | [FPF calendar](https://www.fpf.pt/DownloadDocument.ashx?id=33176): retrieve the women's calendar; access returned 403. |
| France / men's Coupe de France | Earliest actual 2026/27 regional or overseas qualifying match | [FFF calendar](https://media.fff.fr/uploads/documents/calendrier-general-26-27-vfinale-lfp-fff-comex-121225-vdef.pdf): confirm the earliest qualifier, not the federal-entry round. |
| Norway / men's Norwegian Cup | Earliest 2027-edition qualifier across all NFF districts | [NFF Oslo qualifying notice](https://www.fotball.no/kretser/oslo/konkurranse/artikler/2026/kretsvis-kvalifisering-nm-menn-senior-2027/): reconcile district qualifiers with the national calendar. |
| Ecuador / men's Copa Ecuador | Earliest 2026 qualifying match and current final date | [FEF](https://fef.ec/): retrieve official calendar or match notices; FEF returned 403 and secondary dates were not promoted. |

These are seven newly identified manual records, not a consolidated list of every unresolved identity. Existing scope/access holds remain in the ledger. Continue unreviewed soccer and basketball groups only after checking current main, open PRs and active runs.
