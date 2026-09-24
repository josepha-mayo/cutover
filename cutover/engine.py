"""SQLite contract replays. No repository code or shell commands are executed."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "examples"
ENGINE_VERSION = "0.3.13"
PAYLOADS = ["18 Marina Road", "", "O'Connell Street", "12 Àdéníran • 東京"]
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_case(name="parcel"):
    if name not in ("parcel", "contacts"):
        raise ValueError("Unknown sample project")
    return json.loads((CASES / name / "contract.json").read_text(encoding="utf-8"))


def validate_contract(contract):
    """Validate the bounded, single-table contract shape before SQL execution."""
    required = {"project", "summary", "old_column", "new_column", "table",
                "schema", "seed_sql", "seed", "old", "payloads"}
    if not isinstance(contract, dict) or set(contract) != required:
        raise ValueError("Contract must contain exactly the documented ten fields")
    for key in ("project", "summary", "schema", "seed_sql"):
        value = contract[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 12000:
            raise ValueError(f"Contract {key} must be a nonempty string of at most 12000 characters")
    for key in ("table", "old_column", "new_column"):
        value = contract[key]
        if not isinstance(value, str) or len(value) > 63 or not IDENTIFIER.fullmatch(value):
            raise ValueError(f"Contract {key} must be a safe SQL identifier of at most 63 characters")
    if contract["old_column"].casefold() == contract["new_column"].casefold():
        raise ValueError("Old and new columns must be distinct")
    payloads = contract["payloads"]
    if (not isinstance(payloads, list) or not 2 <= len(payloads) <= 8 or
            any(not isinstance(value, str) or len(value) > 1000 for value in payloads) or
            len(set(payloads)) != len(payloads)):
        raise ValueError("Contract payloads must contain 2 to 8 distinct strings of at most 1000 characters")
    old = contract["old"]
    if not isinstance(old, dict) or set(old) != {"read", "write", "insert"}:
        raise ValueError("Contract old adapter must contain read, write and insert SQL")
    for key, value in old.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 12000:
            raise ValueError(f"Contract old.{key} must be a nonempty string of at most 12000 characters")
    seed = contract["seed"]
    if not isinstance(seed, list) or not 1 <= len(seed) <= 16:
        raise ValueError("Contract seed must contain 1 to 16 records")
    ids = set()
    for row in seed:
        if (not isinstance(row, list) or len(row) != 2 or type(row[0]) is not int or
                not 1 <= row[0] <= 1_000_000 or not isinstance(row[1], str) or
                len(row[1]) > 1000 or row[0] in ids):
            raise ValueError("Seed records need unique positive integer IDs and string values")
        ids.add(row[0])
    return contract


def validate_old_contract_behavior(contract):
    """Prove the supplied old adapter works before attributing failures to a migration."""
    for payload_index, update_value in enumerate(contract["payloads"]):
        db = None
        try:
            db = connection(contract)
            schema_objects = db.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE type IN ('table', 'view', 'trigger') AND name NOT LIKE 'sqlite_%'").fetchall()
            if (len(schema_objects) != 1 or schema_objects[0]['type'] != 'table' or
                    schema_objects[0]['name'].casefold() != contract['table'].casefold()):
                raise ValueError("Initial schema must contain exactly the named table and no views or triggers")
            columns = {column[0].casefold() for column in db.execute(
                f'SELECT * FROM "{contract["table"]}" LIMIT 0').description}
            if ({'id', contract['old_column'].casefold()} - columns or
                    contract['new_column'].casefold() in columns):
                raise ValueError("Initial table must have id and old column, but not the new column")
            expected = {row[0]: row[1] for row in contract["seed"]}

            def check_read():
                rows = db.execute(contract["old"]["read"]).fetchmany(100)
                try:
                    actual = {row["id"]: row["value"] for row in rows}
                except (IndexError, KeyError) as exc:
                    raise ValueError("Old reader must return id and value columns") from exc
                if len(rows) != len(expected) or actual != expected:
                    raise ValueError("Old reader does not match the supplied seed and writes")

            check_read()
            for seed_id, _ in contract["seed"]:
                if db.execute(contract["old"]["write"], {"id": seed_id, "value": update_value}).rowcount != 1:
                    raise ValueError("Old updater must acknowledge exactly one row for every seed ID")
                expected[seed_id] = update_value
                check_read()
            new_id = max(expected) + 1
            if db.execute(contract["old"]["insert"], {"id": new_id, "value": update_value}).rowcount != 1:
                raise ValueError("Old inserter must acknowledge exactly one row")
            expected[new_id] = update_value
            check_read()
        except sqlite3.Error as exc:
            raise ValueError(f"Old contract SQL failed for payload index {payload_index}: {exc}") from exc
        finally:
            if db is not None:
                db.close()


def load_plan(case="parcel", name="rename"):
    if name not in ("rename", "backfill", "late_bridge", "bridge", "cross_record"):
        raise ValueError("Unknown reference plan")
    load_case(case)
    return json.loads((CASES / case / f"{name}.json").read_text(encoding="utf-8"))


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != {"name", "migration", "read", "write", "insert"}:
        raise ValueError("Plan must contain exactly name, migration, read, write, insert")
    for key, value in plan.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 12000:
            raise ValueError(f"{key} must be a nonempty string of at most 12000 characters")
    if len(plan["name"]) > 100:
        raise ValueError("Plan name must be at most 100 characters")


def has_sql(fragment):
    """Ignore comment-only and empty fragments when counting migration steps."""
    index = 0
    while index < len(fragment):
        if fragment[index].isspace() or fragment[index] == ";":
            index += 1
        elif fragment.startswith("--", index):
            newline = fragment.find("\n", index + 2)
            index = len(fragment) if newline < 0 else newline + 1
        elif fragment.startswith("/*", index):
            end = fragment.find("*/", index + 2)
            index = len(fragment) if end < 0 else end + 2
        else:
            return True
    return False


def migration_statements(script):
    """Split at SQLite-complete statements, including multi-statement triggers."""
    statements, pending = [], ""
    for char in script:
        pending += char
        if char == ";" and sqlite3.complete_statement(pending):
            if has_sql(pending):
                statements.append(pending.strip())
            pending = ""
    if has_sql(pending):
        if not sqlite3.complete_statement(pending + "\n;"):
            raise ValueError("Migration ends with an incomplete SQLite statement")
        statements.append(pending.strip())
    if not 1 <= len(statements) <= 32:
        raise ValueError("Migration must contain 1 to 32 SQLite statements")
    return statements


def connection(contract, access_log=None, database=":memory:", initialize=True):
    db = sqlite3.connect(database, uri=database != ":memory:", isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA recursive_triggers=ON')
    # The exercise permits schema and data edits only in this ephemeral database.
    # ATTACH, pragmas, extensions, transactions, and connection-local schema
    # objects and virtual-table modules from user SQL are denied. TEMP triggers
    # would not reach other workers; virtual tables are outside this bounded
    # ordinary-table contract and can invoke module-specific behavior.
    denied = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA,
              sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT,
              sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_VIEW,
              sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_CREATE_TEMP_INDEX,
              sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_VIEW,
              sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_INDEX,
              sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE}

    def authorize(action, a, b, database, source):
        if access_log is not None:
            access_log.append((action, a, b, source))
        if action in denied or (action == sqlite3.SQLITE_FUNCTION and str(b).lower() in ("load_extension", "writefile", "readfile")):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    db.set_authorizer(authorize)
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1000000)
    db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20000)
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    deadline = time.monotonic() + 0.15
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    if initialize:
        try:
            db.executescript(contract["schema"])
            db.executemany(contract["seed_sql"], contract["seed"])
        except Exception:
            db.close()
            raise
    return db


def writes_target_without_triggers(db, contract, statement, params):
    """Check that a new update or insert carries its value without triggers."""
    shadow = connection(contract)
    try:
        db.backup(shadow)
        names = [row[0] for row in shadow.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'")]
        for name in names:
            shadow.execute('DROP TRIGGER "' + name.replace('"', '""') + '"')
        cursor = shadow.execute(statement, params)
        if cursor.rowcount != 1:
            return False
        row = shadow.execute(
            f'SELECT "{contract["new_column"]}" FROM "{contract["table"]}" WHERE id = :id',
            {'id': params['id']}).fetchone()
        return row is not None and row[0] == params['value']
    except sqlite3.Error:
        return False
    finally:
        shadow.close()


def schedules():
    # Enumerate both reader versions after every possible pair of old/new writes.
    values = [("old_survives", "Old worker after migration", "compatibility", ["migrate", "old.read"])]
    for writer, reader in itertools.product(("old", "new"), repeat=2):
        category = "rollback" if writer == "new" and reader == "old" else "mixed_versions"
        values.append((f"{writer}_to_{reader}", f"{writer.title()} write → {reader} read", category,
                       ["migrate", f"{writer}.write", f"{reader}.read"]))
        values.append((f"{writer}_insert_{reader}", f"{writer.title()} insert → {reader} read", "new_records",
                       ["migrate", f"{writer}.insert", f"{reader}.read"]))
    for first, second, reader in itertools.product(("old", "new"), repeat=3):
        values.append((f"{first}_{second}_{reader}", f"{first.title()} write → {second} write → {reader} read",
                       "interleaving", ["migrate", f"{first}.write", f"{second}.write", f"{reader}.read"]))
    for reader in ("old", "new"):
        values.append((f"before_{reader}", f"Old write before migration → {reader} read", "in_flight",
                       ["old.write", "migrate", f"{reader}.read"]))
    return values


def replay(contract, plan, actions, payload, statements=None, seed_id=None, insert_id=None, write_ids=None):
    access_log = []
    # A persistent migration must be visible to workers on their own sessions.
    # The URI names one disposable in-memory database shared by three SQLite
    # connections; statements are still interleaved sequentially, not raced.
    database = f"file:cutover-{uuid.uuid4().hex}?mode=memory&cache=shared"
    db = old_db = new_db = None
    oracle = {row[0]: row[1] for row in contract["seed"]}
    selected_id = contract["seed"][0][0] if seed_id is None else seed_id
    trace, failure = [], None
    writes = 0
    updates = 0
    checked_new_adapter = set()
    try:
        db = connection(contract, database=database)
        old_db = connection(contract, database=database, initialize=False)
        new_db = connection(contract, access_log, database=database, initialize=False)
        for index, action in enumerate(actions):
            role = "migration" if action == "migrate" or action.startswith("migration.") else action.split(".")[0]
            event = {"step": index + 1, "action": action, "connection": role, "status": "pass"}
            try:
                if action == "migrate" or action.startswith("migration.statement."):
                    sql = plan["migration"] if action == "migrate" else statements[int(action.rsplit(".", 1)[-1])]
                    event["sql"] = sql
                    db.executescript(sql)
                    event["detail"] = "Migration statement executed against a fresh in-memory database."
                else:
                    version, operation = action.split(".")
                    worker_db = old_db if version == "old" else new_db
                    adapter = contract["old"] if version == "old" else plan
                    event["sql"] = adapter[operation]
                    access_start = len(access_log)
                    if operation == "read":
                        rows = worker_db.execute(adapter["read"]).fetchmany(100)
                        actual = {row["id"]: row["value"] for row in rows}
                        event.update(expected=dict(oracle), actual=actual)
                        if len(rows) != len(oracle) or actual != oracle:
                            failure = {"kind": "data_mismatch", "message": "A reader cannot see the latest acknowledged data.",
                                       "expected": dict(oracle), "actual": actual}
                        else:
                            event["detail"] = f"All {len(oracle)} records match the independent write ledger."
                    else:
                        writes += 1
                        value = payload if writes == 1 else payload + " [updated]"
                        if operation == "insert":
                            selected_id = max(oracle) + 1 if insert_id is None else insert_id
                        elif write_ids is not None:
                            selected_id = write_ids[updates]
                            updates += 1
                        event["params"] = {"id": selected_id, "value": value}
                        direct_target_write = (version != "new" or
                                               writes_target_without_triggers(
                                                   worker_db, contract, adapter[operation], event["params"]))
                        cursor = worker_db.execute(adapter[operation], event["params"])
                        if cursor.rowcount != 1:
                            failure = {"kind": "write_not_acknowledged", "message": f"Expected 1 affected row, got {cursor.rowcount}."}
                        elif not direct_target_write:
                            failure = {"kind": "adapter_contract", "message":
                                       f"New {operation} does not put its value in {contract['new_column']} without triggers."}
                        else:
                            oracle[selected_id] = value
                            event["detail"] = "Write acknowledged; independent ledger updated."
                    if not failure and version == "new" and operation in ("read", "write") and operation not in checked_new_adapter:
                        required = sqlite3.SQLITE_READ if operation == "read" else sqlite3.SQLITE_UPDATE
                        adapter_access = access_log[access_start:]
                        direct_access = any(
                            code == required and str(table).casefold() == contract["table"].casefold()
                            and str(column).casefold() == contract["new_column"].casefold()
                            and (operation == "read" or source is None)
                            for code, table, column, source in adapter_access)
                        old_column_read = operation == "read" and any(
                            code == sqlite3.SQLITE_READ and str(table).casefold() == contract["table"].casefold()
                            and str(column).casefold() == contract["old_column"].casefold()
                            for code, table, column, source in adapter_access)
                        if direct_access and not old_column_read:
                            checked_new_adapter.add(operation)
                        else:
                            failure = {"kind": "adapter_contract", "message":
                                       (f"New reader still accesses the old {contract['old_column']} column."
                                        if old_column_read else
                                        f"New {operation} does not use the required {contract['new_column']} column.")}
                if failure:
                    event.update(status="fail", detail=failure["message"])
            except (sqlite3.Error, KeyError, IndexError) as exc:
                failure = {"kind": "sql_error", "message": str(exc)}
                event.update(status="fail", detail=str(exc))
            trace.append(event)
            if failure:
                failure.update(action=action, step=index + 1)
                break
        if not failure:
            target_sql = (f'SELECT id, "{contract["new_column"]}" AS value '
                          f'FROM "{contract["table"]}" ORDER BY id')
            event = {"step": len(trace) + 1, "action": "target.check",
                     "connection": "migration", "status": "pass", "sql": target_sql}
            try:
                rows = db.execute(target_sql).fetchmany(100)
                actual = {row["id"]: row["value"] for row in rows}
                event.update(expected=dict(oracle), actual=actual)
                if len(rows) != len(oracle) or actual != oracle:
                    failure = {"kind": "target_mismatch", "message":
                               f"Required {contract['new_column']} column does not preserve acknowledged data.",
                               "expected": dict(oracle), "actual": actual}
                else:
                    event["detail"] = "Required target column matches the independent write ledger."
            except sqlite3.Error as exc:
                failure = {"kind": "target_contract", "message":
                           f"Required {contract['new_column']} column is unavailable: {exc}"}
            if failure:
                event.update(status="fail", detail=failure["message"])
                failure.update(action="target.check", step=event["step"])
            trace.append(event)
        return {"passed": failure is None, "trace": trace, "failure": failure}
    finally:
        for active in (new_db, old_db, db):
            if active is not None:
                active.close()


def replay_seed_variants(contract, plan, actions, payload, statements=None):
    """Exercise every record alone, rotating cross-record paths, and two insert IDs.

    A trigger can accidentally protect one fixed row ID. A passing probe must
    survive each relevant ID. Across the eight two-write schedules and at
    least two payloads, a rotating offset covers every ordered pair of up to
    sixteen seeded records without increasing the number of replays.
    """
    ids = ([row[0] for row in contract["seed"]]
           if any(action.endswith(".write") for action in actions)
           else [contract["seed"][0][0]])
    inserts = ([max(row[0] for row in contract["seed"]) + offset for offset in (1, 2)]
               if any(action.endswith(".insert") for action in actions) else [None])
    attempted_seeds = []
    attempted_inserts = []
    cross_paths = []
    first_pass = None
    for seed_id, insert_id in itertools.product(ids, inserts):
        result = replay(contract, plan, actions, payload, statements, seed_id, insert_id)
        if seed_id not in attempted_seeds:
            attempted_seeds.append(seed_id)
        result["seed_id"] = seed_id
        result["seed_ids_tested"] = list(attempted_seeds)
        if insert_id is not None:
            if insert_id not in attempted_inserts:
                attempted_inserts.append(insert_id)
            result["insert_id"] = insert_id
            result["insert_ids_tested"] = list(attempted_inserts)
        if not result["passed"]:
            return result
        if first_pass is None:
            first_pass = result
    write_count = sum(action.endswith(".write") for action in actions)
    if write_count == 2 and len(ids) > 1:
        two_write_actions = [candidate_actions for _, _, _, candidate_actions in schedules()
                             if sum(action.endswith(".write") for action in candidate_actions) == 2]
        schedule_index = two_write_actions.index(actions)
        payloads = contract.get("payloads", PAYLOADS)
        payload_index = payloads.index(payload)
        offset = 1 + (schedule_index * len(payloads) + payload_index) % (len(ids) - 1)
        # Each probe stays linear in seed count; offsets rotate across the
        # full suite so every ordered pair occurs in at least one probe.
        for index, first_id in enumerate(ids):
            second_id = ids[(index + offset) % len(ids)]
            path = [first_id, second_id]
            result = replay(contract, plan, actions, payload, statements,
                            seed_id=first_id, write_ids=path)
            cross_paths.append(path)
            result["seed_id"] = first_id
            result["seed_ids_tested"] = list(attempted_seeds)
            result["write_targets"] = path
            result["cross_record_paths_tested"] = list(cross_paths)
            if not result["passed"]:
                return result
    first_pass["seed_ids_tested"] = attempted_seeds
    if cross_paths:
        first_pass["write_targets"] = [ids[0], ids[0]]
        first_pass["cross_record_paths_tested"] = cross_paths
    if attempted_inserts:
        first_pass["insert_ids_tested"] = attempted_inserts
    return first_pass


def rehearse(case, plan, contract=None):
    start = time.perf_counter()
    validate_plan(plan)
    statements = migration_statements(plan["migration"])
    if contract is None:
        contract = load_case(case)
    else:
        validate_contract(contract)
        validate_old_contract_behavior(contract)
    payloads = contract.get("payloads", PAYLOADS)
    # Same-version green checks intentionally do not count as rollout coverage.
    baseline = []
    for payload in payloads:
        for operation in ("write", "insert"):
            baseline.append(replay_seed_variants(contract, plan, ["migrate", f"new.{operation}", "new.read"], payload))
    results = []
    for sid, title, category, actions in schedules():
        for pindex, payload in enumerate(payloads):
            result = replay_seed_variants(contract, plan, actions, payload)
            result.update(id=f"{sid}-{pindex}", title=title, category=category, payload=payload, actions=actions)
            results.append(result)
    # A migration script can succeed yet leave a write uncovered between its
    # autocommitted statements. Old workers must survive every such boundary.
    for boundary in range(len(statements) + 1):
        for operation in ("write", "insert"):
            actions = ([f"migration.statement.{i}" for i in range(boundary)] +
                       [f"old.{operation}", "old.read"] +
                       [f"migration.statement.{i}" for i in range(boundary, len(statements))] +
                       ["new.read"])
            for pindex, payload in enumerate(payloads):
                result = replay_seed_variants(contract, plan, actions, payload, statements)
                result.update(id=f"window_{operation}_after_{boundary}-{pindex}",
                              title=f"Old {operation} after migration step {boundary}/{len(statements)} → new read",
                              category="migration_window", payload=payload, actions=actions,
                              migration_boundary=boundary)
                results.append(result)
    failures = [r for r in results if not r["passed"]]
    witness = min(failures, key=lambda r: len(r["trace"])) if failures else None
    categories = []
    for category in dict.fromkeys(r["category"] for r in results):
        group = [r for r in results if r["category"] == category]
        categories.append({"id": category, "passed": sum(r["passed"] for r in group), "total": len(group)})
    return {
        "schema_version": 1, "engine_version": ENGINE_VERSION, "sqlite_version": sqlite3.sqlite_version,
        "engine_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "case": case,
        "project": contract["project"], "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan, "plan_hash": digest(plan), "contract_hash": digest(contract),
        "suite_hash": digest({"schedules": schedules(), "payloads": payloads,
                              "connection_policy": "separate migration, old and new SQLite connections to one disposable database",
                              "migration_window_policy": "old update or insert and old read after every SQLite statement boundary",
                              "write_seed_policy": "each seeded record for every update probe",
                              "cross_record_policy": "rotating directed offset; every ordered seed pair across the two-write suite",
                              "insert_id_policy": "two distinct IDs beyond the highest seed for every insert probe"}),
        "status": "pass" if not failures else "blocked",
        "passed": len(results) - len(failures), "failed": len(failures), "total": len(results),
        "baseline": {"passed": sum(r["passed"] for r in baseline), "total": len(baseline), "results": baseline},
        "categories": categories, "witness": witness, "results": results,
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        "scope": (("SQLite user-supplied contract" if case == "custom" else "SQLite sample contracts") +
                  ", separate migration/old/new connections to one disposable in-memory database, target-column postconditions, every seeded record for update probes, every ordered seed pair across rotating two-write probes, two new record IDs for insert probes, bounded sequential interleavings and old-worker read checks at every completed statement boundary. Not a production deployment approval."),
        "limitations": ["No concurrent transactions, lock timing or network failures modeled.",
                        "No PostgreSQL, MySQL or ORM behavior claimed.",
                        "Writes between migration statements are modeled; mid-statement interruption and lock timing are not.",
                        "Contract/drop-column phase is deferred until old workers and rollback windows are retired.",
                        "Each ordered seed pair is covered somewhere in a passing full suite, but not under every schedule and payload combination.",
                        "Passing covers only the fixed adapters, seed data and reported schedules."],
        "bob": {"verified": False, "note": "This execution is deterministic. Bob session evidence must be captured separately."},
    }


def repair_brief(report):
    witness = report.get("witness")
    return {
        "task": "Repair this rollout while preserving old workers and rollback reads. Use executable evidence, then rerun the full fixed suite.",
        "case": report["case"], "plan_hash": report["plan_hash"], "contract_hash": report["contract_hash"],
        "candidate": report["plan"], "shortest_observed_witness": witness,
        "constraints": ["Do not edit the engine, contract, test schedules, seed data, or oracle to make a plan pass.",
                        "Preserve every record and the latest acknowledged write across both versions.",
                        "The new reader must not read the old column. New updates and inserts must carry their values into the fixed target without triggers; explicit dual-writes are valid.",
                        "The target column must preserve every acknowledged ledger value.",
                        "Old readers must remain correct between completed migration statements, not only after migration finishes.",
                        "Cover old/new inserts as well as updates; keep the old column during the rollback window.",
                        "Propose a candidate with name, migration, read, write, insert. Call rehearse_candidate.",
                        "Report the exact coverage and limitations. Do not claim production safety."],
    }
