## Cutover PR gate — ✅ VERIFIED_PASS

| Field | Value |
| --- | --- |
| Classification | `verified_pass` |
| CLI exit | `0` |
| Audit exit | `0` |
| Contract hash (report) | `360b26dff33b79ea62bb12cd150d99dbb39ce0df764783b1dcf30d613bc2b7d5` |
| Plan hash (report) | `e025fa3c3e4fb4acc155505ce4d0f978896ae9b5b199f5f841a5e15298c61a18` |
| SQL source file | `ci/release-dispatch-handover-migration.sql` |
| SQL file SHA-256 | `4e0e9ebe0259e10197b6c692e90956f902332255b269c845db6479bc9fbb2496` |

The migration was loaded from this SQL file. `effective-plan.json`
retains the SQL and adapters supplied to the CLI and independent audit.

### ✅ Verified pass — all probes passed

Both the CLI and the independent audit agree: the candidate passed all
rollout and migration-window probes in this bounded suite.

> **A pass is bounded to this suite; it is not a deployment approval.**

**Coverage:** 124/124 probes passed.

CLI: `PASS: 124/124 rollout and window probes; same-version baseline 8/8; plan e025fa3c3e4f`

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
