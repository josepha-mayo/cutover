## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Plan hash (report) | `862e5029121fdbd47f341daee93015d55071bbeb35499bc89810833ac70e1867` |
| Contract lock | `matched` |
| Expected contract hash | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Observed contract hash | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| SQL source file | `control/contract-lock/unsafe.sql` |
| SQL file SHA-256 | `8e7ad3d4a01e1ba4825e9c2ae18c81cf12c16f2f8899646ea5ac68e2f321777f` |

The contract hash covers the agreed schema, old-worker adapters,
seed records and payloads. A changed contract requires a separate
review; it is not evidence that the migration was repaired.

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 100/132 probes passed.

**Probe:** `old_old_old-0`

**First differing value (row `101`):**

| | Value |
| --- | --- |
| Expected | `18 Marina Road` |
| Actual   | `4 Broad Street` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
