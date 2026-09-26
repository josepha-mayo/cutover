# The reusable Action from consumer inputs

[Controlled PR #11](https://github.com/josepha-mayo/cutover/pull/11) calls
`josepha-mayo/cutover@a5bf69f6e8f94788eade58691d292941e009f8ac` through the
normal GitHub `uses:` interface. The Action is fetched separately from the
consumer inputs; the consumer supplies only a contract, adapters, and SQL.
It does not copy or install the Cutover engine. A conflicting Python module
in the consumer working directory must not replace the Action's evaluator.

The control workflow itself lives in Cutover's repository. It checks out the
fixture source into a separate subdirectory and constructs the consumer
inputs from that source. This verifies the Action boundary and runner behavior;
it is not a claim of third-party adoption.

The [six-job run](https://github.com/josepha-mayo/cutover/actions/runs/36210753957)
has two green jobs and four **intentionally red** jobs. Each final verification
step confirmed its expected classification and Action outputs.

| Runner | Safe SQL | Removed old-update trigger | Missing SQL source |
| --- | --- | --- | --- |
| Ubuntu | [116/116 verified pass](portable-safe-Linux/summary.md) | [72/108 verified block](portable-blocked-Linux/summary.md) | [Unverified](portable-missing-Linux/summary.md) |
| Windows | [116/116 verified pass](portable-safe-Windows/summary.md) | [72/108 verified block](portable-blocked-Windows/summary.md) | [Unverified](portable-missing-Windows/summary.md) |

All six artifacts were downloaded. Each of the four executed review ZIPs was
independently replayed against the exact fixture contract and assembled plan.
The two missing-file cases retained their verdicts and summaries without
inventing a report or a passing result. The blocked jobs exposed row 11:
expected `R-07`, observed `A-01`, linked to `consumer/migration.sql`.
The actual GitHub run and its annotations were inspected in a signed-out browser.

[The receipt](receipt.json) records the pinned Action ref, PR head, actual
consumer merge-checkout SHA, per-job results and artifact hashes.
[The manifest](manifest.json) hashes all mirrored payloads.
`action.json` in each folder also records source paths and the Action ref;
the verdict binds the SQL-file and adapter-file hashes. These hashes detect
changes; they are not signatures. General code checks separately passed on
[Ubuntu and Windows](https://github.com/josepha-mayo/cutover/actions/runs/36210753806).

Use the [pinned workflow example](../../docs/ACTION.md) in another repository.
The packaging and these synthetic controls are Codex work after Bob's original
review-gate task. Bob's repairs and IDE evidence remain documented in
[provenance](../../docs/PROVENANCE.md). A passing bounded SQLite suite does not
approve a deployment or establish production transaction behavior.
