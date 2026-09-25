# Cutover review: Triggers before backfill, one-way sync, dual-write

**Verdict:** PASS — 116/116 rollout and window probes passed.

**Contract:** Parcel / delivery service (`custom`)

| Evidence group | Passed | Total |
| --- | ---: | ---: |
| Same-version baseline | 8 | 8 |
| Completed rollout | 76 | 76 |
| Migration-statement windows | 40 | 40 |

The baseline is separate from the rollout total. Each probe executes against a fresh disposable SQLite database and checks acknowledged values against an independent ledger.

## Example passing migration-window replay

Probe: **`window_write_after_0-0`** — Old write after migration step 0/4 → new read

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

### 1. old.write — pass

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

### 2. old.read — pass

Connection: **old**.

Executed SQL:

~~~sql
SELECT id, delivery_address AS value FROM orders ORDER BY id
~~~

Expected ledger:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

Observed:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

All 2 records match the independent write ledger.

### 3. migration.statement.0 — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE orders ADD COLUMN shipping_address TEXT;
~~~

Migration statement executed against a fresh in-memory database.

### 4. migration.statement.1 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_delivery_to_shipping AFTER UPDATE OF delivery_address ON orders
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 5. migration.statement.2 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_insert_to_shipping AFTER INSERT ON orders
WHEN NEW.shipping_address IS NULL
BEGIN
  UPDATE orders SET shipping_address = NEW.delivery_address WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 6. migration.statement.3 — pass

Connection: **migration**.

Executed SQL:

~~~sql
UPDATE orders SET shipping_address = delivery_address WHERE shipping_address IS NULL;
~~~

Migration statement executed against a fresh in-memory database.

### 7. new.read — pass

Connection: **new**.

Executed SQL:

~~~sql
SELECT id, shipping_address AS value FROM orders ORDER BY id
~~~

Expected ledger:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

Observed:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

All 2 records match the independent write ledger.

### 8. target.check — pass

Connection: **migration**.

Executed SQL:

~~~sql
SELECT id, "shipping_address" AS value FROM "orders" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

Observed:

~~~json
{
  "101": "18 Marina Road",
  "102": "9 Station Road"
}
~~~

Required target column matches the independent write ledger.

**A pass is bounded to this suite; it is not a deployment approval.**

## Evidence identity

- Plan SHA-256: `4d54ca78ffc24cc6b4b2e140dc2a4368244e801ab3326edd3b45f89d65b385c5`
- Contract SHA-256: `ecf66707fc8fe5a8a59f4dbfda92bed4377352cb190c6ad23d69271c8b325418`
- Suite SHA-256: `bc41d4b60e280af5c5b60dea1ec870d7b50da1a2e8c12ebe3d885c30334f07d1`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-25T21:39:59.842253+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
