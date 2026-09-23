"""SQLite contract replays. No repository code or shell commands are executed."""
from __future__ import annotations

import hashlib
import itertools
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "examples"
ENGINE_VERSION = "0.2.2"
PAYLOADS = ["18 Marina Road", "", "O'Connell Street", "12 Àdéníran • 東京"]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_case(name="parcel"):
    if name not in ("parcel", "contacts"):
        raise ValueError("Unknown sample project")
    return json.loads((CASES / name / "contract.json").read_text(encoding="utf-8"))


def load_plan(case="parcel", name="rename"):
    if name not in ("rename", "backfill", "late_bridge", "bridge"):
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


def connection(contract, access_log=None):
    db = sqlite3.connect(":memory:", isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA recursive_triggers=ON')
    db.executescript(contract["schema"])
    db.executemany(contract["seed_sql"], contract["seed"])
    # The exercise permits schema and data edits only in this ephemeral database.
    # ATTACH, pragmas, extensions and transactions from user SQL are denied.
    denied = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA,
              sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT}

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
    return db


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


def replay(contract, plan, actions, payload, statements=None):
    access_log = []
    db = connection(contract, access_log)
    oracle = {row[0]: row[1] for row in contract["seed"]}
    selected_id = contract["seed"][0][0]
    trace, failure = [], None
    writes = 0
    checked_new_adapter = set()
    try:
        for index, action in enumerate(actions):
            event = {"step": index + 1, "action": action, "status": "pass"}
            try:
                if action == "migrate" or action.startswith("migration.statement."):
                    sql = plan["migration"] if action == "migrate" else statements[int(action.rsplit(".", 1)[-1])]
                    event["sql"] = sql
                    db.executescript(sql)
                    event["detail"] = "Migration statement executed against a fresh in-memory database."
                else:
                    version, operation = action.split(".")
                    adapter = contract["old"] if version == "old" else plan
                    event["sql"] = adapter[operation]
                    access_start = len(access_log)
                    if operation == "read":
                        rows = db.execute(adapter["read"]).fetchmany(100)
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
                            selected_id = max(oracle) + 1
                        event["params"] = {"id": selected_id, "value": value}
                        cursor = db.execute(adapter[operation], event["params"])
                        if cursor.rowcount != 1:
                            failure = {"kind": "write_not_acknowledged", "message": f"Expected 1 affected row, got {cursor.rowcount}."}
                        else:
                            oracle[selected_id] = value
                            event["detail"] = "Write acknowledged; independent ledger updated."
                    if not failure and version == "new" and operation in ("read", "write") and operation not in checked_new_adapter:
                        required = sqlite3.SQLITE_READ if operation == "read" else sqlite3.SQLITE_UPDATE
                        direct_access = any(
                            code == required and table == contract["table"] and column == contract["new_column"]
                            and (operation == "read" or source is None)
                            for code, table, column, source in access_log[access_start:])
                        if direct_access:
                            checked_new_adapter.add(operation)
                        else:
                            failure = {"kind": "adapter_contract", "message":
                                       f"New {operation} does not use the required {contract['new_column']} column."}
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
            event = {"step": len(trace) + 1, "action": "target.check", "status": "pass", "sql": target_sql}
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
        db.close()


def rehearse(case, plan):
    validate_plan(plan)
    statements = migration_statements(plan["migration"])
    contract = load_case(case)
    start = time.perf_counter()
    # Same-version green checks intentionally do not count as rollout coverage.
    baseline = []
    for payload in PAYLOADS:
        for operation in ("write", "insert"):
            baseline.append(replay(contract, plan, ["migrate", f"new.{operation}", "new.read"], payload))
    results = []
    for sid, title, category, actions in schedules():
        for pindex, payload in enumerate(PAYLOADS):
            result = replay(contract, plan, actions, payload)
            result.update(id=f"{sid}-{pindex}", title=title, category=category, payload=payload, actions=actions)
            results.append(result)
    # A migration script can succeed yet leave a write uncovered between its
    # autocommitted statements. Old workers must survive every such boundary.
    for boundary in range(len(statements) + 1):
        for operation in ("write", "insert"):
            actions = ([f"migration.statement.{i}" for i in range(boundary)] +
                       [f"old.{operation}"] +
                       [f"migration.statement.{i}" for i in range(boundary, len(statements))] +
                       ["new.read"])
            for pindex, payload in enumerate(PAYLOADS):
                result = replay(contract, plan, actions, payload, statements)
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
        "engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "case": case,
        "project": contract["project"], "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan, "plan_hash": digest(plan), "contract_hash": digest(contract),
        "suite_hash": digest({"schedules": schedules(), "payloads": PAYLOADS,
                              "migration_window_policy": "old update and insert after every SQLite statement boundary"}),
        "status": "pass" if not failures else "blocked",
        "passed": len(results) - len(failures), "failed": len(failures), "total": len(results),
        "baseline": {"passed": sum(r["passed"] for r in baseline), "total": len(baseline), "results": baseline},
        "categories": categories, "witness": witness, "results": results,
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        "scope": "SQLite sample contracts, target-column postconditions, bounded sequential interleavings and completed statement-boundary windows. Not a production deployment approval.",
        "limitations": ["No concurrent transactions, lock timing or network failures modeled.",
                        "No PostgreSQL, MySQL or ORM behavior claimed.",
                        "Writes between migration statements are modeled; mid-statement interruption and lock timing are not.",
                        "Contract/drop-column phase is deferred until old workers and rollback windows are retired.",
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
                        "The new reader and updater must use the fixed target column, which must preserve ledger values.",
                        "Cover old/new inserts as well as updates; keep the old column during the rollback window.",
                        "Propose a candidate with name, migration, read, write, insert. Call rehearse_candidate.",
                        "Report the exact coverage and limitations. Do not claim production safety."],
    }
