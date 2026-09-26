# A SQL-only edit changes the PR verdict

[Controlled PR #10](https://github.com/josepha-mayo/cutover/pull/10) binds
Warehouse to `ci/warehouse-migration.sql`. The adapter JSON stays byte-for-byte
unchanged between the passing and blocked runs. The [entire change](sql-only-change.diff)
removes only the old-update synchronization trigger from the SQL source.

| Run | Warehouse | Unchanged Parcel | Exact downloaded evidence |
| --- | --- | --- | --- |
| [Safe source](https://github.com/josepha-mayo/cutover/actions/runs/36209226731) | 116/116 verified pass | 116/116 verified pass | [Summary](safe/cutover-warehouse-review-evidence/summary.md) · [ZIP](safe/cutover-warehouse-review-evidence/review.zip) · [Receipt](safe/receipt.json) |
| [SQL-only regression](https://github.com/josepha-mayo/cutover/actions/runs/36209366002) | 72/108 verified block | 116/116 verified pass | [Witness](blocked/cutover-warehouse-review-evidence/summary.md) · [ZIP](blocked/cutover-warehouse-review-evidence/review.zip) · [Receipt](blocked/receipt.json) |

The blocked check links its annotation to the SQL file: row 11 expected `R-07`,
observed `A-01`. Fewer migration statements produce fewer boundary probes, so
the total changes from 116 to 108. Both verdicts use the actual checked-in SQL,
not the still-safe migration embedded in `ci/candidate.json`.

The first [general CI run](https://github.com/josepha-mayo/cutover/actions/runs/36208766528)
failed because temporary test checkouts omitted the optional SQL file. That
failure remains public. After the fixture-copy fix, all 108 tests and the other
checks passed on Ubuntu and Windows for both the
[safe head](https://github.com/josepha-mayo/cutover/actions/runs/36209226735) and
[regressed head](https://github.com/josepha-mayo/cutover/actions/runs/36209366009).
The intentional data-safety block is separate from those general code checks.

Each mirrored report and review ZIP was independently replayed against its
exact PR-head contract, adapters, and SQL source. `effective-plan.json` retains
the assembled input; `verdict.json` binds the raw source-file hash and unchanged
adapter-file hash. [The manifest](manifest.json) hashes every mirrored payload.
The public run page was inspected for its status and file-linked witness;
GitHub required sign-in for job details, so the exact downloaded summaries are
also available here. These hashes detect changes; they are not signatures.

The source-file binding, test-fixture correction, and synthetic controls are
Codex work after Bob's two IDE tasks. Bob authored the original gate and the
saved repair used by the safe source. These results cover the bounded SQLite
contracts and executed schedules only. See [setup](../../docs/CI.md#review-the-actual-migration-file)
and [provenance](../../docs/PROVENANCE.md).
