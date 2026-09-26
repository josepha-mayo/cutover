## Cutover PR gate — ✅ VERIFIED_PASS

| Field | Value |
| --- | --- |
| Classification | `verified_pass` |
| CLI exit | `0` |
| Audit exit | `0` |
| Contract hash (report) | `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5` |
| Plan hash (report) | `930c2f30ccd10a81bc34cffc23dbcdceb45d60885d1609ac1a2aa698baa74da6` |
| SQL source file | `consumer/migration.sql` |
| SQL file SHA-256 | `8aba476ea9510071ff704d266897c5c6fd6109fcb0177c2bff6a803267de4c3f` |

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ✅ Verified pass — all probes passed

Both the CLI and the independent audit agree: the candidate passed all
rollout and migration-window probes in this bounded suite.

> **A pass is bounded to this suite; it is not a deployment approval.**

**Coverage:** 116/116 probes passed.

CLI: `PASS: 116/116 rollout and window probes; same-version baseline 8/8; plan 930c2f30ccd1`

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
