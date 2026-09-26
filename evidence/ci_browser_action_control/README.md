# A browser download becomes a pull-request check

The browser-generated **Dispatch handover** scenario rehearses a synthetic
`consignments.loading_bay` → `dispatch_bay` migration. Its unsafe baseline loses
the incoming `DOCK-07` write; the generated bridge passes 124/124 bounded probes.

The kit now contains a pinned workflow and three consumer inputs: contract,
adapters, and migration SQL. [Download the checked live kit](cutover-dispatch-action-kit.zip)
and inspect its README for the four files to copy. A Cutover engine checkout,
package installation, API key, or case manifest is not required in a consumer
repository. Inspect the synthetic contract and SQL before using them.

In [controlled PR #12](https://github.com/josepha-mayo/cutover/pull/12), those four
files were copied without editing the workflow. The public Render download was
then checked byte-for-byte against the same files; [live-download.json](live-download.json)
records the ZIP and file hashes. The two downloaded GitHub artifacts were
independently replayed against their exact run checkouts.

| Change | Outcome | Public GitHub run | Retained summary |
| --- | --- | --- | --- |
| Downloaded compatibility bridge | verified_pass · 124/124 | [safe run](https://github.com/josepha-mayo/cutover/actions/runs/36212493247) | [safe summary](safe/summary.md) |
| Remove only the old-write bridge from the SQL file | verified_block · 80/116 | [regression run](https://github.com/josepha-mayo/cutover/actions/runs/36212735493) | [blocked summary](blocked/summary.md) |

The regression's file-linked annotation names row 1: **expected `DOCK-07`,
observed `A-01`**. Its workflow, adapters and contract stayed identical; only
five SQL lines were removed. The deliberate regression was not merged.

The [safe receipt](safe-verified.json) and [blocked receipt](blocked-verified.json)
bind each report to the Action ref, PR head, actual merge checkout, and SQL hash.
Both directories preserve the downloaded report, Markdown review, replay ZIP,
summary, verdict, effective plan and Action provenance. [manifest.json](manifest.json)
records their exact SHA-256 hashes. The [Action's separate six-job control](../ci_portable_action_control/README.md)
covers passing, blocked and missing-input cases on Ubuntu and Windows.

This is a controlled workflow in the Cutover project, not third-party adoption.
The scenario builder, download kit and reusable packaging are Codex extensions
after Bob's original gate. A pass covers these synthetic SQLite schedules and
does not approve a production deployment.
