# Cutover review: Generated compatibility bridge · verify before use

**Verdict:** PASS — 124/124 rollout and window probes passed.

**Contract:** My release (`custom`)

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
"next release"
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
UPDATE "items" SET "location" = :value WHERE id = :id
~~~

Bound inputs:

~~~json
{
  "id": 1,
  "value": "next release"
}
~~~

Write acknowledged; independent ledger updated.

### 2. old.read — pass

Connection: **old**.

Executed SQL:

~~~sql
SELECT id, "location" AS value FROM "items" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

All 2 records match the independent write ledger.

### 3. migration.statement.0 — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE "items" ADD COLUMN "destination" TEXT;
~~~

Migration statement executed against a fresh in-memory database.

### 4. migration.statement.1 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_old_update AFTER UPDATE OF "location" ON "items"
WHEN NEW."location" IS NOT NEW."destination"
BEGIN
  UPDATE "items" SET "destination" = NEW."location" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 5. migration.statement.2 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_new_update AFTER UPDATE OF "destination" ON "items"
WHEN NEW."destination" IS NOT NEW."location"
BEGIN
  UPDATE "items" SET "location" = NEW."destination" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 6. migration.statement.3 — pass

Connection: **migration**.

Executed SQL:

~~~sql
CREATE TRIGGER cutover_old_insert AFTER INSERT ON "items"
WHEN NEW."destination" IS NULL
BEGIN
  UPDATE "items" SET "destination" = NEW."location" WHERE id = NEW.id;
END;
~~~

Migration statement executed against a fresh in-memory database.

### 7. migration.statement.4 — pass

Connection: **migration**.

Executed SQL:

~~~sql
UPDATE "items" SET "destination" = "location";
~~~

Migration statement executed against a fresh in-memory database.

### 8. new.read — pass

Connection: **new**.

Executed SQL:

~~~sql
SELECT id, "destination" AS value FROM "items" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

All 2 records match the independent write ledger.

### 9. target.check — pass

Connection: **migration**.

Executed SQL:

~~~sql
SELECT id, "destination" AS value FROM "items" ORDER BY id
~~~

Expected ledger:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

Observed:

~~~json
{
  "1": "next release",
  "2": "B-02"
}
~~~

Required target column matches the independent write ledger.

**A pass is bounded to this suite; it is not a deployment approval.**

## Evidence identity

- Plan SHA-256: `094e61d8f32f2dc6b2204b41316fb719acbfcfadf30ba9d791254607f65ea42d`
- Contract SHA-256: `f623f640609056afcbb25a2b59b1aa7d0356c0a4477b8656b9c4e8f02e68798d`
- Suite SHA-256: `4be6fd18e9f84b12a3568d4a52887e60d9d2e2585a0a05ad29f2fe60b99915d6`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-25T21:40:03.071466+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
