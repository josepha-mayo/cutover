## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Plan hash (report) | `fc752d050e87e4e7a5157003298da7496c30100a00826af13ca3606bca364b44` |
| Contract lock | `matched` |
| Expected contract hash | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Observed contract hash | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| SQL source file | `control/witness-source/late-window/migration.sql` |
| SQL file SHA-256 | `81cc7a1736e40b2b7aeb93dfc77470ece005ddc87c0f29e92b575954f151703a` |

The contract hash covers the agreed schema, old-worker adapters,
seed records and payloads. A changed contract requires a separate
review; it is not evidence that the migration was repaired.

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 108/124 probes passed.

**Probe:** `window_write_after_2-0`

**Replay location:** Observed old.write after SQL statement 2 of 5 (SQL line 8).

The annotation marks the observed old-worker operation's boundary,
not a claim that this SQL line alone caused the defect.

````sql
-- Copy current values; ``` is comment text.
UPDATE stock_items
SET fulfillment_bin = pick_bin;
````

**First differing value (row `11`):**

| | Value |
| --- | --- |
| Expected | `R-07` |
| Actual   | `A-01` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
