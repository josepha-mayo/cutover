# Cutover review: Generated compatibility bridge · verify before use

**Verdict:** BLOCKED — 80/116 rollout and window probes passed.

**Contract:** Dispatch handover (`custom`)

| Evidence group | Passed | Total |
| --- | ---: | ---: |
| Same-version baseline | 8 | 8 |
| Completed rollout | 44 | 76 |
| Migration-statement windows | 36 | 40 |

The baseline is separate from the rollout total. Each probe executes against a fresh disposable SQLite database and checks acknowledged values against an independent ledger.

## Shortest observed failing replay

Probe: **`old_to_new-0`** — Old write → new read

Input:

~~~json
"DOCK-07"
~~~

Row shown in this replay: `1`.

Seed IDs checked before this verdict:

~~~json
[
  1
]
~~~

### 1. migrate — pass

Connection: **migration**.

Executed SQL:

~~~sql
ALTER TABLE "consignments" ADD COLUMN "dispatch_bay" TEXT;
CREATE TRIGGER cutover_new_update AFTER UPDATE OF "dispatch_bay" ON "consignments"
WHEN NEW."dispatch_bay" IS NOT NEW."loading_bay"
BEGIN
  UPDATE "consignments" SET "loading_bay" = NEW."dispatch_bay" WHERE id = NEW.id;
END;
CREATE TRIGGER cutover_old_insert AFTER INSERT ON "consignments"
WHEN NEW."dispatch_bay" IS NULL
BEGIN
  UPDATE "consignments" SET "dispatch_bay" = NEW."loading_bay" WHERE id = NEW.id;
END;
UPDATE "consignments" SET "dispatch_bay" = "loading_bay";
~~~

Migration statement executed against a fresh in-memory database.

### 2. old.write — pass

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

### 3. new.read — fail

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
  "1": "A-01",
  "2": "B-02"
}
~~~

A reader cannot see the latest acknowledged data.

Failure: **data\_mismatch** — A reader cannot see the latest acknowledged data.

## Evidence identity

- Plan SHA-256: `e48f7bab7fdcc645217abf68de77101b0162df7254e584263d5afb9ea2b9c31f`
- Contract SHA-256: `360b26dff33b79ea62bb12cd150d99dbb39ce0df764783b1dcf30d613bc2b7d5`
- Suite SHA-256: `3afd914175c173b7d675573da7b649fa52c32ec23bf7d7d8932757a3f45846ca`
- Engine SHA-256: `9b315f8a9b9d434f4de5f46b94aefcc15b635bab64ffd69f1bae989361e50aeb`
- SQLite version: `3.45.1`
- Generated UTC: `2026-09-26T02:46:33.662859+00:00`

## Scope and limits

SQLite user-supplied contract, separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval.

- No concurrent transactions, lock timing or network failures modeled.
- No PostgreSQL, MySQL or ORM behavior claimed.
- Writes between migration statements are modeled; mid-statement interruption and lock timing are not.
- Contract/drop-column phase is deferred until old workers and rollback windows are retired.
- Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.
- Passing covers only the fixed adapters, seed data and reported schedules.

This report documents executed SQL only. It does not establish IBM Bob authorship, production safety, or behavior outside the reported contract and schedules.
