## Cutover PR gate — ❌ VERIFIED_BLOCK

| Field | Value |
| --- | --- |
| Classification | `verified_block` |
| CLI exit | `1` |
| Audit exit | `1` |
| Contract hash (report) | `360b26dff33b79ea62bb12cd150d99dbb39ce0df764783b1dcf30d613bc2b7d5` |
| Plan hash (report) | `e48f7bab7fdcc645217abf68de77101b0162df7254e584263d5afb9ea2b9c31f` |
| SQL source file | `ci/release-dispatch-handover-migration.sql` |
| SQL file SHA-256 | `48a878cd29ce42e157e881a34524c0208b1beaa1a3e5fa956cf8819d96c7594f` |

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ❌ Verified block — candidate has a data-safety gap

The CLI executed the candidate and observed at least one failing probe.
The independent audit confirmed the same result from the checked-in inputs.

**Coverage:** 80/116 probes passed.

**Probe:** `old_to_new-0`

**First differing value (row `1`):**

| | Value |
| --- | --- |
| Expected | `DOCK-07` |
| Actual   | `A-01` |

Review `report.json` and `review.md` in the uploaded artifacts for the
full witness trace.

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
