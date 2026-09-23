# Cutover

**A green build can still be a broken handover.**

![Cutover shows the missed write between a backfill and synchronization](presentation/cover.png)

Cutover rehearses schema-changing releases while old and new application versions share a database. It executes their SQL contracts against disposable SQLite databases and checks that every reader sees the latest acknowledged write, including after application rollback.

The prototype is functional and [the public demo](https://cutover-rehearsal.onrender.com/) is live on Render's free tier. [The source](https://github.com/josepha-mayo/cutover) is public, and the IBM Bob MCP transport has been checked with a real SDK client. An actual Bob session and submission assets remain outstanding. This is pre-event preparation created on September 23, 2026 with Codex, not a claim of work performed by Bob during the event. The free demo may take around a minute to wake after inactivity.

## Run

Python 3.10+ with SQLite 3.25+ is sufficient for the app. No runtime packages, API keys, database account, or build tool are required.

```powershell
python server.py
```

Open http://127.0.0.1:8765. The server binds only to loopback by default. The same sample-only app is hosted at [cutover-rehearsal.onrender.com](https://cutover-rehearsal.onrender.com/); it is a hackathon demo, not a hardened public multi-tenant service.

## Try the three-minute story

1. Select **Direct rename**, then **Run release rehearsal**. All 8 new-version checks pass. Cutover catches 60 failing completed-rollout probes, including an old worker querying a removed column.
2. Select **Expand & backfill**, then run. New-version checks still pass. A write is acknowledged but the other version reads stale data. Select a red square to inspect executed SQL and expected/observed values.
3. Select **Late bridge**. All 76 completed-rollout probes pass, yet 16 of 48 migration-window probes fail. An old write after the backfill and before the triggers silently leaves the new column stale.
4. Select **Window-safe bridge**. Moving synchronization before backfill preserves data through all 124 tested probes. Append `DROP TRIGGER sync_new_update;` to its migration and rerun; 12 failures return. Results are computed from SQL, never chosen by candidate name.
5. Export evidence, save/import a candidate, or prepare a repair task for IBM Bob.

Two sample contracts are included: Parcel's address migration and Relay's contact-field migration. They demonstrate the same structural failure on different identifiers and seed data. They are sample SQL adapters, not claims of integration with production services or full ORM applications. Inputs deliberately stress string preservation and do not validate contact syntax.

## What executes

Each probe gets a fresh in-memory database and a copy of fixed seed records. The old adapter is fixed; the candidate supplies migration SQL and new read/update/insert queries. Each acknowledged write updates an independent Python record ledger. A read must return exactly those records and values. The runner generates 19 completed-rollout schedules with four input strings each, then inserts old updates and inserts at every SQLite statement boundary of the migration. The total varies with the number of migration statements. Same-version baseline tests are reported separately.

The engine detects schema errors, stale values, missing records, ignored writes, and unintended writes to other records. Reports include inputs, executed statements, replay prefixes, coverage, SQLite/engine versions and hashes of the candidate, contract, suite and engine source. Hashes identify inputs; they are not signed attestations.

The smallest failure shown is the **shortest observed failing prefix in this suite**, not a globally minimal counterexample. Rollback means returning traffic to the old application while retaining the expanded database, not executing a down migration.

## Measured impact in the sample challenge

Among three deliberately unsafe rollout patterns, the new-version baseline detects 0/3, completed-rollout checks detect 2/3, and adding migration-statement windows detects 3/3. The late bridge alone passes 76/76 completed-rollout probes but fails 16 window probes. This is a [controlled fixture ablation](docs/IMPACT.md), repeated on two structurally similar examples; it is not a customer benchmark or measured time saving. Recompute it with `python -m evidence.build_ablation`.

## Bob integration

The optional integration uses the official MCP Python SDK v1, pinned to the version tested here.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-mcp.txt
python configure_bob.py --python .venv\Scripts\python.exe
.venv\Scripts\python tests/check_mcp.py
```

On macOS/Linux, use `.venv/bin/python` instead. `configure_bob.py` creates a project-local `.bob/mcp.json` with absolute paths and preserves other server entries. It leaves automatic tool approval off.

For the repair task, first freeze a reference-withheld sibling workspace from a clean commit:

```powershell
python prepare_bob_session.py --python .venv\Scripts\python.exe
```

Open the printed `cutover-bob-session-<commit>` folder in Bob and select **Cutover release engineer**. It contains the same evaluator and failing sample plans, but no bundled passing plan, presentation materials or prior repair notes. The custom mode permits reading and MCP calls, with edits limited to candidate JSON and notes under `work/`. The tools are `inspect_release`, `diagnose_reference`, and `rehearse_candidate`; the diagnostic tool exposes only failing references. A public solution still exists in the source repository, so this reduces answer leakage rather than proving Bob could not have seen it.

Use [BOB_TASK.md](docs/BOB_TASK.md). Capture the real task summary and screenshots, retain Bob's actual candidate, and replay it in this full project with `python -m cutover --plan work/bob-candidate.json`. The interface's four reference plans are prewritten; loading the bridge is not an AI repair. The MVP intentionally does not invent an IBM Bob inference API.

## CLI and verification

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m cutover --reference rename --output work/rename.json
python -m cutover --reference bridge --output work/bridge.json
python -m cutover --plan work/bob-candidate.json --output work/bob-result.json
```

The CLI returns exit code 1 for a failing rehearsal and 0 for a passing suite. The app and MCP server execute candidates in a subprocess with an 8-second overall deadline. SQLite also interrupts long queries and denies external database attachment, pragmas, extension loading and explicit transaction control. Only sample data enters the database; no production connection or shell-command tool is exposed.

The test suite includes negative controls: removing each synchronization trigger, dropping an unrelated record, a write affecting the wrong number of rows, SQL injection characters as data, fresh seed identifiers, runaway SQL, input tampering, HTTP checks and actual subprocess execution.

## Boundaries

Passing is bounded evidence, not a deployment certificate. There is no concurrent transaction/lock simulation, network-failure model, mid-statement interruption, PostgreSQL/MySQL claim, performance estimate, arbitrary repository importer, or completed final column removal. Statement-boundary probes model a successful old write between autocommitted SQLite migration statements, then completion of the remaining statements. Keep the bridge while old workers and rollback remain possible; removing it requires a later contract phase and further verification.

Current HTTP/browser results are not persisted server-side; download the report before refreshing. Bob provenance is intentionally unverified until a real host session is captured. See [STATUS.md](docs/STATUS.md), [the decision record](docs/DECISION.md), and [submission preparation](docs/SUBMISSION.md).

MIT licensed. Independent prototype; not an IBM product.
