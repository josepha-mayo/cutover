## Cutover PR gate — ✅ VERIFIED_PASS

| Field | Value |
| --- | --- |
| Classification | `verified_pass` |
| CLI exit | `0` |
| Audit exit | `0` |
| Contract hash (report) | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Plan hash (report) | `db1490fb7747a988a177444e8261d0e4164f1a2ed6ba55065ec50137e7c3514a` |
| Contract lock | `matched` |
| Expected contract hash | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Observed contract hash | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| SQL source file | `control/contract-lock/safe.sql` |
| SQL file SHA-256 | `c3a8bba29ca19a574ee6a44e0b6d70f7cdd2fd2d7878fe49b1d7d8043981c82e` |

The contract hash covers the agreed schema, old-worker adapters,
seed records and payloads. A changed contract requires a separate
review; it is not evidence that the migration was repaired.

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ✅ Verified pass — all probes passed

Both the CLI and the independent audit agree: the candidate passed all
rollout and migration-window probes in this bounded suite.

> **A pass is bounded to this suite; it is not a deployment approval.**

**Coverage:** 124/124 probes passed.

CLI: `PASS: 124/124 rollout and window probes; same-version baseline 8/8; plan db1490fb7747`

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
