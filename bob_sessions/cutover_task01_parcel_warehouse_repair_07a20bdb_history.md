# Read TASK.md and execute its reference-withheld repair exercise in this workspace. First call cutover.inspect_release(case="parcel") and cutover.diagnose_reference(case="parcel", reference="late_bridge"). Diagnose the shortest failing mixed-version replay, devise your own migration plus new SQL adapter, and call rehearse_candidate on each proposal. Preserve failed attempts. Save the actual five-field Parcel plan to work/bob-candidate.json and the observed reasoning/results to work/bob-repair.md. Then inspect examples/warehouse/contract.json and its late bridge, call inspect_imported_contract and rehearse_candidate(case="custom") with the complete Warehouse contract, and save its distinct attempted plan to work/bob-warehouse-candidate.json. Do not modify evaluator, fixed contracts, fixtures, seed data, schedules, or oracle. Report exact observed coverage and untested boundaries. If MCP is unavailable or the attempt blocks, state that honestly; never invent a pass.

---

**Status:** active  **Date:** 2026-09-25

---

### 👤 User

Read TASK.md and execute its reference-withheld repair exercise in this workspace. First call cutover.inspect_release(case="parcel") and cutover.diagnose_reference(case="parcel", reference="late_bridge"). Diagnose the shortest failing mixed-version replay, devise your own migration plus new SQL adapter, and call rehearse_candidate on each proposal. Preserve failed attempts. Save the actual five-field Parcel plan to work/bob-candidate.json and the observed reasoning/results to work/bob-repair.md. Then inspect examples/warehouse/contract.json and its late bridge, call inspect_imported_contract and rehearse_candidate(case="custom") with the complete Warehouse contract, and save its distinct attempted plan to work/bob-warehouse-candidate.json. Do not modify evaluator, fixed contracts, fixtures, seed data, schedules, or oracle. Report exact observed coverage and untested boundaries. If MCP is unavailable or the attempt blocks, state that honestly; never invent a pass.

---

### 🤖 Assistant

> 🔧 called: read_file, mcp__cutover__inspect_release, mcp__cutover__diagnose_reference

I'll start by reading TASK.md and running the initial inspections in parallel.

> 🔧 **read_file** — TASK.md

> 🔧 **mcp__cutover__inspect_release** — parcel

> 🔧 **mcp__cutover__diagnose_reference** — parcel

### 🤖 Assistant

> 🔧 called: list_files, list_files

The diagnosis is clear. Let me analyze the failure before proposing a candidate.

**Root cause of the failing replay (step 8):**
- Migration statements 0+1 run: `ADD COLUMN shipping_address` + `UPDATE … SET shipping_address = delivery_address` (backfill).
- Then an **old worker writes** `delivery_address = '18 Marina Road'` for id=101 (step 3) — acknowledged.
- Triggers are installed only in statements 2-4, which run *after* the old write (steps 5-7).
- So the backfill was clobbered: `delivery_address` is now `'18 Marina Road'` but `shipping_address` is still `'4 Broad Street'`.
- New reader reads `shipping_address` → stale value → **mismatch**.

**Fix:** The triggers must exist *before* any old write can clobber `shipping_address`. Move trigger creation to before the backfill, or combine the add-column and trigger creation before the backfill. Since the engine splits on `;` per statement, I need to order: ADD COLUMN → CREATE TRIGGERs → backfill. That way any old write between statements will be caught by the sync trigger.

Let me also check the `work/` directory and the warehouse contract:

> 🔧 **list_files** — examples

> 🔧 **list_files** — work

### 🤖 Assistant

> 🔧 called: list_files



> 🔧 **list_files** — examples/warehouse

### 🤖 Assistant

> 🔧 called: mcp__cutover__rehearse_candidate

Now let me run my first Parcel candidate. The strategy: reorder migration so triggers are created **before** the backfill. Old writes between ADD COLUMN and the triggers are also a gap, but ADD COLUMN sets `shipping_address = NULL` initially — so an old write to `delivery_address` between stmt 0 (ADD COLUMN) and trigger creation would leave `shipping_address = NULL`. I need to handle that too.

**Strategy:** 
1. `ADD COLUMN shipping_address TEXT` 
2. Create sync triggers immediately (before any backfill)
3. Backfill: `UPDATE orders SET shipping_address = delivery_address WHERE shipping_address IS NULL`

Any old write after stmt 1 (trigger creation) will fire `sync_old_update` keeping `shipping_address` in sync. The backfill in stmt 3 only fills NULLs, preserving trigger-synced values. Old writes between stmt 0 (ADD COLUMN) and stmt 1 (trigger) would leave `shipping_address = NULL` — the backfill's `WHERE shipping_address IS NULL` fixes those too.

New reader reads `shipping_address`. New writer writes `shipping_address` (explicit dual-write also required since no triggers). New insert must write both columns.

> 🔧 **mcp__cutover__rehearse_candidate** — parcel

### 🤖 Assistant

> 🔧 called: mcp__cutover__rehearse_candidate

**Attempt 1 blocked** — `too many levels of trigger recursion`. The two bidirectional UPDATE triggers (`sync_old_update` fires UPDATE on `shipping_address` → `sync_new_update` fires UPDATE on `delivery_address` → loop). The engine is treating the migration as a single string (no `;` splitting when triggers contain `;` in their bodies).

Wait — looking more carefully: the engine **did** split the reference plan's migration into 5 statements. But mine was sent as one big block. The issue is the **recursive trigger loop**: `sync_old_update` updates `shipping_address` → fires `sync_new_update` → updates `delivery_address` → fires `sync_old_update` again → infinite recursion.

The fix: use `WHEN` guards that prevent the back-fire. The reference plan used `WHEN NEW.delivery_address IS NOT NEW.shipping_address` guards — but those still recurse because after the trigger fires, the NEW values in the recursive UPDATE become equal, but SQLite's trigger recursion detection fires on depth, not on value equality.

Actually the real problem: SQLite's `PRAGMA recursive_triggers` is OFF by default, meaning triggers do NOT fire recursively. But the error says "too many levels" — this means RECURSIVE triggers are ON in this engine. With recursive triggers ON, the mutual sync triggers loop forever.

**Solution**: Drop the `sync_new_update` trigger entirely. The new writer uses an **explicit dual-write** (`UPDATE orders SET delivery_address = :value, shipping_address = :value`) — no need for a trigger to sync new→old. The `sync_old_update` trigger syncs old writes to `shipping_address`. No circular dependency.

> 🔧 **mcp__cutover__rehearse_candidate** — parcel

### 🤖 Assistant

> 🔧 called: read_file, read_file

**Attempt 2: PASS — 116/116.** Now let me read the Warehouse contract while saving the Parcel results:

> 🔧 **read_file** — examples/warehouse/contract.json

> 🔧 **read_file** — examples/warehouse/late_bridge.json

### 🤖 Assistant

> 🔧 called: mcp__cutover__inspect_imported_contract

The Warehouse late_bridge has the same structural flaw as the Parcel reference: backfill first, triggers second — so old writes between statements 1 and 2 corrupt `fulfillment_bin`. Plus the same bidirectional trigger recursion problem.

Now validate the contract and then rehearse the Warehouse candidate:

> 🔧 **mcp__cutover__inspect_imported_contract** — {"project":"Warehouse / bin relocation","summary":"Move pick_bin to fulfillment_bin while older scanner workers still update stock locations.","old_column":"pick_bin","new_column":"fulfillment_bin","table":"stock_items","schema":"CREATE TABLE stock_items (id INTEGER PRIMARY KEY, pick_bin TEXT NOT NULL);","seed_sql":"INSERT INTO stock_items (id, pick_bin) VALUES (?, ?)","seed":[[11,"A-01"],[22,"B-02"],[33,"C-03"]],"payloads":["R-07","Z'12","0","東京-棚"],"old":{"read":"SELECT id, pick_bin AS value FROM stock_items ORDER BY id","write":"UPDATE stock_items SET pick_bin = :value WHERE id = :id","insert":"INSERT INTO stock_items (id, pick_bin) VALUES (:id, :value)"}}

### 🤖 Assistant

> 🔧 called: mcp__cutover__rehearse_candidate

Contract is valid. Now rehearse the Warehouse candidate — same structural fix: triggers before backfill, one-way sync, explicit dual-write:

> 🔧 **mcp__cutover__rehearse_candidate** — custom

### 🤖 Assistant

> 🔧 called: write_file, write_file

**Warehouse: PASS — 116/116.** Now write all output files:

> 🔧 **write_file** — work/bob-candidate.json

> 🔧 **write_file** — work/bob-warehouse-candidate.json

### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — work/bob-repair.md

### 🤖 Assistant

All three output files are saved. Here is the complete summary.

---

## Summary

### Diagnosed failure (Parcel late_bridge, `window_write_after_2-0`)

The reference plan has 5 migration statements with this order:
1. `ADD COLUMN shipping_address TEXT`
2. `UPDATE … SET shipping_address = delivery_address` ← **backfill**
3. `CREATE TRIGGER sync_old_update …`
4. `CREATE TRIGGER sync_new_update …`
5. `CREATE TRIGGER sync_old_insert …`

An old worker writes `delivery_address = '18 Marina Road'` for id=101 **between statements 1 and 2** (after backfill, before triggers exist). The trigger never fires. When the new reader checks `shipping_address` it still sees `'4 Broad Street'` — the stale backfilled seed value.

---

### Parcel Attempt 1 — BLOCKED (`plan_hash 543e61d3…`)

Moved triggers before backfill but included **bidirectional sync triggers** (`sync_old_update` + `sync_new_update`). Both UPDATE each other: `delivery_address` change → trigger updates `shipping_address` → fires second trigger updating `delivery_address` → loops. Engine: `too many levels of trigger recursion`. 0/124.

### Parcel Attempt 2 — PASS 116/116 ✓ ([`work/bob-candidate.json`](work/bob-candidate.json))

**Fix:** Drop the reverse trigger entirely. The new writer uses an **explicit dual-write** (`SET delivery_address = :value, shipping_address = :value`), so no reverse trigger is needed. Only one one-way trigger exists: `sync_delivery_to_shipping` (old UPDATE → copies to `shipping_address`). Migration order: ADD COLUMN → trigger → insert-guard trigger → backfill (`WHERE shipping_address IS NULL` skips already-synced rows).

| Category | Passed/Total |
|---|---|
| compatibility | 4/4 |
| mixed_versions | 12/12 |
| new_records | 16/16 |
| rollback | 4/4 |
| interleaving | 32/32 |
| in_flight | 8/8 |
| migration_window | 40/40 |
| **Total** | **116/116** |

---

### Warehouse Attempt 1 — PASS 116/116 ✓ ([`work/bob-warehouse-candidate.json`](work/bob-warehouse-candidate.json))

Same structural fix, independently written for `stock_items` / `pick_bin` → `fulfillment_bin`. Submitted with `case=custom` and the full Warehouse contract on every call. Covers 3 seeds and 4 payloads including `Z'12` (embedded quote) and `東京-棚` (Unicode). 116/116 across all 7 categories.

---

### Untested boundaries (engine-stated)

- No concurrent transactions or lock-timing races
- No mid-statement crash/rollback modeling
- Drop-column final phase deferred until old workers retired
- Not every schedule × payload Cartesian product
- SQLite only — trigger and rename semantics differ on PostgreSQL/MySQL
- Not a production deployment approval