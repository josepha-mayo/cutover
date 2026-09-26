# Cutover review: Warehouse late synchronization

**Verdict:** BLOCKED — 108/124 rollout and window probes passed.

**Contract:** Warehouse / bin relocation (`custom`)

| Evidence group | Passed | Total |
| --- | ---: | ---: |
| Same-version baseline | 8 | 8 |
| Completed rollout | 76 | 76 |
| Migration-statement windows | 32 | 48 |

The baseline is separate from the rollout total. Each probe executes against a fresh disposable SQLite database and checks acknowledged values against an independent ledger.

## Shortest observed failing replay

Probe: **`window_write_after_2-0`** — Old write after migration step 2/5 → new read

Input:

~~~json
"R-07"
~~~

Row shown in this replay: `11`.

Seed IDs checked before this verdict:

~~~json
[
  11
]
~~~

### 1. migration.statement.0 — pass

Connection: **migration**.

Executed SQL:

~~~sql
-- Reviewed SQL; this is a comment.
/* Another comment.
   Still a comment.
*/
ALTER TABLE stock_items ADD COLUMN fulfillment_bin TEXT;
~~~

Migration statement executed against a fresh in-memory database.

### 2. migration.statement.1 — pass

Connection: **migration**.

Executed SQL:

~~~sql
-- Copy current values; ``` is comment text.
UPDATE stock_items
SET fulfillment_bin = pick_bin;
~~~

Migration statement executed against a fresh in-memory database.

### 3. old.write — pass

Connection: **old**.

Executed SQL:

~~~sql
UPDATE stock_items SET pick_bin = :value WHERE id = :id
~~~

Bound inputs:

~~~json
{
  "id": 11,
  "value": "R-07"
}
~~~

Write acknowledged; independent ledger updated.

### 4. old.read — pass

Connection: **old**.

Executed SQL:

~~~sql
SELECT id, pick_bin AS value FROM stock_items ORDER BY id
~~~

Expected ledger:

~~~json
{
  "11": "R-07",
  "22": "B-02",
  "33": "C-03"
}
~~~

Observed:

~~~json
{
  "11": "R-07",
  "22": "B-02",
  "33": "C-03"
}
~~~

All 3 records match the independent write ledger.

### 5. migration.statement.2 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_old_update AFTER UPDATE OF pick_bin ON stock_items
WHEN NEW.pick_bin IS NOT NEW.fulfillment_bin
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 6. migration.statement.3 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_new_update AFTER UPDATE OF fulfillment_bin ON stock_items
WHEN NEW.fulfillment_bin IS NOT NEW.pick_bin
BEGIN
  UPDATE stock_items SET pick_bin = NEW.fulfillment_bin WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 7. migration.statement.4 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_old_insert AFTER INSERT ON stock_items
WHEN NEW.fulfillment_bin IS NULL
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 8. new.read — fail

Connection: **new**.

Executed SQL:

~~~sql
SELECT id, fulfillment_bin AS value FROM stock_items ORDER BY id
~~~

Expected ledger:

~~~json
{
  "11": "R-07",
  "22": "B-02",
  "33": "C-03"
}
~~~

Observed:

~~~json
{
  "11": "A-01",
  "22": "B-02",
  "33": "C-03"
}
~~~

A reader cannot see the latest acknowledged data.

Failure: **data\_mismatch** — A reader cannot see the latest acknowledged data.

## Evidence identity

- Plan SHA-256: `fc752d050e87e4e7a5157003298da7496c30100a00826af13ca3606bca364b44`
- Contract SHA-256: `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5`
- Suite SHA-256: `dbd9cb724455cadced8634b8ad2ceab343b8ba47dd4a9f2d880a4a7381ba0f86`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-26T04:35:13.497755+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
