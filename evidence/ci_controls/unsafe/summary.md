## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Plan hash (report) | `f7ff94084d775c2eb236ad3f2f1e65a52a6d56b46ffe885672b36a8dcc6ee6e4` |

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 108/124 probes passed.

**Probe:** `window_write_after_2-0`

**First differing value (row `11`):**

| | Value |
| --- | --- |
| Expected | `R-07` |
| Actual   | `A-01` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
