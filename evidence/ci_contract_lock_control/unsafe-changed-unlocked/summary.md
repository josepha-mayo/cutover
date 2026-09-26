## Cutover PR gate — ✅ VERIFIED_PASS

| Field | Value |
| --- | --- |
| Classification | `verified_pass` |
| CLI exit | `0` |
| Audit exit | `0` |
| Contract hash (report) | `17850c1af80fe449c9a32930bb6ffd796123efaad31480366d8751e301668849` |
| Plan hash (report) | `862e5029121fdbd47f341daee93015d55071bbeb35499bc89810833ac70e1867` |
| SQL source file | `control/contract-lock/unsafe.sql` |
| SQL file SHA-256 | `8e7ad3d4a01e1ba4825e9c2ae18c81cf12c16f2f8899646ea5ac68e2f321777f` |

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ✅ Verified pass — all probes passed

Both the CLI and the independent audit agree: the candidate passed all
rollout and migration-window probes in this bounded suite.

> **A pass is bounded to this suite; it is not a deployment approval.**

**Coverage:** 132/132 probes passed.

CLI: `PASS: 132/132 rollout and window probes; same-version baseline 8/8; plan 862e5029121f`

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
