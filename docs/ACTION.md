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
      - uses: josepha-mayo/cutover@65984c8efd007e2d50d6beaf5afbdac500ec690b
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
scenario's PR gate kit from the browser. Its README lists four files to copy:
the generated pinned workflow, contract, adapters and migration SQL. The
[checked browser kit](../evidence/ci_browser_action_control/README.md) passed
124/124 in a real PR; removing only its old-write synchronization SQL blocked
80/116 with the same workflow and adapters.

Each review retains an artifact, including on verified blocks or input errors:
`verdict.json` and `summary.md`, plus the report, Markdown review and replay ZIP
when execution produced them. A separate SQL file also produces
`effective-plan.json`; `action.json` records the Action ref and consumer
checkout SHA. The SQL-file SHA-256 is retained in the verdict. A blocked
result shows its differing row value in the job summary and a file-linked
annotation.

## Keep the agreed test contract fixed

New browser kits include `expected-contract-hash` automatically. For a manually
written workflow, set it to the `contract_hash` from a reviewed report. The hash
covers the complete contract, including old-worker queries, schema, seed records
and payloads. JSON key order, indentation and line endings do not affect it.

For the linked Warehouse contract above, the input is:

```yaml
          expected-contract-hash: '6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5'
```

The equivalent local option is `--expected-contract-hash HASH` on
`ci/review_gate.py`. A mismatch exits 2, records both hashes in `verdict.json`
and the job summary, and annotates the contract file. It does not execute SQL or
claim a verified block. The executed report must also match the lock before a
pass can be recorded.

This prevents changed test records from silently looking like a repaired
migration. In [control PR #13](../evidence/ci_contract_lock_control/README.md),
the same unsafe SQL blocked 100/132 on the original records but passed 132/132
after changing only their IDs. Enforcing the original lock stopped the changed
contract as unverified. A real SQL repair passed 124/124 on the original locked
contract. All three executed packets were independently replayed.

Review intentional contract changes separately before updating the stored hash.
Do not recalculate the expected hash from the proposed contract inside the PR.
The lock is optional for manually authored workflows, and it is not a signature
or branch-protection rule. Review changes to the workflow and lock themselves.

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

The earlier Action version was exercised in [six GitHub control jobs](../evidence/ci_portable_action_control/README.md): pass, verified block, and unverified input error on both Ubuntu and Windows. The current pin adds the contract lock and was exercised in PR #13. Historical artifacts retain their original pins; they are not rewritten as runs of the new version.
