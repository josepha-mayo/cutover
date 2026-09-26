## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Plan hash (report) | `d078a43429aea5c4ca76aac8a3459efd9524ee12fd68fe3625438c0c0664307c` |
| SQL source file | `ci/warehouse-migration.sql` |
| SQL file SHA-256 | `fcd96ac4d155308fe78c0d334e381cdfccb15617daf618bd35bded5fca654f65` |

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 72/108 probes passed.

**Probe:** `old_to_new-0`

**First differing value (row `11`):**

| | Value |
| --- | --- |
| Expected | `R-07` |
| Actual   | `A-01` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
