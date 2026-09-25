## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Plan hash (report) | `7e7bc349a783c824777fa99a4e2fdf1c245aa7f1f1e404421fa62541cf2ff252` |

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 108/124 probes passed.

**Probe:** `window_write_after_2-0`

**First differing value (row `101`):**

| | Value |
| --- | --- |
| Expected | `18 Marina Road` |
| Actual   | `4 Broad Street` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
