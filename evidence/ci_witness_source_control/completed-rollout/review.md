# Cutover review: Cross-record reset trap

**Verdict:** BLOCKED — 100/132 rollout and window probes passed.

**Contract:** Parcel / delivery service (`custom`)

| Evidence group | Passed | Total |
| --- | ---: | ---: |
| Same-version baseline | 8 | 8 |
| Completed rollout | 44 | 76 |
| Migration-statement windows | 56 | 56 |

The baseline is separate from the rollout total. Each probe executes against a fresh disposable SQLite database and checks acknowledged values against an independent ledger.

## Shortest observed failing replay

Probe: **`old_old_old-0`** — Old write → old write → old read

Input:

~~~json
"18 Marina Road"
~~~

Row shown in this replay: `101`.

Seed IDs checked before this verdict:

~~~json
[
  101,
  102
]
~~~

Write targets shown in this replay:

~~~json
[
  101,
  102
]
~~~

Cross-record paths checked before this verdict:

~~~json
[
  [
    101,
    102
  ]
]
~~~

### 1. migrate — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE orders ADD COLUMN shipping_address TEXT;

-- Preserve both reader contracts throughout the rollback window.
CREATE TRIGGER sync_old_update AFTER UPDATE OF delivery_address ON orders
WHEN NEW.delivery_address IS NOT NEW.shipping_address
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;

CREATE TRIGGER sync_new_update AFTER UPDATE OF shipping_address ON orders
WHEN NEW.shipping_address IS NOT NEW.delivery_address
BEGIN
  UPDATE orders SET delivery_address = NEW.shipping_address WHERE id = NEW.id;
END;

CREATE TRIGGER sync_old_insert AFTER INSERT ON orders
WHEN NEW.shipping_address IS NULL
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;

-- Backfill only after the synchronization triggers are active.
UPDATE orders SET shipping_address = delivery_address;

-- Adversarial fixture: a later write silently erases an earlier record.
CREATE TRIGGER reset_other_record AFTER UPDATE OF delivery_address ON orders
WHEN NEW.id = 102
BEGIN
  UPDATE orders SET delivery_address = '4 Broad Street', shipping_address = '4 Broad Street' WHERE id = 101;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 2. old.write — pass

Connection: **old**.

Executed SQL:

~~~sql
UPDATE orders SET delivery_address = :value WHERE id = :id
~~~

Bound inputs:

~~~json
{
  "id": 101,
  "value": "18 Marina Road"
}
~~~

Write acknowledged; independent ledger updated.

### 3. old.write — pass

Connection: **old**.

Executed SQL:

~~~sql
UPDATE orders SET delivery_address = :value WHERE id = :id
~~~

Bound inputs:

~~~json
{
  "id": 102,
  "value": "18 Marina Road [updated]"
}
~~~

Write acknowledged; independent ledger updated.

### 4. old.read — fail

Connection: **old**.

Executed SQL:

~~~sql
SELECT id, delivery_address AS value FROM orders ORDER BY id
~~~

Expected ledger:

~~~json
{
  "101": "18 Marina Road",
  "102": "18 Marina Road [updated]"
}
~~~

Observed:

~~~json
{
  "101": "4 Broad Street",
  "102": "18 Marina Road [updated]"
}
~~~

A reader cannot see the latest acknowledged data.

Failure: **data\_mismatch** — A reader cannot see the latest acknowledged data.

## Evidence identity

- Plan SHA-256: `862e5029121fdbd47f341daee93015d55071bbeb35499bc89810833ac70e1867`
- Contract SHA-256: `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418`
- Suite SHA-256: `bc41d4b60e280af5c5b60dea1ec870d7b50da1a2e8c12ebe3d885c30334f07d1`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-26T04:35:13.416375+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
