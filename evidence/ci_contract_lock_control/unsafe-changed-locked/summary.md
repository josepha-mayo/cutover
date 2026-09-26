## Cutover PR gate — ⚠️ UNVERIFIED

| Field | Value |
| --- | --- |
| Classification | `unverified` |
| CLI exit | `None` |
| Audit exit | `None` |
| Contract lock | `changed` |
| Expected contract hash | `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418` |
| Observed contract hash | `17850c1af80fe449c9a32930bb6ffd796123efaad31480366d8751e301668849` |

The contract hash covers the agreed schema, old-worker adapters,
seed records and payloads. A changed contract requires a separate
review; it is not evidence that the migration was repaired.

### ⚠️ Unverified — evidence could not be independently confirmed

The gate could not produce a definitive verdict.
Possible causes: timeout, invalid inputs, process error, or a
CLI/audit exit-code pair that does not map to a known outcome.

**Audit stderr:**

```
Contract changed from the reviewed lock; review the test contract separately
```

---
_Evidence artifacts are uploaded unconditionally; see the Actions run._
