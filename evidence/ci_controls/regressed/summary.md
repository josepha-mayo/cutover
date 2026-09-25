## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Plan hash (report) | `b91f1fdacf6fc23d39b2473dcdf48a1d2cceb9fd3465c67662690266340a77a4` |

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 100/116 probes passed.

**Probe:** `new_to_old-0`

**First differing value (row `11`):**

| | Value |
| --- | --- |
| Expected | `R-07` |
| Actual   | `A-01` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
