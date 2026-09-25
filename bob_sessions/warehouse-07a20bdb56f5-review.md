# Cutover review: Warehouse: triggers before backfill, one-way sync, dual-write

**Verdict:** PASS — 116/116 rollout and window probes passed.

**Contract:** Warehouse / bin relocation (`custom`)

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
"R-07"
~~~

Row shown in this replay: `11`.

Seed IDs checked before this verdict:

~~~json
[
  11,
  22,
  33
]
~~~

### 1. old.write — pass

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

### 2. old.read — pass

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

### 3. migration.statement.0 — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE stock_items ADD COLUMN fulfillment_bin TEXT;
~~~

Migration statement executed against a fresh in-memory database.

### 4. migration.statement.1 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_pick_to_fulfillment AFTER UPDATE OF pick_bin ON stock_items
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 5. migration.statement.2 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER sync_insert_to_fulfillment AFTER INSERT ON stock_items
WHEN NEW.fulfillment_bin IS NULL
BEGIN
  UPDATE stock_items SET fulfillment_bin = NEW.pick_bin WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 6. migration.statement.3 — pass

Connection: **migration**.

Executed SQL:

~~~sql
UPDATE stock_items SET fulfillment_bin = pick_bin WHERE fulfillment_bin IS NULL;
~~~

Migration statement executed against a fresh in-memory database.

### 7. new.read — pass

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
  "11": "R-07",
  "22": "B-02",
  "33": "C-03"
}
~~~

All 3 records match the independent write ledger.

### 8. target.check — pass

Connection: **migration**.

Executed SQL:

~~~sql
SELECT id, "fulfillment_bin" AS value FROM "stock_items" ORDER BY id
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

Required target column matches the independent write ledger.

**A pass is bounded to this suite; it is not a deployment approval.**

## Evidence identity

- Plan SHA-256: `930c2f30ccd10a81bc34cffc23dbcdceb45d60885d1609ac1a2aa698baa74da6`
- Contract SHA-256: `6455c1c197d93e0bdd5915232d94e4558514efe9d3245d576d970172e8f9b5a5`
- Suite SHA-256: `dbd9cb724455cadced8634b8ad2ceab343b8ba47dd4a9f2d880a4a7381ba0f86`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.50.4`
- Generated UTC: `2026-09-25T15:51:35.739342+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
