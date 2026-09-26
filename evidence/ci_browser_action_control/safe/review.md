# Cutover review: Generated compatibility bridge · verify before use

**Verdict:** PASS — 124/124 rollout and window probes passed.

**Contract:** Dispatch handover (`custom`)

| Evidence group | Passed | Total |
| --- | ---: | ---: |
| Same-version baseline | 8 | 8 |
| Completed rollout | 76 | 76 |
| Migration-statement windows | 48 | 48 |

The baseline is separate from the rollout total. Each probe executes against a fresh disposable SQLite database and checks acknowledged values against an independent ledger.

## Example passing migration-window replay

Probe: **`window_write_after_0-0`** — Old write after migration step 0/5 → new read

Input:

~~~json
"DOCK-07"
~~~

Row shown in this replay: `1`.

Seed IDs checked before this verdict:

~~~json
[
  1,
  2
]
~~~

### 1. old.write — pass

Connection: **old**.

Executed SQL:

~~~sql
UPDATE "consignments" SET "loading_bay" = :value WHERE id = :id
~~~

Bound inputs:

~~~json
{
  "id": 1,
  "value": "DOCK-07"
}
~~~

Write acknowledged; independent ledger updated.

### 2. old.read — pass

Connection: **old**.

Executed SQL:

~~~sql
SELECT id, "loading_bay" AS value FROM "consignments" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

All 2 records match the independent write ledger.

### 3. migration.statement.0 — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE "consignments" ADD COLUMN "dispatch_bay" TEXT;
~~~

Migration statement executed against a fresh in-memory database.

### 4. migration.statement.1 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_old_update AFTER UPDATE OF "loading_bay" ON "consignments"
WHEN NEW."loading_bay" IS NOT NEW."dispatch_bay"
BEGIN
  UPDATE "consignments" SET "dispatch_bay" = NEW."loading_bay" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 5. migration.statement.2 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_new_update AFTER UPDATE OF "dispatch_bay" ON "consignments"
WHEN NEW."dispatch_bay" IS NOT NEW."loading_bay"
BEGIN
  UPDATE "consignments" SET "loading_bay" = NEW."dispatch_bay" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 6. migration.statement.3 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_old_insert AFTER INSERT ON "consignments"
WHEN NEW."dispatch_bay" IS NULL
BEGIN
  UPDATE "consignments" SET "dispatch_bay" = NEW."loading_bay" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 7. migration.statement.4 — pass

Connection: **migration**.

Executed SQL:

~~~sql
UPDATE "consignments" SET "dispatch_bay" = "loading_bay";
~~~

Migration statement executed against a fresh in-memory database.

### 8. new.read — pass

Connection: **new**.

Executed SQL:

~~~sql
SELECT id, "dispatch_bay" AS value FROM "consignments" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

All 2 records match the independent write ledger.

### 9. target.check — pass

Connection: **migration**.

Executed SQL:

~~~sql
SELECT id, "dispatch_bay" AS value FROM "consignments" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "DOCK-07",
  "2": "B-02"
}
~~~

Required target column matches the independent write ledger.

**A pass is bounded to this suite; it is not a deployment approval.**

## Evidence identity

- Plan SHA-256: `e025fa3c3e4fb4acc155505ce4d0f978896ae9b5b199f5f841a5e15298c61a18`
- Contract SHA-256: `360b26dff33b79ea62bb12cd150d99dbb39ce0df764783b1dcf30d613bc2b7d5`
- Suite SHA-256: `3afd914175c173b7d675573da7b649fa52c32ec23bf7d7d8932757a3f45846ca`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-26T02:41:52.873871+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
