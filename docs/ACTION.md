# Review a migration in your own repository

The reusable Cutover Action runs the same CLI and independent audit as the
project's PR gate. Your repository supplies only a bounded SQLite contract,
new-worker adapters, and migration SQL. You do not need to copy the engine,
install packages, configure an API key, or use Cutover's `ci/cases.json`.

Check in those inputs and add a workflow:

```yaml
name: Migration handover
on: pull_request
permissions:
  contents: read
jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: josepha-mayo/cutover@a5bf69f6e8f94788eade58691d292941e009f8ac
        with:
          contract: ci/release-contract.json
          plan: ci/release-adapters.json
          migration-file: migrations/add-destination.sql
          artifact-name: cutover-release-review
```

Pin the Action to the full commit you reviewed. The Action's own setup and
artifact-upload dependencies are pinned too. It runs from its own checkout,
so a same-named Python package in your application cannot accidentally replace
the Cutover evaluator.

`contract` and `plan` are required paths relative to your checkout. The
optional `migration-file` supplies the authoritative SQL; omit the plan's
embedded `migration` field when that file is your source of truth. Without
`migration-file`, the plan must contain migration SQL. Use the
[Warehouse contract](../examples/warehouse/contract.json) and
[saved plan](../ci/candidate.json) as format examples, or download a custom
scenario's PR gate kit from the browser and copy its two `ci/` inputs into
your repository.

Each review retains an artifact, including on verified blocks or input errors:
`verdict.json` and `summary.md`, plus the report, Markdown review and replay ZIP
when execution produced them. A separate SQL file also produces
`effective-plan.json`; `action.json` records the Action ref and consumer
checkout SHA. The SQL-file SHA-256 is retained in the verdict. A blocked
result shows its differing row value in the job summary and a file-linked
annotation.

The Action fails the step for either `verified_block` or `unverified`.
`verified_pass` requires both the rehearsal and independent audit to pass.
The `classification`, `coverage`, and `evidence-path` outputs are available
for subsequent workflow steps. For multiple reviews in one job, choose
distinct `output-dir` and `artifact-name` values. A nonempty output directory
is rejected and preserved; it is not uploaded as fresh evidence.

These are bounded synthetic SQLite schedules, not production transaction,
locking, crash, or PostgreSQL/MySQL simulation. Keep confidential schema and
data out of public workflow artifacts. A pass is not a deployment approval.
The reusable packaging is a Codex extension after Bob's original gate;
[Bob's actual IDE work and limits](PROVENANCE.md) remain separately documented.

The pinned version was exercised in [six GitHub control jobs](../evidence/ci_portable_action_control/README.md): pass, verified block, and unverified input error on both Ubuntu and Windows. All expected classifications and Action outputs were confirmed; the four executed packets also passed independent replay.
